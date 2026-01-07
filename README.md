# Dify Backup Plugin

**Author:** [leslie2046](https://github.com/leslie2046/dify_backup_plugin)  
**Version:** 0.0.1  
**Type:** tool

<p align="center">
  <img src="_assets/icon.svg" alt="Dify Backup Logo" width="120" height="120">
</p>

<p align="center">
  <strong>🔄 备份和导出 Dify 应用的强大插件工具</strong>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#工具说明">工具说明</a> •
  <a href="#使用场景">使用场景</a> •
  <a href="#常见问题">常见问题</a>
</p>

---

## ✨ 功能特性

- **🗂️ 批量导出** - 一键导出工作空间中的所有应用
- **📦 单应用导出** - 通过下拉选择器精准导出指定应用
- **🔀 版本选择** - 支持导出草稿版本、已发布版本或全部版本
- **🏷️ 类型过滤** - 按应用类型筛选（Workflow、Chat、Agent 等）
- **📝 JSON 流式输出** - 逐个返回应用 DSL，适合大批量导出
- **🔐 账号登录认证** - 使用 Dify 账号密码安全登录

## 📋 前置要求

- **Dify 版本**: >= 1.7.0
- **Python 版本**: 3.12+
- **Dify 账号**: 需要有权限访问目标工作空间的账号

## 🚀 快速开始

### 1. 安装插件

在 Dify 插件市场中搜索 **"Dify Backup"** 并安装，或手动上传插件包。

### 2. 配置凭证

在插件设置中填写以下信息：

| 参数 | 说明 | 示例 |
|------|------|------|
| **Dify Instance URL** | Dify 实例的基础 URL | `https://cloud.dify.ai` 或 `http://localhost` |
| **Email** | Dify 账号邮箱 | `admin@example.com` |
| **Password** | Dify 账号密码 | `your-password` |

> ⚠️ **注意**: URL 不需要包含 `/console` 或 `/api` 后缀

### 3. 开始使用

配置完成后，即可在工作流或对话中调用导出工具。

---

## 🛠️ 工具说明

### Export All Apps（导出所有应用）

批量导出工作空间中所有应用的 DSL 配置。

#### 参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `app_mode` | select | ❌ | `all` | 应用类型过滤 |
| `version_type` | select | ❌ | `draft` | 导出版本类型 |

#### 应用类型选项

- `all` - 所有类型
- `workflow` - 工作流
- `advanced-chat` - 高级聊天
- `chat` - 聊天
- `agent-chat` - Agent 聊天
- `completion` - 文本补全

#### 版本类型选项

- `draft` - 仅草稿版本
- `published` - 仅已发布版本
- `all` - 所有版本（草稿 + 已发布）

#### 输出格式

工具会以 **流式 JSON** 的形式逐个返回每个应用的导出结果：

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

最后返回导出摘要：

```
✅ 批量导出完成

成功应用数: 10
总文件数: 15

❌ 部分应用处理失败:
- 应用A: 错误信息
```

---

### Export Single App（导出单个应用）

导出指定应用的 DSL 配置。

#### 参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `app_identifier` | app-selector | ✅ | - | 从下拉列表选择应用 |
| `version_type` | select | ❌ | `draft` | 导出版本类型 |

#### 输出格式

与批量导出相同，以 JSON 格式返回应用的 DSL 配置。

---

## 💡 使用场景

### 🔄 定时自动备份

创建定时触发的工作流，自动备份所有应用：

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│ 定时触发器   │───▶│ Export All Apps  │───▶│ 存储/通知   │
│ (每天 2:00)  │    │                  │    │             │
└─────────────┘    └──────────────────┘    └─────────────┘
```

**配置建议**：
- `version_type`: `all`（同时备份草稿和已发布版本）
- `app_mode`: `all`（备份所有类型应用）

### 📋 版本归档

在发布新版本前，导出当前已发布版本作为归档：

```
用户: "导出 '客服机器人' 的已发布版本"
工具: [调用 Export Single App, version_type=published]
结果: 返回已发布版本的完整 DSL
```

### 🚚 环境迁移

将应用从开发环境迁移到生产环境：

1. 在开发环境导出所有应用
2. 在生产环境使用导入功能恢复

```
用户: "导出所有工作流应用，准备迁移到生产环境"
工具: [调用 Export All Apps, app_mode=workflow, version_type=published]
结果: 返回所有工作流应用的 DSL 配置
```

### 🔍 配置审计

定期导出应用配置用于审计和对比：

```
用户: "导出所有 Agent 应用的草稿版本"
工具: [调用 Export All Apps, app_mode=agent-chat, version_type=draft]
结果: 返回所有 Agent 应用的草稿配置
```

---

## 🔧 技术细节

### API 端点

插件使用以下 Dify Console API：

| 端点 | 说明 |
|------|------|
| `POST /console/api/login` | 账号登录认证 |
| `GET /console/api/apps` | 获取应用列表 |
| `GET /console/api/apps/{app_id}` | 获取应用详情 |
| `GET /console/api/apps/{app_id}/workflows` | 获取应用版本列表 |
| `GET /console/api/apps/{app_id}/export` | 导出应用 DSL |

### 超时配置

所有 API 请求的默认超时时间为 **60 秒**，可满足大多数网络环境需求。

### 版本命名规则

导出文件名格式：`{应用名称}-{版本标识}.yml`

- 草稿版本：`我的应用-draft.yml`
- 已发布版本（有标记名）：`我的应用-生产版本.yml`
- 已发布版本（无标记名）：`我的应用-未命名-202601071000.yml`

---

## ❓ 常见问题

### 认证失败

**症状**: 提示登录失败或凭证无效

**排查步骤**:
1. ✅ 确认邮箱和密码正确
2. ✅ 确认 Dify 实例 URL 可访问
3. ✅ 检查账号是否有权限访问目标工作空间
4. ✅ 如使用私有部署，确认防火墙允许访问

### 导出超时

**症状**: 提示 `Read timed out`

**解决方案**:
1. 检查网络连接稳定性
2. 如果应用数量较多，可分批导出
3. 确认 Dify 服务器响应正常

### 找不到已发布版本

**症状**: 导出已发布版本时返回空

**说明**: 
- 部分应用类型（如 Chat）可能不支持版本管理
- 新创建的应用可能还没有发布过版本
- 插件会自动尝试降级获取当前版本

### 部分应用导出失败

**症状**: 摘要中显示部分应用处理失败

**可能原因**:
- 应用正在编辑中
- 应用权限不足
- 应用配置损坏

**建议**: 查看错误信息，单独处理失败的应用

---

## 📄 版本信息

| 项目 | 版本 |
|------|------|
| **插件版本** | 0.0.1 |
| **最低 Dify 版本** | 1.7.0 |
| **作者** | leslie2046 |
| **许可证** | Apache License 2.0 |

---

## 🤝 贡献与支持

如有问题或建议：

1. 📖 查阅本文档的常见问题部分
2. 📚 参考 [Dify 官方文档](https://docs.dify.ai)
3. 🐛 提交 Issue 到本仓库
4. 💬 加入 Dify 社区讨论

---

<p align="center">
  Made with ❤️ for the Dify Community
</p>
