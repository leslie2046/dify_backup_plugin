from collections.abc import Generator
from typing import Any
import logging
import csv
import io

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.config.logger_format import plugin_logger_handler
from provider.dify_backup import DifyClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class ExportAllAnnotationsTool(Tool):
    """
    Tool for exporting annotations for all Dify applications
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Export annotations for all applications using DifyClient
        """
        base_url = self.runtime.credentials.get("dify_base_url", "")
        email = self.runtime.credentials.get("email", "")
        password = self.runtime.credentials.get("password", "")

        if not base_url or not email or not password:
            yield self.create_text_message("Error: Provider credentials not configured")
            return

        try:
            # 初始化 Client (会自动登录)
            client = DifyClient(base_url, email, password)

            # 获取所有应用
            logger.info("开始获取应用列表...")
            all_apps = client.get_all_apps(limit=100, mode="all")
            logger.info(f"获取到 {len(all_apps)} 个应用")

            successful_app_count = 0
            total_annotations_count = 0
            failed_apps_info = []

            for app in all_apps:
                app_id = app.get("id")
                app_name = app.get("name")
                
                try:
                    # 获取该应用的标注
                    annotations = client.get_all_annotations(app_id)
                    
                    # 标注数量为0的无需yield
                    if not annotations:
                        logger.info(f"[{app_name}] 无标注，跳过")
                        continue

                    # 生成 CSV 内容
                    csv_content = self._generate_csv_content(annotations)
                    
                    # 生成文件名：应用-annotations.csv
                    # 保留中文字符和常用字符
                    safe_app_name = "".join(c for c in app_name if c.isalnum() or c in (' ', '-', '_') or '\u4e00' <= c <= '\u9fff').strip().replace(' ', '_')
                    filename = f"{safe_app_name}-annotations.csv"
                    
                    # 返回 JSON 对象
                    json_item = {
                        "name": app_name,
                        "filename": filename,
                        "content": csv_content
                    }
                    
                    yield self.create_json_message(json_item)
                    
                    successful_app_count += 1
                    total_annotations_count += len(annotations)
                    logger.info(f"[{app_name}] 成功导出 {len(annotations)} 条标注")

                except Exception as e:
                    logger.error(f"处理应用 {app_name} ({app_id}) 时出错: {str(e)}")
                    failed_apps_info.append(f"{app_name}: {str(e)}")

            # 返回摘要信息
            summary_text = f"✅ 批量导出标注完成\n\n"
            summary_text += f"成功应用数: {successful_app_count}\n"
            summary_text += f"总标注数: {total_annotations_count}\n"
            
            if failed_apps_info:
                summary_text += f"\n❌ 部分应用处理失败:\n"
                for err in failed_apps_info[:10]:
                    summary_text += f"- {err}\n"
                if len(failed_apps_info) > 10:
                    summary_text += f"... (共 {len(failed_apps_info)} 个错误)"
            
            yield self.create_text_message(summary_text)

        except Exception as e:
            error_msg = f"Export All Annotations failed: {str(e)}"
            logger.error(error_msg)
            yield self.create_text_message(error_msg)

    def _generate_csv_content(self, annotations: list) -> str:
        """
        生成 CSV 内容
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # 写入表头
        writer.writerow(['question', 'answer'])
        
        # 写入数据
        for annotation in annotations:
            question = annotation.get('question', '')
            answer = annotation.get('answer', '') or annotation.get('content', '')
            
            # CSV 注入防护：如果以特殊字符开头，添加单引号前缀
            question = self._sanitize_csv_value(question)
            answer = self._sanitize_csv_value(answer)
            
            writer.writerow([question, answer])
        
        return output.getvalue()

    def _sanitize_csv_value(self, value: str) -> str:
        """
        CSV 注入防护
        """
        if value and isinstance(value, str):
            # 如果以这些字符开头，可能会被解释为公式
            dangerous_chars = ('=', '+', '-', '@', '\t', '\r', '\n')
            if value.startswith(dangerous_chars):
                return "'" + value
        return value
