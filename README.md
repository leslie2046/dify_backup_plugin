# Dify Backup Plugin

**Author:** [leslie2046](https://github.com/leslie2046/dify_backup_plugin)  
**Version:** 0.0.5
**Type:** tool

<p align="center">
  <img src="_assets/icon.svg" alt="Dify Backup" width="100" height="100">
</p>

> 🔄 One-click backup and export Dify application DSL configurations, annotations, and knowledge base files

---

## ✨ Features

- 📦 **Batch Export Apps** - Export all applications DSL in workspace
- 🎯 **Single App Export** - Export specific application DSL
- 🔀 **Version Support** - Draft / Published / All versions
- 🏷️ **Type Filter** - Workflow / Chat / Agent, etc.
- 📝 **Batch Export Annotations** - Export annotations for all apps as CSV
- 🗂️ **Export Dataset Files** - Download knowledge base files as ZIP archives with multi-select support

## 🚀 Quick Start

### 1. Install Plugin

Search for **"Dify Backup"** in Dify Plugin Marketplace and install, or upload the plugin package manually.

### 2. Configure Credentials

| Parameter | Description | Example |
|-----------|-------------|---------|
| Dify Instance URL | Dify instance base URL | `https://cloud.dify.ai` |
| Email | Account email | `admin@example.com` |
| Password | Account password | - |

> ⚠️ URL should not include `/console` or `/api` suffix

### 3. Start Using

After configuration, you can invoke the export tools in workflows or conversations.

---

## 🛠️ Tools

### Export All Apps

Batch export DSL configurations for all applications in the workspace.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_mode` | select | ✅ | App type: all / workflow / chat / agent-chat / completion |
| `version_type` | select | ✅ | Version: draft / published / all |

**Output Format**: Streaming JSON, returns DSL for each app

```json
{
  "id": "app-uuid",
  "name": "App Name",
  "mode": "workflow",
  "version": "draft",
  "filename": "AppName-draft.yml",
  "dsl": { "..." }
}
```

### Export Single App

Export DSL configuration for a specific application.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_identifier` | app-selector | ✅ | Select app from dropdown |
| `version_type` | select | ✅ | Version: draft / published / all |

### Export All Annotations

Batch export annotations (Q&A pairs) for all applications in the workspace.

- **No parameters required** - One-click export
- **Smart filtering** - Automatically skips apps with no annotations
- **CSV format** - Each app exports as `{AppName}-annotations.csv`

**Output Format**: Streaming JSON, returns CSV content for each app with annotations

```json
{
  "name": "App Name",
  "filename": "AppName-annotations.csv",
  "content": "\"question\",\"answer\"\n\"Q1\",\"A1\"\n..."
}
```

### Export Dataset Files ⭐ New

Export original uploaded files from one or more knowledge bases as ZIP archives.  
**Supports multi-select datasets — leave `dataset_ids` blank to export all.**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `dataset_ids` | string | ❌ | _(all)_ | Comma-separated dataset IDs. Leave blank to export **all** datasets |

**Behavior:**

1. Fetches all knowledge bases (filtered by `dataset_ids` if provided)
2. For each dataset, downloads every document's original uploaded file
3. Packages each dataset's files into a separate ZIP: `{DatasetName}-documents.zip`
4. Returns all ZIPs as file blobs plus a per-dataset structured manifest

**Returns:**
- One ZIP blob per dataset (streamed)
- Summary text with full file list
- Structured JSON manifest

```json
{
  "total_datasets": 3,
  "total_files": 12,
  "datasets": [
    {
      "dataset_id": "dataset-uuid-1",
      "dataset_name": "My Knowledge Base",
      "status": "exported",
      "exported_file_count": 2,
      "zip_filename": "my_knowledge_base-documents.zip"
    },
    {
      "dataset_id": "dataset-uuid-2",
      "dataset_name": "Empty Knowledge Base",
      "status": "no_documents",
      "exported_file_count": 0
    }
  ]
}
```

---

## 💡 Use Cases

### Scheduled Auto Backup

Create a scheduled workflow to automatically backup all apps:

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│   Schedule  │───▶│ Export All Apps  │───▶│   Storage   │
│ (Daily 2AM) │    │                  │    │             │
└─────────────┘    └──────────────────┘    └─────────────┘
```

### Knowledge Base Archiving

Export specific knowledge bases before restructuring:

```
┌─────────────────┐    ┌──────────────────────┐    ┌───────────┐
│  Select Dataset │───▶│ Export Dataset Files  │───▶│  Archive  │
│  (by IDs)       │    │ → ZIPs per dataset    │    │  Storage  │
└─────────────────┘    └──────────────────────┘    └───────────┘
```

### Version Archiving

Export current version as archive before publishing new version.

### Environment Migration

1. Export all apps in dev environment (`version_type=published`)
2. Import in production environment

---

## 🔧 Technical Details

| Item | Description |
|------|-------------|
| Timeout | 60 seconds |
| Authentication | Email/password login |
| Output Format | Streaming JSON + File blobs |
| App File Naming | `{AppName}-{VersionId}.yml` |
| Dataset ZIP Naming | `{DatasetName}-documents.zip` |

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /console/api/login` | Login authentication |
| `GET /console/api/apps` | List applications |
| `GET /console/api/apps/{id}/export` | Export app DSL |
| `GET /console/api/apps/{id}/annotations` | Get annotations |
| `GET /console/api/datasets` | List knowledge bases |
| `GET /console/api/datasets/{id}/documents` | List documents in dataset |
| `GET /console/api/datasets/{id}/documents/{document_id}/download` | Get document download URL |
| `GET /console/api/files/{file_id}/file-preview` | Legacy fallback for original file download |

---

## ❓ FAQ

| Issue | Solution |
|-------|----------|
| Login Failed | Check email/password, verify URL is accessible |
| Request Timeout | Check network, export in batches |
| Empty Versions | Some app types don't support version management |
| Dataset files not downloading | File download requires the document to have an exportable original file. Some non-file-backed documents may be skipped. |

## 🔒 Privacy Policy

This plugin **does not store or share** any user data. Credentials are only used for direct communication with your specified Dify instance.

See [PRIVACY.md](PRIVACY.md) for details.

## 📄 License

[Apache License 2.0](LICENSE)

---

<p align="center">
  Made with ❤️ for Dify
</p>

## Langfuse monitoring automation (0.0.5)

| Tool | Purpose |
|---|---|
| `list_apps` | Paginate accessible workspace apps; filter by mode and inclusive `created_after` (Unix seconds); optionally include sanitized monitoring state. |
| `get_app_monitoring` | Read `/trace` and Langfuse `/trace-config`; return enabled/provider/host/project ID, never keys. |
| `configure_app_langfuse` | Save existing project keys from provider credentials, enable tracing, then verify by read-back. Requires `overwrite=true` to replace a config or switch providers. |
| `provision_app_langfuse` | Reuse/create a project and create a project key, save it directly to Dify, then enable tracing. |
| `sync_apps_langfuse` | Batch reconcile missing monitoring; includes per-app results and a final summary. |

### Prerequisites and credentials

Keep the existing Dify URL/email/password credentials. The account must have permission to edit tracing in the intended active workspace. This plugin does not switch workspaces or support SSO-only login.

Additional **optional provider credentials** (backup tools do not require them):

- `langfuse_host`: reachable Langfuse base URL (no `/api/public` suffix). Both plugin and Dify API servers must reach it. Use HTTPS outside a trusted local network.
- `langfuse_org_public_key`, `langfuse_org_secret_key`: organization-scoped Basic Auth keys for automatic provisioning. Project keys cannot create projects.
- `langfuse_project_public_key`, `langfuse_project_secret_key`: existing project keys used only by `configure_app_langfuse`, as a fallback when organization APIs are unavailable.

**Edition requirement:** Langfuse's official organization management APIs require an eligible Enterprise plan / self-hosted Enterprise Edition. Community self-hosting and ordinary project keys alone do not provide this provisioning capability. No private UI/tRPC API or database writes are used as a bypass.

Dify contracts were checked against **1.17.1** and upstream source; Langfuse uses the documented organization projects, project create and project API-key endpoints. Deployments must expose `GET /api/public/organizations/projects`. A missing/forbidden endpoint fails explicitly. This change has mocked API tests, not a live integration test against your deployment.

### Daily Dify workflow

1. Configure the provider credentials above.
2. Use a daily Schedule Trigger (for example 09:00 Asia/Shanghai), or an external scheduler invoking the workflow if your Dify version lacks it.
3. Add `sync_apps_langfuse`: `app_mode=all`, `created_after=0`, `dry_run=true`, `max_apps=10`. Inspect the preview.
4. Set `dry_run=false` to apply. Each unconfigured app receives `dify-<instance URL hash>-<app UUID>` as its project name. Keys are sent directly to Dify and never returned in tool outputs.
5. Inspect the **last JSON message**, `type=summary` (`json[-1]`): `failed`, `remaining_candidates`, `complete` and per-app `results`. Alert on failures; run another batch if candidates remain.

A full scan (`created_after=0`) catches new apps and failed previous attempts without requiring a checkpoint. For large workspaces use `list_apps` then a **sequential** iteration calling `provision_app_langfuse` for each UUID; this avoids one long tool invocation. A nonzero timestamp is an optional optimization: keep an overlap and advance your external watermark only after a complete successful scan. Existing apps with disabled tracing are preserved unless they have a matching plugin-managed project, in which case enabling is resumed. Other active providers and existing Langfuse configurations are skipped.

### Retry and recovery contract

- `dry_run` defaults to true for provisioning/sync. Preview performs reads only, and still checks organization API access.
- Project names include the instance URL hash and full App UUID, avoiding collisions across renamed apps. Keep the configured instance URL stable. Same-name duplicates are rejected.
- Run **one automation at a time** per Dify workspace/Langfuse organization. Name lookup + create is not an atomic cross-system transaction; concurrent runs can create duplicates. This plugin does not promise distributed exactly-once execution.
- After a project is created, retries reuse it. After config is saved but enabling fails, retries resume enabling the matching managed config. Already configured apps never receive another key.
- Langfuse reveals a secret only at key creation. If creation succeeds but config fails (or the request times out), the next run detects the managed key note and reports `recovery_required`, rather than generating more keys. Re-query Dify first: if config is present, retry enabling; if absent, use `configure_app_langfuse` with a securely retained pair, or manually revoke the confirmed unused key and retry. Projects and keys are not automatically deleted on ambiguous failures.
- HTTP errors, partial pagination failures and malformed responses fail explicitly; they are not reported as an empty or successful scan. Raw error bodies, authorization headers and keys are omitted. Secrets are not persisted by this code; provider credentials are managed by Dify and tracing project keys are persisted by Dify itself.
- Read-back verifies configuration and the tracing switch, not ingestion. Send a test app request and check Langfuse for a trace after deployment.

API references: [Dify tracing controller](https://github.com/langgenius/dify/blob/1.17.1/api/controllers/console/app/ops_trace.py), [Dify tracing switch](https://github.com/langgenius/dify/blob/1.17.1/api/controllers/console/app/app.py), [Langfuse Org API and edition availability](https://langfuse.com/docs/administration/scim-and-org-api), [Langfuse API contract](https://github.com/langfuse/langfuse/blob/main/web/public/generated/api/openapi.yml).

Development checks: `python -m pip install -r requirements.txt pytest`, then `python -m pytest -q`.
