from collections.abc import Generator
from typing import Any
import uuid
import base64
import json
import logging

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.config.logger_format import plugin_logger_handler
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class ExportAppTool(Tool):
    """
    Tool for exporting a single Dify application DSL configuration via HTTP API
    Uses provider credentials (email/password) for authentication
    Based on: https://github.com/sattosan/dify-apps-dsl-exporter
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Export a single application DSL configuration using Dify Console API
        
        Args:
            tool_parameters: Tool parameters including:
                - app_identifier: App ID (UUID) from app-selector
                - version_type: Version type to export
        """
        # Get parameters
        app_selector_value = tool_parameters.get("app_identifier")
        version_type = tool_parameters.get("version_type", "draft")  # 版本类型参数
        
        # 固定不包含敏感信息（安全考虑）
        include_secret = False

        # app-selector 返回的是字典格式: {"app_id": "xxx"}
        if not app_selector_value:
            yield self.create_text_message("Error: app_identifier is required")
            return
        
        # 从 app-selector 返回值中提取 app_id
        if isinstance(app_selector_value, dict):
            app_id = app_selector_value.get("app_id", "")
        else:
            # 兼容处理：如果直接是字符串（旧版本或测试）
            app_id = str(app_selector_value).strip()
        
        if not app_id:
            yield self.create_text_message("Error: Invalid app_identifier")
            return

        # Get provider credentials
        base_url = self.runtime.credentials.get("dify_base_url", "").rstrip("/")
        email = self.runtime.credentials.get("email", "")
        password = self.runtime.credentials.get("password", "")

        if not base_url or not email or not password:
            yield self.create_text_message("Error: Provider credentials not configured")
            return

        try:
            # Encode password to base64 as required by Dify's FieldEncryption.decrypt_field()
            password_base64 = base64.b64encode(password.encode("utf-8")).decode("utf-8")

            # 使用 Session 来自动管理 cookies (包括 CSRF token)
            session = requests.Session()
            
            # Login to get access token
            login_url = f"{base_url}/console/api/login"
            login_response = session.post(
                login_url,
                json={"email": email, "password": password_base64, "remember_me": True},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if login_response.status_code != 200:
                yield self.create_text_message(
                    f"Error logging in: {login_response.status_code} - {login_response.text}"
                )
                return

            login_data = login_response.json()
            if login_data.get("result") != "success":
                yield self.create_text_message(f"Login failed: {login_data.get('result', 'Unknown error')}")
                return

            # Access token extraction (支持多种方式)
            access_token = None
            
            # Method 1: Check data["data"]["access_token"]
            token_data = login_data.get("data", {})
            if isinstance(token_data, dict):
                access_token = token_data.get("access_token")
            
            # Method 2: Check data["access_token"]
            if not access_token:
                access_token = login_data.get("access_token")
            
            # Method 3: Check cookies (支持多种可能的cookie名称)
            if not access_token:
                logger.info("尝试从 cookies 中获取 token...")
                cookie_names = [
                    "__Host-access_token",  # 带__Host-前缀的安全cookie
                    "access_token",          # 标准名称
                    "console_token",         # 旧版名称
                ]
                for cookie_name in cookie_names:
                    access_token = session.cookies.get(cookie_name)
                    if access_token:
                        logger.info(f"从 cookies['{cookie_name}'] 获取到 token")
                        break
            
            if not access_token:
                logger.error(f"未能获取 access_token. 响应: {json.dumps(login_data)}")
                yield self.create_text_message("Error: No access token received from login")
                return

            # 提取 CSRF token 从 cookies
            csrf_token = session.cookies.get("__Host-csrf_token") or session.cookies.get("csrf_token")
            if csrf_token:
                logger.info(f"成功获取 csrf_token")
            else:
                logger.warning("未找到 csrf_token")

            # Prepare headers with Bearer token and CSRF token
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            # 添加 CSRF token 到 header（Dify 要求）
            if csrf_token:
                headers["X-CSRF-Token"] = csrf_token
                logger.info("已添加 X-CSRF-Token 到请求头")

            # 确定要导出的版本列表
            versions_to_export = []
            if version_type == "all":
                versions_to_export = ["draft", "published"]
            else:
                versions_to_export = [version_type]
            
            # 获取应用信息（用于文件名）
            app_info_response = session.get(
                f"{base_url}/console/api/apps/{app_id}",
                headers=headers,
                timeout=30,
            )

            app_name = "Unknown"
            app_mode = "Unknown"
            if app_info_response.status_code == 200:
                app_info = app_info_response.json()
                app_name = app_info.get("name", "Unknown")
                app_mode = app_info.get("mode", "Unknown")
            
            # 循环导出每个版本
            exported_versions = []
            failed_versions = []
            
            for current_version in versions_to_export:
                try:
                    # Export the app
                    export_params = {"include_secret": str(include_secret).lower()}
                    
                    # 如果选择published版本，需要获取所有已发布的workflows
                    workflow_ids = []
                    if current_version == "published":
                        # 调用 workflows API 获取所有已发布版本
                        workflows_response = session.get(
                            f"{base_url}/console/api/apps/{app_id}/workflows",
                            headers=headers,
                            params={"page": 1, "limit": 100},  # 假设不会超过100个版本
                            timeout=30,
                        )
                        
                        if workflows_response.status_code == 200:
                            workflows_data = workflows_response.json()
                            # 过滤掉 draft 版本，获取所有已发布版本
                            for workflow in workflows_data.get("items", []):
                                if workflow.get("version") != "draft":
                                    wf_id = workflow.get("id")
                                    wf_version = workflow.get("version", "unknown")
                                    wf_marked_name = workflow.get("marked_name", "")
                                    wf_created_at = workflow.get("created_at")
                                    
                                    # 生成 display_name
                                    if wf_marked_name:
                                        display_name = wf_marked_name
                                    else:
                                        # 未命名版本：使用时间戳
                                        if wf_created_at:
                                            # 格式化时间戳为 YYYYMMDDHHmm
                                            from datetime import datetime
                                            try:
                                                if isinstance(wf_created_at, int):
                                                    dt = datetime.fromtimestamp(wf_created_at)
                                                else:
                                                    dt = datetime.fromisoformat(str(wf_created_at).replace('Z', '+00:00'))
                                                timestamp_str = dt.strftime("%Y%m%d%H%M")
                                                display_name = f"未命名-{timestamp_str}"
                                            except:
                                                display_name = f"未命名-{wf_version}"
                                        else:
                                            display_name = f"未命名-{wf_version}"
                                    
                                    workflow_ids.append({
                                        "id": wf_id,
                                        "version": wf_version,
                                        "marked_name": wf_marked_name,
                                        "display_name": display_name
                                    })
                            
                            logger.info(f"找到 {len(workflow_ids)} 个已发布版本")
                            
                            if not workflow_ids:
                                logger.warning(f"应用没有已发布版本")
                                failed_versions.append("published")
                                if version_type == "published":
                                    yield self.create_text_message("Error: No published version found for this app")
                                    return
                                continue
                        else:
                            logger.error(f"获取workflows列表失败: {workflows_response.status_code}")
                            failed_versions.append("published")
                            if version_type == "published":
                                yield self.create_text_message(f"Error: Failed to get workflows list: {workflows_response.status_code}")
                                return
                            continue
                    else:
                        # draft 版本，不需要 workflow_id
                        workflow_ids.append({"id": None, "version": "draft", "marked_name": ""})
                    
                    # 导出每个版本
                    for wf_info in workflow_ids:
                        workflow_id = wf_info["id"]
                        wf_version = wf_info["version"]
                        wf_display_name = wf_info.get("display_name", wf_info.get("marked_name", ""))
                        
                        export_params_copy = export_params.copy()
                        if workflow_id:
                            export_params_copy["workflow_id"] = workflow_id

                        export_response = session.get(
                            f"{base_url}/console/api/apps/{app_id}/export",
                            headers=headers,
                            params=export_params_copy,
                            timeout=60,
                        )

                        if export_response.status_code != 200:
                            logger.error(f"导出 {wf_version} 版本失败: {export_response.status_code}")
                            failed_versions.append(f"{current_version}-{wf_version}")
                            if version_type != "all":
                                yield self.create_text_message(
                                    f"Error exporting app: {export_response.status_code} - {export_response.text}"
                                )
                                return
                            continue

                        export_data = export_response.json()
                        dsl_content = export_data.get("data", "")

                        if dsl_content:
                            # 生成文件名
                            safe_app_name = "".join(c for c in app_name if c.isalnum() or c in (' ', '-', '_')).strip()
                            safe_app_name = safe_app_name.replace(' ', '_')
                            
                            # 文件名格式：应用名-版本.yml
                            if current_version == "published":
                                # 已发布版本：使用 display_name（已经处理好了命名）
                                safe_display_name = "".join(c for c in wf_display_name if c.isalnum() or c in (' ', '-', '_')).strip()
                                safe_display_name = safe_display_name.replace(' ', '_')
                                filename = f"{safe_app_name}-{safe_display_name}.yml"
                            else:
                                # draft 版本
                                filename = f"{safe_app_name}-draft.yml"
                            
                            # 创建文件消息
                            yield self.create_blob_message(
                                blob=dsl_content.encode('utf-8') if isinstance(dsl_content, str) else dsl_content,
                                meta={
                                    "mime_type": "text/yaml",
                                    "filename": filename
                                }
                            )
                            
                            # 返回 JSON 消息（包含 DSL 内容）
                            try:
                                import yaml
                                dsl_dict = yaml.safe_load(dsl_content) if isinstance(dsl_content, str) else dsl_content
                                yield self.create_json_message(dsl_dict)
                            except:
                                yield self.create_json_message({
                                    "id": app_id,
                                    "name": app_name,
                                    "mode": app_mode,
                                    "version": wf_version,
                                    "dsl": dsl_content
                                })
                            
                            exported_versions.append(wf_version)
                            logger.info(f"成功导出 {wf_version} 版本")
                        else:
                            failed_versions.append(f"{current_version}-{wf_version}")
                        
                except Exception as e:
                    logger.error(f"导出{current_version}版本异常: {str(e)}")
                    failed_versions.append(current_version)
                    if version_type != "all":
                        raise
            
            # 返回摘要信息
            if exported_versions:
                summary = f"✅ 成功导出应用\n\n"
                summary += f"应用名称: {app_name}\n"
                summary += f"应用ID: {app_id}\n"
                summary += f"应用模式: {app_mode}\n"
                summary += f"导出版本: {', '.join(exported_versions)}\n"
                if failed_versions:
                    summary += f"失败版本: {', '.join(failed_versions)}\n"
                summary += f"导出文件数: {len(exported_versions)}"
                
                yield self.create_text_message(summary)
            else:
                yield self.create_text_message("Error: No version was exported successfully")

        except requests.exceptions.RequestException as e:
            yield self.create_text_message(f"Network error: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"Error during export: {str(e)}")



