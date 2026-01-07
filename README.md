# Dify Backup Plugin

**Author:** [leslie2046](https://github.com/leslie2046/dify_backup_plugin)  
**Version:** 0.0.1  
**Type:** tool

<p align="center">
  <img src="_assets/icon.svg" alt="Dify Backup" width="100" height="100">
</p>

> 🔄 One-click backup and export Dify application DSL configurations

---

## ✨ Features

- 📦 **Batch Export** - Export all applications in workspace
- 🎯 **Single App Export** - Export specific application
- 🔀 **Version Support** - Draft / Published / All versions
- 🏷️ **Type Filter** - Workflow / Chat / Agent, etc.

## 🚀 Quick Start

### Configure Credentials

| Parameter | Description |
|-----------|-------------|
| Dify Instance URL | Dify instance URL (e.g., `https://cloud.dify.ai`) |
| Email | Account email |
| Password | Account password |

### Tool Parameters

**Export All Apps**

| Parameter | Default | Options |
|-----------|---------|---------|
| `app_mode` | all | all / workflow / chat / agent-chat / completion |
| `version_type` | draft | draft / published / all |

**Export Single App**

| Parameter | Description |
|-----------|-------------|
| `app_identifier` | Select app from dropdown |
| `version_type` | draft / published / all |

## 💡 Use Cases

| Scenario | Recommended Config |
|----------|-------------------|
| Scheduled Backup | `version_type=all` to backup both draft and published |
| Environment Migration | `version_type=published` for production only |
| Version Archiving | Export current version before publishing |

## 🔧 Technical Details

- **Timeout**: 60 seconds
- **Authentication**: Email/password login
- **Output Format**: Streaming JSON, returns DSL per app

## ❓ FAQ

| Issue | Solution |
|-------|----------|
| Login Failed | Check email/password, verify URL is accessible |
| Request Timeout | Check network, export in batches |
| Empty Versions | Some app types don't support version management |

## 🔒 Privacy Policy

This plugin **does not store or share** any user data. Credentials are only used for direct communication with your specified Dify instance.

See [PRIVACY.md](PRIVACY.md) for details.

## 📄 License

[Apache License 2.0](LICENSE)

---

<p align="center">
  Made with ❤️ for Dify
</p>
