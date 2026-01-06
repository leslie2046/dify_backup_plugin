from collections.abc import Generator
from typing import Any
import uuid
import base64

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
import requests


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
                - app_identifier: App ID (UUID) or app name
                - include_secret: Whether to include secrets
        """
        # Get parameters
        app_identifier = tool_parameters.get("app_identifier", "").strip()
        include_secret = tool_parameters.get("include_secret", False)

        if not app_identifier:
            yield self.create_text_message("Error: app_identifier is required")
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

            # Login to get access token
            login_url = f"{base_url}/console/api/login"
            login_response = requests.post(
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

            # Access token is in data["data"]["access_token"]
            token_data = login_data.get("data", {})
            access_token = token_data.get("access_token")
            
            if not access_token:
                yield self.create_text_message("Error: No access token received from login")
                return

            # Prepare headers with Bearer token
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Try to determine if identifier is UUID or name
            app_id = None

            try:
                # Try to parse as UUID
                uuid.UUID(app_identifier)
                app_id = app_identifier
            except ValueError:
                # Not a UUID, search by name
                page = 1
                limit = 100
                found = False

                while not found:
                    response = requests.get(
                        f"{base_url}/console/api/apps",
                        headers=headers,
                        params={"page": page, "limit": limit},
                        timeout=30,
                    )

                    if response.status_code != 200:
                        yield self.create_text_message(
                            f"Error fetching apps: {response.status_code} - {response.text}"
                        )
                        return

                    data = response.json()
                    apps = data.get("data", [])

                    # Search for app by name
                    for app in apps:
                        if app.get("name") == app_identifier:
                            app_id = app.get("id")
                            found = True
                            break

                    # Check if there are more pages
                    if not found and not data.get("has_more", False):
                        break

                    page += 1

                if not app_id:
                    yield self.create_text_message(f"Error: Application '{app_identifier}' not found")
                    return

            # Export the app
            export_params = {"include_secret": str(include_secret).lower()}

            export_response = requests.get(
                f"{base_url}/console/api/apps/{app_id}/export",
                headers=headers,
                params=export_params,
                timeout=60,
            )

            if export_response.status_code != 200:
                yield self.create_text_message(
                    f"Error exporting app: {export_response.status_code} - {export_response.text}"
                )
                return

            export_data = export_response.json()
            dsl_content = export_data.get("data", "")

            # Get app info for metadata
            app_info_response = requests.get(
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

            # Return JSON with metadata and DSL
            result = {
                "id": app_id,
                "name": app_name,
                "mode": app_mode,
                "dsl": dsl_content,
            }

            yield self.create_json_message(result)

        except requests.exceptions.RequestException as e:
            yield self.create_text_message(f"Network error: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"Error during export: {str(e)}")
