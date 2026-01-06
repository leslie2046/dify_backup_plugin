from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.config.logger_format import plugin_logger_handler
import requests
import base64
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class DifyBackupProvider(ToolProvider):
    """
    Dify Backup Tools Provider
    Provides tools for backing up and exporting Dify applications
    """

    def _validate_credentials(self, credentials: dict) -> None:
        """
        Validate the credentials by attempting to login to Dify
        Password must be base64 encoded as required by Dify's FieldEncryption
        """
        try:
            base_url = credentials.get("dify_base_url", "").rstrip("/")
            email = credentials.get("email", "")
            password = credentials.get("password", "")

            if not base_url or not email or not password:
                raise ToolProviderCredentialValidationError(
                    "Dify instance URL, email, and password are required"
                )

            # Encode password to base64 as required by Dify's FieldEncryption.decrypt_field()
            password_base64 = base64.b64encode(password.encode("utf-8")).decode("utf-8")
            
            # Attempt to login to validate credentials
            login_url = f"{base_url}/console/api/login"
            
            logger.info(f"开始验证凭证 - 准备登录到: {login_url}")
            logger.info(f"登录邮箱: {email}")

            response = requests.post(
                login_url,
                json={"email": email, "password": password_base64, "remember_me": True},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            logger.info(f"登录响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("message", "Login failed")
                logger.error(f"登录失败 - 状态码: {response.status_code}, 错误信息: {error_msg}")
                raise ToolProviderCredentialValidationError(
                    f"Failed to login to Dify: {error_msg}"
                )

            # 解析登录响应
            data = response.json()
            logger.info(f"登录响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
            logger.info(f"响应 Cookies: {response.cookies.get_dict()}")
            logger.info(f"响应 Headers: {dict(response.headers)}")
            
            result = data.get("result")
            logger.info(f"登录结果: {result}")
            
            if result != "success":
                logger.error(f"登录失败 - result字段不为success: {result}")
                raise ToolProviderCredentialValidationError(
                    f"Login failed: {result or 'Unknown error'}"
                )

            # Try to get access token from different possible locations
            logger.info("开始提取 access_token...")
            access_token = None
            
            # Method 1: Check data["data"]["access_token"]
            logger.info("方法1: 检查 data['data']['access_token']")
            token_data = data.get("data", {})
            logger.info(f"data['data'] 的值: {token_data}")
            logger.info(f"data['data'] 的类型: {type(token_data)}")
            if isinstance(token_data, dict):
                access_token = token_data.get("access_token")
                logger.info(f"从 data['data']['access_token'] 获取到的 token: {access_token}")
            
            # Method 2: Check data["access_token"]
            if not access_token:
                logger.info("方法2: 检查 data['access_token']")
                access_token = data.get("access_token")
                logger.info(f"从 data['access_token'] 获取到的 token: {access_token}")
            
            # Method 3: Check cookies (支持多种可能的cookie名称)
            if not access_token:
                logger.info("方法3: 检查 cookies")
                # 尝试多种可能的cookie名称
                cookie_names = [
                    "__Host-access_token",  # 带__Host-前缀的安全cookie
                    "access_token",          # 标准名称
                    "console_token",         # 旧版名称
                ]
                for cookie_name in cookie_names:
                    access_token = response.cookies.get(cookie_name)
                    if access_token:
                        logger.info(f"从 cookies['{cookie_name}'] 获取到的 token: {access_token[:20]}...")
                        break
                    else:
                        logger.info(f"cookies['{cookie_name}'] 不存在")
                
                if not access_token:
                    logger.info(f"cookies 中所有可用的键: {list(response.cookies.keys())}")
            
            if not access_token:
                logger.error("所有方法均未能获取到 access_token")
                logger.error(f"完整响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
                logger.error(f"响应数据的所有键: {list(data.keys())}")
                raise ToolProviderCredentialValidationError(
                    f"Login succeeded but no access token received. Response: {json.dumps(data)}"
                )
            
            logger.info(f"成功获取 access_token (前10个字符): {access_token[:10]}...")
            logger.info("凭证验证成功")

        except requests.exceptions.RequestException as e:
            raise ToolProviderCredentialValidationError(
                f"Network error connecting to Dify: {str(e)}"
            ) from e
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e)) from e
