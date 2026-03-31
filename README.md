# Dify Backup Plugin

**Author:** [leslie2046](https://github.com/leslie2046/dify_backup_plugin)  
**Version:** 0.0.4  
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
| `include_segments` | boolean | ❌ | `false` | Fallback to text-segment export when original file cannot be downloaded |

**Behavior:**

1. Fetches all knowledge bases (filtered by `dataset_ids` if provided)
2. For each dataset, downloads every document's original uploaded file
3. Packages each dataset's files into a separate ZIP: `{DatasetName}-documents.zip`
4. Returns all ZIPs as file blobs plus a structured file list

**Returns:**
- One ZIP blob per dataset (streamed)
- Summary text with full file list
- Structured JSON manifest

```json
{
  "total_datasets": 3,
  "total_files": 12,
  "failed_datasets": [],
  "file_list": [
    "📂 My Knowledge Base → my_knowledge_base-documents.zip",
    "   └─ document1.pdf",
    "   └─ document2.docx"
  ]
}
```

> 💡 **`include_segments` fallback**: If a document was added via API text import rather than file upload, enabling this option exports its indexed segments as a `.txt` file inside the ZIP.

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
| `GET /console/api/files/{file_id}/file-preview` | Download original file |

---

## ❓ FAQ

| Issue | Solution |
|-------|----------|
| Login Failed | Check email/password, verify URL is accessible |
| Request Timeout | Check network, export in batches |
| Empty Versions | Some app types don't support version management |
| Dataset files not downloading | Enable `include_segments` to fall back to text export; file download requires the document to have been added via file upload |

## 🔒 Privacy Policy

This plugin **does not store or share** any user data. Credentials are only used for direct communication with your specified Dify instance.

See [PRIVACY.md](PRIVACY.md) for details.

## 📄 License

[Apache License 2.0](LICENSE)

---

<p align="center">
  Made with ❤️ for Dify
</p>
