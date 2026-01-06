# Dify Backup Plugin

A Dify official plugin for backing up and exporting application DSL configurations.

## Features

- **Export All Apps**: Batch export all applications in your workspace
- **Export Single App**: Export a specific application by ID or name
- **Flexible Filtering**: Filter apps by type (workflow, chat, agent-chat, etc.)
- **Security Options**: Choose whether to include secrets in exports
- **Multiple Output Formats**: Summary, full DSL content, or JSON with metadata

## Installation

1. Install the plugin in your Dify instance
2. Configure the plugin with your Dify API credentials

## Tools

### 1. Export All Apps

Export DSL configurations for all applications in your workspace.

**Parameters:**
- `dify_api_base_url` (required): Your Dify API base URL (e.g., `https://api.dify.ai`)
- `api_key` (required): Your Dify Console API key
- `app_mode` (optional): Filter by app type (all, workflow, chat, etc.)
- `include_secret` (optional): Include secrets in export (default: false)
- `output_format` (optional): Output format - summary or full (default: summary)

**Example Usage:**
```
"Export all workflow applications"
"Export all apps and show me a summary"
```

### 2. Export App

Export DSL configuration for a specific application.

**Parameters:**
- `dify_api_base_url` (required): Your Dify API base URL
- `api_key` (required): Your Dify Console API key
- `app_identifier` (required): App ID (UUID) or app name
- `include_secret` (optional): Include secrets in export (default: false)
- `return_format` (optional): Return format - yaml or json (default: yaml)

**Example Usage:**
```
"Export the app named 'My Workflow'"
"Export app with ID cf7d7b5b-ae04-476a-886d-6a5282fac8ef"
```

## Authentication

This plugin uses Dify Console API for authentication. You need to provide:

1. **API Base URL**: The base URL of your Dify instance
   - Cloud: `https://api.dify.ai`
   - Self-hosted: `http://your-domain/api` or `http://localhost/api`

2. **API Key**: Your Dify Console API key (JWT token)
   - Obtain from Dify Console → Settings → API Keys
   - Or use your login JWT token

## Security Notes

⚠️ **Important:**
- By default, secrets are NOT included in exports (`include_secret=false`)
- Only enable `include_secret=true` if you need to export sensitive information
- Keep your API keys secure and never share them publicly
- Exported configurations may contain sensitive data - handle with care

## Use Cases

### Automated Backup

Create a workflow with a scheduled trigger to automatically backup all apps:

1. Add a Schedule Trigger node (e.g., daily at 2 AM)
2. Add "Export All Apps" tool node
3. Configure parameters:
   - `app_mode`: all
   - `include_secret`: false
   - `output_format`: summary
4. Add notification or storage nodes as needed

### Version Control

Export apps before making changes to track versions:

```
User: "Export 'My Workflow' app before I make changes"
Agent: [Calls Export App tool]
Agent: "Exported successfully. You can now make changes safely."
```

### Migration Preparation

Export all apps when preparing to migrate to a new environment:

```
User: "Export all my applications for migration"
Agent: [Calls Export All Apps tool with output_format=full]
Agent: "Exported 10 applications. Ready for migration."
```

## Troubleshooting

### Authentication Errors

- Verify your API key is correct
- Check that the API base URL is accessible
- Ensure your API key has necessary permissions

### App Not Found

- Verify the app ID or name is correct
- Check that the app exists in your workspace
- Ensure you have access to the app

### Network Errors

- Check your network connection
- Verify the Dify instance is accessible
- Check firewall settings if using self-hosted Dify

## API Endpoints Used

This plugin calls the following Dify Console APIs:

- `GET /console/api/apps` - List applications
- `GET /console/api/apps/{app_id}` - Get app details
- `GET /console/api/apps/{app_id}/export` - Export app DSL

## Version

- **Version**: 1.0.0
- **Minimum Dify Version**: 1.7.0
- **Author**: langgenius

## License

Apache License 2.0

## Support

For issues or questions:
- Check the troubleshooting section above
- Review Dify documentation
- Submit an issue to the dify-official-plugins repository
