from collections.abc import Generator
from typing import Any
import json
import base64

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.config.logger_format import plugin_logger_handler
import requests
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)

class ExportAllAppsTool(Tool):
    """
    Tool for exporting all Dify applications DSL configurations via HTTP API
    Uses provider credentials (email/password) for authentication
    Based on: https://github.com/sattosan/dify-apps-dsl-exporter
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Export all applications DSL configurations using Dify Console API
        
        Args:
            tool_parameters: Tool parameters including:
                - app_mode: Filter by app type
                - include_secret: Whether to include secrets
        """
        # Get parameters
        app_mode = tool_parameters.get("app_mode", "all")
        include_secret = tool_parameters.get("include_secret", False)

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
            
            logger.info(f"开始导出流程 - 准备登录到: {base_url}")
            logger.info(f"使用邮箱: {email}")
            logger.info(f"app_mode: {app_mode}, include_secret: {include_secret}")

            # Login to get access token
            login_url = f"{base_url}/console/api/login"
            logger.info(f"发送登录请求到: {login_url}")
            
            login_response = requests.post(
                login_url,
                json={"email": email, "password": password_base64, "remember_me": True},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            
            logger.info(f"登录响应状态码: {login_response.status_code}")

            if login_response.status_code != 200:
                logger.error(f"登录失败 - 状态码: {login_response.status_code}")
                yield self.create_text_message(
                    f"Error logging in: {login_response.status_code} - {login_response.text}"
                )
                return

            login_data = login_response.json()
            logger.info(f"登录响应数据: {json.dumps(login_data, indent=2, ensure_ascii=False)}")
            result = login_data.get("result")
            logger.info(f"登录结果: {result}")
            
            if result != "success":
                logger.error(f"登录失败 - result字段值: {result}")
                yield self.create_text_message(f"Login failed: {result or 'Unknown error'}")
                return

            # Access token is in data["data"]["access_token"]
            logger.info("开始提取 access_token...")
            token_data = login_data.get("data", {})
            logger.info(f"login_data['data'] 的值: {token_data}")
            logger.info(f"login_data['data'] 的类型: {type(token_data)}")
            
            access_token = token_data.get("access_token")
            logger.info(f"从 token_data 提取到的 access_token: {access_token}")
            
            if not access_token:
                logger.error("未能从登录响应中获取 access_token")
                logger.error(f"完整登录数据: {json.dumps(login_data, indent=2, ensure_ascii=False)}")
                logger.error(f"响应数据的所有键: {list(login_data.keys())}")
                yield self.create_text_message("Error: No access token received from login")
                return
            
            logger.info(f"成功获取 access_token (前10个字符): {access_token[:10]}...")

            # Prepare headers with Bearer token
            logger.info("准备请求头...")
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Fetch all applications with pagination
            logger.info("开始获取应用列表...")
            all_apps = []
            page = 1
            limit = 100

            while True:
                # Call Dify API to get apps list
                params = {"page": page, "limit": limit}
                if app_mode != "all":
                    params["mode"] = app_mode
                
                response = requests.get(
                    f"{base_url}/console/api/apps",
                    headers=headers,
                    params=params,
                    timeout=30,
                )
                
                logger.info(f"获取应用列表响应状态码: {response.status_code}")

                if response.status_code != 200:
                    yield self.create_text_message(
                        f"Error fetching apps: {response.status_code} - {response.text}"
                    )
                    return

                data = response.json()
                apps = data.get("data", [])
                logger.info(f"第{page}页获取到 {len(apps)} 个应用")
                all_apps.extend(apps)

                # Check if there are more pages
                has_more = data.get("has_more", False)
                logger.info(f"has_more: {has_more}")
                if not has_more:
                    break

                page += 1

            logger.info(f"总共获取到 {len(all_apps)} 个应用")
            
            # Export each application
            exported_apps = []

            for app in all_apps:
                try:
                    app_id = app.get("id")
                    app_name = app.get("name")
                    app_mode_type = app.get("mode")

                    # Call export API
                    export_params = {"include_secret": str(include_secret).lower()}
                    
                    export_response = requests.get(
                        f"{base_url}/console/api/apps/{app_id}/export",
                        headers=headers,
                        params=export_params,
                        timeout=60,
                    )

                    if export_response.status_code == 200:
                        export_data = export_response.json()
                        dsl_content = export_data.get("data", "")
                        logger.info(f"成功导出应用: {app_name} (ID: {app_id})")

                        exported_apps.append({
                            "id": app_id,
                            "name": app_name,
                            "mode": app_mode_type,
                            "dsl": dsl_content,
                        })
                    else:
                        logger.warning(f"导出应用失败: {app_name} (ID: {app_id}), 状态码: {export_response.status_code}")

                except Exception as e:
                    # Skip failed apps, continue with others
                    logger.warning(f"导出应用异常: {e}")
                    continue

            # Return JSON with all exported apps
            logger.info(f"导出完成，总计 {len(exported_apps)} 个应用")
            result = {
                "total": len(exported_apps),
                "apps": exported_apps,
            }

            yield self.create_json_message(result)

        except requests.exceptions.RequestException as e:
            yield self.create_text_message(f"Network error: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"Error during export: {str(e)}")
