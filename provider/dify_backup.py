from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.config.logger_format import plugin_logger_handler
import requests
import base64
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class DifyClient:
    """
    Dify API Client - 封装所有与 Dify Console API 的交互
    """
    
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.access_token = None
        self.csrf_token = None
        
        # 登录并初始化 session
        self._login()

    def _login(self):
        """登录 Dify 并获取 Access Token 和 CSRF Token"""
        try:
            password_base64 = base64.b64encode(self.password.encode("utf-8")).decode("utf-8")
            login_url = f"{self.base_url}/console/api/login"
            
            logger.info(f"正在登录 Dify: {login_url}")
            login_response = self.session.post(
                login_url,
                json={"email": self.email, "password": password_base64, "remember_me": True},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if login_response.status_code != 200:
                raise Exception(f"Login failed: {login_response.status_code} - {login_response.text}")

            login_data = login_response.json()
            if login_data.get("result") != "success":
                raise Exception(f"Login failed: {login_data.get('result', 'Unknown error')}")

            # 提取 Access Token
            self.access_token = self._extract_access_token(login_data)
            if not self.access_token:
                raise Exception("Failed to retrieve access token")

            # 提取 CSRF Token
            self.csrf_token = self.session.cookies.get("__Host-csrf_token") or self.session.cookies.get("csrf_token")
            
            # 设置公共 Headers
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            })
            if self.csrf_token:
                self.session.headers["X-CSRF-Token"] = self.csrf_token
                logger.info("CSRF Token configured")
            
            logger.info("登录成功")

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise

    def _extract_access_token(self, login_data: dict) -> str:
        """从响应或 Cookie 中提取 Access Token"""
        # 1. Check data["data"]["access_token"]
        token_data = login_data.get("data", {})
        if isinstance(token_data, dict) and token_data.get("access_token"):
            return token_data.get("access_token")
        
        # 2. Check data["access_token"]
        if login_data.get("access_token"):
            return login_data.get("access_token")
        
        # 3. Check cookies
        cookie_names = ["__Host-access_token", "access_token", "console_token"]
        for name in cookie_names:
            token = self.session.cookies.get(name)
            if token:
                return token
        return None

    def get_app_info(self, app_id: str) -> dict:
        """获取应用基本信息"""
        response = self.session.get(f"{self.base_url}/console/api/apps/{app_id}", timeout=30)
        if response.status_code == 200:
            return response.json()
        return None

    def get_all_apps(self, limit: int = 100) -> list:
        """获取所有应用列表"""
        all_apps = []
        page = 1
        while True:
            response = self.session.get(
                f"{self.base_url}/console/api/apps",
                params={"page": page, "limit": limit},
                timeout=30
            )
            if response.status_code != 200:
                logger.error(f"Failed to fetch apps page {page}: {response.status_code}")
                break
                
            data = response.json()
            items = data.get("data", [])
            if not items:
                break
                
            all_apps.extend(items)
            if not data.get("has_more", False):
                break
            page += 1
        return all_apps

    def get_versions_to_export(self, app_id: str, app_name: str, version_type: str = "draft") -> list:
        """获取需要导出的版本列表信息"""
        versions = []
        target_types = ["draft", "published"] if version_type == "all" else [version_type]

        for v_type in target_types:
            if v_type == "draft":
                versions.append({"id": None, "version": "draft", "display_name": "draft"})
            
            elif v_type == "published":
                # 获取已发布版本列表
                pub_versions = self._get_published_versions(app_id, app_name)
                versions.extend(pub_versions)
        
        return versions

    def _get_published_versions(self, app_id: str, app_name: str) -> list:
        """获取已发布版本列表（包含 404 降级处理）"""
        versions = []
        response = self.session.get(
            f"{self.base_url}/console/api/apps/{app_id}/workflows",
            params={"page": 1, "limit": 100},
            timeout=30
        )

        if response.status_code == 200:
            items = response.json().get("items", [])
            published_items = [v for v in items if v.get("version") != "draft"]
            
            for item in published_items:
                versions.append(self._parse_version_info(item))
            logger.info(f"[{app_name}] Found {len(versions)} published versions")

        elif response.status_code == 404:
            logger.info(f"[{app_name}] Workflows API 404, attempting fallback to current version")
            # 降级处理：尝试从 App Info 获取当前 workflow_id
            app_info = self.get_app_info(app_id)
            if app_info:
                wf_id = None
                if "workflow" in app_info and app_info["workflow"]:
                    wf_id = app_info["workflow"].get("id")
                elif "workflow_id" in app_info:
                    wf_id = app_info.get("workflow_id")
                
                if wf_id:
                    logger.info(f"[{app_name}] Found current published workflow ID: {wf_id}")
                    versions.append({
                        "id": wf_id,
                        "version": "published",
                        "display_name": "published",
                        "marked_name": "current"
                    })
        else:
            logger.warning(f"[{app_name}] Failed to get workflows: {response.status_code}")

        return versions

    def _parse_version_info(self, item: dict) -> dict:
        """解析版本信息，生成 display_name"""
        wf_version = item.get("version", "unknown")
        marked_name = item.get("marked_name", "")
        created_at = item.get("created_at")

        display_name = marked_name
        if not display_name:
            if created_at:
                try:
                    if isinstance(created_at, int):
                        dt = datetime.fromtimestamp(created_at)
                    else:
                        dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                    display_name = f"未命名-{dt.strftime('%Y%m%d%H%M')}"
                except:
                    display_name = f"未命名-{wf_version}"
            else:
                display_name = f"未命名-{wf_version}"
        
        return {
            "id": item.get("id"),
            "version": wf_version,
            "display_name": display_name,
            "marked_name": marked_name
        }

    def export_dsl(self, app_id: str, workflow_id: str = None) -> str:
        """导出 DSL"""
        params = {"include_secret": "false"}
        if workflow_id:
            params["workflow_id"] = workflow_id
        
        response = self.session.get(
            f"{self.base_url}/console/api/apps/{app_id}/export",
            params=params,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get("data", "")
        else:
            logger.warning(f"Export failed for app {app_id} (wf: {workflow_id}): {response.status_code}")
            return None

    @staticmethod
    def generate_filename(app_name: str, version_display_name: str) -> str:
        """生成安全的文件名"""
        safe_app = "".join(c for c in app_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        safe_ver = "".join(c for c in version_display_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        return f"{safe_app}-{safe_ver}.yml"


class DifyBackupProvider(ToolProvider):
    """
    Dify Backup Tools Provider
    Provides tools for backing up and exporting Dify applications
    """

    def _validate_credentials(self, credentials: dict) -> None:
        """
        Validate the credentials by attempting to login to Dify
        """
        try:
            base_url = credentials.get("dify_base_url", "")
            email = credentials.get("email", "")
            password = credentials.get("password", "")

            if not base_url or not email or not password:
                raise ToolProviderCredentialValidationError(
                    "Dify instance URL, email, and password are required"
                )

            # 使用 DifyClient 验证凭证（登录成功即验证通过）
            client = DifyClient(base_url, email, password)
            logger.info("凭证验证成功")

        except requests.exceptions.RequestException as e:
            raise ToolProviderCredentialValidationError(
                f"Network error connecting to Dify: {str(e)}"
            ) from e
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e)) from e
