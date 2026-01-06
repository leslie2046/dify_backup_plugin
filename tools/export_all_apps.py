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
        version_type = tool_parameters.get("version_type", "draft")  # 版本类型参数
        
        # 固定不包含敏感信息（安全考虑）
        include_secret = False

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

            # 使用 Session 来自动管理 cookies (包括 CSRF token)
            session = requests.Session()
            
            # Login to get access token
            login_url = f"{base_url}/console/api/login"
            logger.info(f"发送登录请求到: {login_url}")
            
            login_response = session.post(
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

            # Access token is in data["data"]["access_token"] or cookies
            logger.info("开始提取 access_token...")
            access_token = None
            
            # Method 1: Check data["data"]["access_token"]
            token_data = login_data.get("data", {})
            logger.info(f"login_data['data'] 的值: {token_data}")
            logger.info(f"login_data['data'] 的类型: {type(token_data)}")
            
            if isinstance(token_data, dict):
                access_token = token_data.get("access_token")
                logger.info(f"从 login_data['data']['access_token'] 提取到的 token: {access_token}")
            
            # Method 2: Check data["access_token"]
            if not access_token:
                access_token = login_data.get("access_token")
                logger.info(f"从 login_data['access_token'] 提取到的 token: {access_token}")
            
            # Method 3: Check cookies (支持多种可能的cookie名称)
            if not access_token:
                logger.info("尝试从 cookies 中获取 token...")
                # 尝试多种可能的cookie名称
                cookie_names = [
                    "__Host-access_token",  # 带__Host-前缀的安全cookie
                    "access_token",          # 标准名称
                    "console_token",         # 旧版名称
                ]
                for cookie_name in cookie_names:
                    access_token = session.cookies.get(cookie_name)
                    if access_token:
                        logger.info(f"从 cookies['{cookie_name}'] 获取到的 token: {access_token[:20]}...")
                        break
                    else:
                        logger.info(f"cookies['{cookie_name}'] 不存在")
                
                if not access_token:
                    logger.info(f"cookies 中所有可用的键: {list(session.cookies.keys())}")
            
            if not access_token:
                logger.error("未能从登录响应中获取 access_token")
                logger.error(f"完整登录数据: {json.dumps(login_data, indent=2, ensure_ascii=False)}")
                logger.error(f"响应数据的所有键: {list(login_data.keys())}")
                logger.error(f"cookies: {session.cookies.get_dict()}")
                yield self.create_text_message("Error: No access token received from login")
                return

            
            logger.info(f"成功获取 access_token (前10个字符): {access_token[:10]}...")
            
            # 提取 CSRF token 从 cookies
            csrf_token = session.cookies.get("__Host-csrf_token") or session.cookies.get("csrf_token")
            logger.info(f"Session cookies: {list(session.cookies.keys())}")
            if csrf_token:
                logger.info(f"成功获取 csrf_token (前10个字符): {csrf_token[:10]}...")
            else:
                logger.warning("未找到 csrf_token")

            # Prepare headers with Bearer token and CSRF token
            logger.info("准备请求头...")
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            # 添加 CSRF token 到 header（Dify 要求）
            if csrf_token:
                headers["X-CSRF-Token"] = csrf_token
                logger.info("已添加 X-CSRF-Token 到请求头")

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
                
                response = session.get(
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
            exported_dsl_count = 0  # DSL文件计数
            successful_app_ids = set() # 成功导出的应用ID集合
            failed_apps = []
            exported_apps = []  # 用于存储成功导出的应用信息
            
            # 确定要导出的版本列表
            versions_to_export = []
            if version_type == "all":
                versions_to_export = ["draft", "published"]
            else:
                versions_to_export = [version_type]

            for app in all_apps:
                app_id = app.get("id")
                app_name = app.get("name")
                app_mode_type = app.get("mode")
                
                # 循环导出每个版本
                for current_version in versions_to_export:
                    # 获取该版本的所有 workflows
                    workflow_ids = []
                    
                    if current_version == "published":
                        # 调用 workflows API 获取所有已发布版本
                        workflows_response = session.get(
                            f"{base_url}/console/api/apps/{app_id}/workflows",
                            headers=headers,
                            params={"page": 1, "limit": 100},
                            timeout=30,
                        )
                        
                        if workflows_response.status_code == 200:
                            workflows_data = workflows_response.json()
                            # 过滤掉 draft 版本
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
                            
                            logger.info(f"{app_name}: 找到 {len(workflow_ids)} 个已发布版本")
                            
                            if not workflow_ids:
                                logger.warning(f"{app_name}: 应用没有已发布版本")
                                if version_type == "published":
                                    failed_apps.append(f"{app_name} (没有已发布版本)")
                                continue
                        else:
                            logger.warning(f"{app_name}: 获取workflows列表失败: {workflows_response.status_code}")
                            if version_type == "published":
                                failed_apps.append(f"{app_name} (获取workflows失败)")
                            continue
                    else:
                        # draft 版本
                        workflow_ids.append({"id": None, "version": "draft", "marked_name": ""})
                    
                    # 导出每个 workflow 版本
                    for wf_info in workflow_ids:
                        try:
                            workflow_id = wf_info["id"]
                            wf_version = wf_info["version"]
                            wf_display_name = wf_info.get("display_name", wf_info.get("marked_name", ""))
                            
                            export_params = {"include_secret": str(include_secret).lower()}
                            if workflow_id:
                                export_params["workflow_id"] = workflow_id
                        
                            export_response = session.get(
                                f"{base_url}/console/api/apps/{app_id}/export",
                                headers=headers,
                                params=export_params,
                                timeout=60,
                            )

                            if export_response.status_code == 200:
                                export_data = export_response.json()
                                dsl_content = export_data.get("data", "")
                                logger.info(f"成功导出应用: {app_name} (ID: {app_id}, 版本: {wf_version})")
                                
                                if dsl_content:
                                    # 生成文件名
                                    safe_app_name = "".join(c for c in app_name if c.isalnum() or c in (' ', '-', '_')).strip()
                                    safe_app_name = safe_app_name.replace(' ', '_')
                                    
                                    # 文件名格式
                                    if current_version == "published":
                                        safe_display_name = "".join(c for c in wf_display_name if c.isalnum() or c in (' ', '-', '_')).strip()
                                        safe_display_name = safe_display_name.replace(' ', '_')
                                        filename = f"{safe_app_name}-{safe_display_name}.yml"
                                    else:
                                        filename = f"{safe_app_name}-draft.yml"
                                    
                                    # 创建文件消息
                                    yield self.create_blob_message(
                                        blob=dsl_content.encode('utf-8') if isinstance(dsl_content, str) else dsl_content,
                                        meta={
                                            "mime_type": "text/yaml",
                                            "filename": filename
                                        }
                                    )
                                    
                                    # 保存应用信息用于 JSON 输出
                                    try:
                                        import yaml
                                        dsl_dict = yaml.safe_load(dsl_content) if isinstance(dsl_content, str) else dsl_content
                                    except:
                                        dsl_dict = dsl_content
                                    
                                    exported_apps.append({
                                        "id": app_id,
                                        "name": app_name,
                                        "mode": app_mode_type,
                                        "version": wf_version,
                                        "filename": filename,
                                        "dsl": dsl_dict
                                    })
                                    
                                    exported_dsl_count += 1
                                    successful_app_ids.add(app_id)
                                    logger.info(f"已生成文件: {filename}")
                            else:
                                error_msg = f"{app_name}-{wf_version} (状态码: {export_response.status_code})"
                                logger.warning(f"导出应用失败: {error_msg}")
                                failed_apps.append(error_msg)

                        except Exception as e:
                            error_msg = f"{app_name}-{wf_version} (异常: {str(e)})"
                            logger.warning(f"导出应用异常: {error_msg}")
                            failed_apps.append(error_msg)
                            continue

            # 返回 JSON 消息（包含所有应用的 DSL）
            json_result = {
                "total_apps": len(successful_app_ids),
                "total_files": exported_dsl_count,
                "failed": len(failed_apps),
                "apps": exported_apps
            }
            yield self.create_json_message(json_result)
            
            # 返回摘要信息
            summary_text = f"成功导出 {len(successful_app_ids)} 个应用，{exported_dsl_count} 个 DSL 文件"
            logger.info(f"导出完成: {summary_text}")
            
            if exported_dsl_count > 0:
                summary = f"应用导出成功\n\n- {summary_text}\n"
                
                if failed_apps:
                    summary += f"- 失败版本数: {len(failed_apps)}\n"
                    # 最多显示前5个失败信息
                    for fail in failed_apps[:5]:
                        summary += f"  - {fail}\n"
                    if len(failed_apps) > 5:
                        summary += f"  - ... 等共 {len(failed_apps)} 个错误\n"
                    
                yield self.create_text_message(summary)
            else:
                yield self.create_text_message(f"未导出任何应用。错误数: {len(failed_apps)}")

        except requests.exceptions.RequestException as e:
            yield self.create_text_message(f"Network error: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"Error during export: {str(e)}")
