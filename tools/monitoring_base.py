"""Shared tool boundary. Secrets stay in credentials and never appear in results."""

from collections.abc import Generator
from typing import Any
import math

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from provider.monitoring import (
    LangfuseClient,
    MonitoringClient,
    MonitoringError,
    app_uuid,
    boolean,
    provision,
    valid_url,
)


class MonitoringTool(Tool):
    action = ""

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        dify = langfuse = None
        try:
            params = tool_parameters
            credentials = self.runtime.credentials
            base_url = valid_url(credentials.get("dify_base_url"))
            if not credentials.get("email") or not credentials.get("password"):
                raise MonitoringError("Dify provider credentials are required")
            # Validate everything possible before logging in or mutating remote state.
            app_id = (
                app_uuid(params.get("app_id"))
                if self.action not in ("list_apps", "sync_apps_langfuse")
                else None
            )
            created_after = float(params.get("created_after") or 0)
            if not math.isfinite(created_after) or created_after < 0:
                raise MonitoringError(
                    "created_after must be a non-negative Unix timestamp in seconds"
                )
            dry_run = boolean(params.get("dry_run"), True)
            overwrite = boolean(params.get("overwrite"), False)
            max_apps = int(params.get("max_apps") or 10)
            if not 1 <= max_apps <= 100:
                raise MonitoringError("max_apps must be between 1 and 100")
            dify = MonitoringClient(
                base_url, credentials["email"], credentials["password"]
            )
            if self.action == "list_apps":
                apps = dify.list_apps(params.get("app_mode") or "all", created_after)
                if boolean(params.get("include_monitoring"), False):
                    for app in apps:
                        app["monitoring"] = dify.monitoring(app["id"])
                yield self.create_json_message(
                    {"apps": apps, "total": len(apps), "complete": True}
                )
            elif self.action == "get_app_monitoring":
                yield self.create_json_message(dify.monitoring(app_id))
            elif self.action == "configure_app_langfuse":
                result = dify.configure(
                    app_id,
                    credentials.get("langfuse_host"),
                    credentials.get("langfuse_project_public_key"),
                    credentials.get("langfuse_project_secret_key"),
                    overwrite,
                )
                yield self.create_json_message({"status": "configured", **result})
            else:
                langfuse = LangfuseClient(
                    credentials.get("langfuse_host"),
                    credentials.get("langfuse_org_public_key"),
                    credentials.get("langfuse_org_secret_key"),
                )
                projects = (
                    langfuse.projects()
                )  # Permission preflight before any mutation.
                apps = (
                    [{"id": app_id}]
                    if self.action == "provision_app_langfuse"
                    else dify.list_apps(params.get("app_mode") or "all", created_after)
                )
                results, attempted, remaining = [], 0, 0
                for app in apps:
                    try:
                        # Read-only plan lets limits count candidates, not already configured apps.
                        plan = provision(dify, langfuse, app, projects, dry_run=True)
                        candidate = plan["status"] in (
                            "would_provision",
                            "would_enable",
                        )
                        if candidate and attempted >= max_apps:
                            remaining += 1
                            continue
                        if candidate:
                            attempted += 1
                        result = (
                            plan
                            if dry_run or not candidate
                            else provision(dify, langfuse, app, projects, dry_run=False)
                        )
                    except MonitoringError as exc:
                        result = {
                            "app_id": app["id"],
                            "status": "failed",
                            "error": str(exc),
                        }
                    results.append(result)
                    # Emit progress; workflows can consume the final summary at json[-1].
                    yield self.create_json_message({"type": "app_result", **result})
                failed = sum(r["status"] == "failed" for r in results)
                yield self.create_json_message(
                    {
                        "type": "summary",
                        "dry_run": dry_run,
                        "results": results,
                        "failed": failed,
                        "remaining_candidates": remaining,
                        "complete": remaining == 0 and failed == 0,
                    }
                )
        except MonitoringError as exc:
            yield self.create_json_message(
                {"status": "failed", "error": str(exc), "complete": False}
            )
        except Exception:
            # Dify login and third party errors may include sensitive response bodies.
            yield self.create_json_message(
                {
                    "status": "failed",
                    "error": "Monitoring operation failed; check credentials, inputs and API compatibility",
                    "complete": False,
                }
            )
        finally:
            if dify is not None:
                dify.session.close()
            if langfuse is not None:
                langfuse.session.close()
