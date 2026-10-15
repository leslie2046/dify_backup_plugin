from unittest.mock import Mock
import json

import pytest
import requests

from provider.monitoring import (
    LangfuseClient,
    MonitoringClient,
    MonitoringError,
    app_uuid,
    boolean,
    project_name,
    provision,
    request_json,
    valid_url,
)

APP = "a57b3052-5195-4616-bfbb-ddb2bde606e9"
HOST = "https://lf.example"
DIFY = "https://dify.example"


def response(data, status=200):
    r = Mock(status_code=status)
    r.json.return_value = data
    return r


def dify_client(responses):
    c = MonitoringClient.__new__(MonitoringClient)
    c.base_url = DIFY
    c.session = Mock()
    c.session.request.side_effect = responses
    return c


def missing(enabled=False, provider=None):
    return [
        response({"enabled": enabled, "tracing_provider": provider}),
        response({"has_not_configured": True}),
    ]


def configured(enabled=False):
    return [
        response({"enabled": enabled, "tracing_provider": "langfuse"}),
        response(
            {
                "tracing_config": {
                    "host": HOST,
                    "project_key": "project1",
                    "public_key": "pk-secret",
                    "secret_key": "sk-secret",
                    "unexpected_secret": "oops",
                }
            }
        ),
    ]


def test_monitoring_sanitizes_even_unmasked_response():
    state = dify_client(configured()).monitoring(APP)
    assert state["langfuse"] == {"host": HOST, "project_key": "project1"}
    assert "secret" not in json.dumps(state)


def test_apps_pagination_filters_inclusively_and_fails_closed():
    c = dify_client(
        [
            response({"data": [{"id": APP, "created_at": 10}], "has_more": True}),
            response({"data": [{"id": "other", "created_at": 20}], "has_more": False}),
        ]
    )
    assert [a["id"] for a in c.list_apps(created_after=20)] == ["other"]
    c = dify_client([response({"data": [], "has_more": True})])
    with pytest.raises(MonitoringError, match="incomplete"):
        c.list_apps()
    c = dify_client(
        [response({"data": [{"id": APP}], "has_more": True}), response({}, 403)]
    )
    with pytest.raises(MonitoringError, match="403"):
        c.list_apps()


def test_configure_creates_then_enables_and_verifies():
    c = dify_client(
        missing()
        + [response({"result": "success"}, 201), response({"result": "success"})]
        + configured(True)
    )
    assert c.configure(APP, HOST, "pk", "sk", project_id="project1")["enabled"]
    calls = c.session.request.call_args_list
    assert calls[2].args == ("POST", f"{DIFY}/console/api/apps/{APP}/trace-config")
    assert calls[2].kwargs["json"]["tracing_config"]["project_key"] == "project1"
    assert calls[3].kwargs["json"] == {"enabled": True, "tracing_provider": "langfuse"}


def test_explicit_overwrite_uses_put():
    c = dify_client(configured() + [response({}), response({})] + configured(True))
    c.configure(APP, HOST, "pk", "sk", overwrite=True)
    assert c.session.request.call_args_list[2].args[0] == "PUT"
    c = dify_client(configured())
    with pytest.raises(MonitoringError, match="already exists"):
        c.configure(APP, HOST, "pk", "sk")
    assert len(c.session.request.call_args_list) == 2


def test_other_tracer_is_preserved_and_failed_save_never_enables():
    c = dify_client(missing(True, "langsmith"))
    with pytest.raises(MonitoringError, match="Another"):
        c.configure(APP, HOST, "pk", "sk")
    c = dify_client(missing() + [response({"secret_key": "never-show"}, 400)])
    with pytest.raises(MonitoringError, match="400") as exc:
        c.configure(APP, HOST, "pk", "sk")
    assert "never-show" not in str(exc.value)
    assert len(c.session.request.call_args_list) == 3


def clients(state=None):
    d = Mock(base_url=DIFY)
    d.monitoring.return_value = state or {
        "langfuse_configured": False,
        "enabled": False,
    }
    lf = Mock(host=HOST)
    lf.ensure_project.return_value = {"id": "project1"}
    lf.create_app_key.return_value = {
        "publicKey": "pk-secret",
        "secretKey": "sk-secret",
    }
    return d, lf


def test_dry_run_and_success_and_repeat():
    d, lf = clients()
    assert provision(d, lf, {"id": APP}, [], True)["status"] == "would_provision"
    lf.ensure_project.assert_not_called()
    result = provision(d, lf, {"id": APP}, [], False)
    assert result["status"] == "configured"
    assert "secret" not in json.dumps(result)
    d.configure.assert_called_once_with(
        APP, HOST, "pk-secret", "sk-secret", project_id="project1"
    )
    d.monitoring.return_value = {
        "langfuse_configured": True,
        "enabled": True,
        "langfuse": {"host": HOST, "project_key": "project1"},
    }
    assert (
        provision(d, lf, {"id": APP}, [], False)["status"] == "skipped_existing_config"
    )
    assert lf.create_app_key.call_count == 1


def test_resume_enable_only_for_managed_project():
    d, lf = clients(
        {
            "langfuse_configured": True,
            "enabled": False,
            "langfuse": {"host": HOST, "project_key": "project1"},
        }
    )
    projects = [{"name": project_name(DIFY, APP), "id": "project1"}]
    assert provision(d, lf, {"id": APP}, projects, False)["status"] == "enabled"
    d.enable_langfuse.assert_called_once_with(APP)
    lf.create_app_key.assert_not_called()
    d.reset_mock()
    assert (
        provision(d, lf, {"id": APP}, [], False)["status"] == "skipped_existing_config"
    )
    d.enable_langfuse.assert_not_called()


def test_key_or_config_failure_does_not_delete_resources_or_leak_keys():
    d, lf = clients()
    d.configure.side_effect = MonitoringError("API HTTP 500")
    r = provision(d, lf, {"id": APP}, [], False)
    assert r["status"] == "failed" and r["project_id"] == "project1"
    assert "secret" not in json.dumps(r)
    lf.api.assert_not_called()


def test_org_auth_paths_and_recovery_guard():
    lf = LangfuseClient(HOST, "org-pk", "org-sk")
    assert lf.session.auth == ("org-pk", "org-sk")
    lf.session = Mock()
    lf.session.request.side_effect = [
        response({"projects": []}),
        response({"id": "p1", "name": "managed"}),
        response({"apiKeys": []}),
        response({"publicKey": "pk", "secretKey": "sk"}),
    ]
    projects = lf.projects()
    assert lf.ensure_project("managed", projects)["id"] == "p1"
    assert lf.ensure_project("managed", projects)["id"] == "p1"  # cached reuse
    assert lf.create_app_key("p1", "managed")["secretKey"] == "sk"
    calls = lf.session.request.call_args_list
    assert calls[0].args[1].endswith("/organizations/projects")
    assert calls[1].kwargs["json"] == {"name": "managed", "retention": 0}
    assert calls[3].kwargs["json"] == {"note": "managed"}
    lf.session.request.side_effect = [response({"apiKeys": [{"note": "managed"}]})]
    with pytest.raises(MonitoringError, match="recovery_required"):
        lf.create_app_key("p1", "managed")
    assert lf.session.request.call_count == 5  # no POST on recovery


@pytest.mark.parametrize("status", [301, 401, 403, 404, 429, 500])
def test_http_errors_are_sanitized_and_not_retried(status):
    session = Mock()
    session.request.return_value = response({"secret": "do-not-echo"}, status)
    with pytest.raises(MonitoringError) as exc:
        request_json(session, "POST", HOST, json={"secret": "do-not-echo"})
    assert "do-not-echo" not in str(exc.value)
    assert session.request.call_count == 1
    assert session.request.call_args.kwargs["allow_redirects"] is False


def test_timeout_is_ambiguous_and_no_auto_retry():
    s = Mock()
    s.request.side_effect = requests.Timeout("sk-secret")
    with pytest.raises(MonitoringError, match="unknown") as exc:
        request_json(s, "POST", HOST)
    assert "sk-secret" not in str(exc.value)
    assert s.request.call_count == 1


def test_project_namespace_and_input_validation():
    assert project_name(DIFY, APP) == project_name(DIFY + "/", APP)
    assert project_name(DIFY, APP) != project_name("https://other", APP)
    with pytest.raises(MonitoringError):
        app_uuid("../bad")
    with pytest.raises(MonitoringError):
        valid_url("https://user:pass@host")
    assert boolean("false") is False
    assert boolean(None, True) is True


def test_batch_limit_does_not_count_skips_and_continues_after_failure(monkeypatch):
    from types import SimpleNamespace
    from tools.monitoring_base import MonitoringTool
    import tools.monitoring_base as module

    d, lf = clients()
    apps = [{"id": str(__import__("uuid").UUID(int=i))} for i in range(1, 5)]
    d.list_apps.return_value = apps
    lf.projects.return_value = []
    monkeypatch.setattr(module, "MonitoringClient", Mock(return_value=d))
    monkeypatch.setattr(module, "LangfuseClient", Mock(return_value=lf))

    def fake_provision(_d, _lf, app, projects, dry_run):
        if app == apps[0]:
            return {"status": "skipped_existing_config", "app_id": app["id"]}
        if app == apps[1] and not dry_run:
            raise MonitoringError("API HTTP 500")
        return {
            "status": "would_provision" if dry_run else "configured",
            "app_id": app["id"],
        }

    monkeypatch.setattr(module, "provision", fake_provision)
    tool = SimpleNamespace(
        action="sync_apps_langfuse",
        runtime=SimpleNamespace(
            credentials={
                "dify_base_url": DIFY,
                "email": "admin@example.com",
                "password": "private",
                "langfuse_host": HOST,
                "langfuse_org_public_key": "org-pk",
                "langfuse_org_secret_key": "org-sk",
            }
        ),
        create_json_message=lambda data: data,
    )
    outputs = list(MonitoringTool._invoke(tool, {"dry_run": "false", "max_apps": 2}))
    summary = outputs[-1]
    assert [r["status"] for r in summary["results"]] == [
        "skipped_existing_config",
        "failed",
        "configured",
    ]
    assert summary["failed"] == 1 and summary["remaining_candidates"] == 1
    assert summary["complete"] is False
    assert "private" not in json.dumps(outputs)
    d.session.close.assert_called_once()
    lf.session.close.assert_called_once()


def test_sdk_loads_all_registered_tools_and_sources():
    from pathlib import Path
    import importlib
    import yaml
    from dify_plugin import Tool
    from dify_plugin.core.utils.class_loader import load_single_subclass_from_source
    from dify_plugin.entities.tool import ToolProviderConfiguration

    data = yaml.safe_load(Path("provider/dify_backup.yaml").read_text())
    config = ToolProviderConfiguration.model_validate(data)
    assert len(config.tools) == 9
    for tool in config.tools:
        source = tool.extra.python.source
        module = importlib.import_module(source.removesuffix(".py").replace("/", "."))
        cls = load_single_subclass_from_source(
            module_name=module.__name__, script_path=source, parent_type=Tool
        )
        assert cls.__module__ == module.__name__
