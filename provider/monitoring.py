"""Console tracing APIs and conservative, repeatable Langfuse provisioning."""

import hashlib
from urllib.parse import quote, urlsplit
from uuid import UUID

import requests

from provider.dify_backup import DifyClient


class MonitoringError(Exception):
    """Only credential-free, actionable messages may cross the tool boundary."""


def valid_url(value):
    value = str(value or "").strip().rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise MonitoringError(
            "Expected an HTTP(S) base URL without credentials, query or fragment"
        )
    return value


def app_uuid(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise MonitoringError("app_id must be a UUID") from None


def boolean(value, default=False):
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if value in ("true", "True", 1, "1"):
        return True
    if value in ("false", "False", 0, "0"):
        return False
    raise MonitoringError("Expected a boolean")


def request_json(session, method, url, **kwargs):
    # No raw response bodies or requests exceptions: these may contain keys.
    try:
        response = session.request(
            method, url, timeout=60, allow_redirects=False, **kwargs
        )
    except requests.RequestException:
        raise MonitoringError(
            "API connection failed; mutation outcome may be unknown. Re-query before retrying."
        ) from None
    if not 200 <= response.status_code < 300:
        raise MonitoringError(
            f"API HTTP {response.status_code}; check permissions, API support and server logs"
        )
    if response.status_code == 204:
        return {}
    try:
        data = response.json()
    except ValueError:
        raise MonitoringError(
            "API returned invalid JSON; re-query before retrying mutations"
        ) from None
    if not isinstance(data, dict):
        raise MonitoringError("Unexpected API response shape")
    if data.get("result") == "error" or data.get("error"):
        raise MonitoringError("API reported an operation failure; check server logs")
    return data


class MonitoringClient(DifyClient):
    def api(self, method, path, **kwargs):
        return request_json(
            self.session, method, f"{self.base_url}/console/api{path}", **kwargs
        )

    def list_apps(self, mode="all", created_after=0):
        if mode not in (
            "all",
            "workflow",
            "advanced-chat",
            "chat",
            "agent-chat",
            "completion",
        ):
            raise MonitoringError("Unsupported app_mode")
        result, seen, page = [], set(), 1
        while True:
            params = {"page": page, "limit": 100}
            if mode != "all":
                params["mode"] = mode
            data = self.api("GET", "/apps", params=params)
            items = data.get("data")
            if not isinstance(items, list):
                raise MonitoringError("App list response is missing data")
            added = 0
            for app in items:
                if app["id"] in seen:
                    continue
                seen.add(app["id"])
                added += 1
                if float(app.get("created_at") or 0) >= created_after:
                    result.append(
                        {
                            k: app.get(k)
                            for k in ("id", "name", "mode", "created_at", "updated_at")
                        }
                    )
            if not data.get("has_more"):
                return result
            if not added:
                raise MonitoringError(
                    "App pagination made no progress; scan is incomplete"
                )
            page += 1

    def monitoring(self, app_id):
        app_id = app_uuid(app_id)
        trace = self.api("GET", f"/apps/{app_id}/trace")
        config = self.api(
            "GET",
            f"/apps/{app_id}/trace-config",
            params={"tracing_provider": "langfuse"},
        )
        if not isinstance(trace.get("enabled"), bool):
            raise MonitoringError("Unrecognized Dify trace response")
        missing = config.get("has_not_configured") is True
        if not missing and not isinstance(config.get("tracing_config"), dict):
            raise MonitoringError("Unrecognized Dify trace-config response")
        cfg = config.get("tracing_config") or {}
        # Allowlist; Dify currently masks keys, but do not rely on that behavior.
        return {
            "app_id": app_id,
            "enabled": trace["enabled"],
            "tracing_provider": trace.get("tracing_provider"),
            "langfuse_configured": not missing,
            "langfuse": {k: cfg.get(k) for k in ("host", "project_key")},
            "is_active": config.get("is_active"),
        }

    def enable_langfuse(self, app_id):
        self.api(
            "POST",
            f"/apps/{app_uuid(app_id)}/trace",
            json={"enabled": True, "tracing_provider": "langfuse"},
        )
        state = self.monitoring(app_id)
        if (
            not state["enabled"]
            or state["tracing_provider"] != "langfuse"
            or not state["langfuse_configured"]
        ):
            raise MonitoringError("Dify tracing read-back verification failed")
        return state

    def configure(
        self, app_id, host, public_key, secret_key, overwrite=False, project_id=None
    ):
        if not public_key or not secret_key:
            raise MonitoringError(
                "Langfuse project public and secret keys are required"
            )
        state = self.monitoring(app_id)
        if state["langfuse_configured"] and not overwrite:
            raise MonitoringError(
                "Langfuse config already exists; use overwrite=true to replace it"
            )
        if (
            state["enabled"]
            and state["tracing_provider"] != "langfuse"
            and not overwrite
        ):
            raise MonitoringError(
                "Another tracing provider is enabled; use overwrite=true to switch"
            )
        config = {
            "host": valid_url(host),
            "public_key": public_key,
            "secret_key": secret_key,
        }
        if project_id:
            config["project_key"] = project_id
        self.api(
            "PUT" if state["langfuse_configured"] else "POST",
            f"/apps/{app_uuid(app_id)}/trace-config",
            json={"tracing_provider": "langfuse", "tracing_config": config},
        )
        return self.enable_langfuse(app_id)


class LangfuseClient:
    def __init__(self, host, public_key, secret_key):
        self.host = valid_url(host)
        if not public_key or not secret_key:
            raise MonitoringError(
                "Langfuse organization public and secret keys are required (organization API entitlement needed)"
            )
        self.session = requests.Session()
        self.session.auth = (public_key, secret_key)

    def api(self, method, path, **kwargs):
        return request_json(
            self.session, method, f"{self.host}/api/public{path}", **kwargs
        )

    def projects(self):
        data = self.api("GET", "/organizations/projects")
        if not isinstance(data.get("projects"), list):
            raise MonitoringError("Unrecognized organization projects response")
        return data["projects"]

    def ensure_project(self, name, projects):
        matches = [p for p in projects if p.get("name") == name]
        if len(matches) > 1:
            raise MonitoringError(
                "Multiple matching Langfuse projects; resolve duplicates before retrying"
            )
        if matches:
            return matches[0]
        project = self.api("POST", "/projects", json={"name": name, "retention": 0})
        if not project.get("id"):
            raise MonitoringError(
                "Project creation returned no ID; re-query before retrying"
            )
        projects.append(project)
        return project

    def create_app_key(self, project_id, note):
        path = f'/projects/{quote(project_id, safe="")}/apiKeys'
        data = self.api("GET", path)
        if not isinstance(data.get("apiKeys"), list):
            raise MonitoringError("Unrecognized API key list response")
        if any(k.get("note") == note or k.get("name") == note for k in data["apiKeys"]):
            raise MonitoringError(
                "recovery_required: a managed API key exists but Dify has no config. "
                "Its secret cannot be retrieved. Configure manually or remove that unused key before retrying."
            )
        # note is supported by Langfuse v3 and remains a deprecated alias in v4.
        key = self.api("POST", path, json={"note": note})
        if not key.get("publicKey") or not key.get("secretKey"):
            raise MonitoringError(
                "Key creation returned no key pair; inspect project keys before retrying"
            )
        return key


def project_name(dify_url, app_id):
    namespace = hashlib.sha256(dify_url.rstrip("/").encode()).hexdigest()[:12]
    return f"dify-{namespace}-{app_uuid(app_id)}"


def provision(dify, langfuse, app, projects, dry_run=True):
    app_id = app_uuid(app["id"])
    result = {
        "app_id": app_id,
        "name": app.get("name"),
        "project_name": project_name(dify.base_url, app_id),
    }
    state = dify.monitoring(app_id)
    if state["langfuse_configured"]:
        # Only resume enabling an existing config if it belongs to our deterministic project.
        matches = [p for p in projects if p.get("name") == result["project_name"]]
        managed = (
            len(matches) == 1
            and state["langfuse"]["project_key"] == matches[0]["id"]
            and (state["langfuse"]["host"] or "").rstrip("/") == langfuse.host
        )
        if managed and not state["enabled"]:
            if not dry_run:
                dify.enable_langfuse(app_id)
            result["status"] = "would_enable" if dry_run else "enabled"
        else:
            result["status"] = "skipped_existing_config"
        return result
    if state["enabled"]:
        result["status"] = "skipped_existing_tracing"
        return result
    if dry_run:
        result["status"] = "would_provision"
        return result
    project = langfuse.ensure_project(result["project_name"], projects)
    result["project_id"] = project["id"]
    try:
        key = langfuse.create_app_key(project["id"], result["project_name"])
        dify.configure(
            app_id,
            langfuse.host,
            key["publicKey"],
            key["secretKey"],
            project_id=project["id"],
        )
    except MonitoringError as exc:
        # Do not delete keys on ambiguous failures: Dify may already have saved them.
        result.update(status="failed", error=str(exc))
        return result
    result["status"] = "configured"
    return result
