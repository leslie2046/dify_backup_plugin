from collections.abc import Generator
from typing import Any
import logging
import yaml

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.config.logger_format import plugin_logger_handler
from provider.dify_backup import DifyClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class ExportAllAppsTool(Tool):
    """
    Tool for exporting all Dify applications DSL configurations
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Export all applications DSL configurations using DifyClient
        """
        version_type = tool_parameters.get("version_type", "draft")

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
            all_apps = client.get_all_apps(limit=100)
            logger.info(f"获取到 {len(all_apps)} 个应用")

            successful_app_ids = set()
            exported_dsl_count = 0
            failed_apps_info = []

            for app in all_apps:
                app_id = app.get("id")
                app_name = app.get("name")
                app_mode = app.get("mode", "unknown")
                
                try:
                    # 获取该应用要导出的版本列表
                    versions = client.get_versions_to_export(app_id, app_name, version_type)
                    
                    if not versions:
                        # 如果没找到版本，跳过
                        continue

                    has_success_version = False
                    for ver in versions:
                        dsl_content = client.export_dsl(app_id, ver["id"])
                        
                        if dsl_content:
                            filename = client.generate_filename(app_name, ver["display_name"])
                            
                            # 解析 YAML
                            try:
                                dsl_dict = yaml.safe_load(dsl_content) if isinstance(dsl_content, str) else dsl_content
                            except:
                                dsl_dict = dsl_content

                            json_item = {
                                "id": app_id,
                                "name": app_name,
                                "mode": app_mode,
                                "version": ver["version"],
                                "filename": filename,
                                "dsl": dsl_dict
                            }
                            
                            # 实时返回 JSON
                            yield self.create_json_message(json_item)
                            
                            exported_dsl_count += 1
                            has_success_version = True
                            logger.info(f"[{app_name}] 成功导出版本: {ver['version']}")
                        else:
                            logger.warning(f"[{app_name}] 导出失败: {ver['display_name']}")
                    
                    if has_success_version:
                        successful_app_ids.add(app_id)

                except Exception as e:
                    logger.error(f"处理应用 {app_name} ({app_id}) 时出错: {str(e)}")
                    failed_apps_info.append(f"{app_name}: {str(e)}")

            # 返回摘要信息
            summary_text = f"✅ 批量导出完成\n\n"
            summary_text += f"成功应用数: {len(successful_app_ids)}\n"
            summary_text += f"总文件数: {exported_dsl_count}\n"
            
            if failed_apps_info:
                summary_text += f"\n❌ 部分应用处理失败:\n"
                for err in failed_apps_info[:10]:
                    summary_text += f"- {err}\n"
                if len(failed_apps_info) > 10:
                    summary_text += f"... (共 {len(failed_apps_info)} 个错误)"
            
            yield self.create_text_message(summary_text)

        except Exception as e:
            error_msg = f"Export All Apps failed: {str(e)}"
            logger.error(error_msg)
            yield self.create_text_message(error_msg)
