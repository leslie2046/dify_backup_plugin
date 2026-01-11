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


class ExportAppTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Export a specific Dify application DSL.
        """
        # Get parameters
        app_selector_value = tool_parameters.get("app_identifier")
        version_type = tool_parameters.get("version_type", "draft")
        
        if not app_selector_value:
            yield self.create_text_message("Error: app_identifier is required")
            return
        
        # 提取 app_id
        if isinstance(app_selector_value, dict):
            app_id = app_selector_value.get("app_id", "")
        else:
            app_id = str(app_selector_value).strip()
        
        if not app_id:
            yield self.create_text_message("Error: Invalid app_identifier")
            return

        # Get credentials
        base_url = self.runtime.credentials.get("dify_base_url", "")
        email = self.runtime.credentials.get("email", "")
        password = self.runtime.credentials.get("password", "")

        if not base_url or not email or not password:
            yield self.create_text_message("Error: Provider credentials not configured")
            return

        try:
            # 初始化 Client (会自动登录)
            client = DifyClient(base_url, email, password)
            
            # 获取应用信息（用于名字）
            app_info = client.get_app_info(app_id)
            if not app_info:
                yield self.create_text_message(f"Error: App {app_id} not found")
                return
            
            app_name = app_info.get("name", "Unknown")
            app_mode = app_info.get("mode", "Unknown")
            
            # 获取导出版本列表
            versions = client.get_versions_to_export(app_id, app_name, version_type)
            
            exported_files = []
            exported_count = 0
            
            for ver in versions:
                # 导出 DSL
                dsl_content = client.export_dsl(app_id, ver["id"])
                
                if dsl_content:
                    filename = client.generate_filename(app_name, ver["display_name"])
                    
                    # 保持原始 YAML 格式
                    dsl_yaml = dsl_content if isinstance(dsl_content, str) else yaml.dump(dsl_content, allow_unicode=True, default_flow_style=False, sort_keys=False)
                    
                    json_item = {
                        "id": app_id,
                        "name": app_name,
                        "mode": app_mode,
                        "version": ver["version"],
                        "filename": filename,
                        "dsl": dsl_yaml
                    }
                    exported_files.append(json_item)
                    exported_count += 1
                    
                    # 实时返回 JSON
                    yield self.create_json_message(json_item)
                    logger.info(f"成功导出: {filename}")
                else:
                    logger.warning(f"Failed to export content for {ver['display_name']}")

            # 返回摘要
            if exported_count > 0:
                summary = f"✅ 成功导出应用: {app_name}\n"
                summary += f"数量: {exported_count} 个版本\n"
                yield self.create_text_message(summary)
            else:
                yield self.create_text_message(f"未能导出任何版本 (Type: {version_type})")

        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            logger.error(error_msg)
            yield self.create_text_message(error_msg)
