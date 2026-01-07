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

### 配置凭证

| 参数 | 说明 |
|------|------|
| Dify Instance URL | Dify 实例地址（如 `https://cloud.dify.ai`） |
| Email | 账号邮箱 |
| Password | 账号密码 |

### 工具参数

**Export All Apps**

| 参数 | 默认值 | 选项 |
|------|--------|------|
| `app_mode` | all | all / workflow / chat / agent-chat / completion |
| `version_type` | draft | draft / published / all |

**Export Single App**

| 参数 | 说明 |
|------|------|
| `app_identifier` | 从下拉列表选择应用 |
| `version_type` | draft / published / all |

## 💡 使用场景

| 场景 | 配置建议 |
|------|----------|
| 定时备份 | `version_type=all` 同时备份草稿和发布版本 |
| 环境迁移 | `version_type=published` 仅导出生产版本 |
| 版本归档 | 发布前导出当前版本作为备份 |

## 🔧 技术说明

- **超时设置**: 60 秒
- **API 认证**: 邮箱密码登录
- **输出格式**: 流式 JSON，逐个返回应用 DSL

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
