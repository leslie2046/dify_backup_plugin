# Dify Backup Plugin

**作者：** [leslie2046](https://github.com/leslie2046/dify_backup_plugin)  
**版本：** 0.0.4  
**类型：** tool

<p align="center">
  <img src="../_assets/icon.svg" alt="Dify Backup" width="100" height="100">
</p>

> 🔄 一键备份和导出 Dify 应用 DSL 配置、标注数据与知识库文件

---

## ✨ 功能特性

- 📦 **批量导出应用** - 导出工作空间中所有应用的 DSL 配置
- 🎯 **单应用导出** - 从下拉列表选择指定应用导出 DSL
- 🔀 **版本支持** - 草稿版本 / 已发布版本 / 全部版本
- 🏷️ **类型过滤** - Workflow / Chat / Agent 等多种类型
- 📝 **批量导出标注** - 将所有应用的标注问答对导出为 CSV
- 🗂️ **导出知识库文件** - 将知识库原始文件打包为 ZIP，支持多选知识库

## 🚀 快速开始

### 1. 安装插件

在 Dify 插件市场搜索 **"Dify Backup"** 并安装，或手动上传插件包。

### 2. 配置凭证

| 参数 | 说明 | 示例 |
|------|------|------|
| Dify Instance URL | Dify 实例基础 URL | `https://cloud.dify.ai` |
| Email | 账号邮箱 | `admin@example.com` |
| Password | 账号密码 | - |

> ⚠️ URL 末尾不需要包含 `/console` 或 `/api` 等路径

### 3. 开始使用

配置完成后，即可在工作流或对话中调用以下导出工具。

---

## 🛠️ 工具说明

### Export All Apps（导出所有应用）

批量导出工作空间中所有应用的 DSL 配置。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `app_mode` | select | ✅ | 应用类型：all / workflow / advanced-chat / chat / agent-chat / completion |
| `version_type` | select | ✅ | 版本类型：draft（草稿）/ published（已发布）/ all（全部） |

**输出格式**：流式 JSON，实时逐个返回每个应用的 DSL

```json
{
  "id": "app-uuid",
  "name": "应用名称",
  "mode": "workflow",
  "version": "draft",
  "filename": "应用名称-draft.yml",
  "dsl": "..."
}
```

---

### Export Single App（导出单个应用）

通过下拉选择器导出指定应用的 DSL 配置。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `app_identifier` | app-selector | ✅ | 从下拉列表选择目标应用 |
| `version_type` | select | ✅ | 版本类型：draft / published / all |

---

### Export All Annotations（导出所有应用标注）

批量导出工作空间中所有应用的标注（问答对）为 CSV 文件。

- **无需参数** - 一键导出，零配置
- **智能过滤** - 自动跳过无标注的应用
- **CSV 格式** - 每个应用导出为独立文件：`{应用名}-annotations.csv`

**输出格式**：流式 JSON，逐个返回每个有标注应用的 CSV 内容

```json
{
  "name": "应用名称",
  "filename": "应用名称-annotations.csv",
  "content": "\"question\",\"answer\"\n\"问题1\",\"回答1\"\n..."
}
```

---

### Export Dataset Files（导出知识库文件）⭐ 新增

将一个或多个知识库的原始上传文件打包为 ZIP 压缩包。  
**支持多选知识库 —— `dataset_ids` 留空则导出所有知识库。**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `dataset_ids` | string | ❌ | _（全部）_ | 逗号分隔的知识库 ID，留空则导出**所有**知识库 |
| `include_segments` | boolean | ❌ | `false` | 启用后，对无法下载原始文件的文档，使用已索引的分段内容降级导出为 `.txt` |

**执行流程：**

1. 获取所有知识库列表，根据 `dataset_ids` 过滤（为空则取全部）
2. 对每个知识库，获取其文档列表并下载原始上传文件
3. 每个知识库单独打包为一个 ZIP 文件：`{知识库名}-documents.zip`
4. 流式返回各 ZIP 文件 blob，并附带结构化文件清单

**返回内容：**
- 每个知识库一个 ZIP 文件 blob（流式）
- 包含完整文件清单的摘要文本
- 结构化 JSON 清单

```json
{
  "total_datasets": 3,
  "total_files": 12,
  "failed_datasets": [],
  "file_list": [
    "📂 我的知识库 → 我的知识库-documents.zip",
    "   └─ 文档1.pdf",
    "   └─ 文档2.docx"
  ]
}
```

> 💡 **`include_segments` 降级说明**：若文档是通过 API 文本方式导入（而非文件上传），启用此选项后，工具会将该文档的索引分段内容导出为 `.txt` 文件并放入 ZIP。

---

## 💡 使用场景

### 定时自动备份

创建定时触发的工作流，自动备份所有应用：

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│  定时触发器  │───▶│ Export All Apps  │───▶│  存储/通知  │
│ (每天 2:00) │    │                  │    │             │
└─────────────┘    └──────────────────┘    └─────────────┘
```

### 知识库归档备份

在重构知识库前，导出指定知识库的所有原始文件：

```
┌──────────────────┐    ┌──────────────────────┐    ┌───────────┐
│  指定知识库 ID   │───▶│ Export Dataset Files │───▶│  归档存储 │
│  (逗号分隔多个)  │    │  → 每库一个 ZIP      │    │           │
└──────────────────┘    └──────────────────────┘    └───────────┘
```

### 发布前版本归档

发布新版本前，先导出当前版本作为历史归档。

### 跨环境迁移

1. 在开发环境导出所有应用（`version_type=published`）
2. 在生产环境通过 Dify 导入功能恢复

---

## 🔧 技术细节

| 项目 | 说明 |
|------|------|
| 超时设置 | 60 秒 |
| API 认证 | 邮箱密码登录，自动管理 Session |
| 输出格式 | 流式 JSON + 文件 Blob |
| 应用文件命名 | `{应用名称}-{版本标识}.yml` |
| 知识库 ZIP 命名 | `{知识库名称}-documents.zip` |

### 使用的 API 端点

| 端点 | 说明 |
|------|------|
| `POST /console/api/login` | 登录认证 |
| `GET /console/api/apps` | 获取应用列表 |
| `GET /console/api/apps/{id}/export` | 导出应用 DSL |
| `GET /console/api/apps/{id}/annotations` | 获取应用标注 |
| `GET /console/api/datasets` | 获取知识库列表 |
| `GET /console/api/datasets/{id}/documents` | 获取知识库文档列表 |
| `GET /console/api/files/{file_id}/file-preview` | 下载原始文件 |

---

## ❓ 常见问题

| 问题 | 解决方案 |
|------|----------|
| 登录失败 | 检查邮箱密码是否正确，确认 Dify 实例 URL 可访问 |
| 请求超时 | 检查网络连接，或指定 `dataset_ids` 分批导出 |
| 版本列表为空 | 部分应用类型不支持版本管理，属于正常现象 |
| 知识库文件无法下载 | 启用 `include_segments` 选项以降级为分段文本导出；原始文件下载要求文档通过文件上传方式导入 |

## 🔒 隐私政策

本插件**不存储、不共享**任何用户数据。填写的凭证仅用于直接与您指定的 Dify 实例通信，不经过任何第三方。

详见 [PRIVACY.md](../PRIVACY.md)

## 📄 许可证

[Apache License 2.0](../LICENSE)

---

<p align="center">
  Made with ❤️ for Dify
</p>
