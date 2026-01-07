# Privacy Policy / 隐私政策

**Last Updated / 最后更新**: 2026-01-07

## English

### Introduction

This privacy policy describes how the **Dify Backup Plugin** ("Plugin") handles user data. We are committed to protecting your privacy and ensuring you understand how your information is used.

### Data Collection

The Plugin collects and processes the following types of data:

| Data Type | Purpose | Storage |
|-----------|---------|---------|
| **Email Address** | Authentication with Dify Console API | Not stored by plugin |
| **Password** | Authentication with Dify Console API | Not stored by plugin |
| **Dify Instance URL** | API endpoint configuration | Not stored by plugin |
| **Application DSL** | Export and backup operations | Not stored by plugin |

### How Data is Used

1. **Authentication**: Your email and password are used solely to authenticate with the Dify Console API. These credentials are transmitted directly to your specified Dify instance and are not stored, logged, or transmitted elsewhere by this plugin.

2. **API Requests**: The plugin makes HTTP requests to your Dify instance to:
   - Login and obtain access tokens
   - Retrieve application lists
   - Export application DSL configurations

3. **Data Processing**: All data processing occurs in real-time. The plugin does not maintain any persistent storage of your credentials or exported data.

### Data Sharing

- **No Third-Party Sharing**: This plugin does not share any data with third parties.
- **Direct Communication Only**: All data is transmitted directly between the Dify platform and your specified Dify instance.
- **No Analytics**: This plugin does not implement any analytics or tracking mechanisms.

### Data Security

- Credentials are transmitted over HTTPS when your Dify instance supports it.
- No credentials or sensitive data are logged or persisted.
- Session tokens are managed in memory and cleared after each operation.

### User Rights

You have the right to:
- Know what data is being processed
- Control which Dify instance receives your credentials
- Stop using the plugin at any time without data retention concerns

### Contact

For questions about this privacy policy, please contact:
- **Author**: [leslie2046](https://github.com/leslie2046)
- **Repository**: [dify_backup_plugin](https://github.com/leslie2046/dify_backup_plugin)

---

## 中文

### 简介

本隐私政策说明了 **Dify 备份插件**（"插件"）如何处理用户数据。我们致力于保护您的隐私，并确保您了解您的信息如何被使用。

### 数据收集

本插件收集和处理以下类型的数据：

| 数据类型 | 用途 | 存储方式 |
|----------|------|----------|
| **电子邮箱** | Dify Console API 认证 | 插件不存储 |
| **密码** | Dify Console API 认证 | 插件不存储 |
| **Dify 实例 URL** | API 端点配置 | 插件不存储 |
| **应用 DSL** | 导出和备份操作 | 插件不存储 |

### 数据使用方式

1. **认证**：您的邮箱和密码仅用于与 Dify Console API 进行认证。这些凭证直接传输到您指定的 Dify 实例，本插件不会存储、记录或传输到其他任何地方。

2. **API 请求**：插件向您的 Dify 实例发送 HTTP 请求以：
   - 登录并获取访问令牌
   - 获取应用列表
   - 导出应用 DSL 配置

3. **数据处理**：所有数据处理都是实时进行的。插件不会持久存储您的凭证或导出的数据。

### 数据共享

- **不与第三方共享**：本插件不会与任何第三方共享数据。
- **仅直接通信**：所有数据仅在 Dify 平台与您指定的 Dify 实例之间直接传输。
- **无分析追踪**：本插件不实现任何分析或跟踪机制。

### 数据安全

- 当您的 Dify 实例支持时，凭证通过 HTTPS 传输。
- 不会记录或持久化任何凭证或敏感数据。
- 会话令牌在内存中管理，每次操作后清除。

### 用户权利

您有权：
- 了解正在处理哪些数据
- 控制哪个 Dify 实例接收您的凭证
- 随时停止使用插件，无需担心数据保留问题

### 联系方式

如对本隐私政策有任何疑问，请联系：
- **作者**: [leslie2046](https://github.com/leslie2046)
- **仓库**: [dify_backup_plugin](https://github.com/leslie2046/dify_backup_plugin)
