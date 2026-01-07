# Dify Backup Plugin

**Author:** [leslie2046](https://github.com/leslie2046/dify_backup_plugin)  
**Version:** 0.0.1  
**Type:** tool

<p align="center">
  <img src="../_assets/icon.svg" alt="Dify Backup" width="100" height="100">
</p>

> 🔄 一键备份和导出 Dify 应用 DSL 配置

---

## ✨ 功能

- 📦 **批量导出** - 导出工作空间中所有应用
- 🎯 **单应用导出** - 选择指定应用导出
- 🔀 **版本支持** - 草稿版本 / 已发布版本 / 全部
- 🏷️ **类型过滤** - Workflow / Chat / Agent 等

## 🚀 快速开始

### 1. 安装插件

在 Dify 插件市场中搜索 **"Dify Backup"** 并安装，或手动上传插件包。

### 2. 配置凭证

| 参数 | 说明 | 示例 |
|------|------|------|
| Dify Instance URL | Dify 实例基础 URL | `https://cloud.dify.ai` |
| Email | 账号邮箱 | `admin@example.com` |
| Password | 账号密码 | - |

> ⚠️ URL 不需要包含 `/console` 或 `/api` 后缀

### 3. 开始使用

配置完成后，即可在工作流或对话中调用导出工具。

---

## 🛠️ 工具说明

### Export All Apps（导出所有应用）

批量导出工作空间中所有应用的 DSL 配置。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `app_mode` | select | ✅ | 应用类型：all / workflow / chat / agent-chat / completion |
| `version_type` | select | ✅ | 版本类型：draft / published / all |

**输出格式**：流式 JSON，逐个返回每个应用的 DSL

```json
{
  "id": "app-uuid",
  "name": "应用名称",
  "mode": "workflow",
  "version": "draft",
  "filename": "应用名称-draft.yml",
  "dsl": { ... }
}
```

### Export Single App（导出单个应用）

导出指定应用的 DSL 配置。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `app_identifier` | app-selector | ✅ | 从下拉列表选择应用 |
| `version_type` | select | ✅ | 版本类型：draft / published / all |

---

## 💡 使用场景

### 定时自动备份

创建定时触发的工作流，自动备份所有应用：

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│ 定时触发器   │───▶│ Export All Apps  │───▶│ 存储/通知   │
│ (每天 2:00)  │    │                  │    │             │
└─────────────┘    └──────────────────┘    └─────────────┘
```

### 版本归档

发布新版本前，导出当前版本作为归档备份。

### 环境迁移

1. 在开发环境导出所有应用（`version_type=published`）
2. 在生产环境使用导入功能恢复

---

## 🔧 技术细节

| 项目 | 说明 |
|------|------|
| 超时设置 | 60 秒 |
| API 认证 | 邮箱密码登录 |
| 输出格式 | 流式 JSON |
| 文件命名 | `{应用名称}-{版本标识}.yml` |

### API 端点

| 端点 | 说明 |
|------|------|
| `POST /console/api/login` | 登录认证 |
| `GET /console/api/apps` | 获取应用列表 |
| `GET /console/api/apps/{id}/export` | 导出 DSL |

---

## ❓ 常见问题

| 问题 | 解决方案 |
|------|----------|
| 登录失败 | 检查邮箱密码、确认 URL 可访问 |
| 请求超时 | 检查网络、分批导出 |
| 版本为空 | 部分应用类型不支持版本管理 |

## 🔒 隐私政策

本插件**不存储、不共享**任何用户数据。凭证仅用于直接与您指定的 Dify 实例通信。

详见 [PRIVACY.md](../PRIVACY.md)

## 📄 许可证

[Apache License 2.0](../LICENSE)

---

<p align="center">
  Made with ❤️ for Dify
</p>
