# MinerU MCP Server

## 安装

```bash
uv pip install -U "mineru[all]"
```

## MCP 配置

```toml
# reasonix
[[plugins]]
name    = "mineru"
command = "python"
args    = ["path/to/mineru-env/server.py"]
auto_start = true
```

```json
// Claude Desktop / Cline / 通用 MCP 客户端
{
  "mcpServers": {
    "mineru": {
      "command": "python",
      "args": ["path/to/mineru-env/server.py"]
    }
  }
}
```

> 注意：`command` 需指向 mineru 所在 venv 的 python（如 `path/to/.venv/bin/python`），确保能 import `mcp` 和找到 `mineru` 二进制。

## AI Tool 使用指南

本 MCP 提供两个 tool。

### `mineru_parse` — 解析文档

将 PDF/图片/Office 文档解析为 Markdown。参数透传 mineru CLI，**默认 `--backend vlm-engine --effort high`**，无需重复传入。

```json
// 最简调用
["-p", "/path/to/doc.pdf", "-o", "/tmp/output"]

// 指定页码范围
["-p", "/path/to/doc.pdf", "-o", "/tmp/output", "-s", "0", "-e", "10"]

// 批量解析目录
["-p", "/path/to/pdf_dir", "-o", "/tmp/output"]

// 查看帮助
["--help"]
```

### `mineru_read_result` — 读取已有结果

从之前的输出目录重读解析结果，避免重复解析。

```json
{ "result_dir": "/tmp/output" }
```
