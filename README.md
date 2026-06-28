# Install MinerU
```bash
uv pip install -U "mineru[all]"
```
---

## MCP 配置

### reasonix
```toml
[[plugins]]
name    = "mineru"
command = "/home/gengtianhao/mineru-env/.venv/bin/python"
args    = ["/home/gengtianhao/mineru-env/server.py"]
auto_start = true
```

### Claude Desktop / Cline / 通用 MCP 客户端
```json
{
  "mcpServers": {
    "mineru": {
      "command": "/home/gengtianhao/mineru-env/.venv/bin/python",
      "args": ["/home/gengtianhao/mineru-env/server.py"]
    }
  }
}
```

## AI Tool 使用指南

本 MCP 提供两个 tool，AI 应优先使用 `mineru_parse`，仅在需要重读已有结果时使用 `mineru_read_result`。

### `mineru_parse` — 解析文档

将 PDF/图片/Office 文档解析为 Markdown。参数采用 CLI 透传模式，直接传入 mineru 原生命令行参数。

**默认值**：`--backend vlm-engine`、`--effort high`（AI 无需重复传入，除非需要覆盖）。

**调用示例**：

```json
// 最简调用（使用默认 backend + effort）
["-p", "/path/to/doc.pdf", "-o", "/tmp/output"]

// 覆盖默认值
["-p", "/path/to/doc.pdf", "-o", "/tmp/output", "--backend", "pipeline"]

// 指定页码范围
["-p", "/path/to/doc.pdf", "-o", "/tmp/output", "-s", "0", "-e", "10"]

// 批量解析整个目录
["-p", "/path/to/pdf_dir", "-o", "/tmp/output"]

// 查看帮助
["--help"]
```

**返回值**：包含解析后的 Markdown 全文 + 输出目录的文件清单。

### `mineru_read_result` — 读取已有结果

从之前的输出目录中重新读取解析结果，不重新执行解析。

```json
// result_dir 即之前 mineru_parse 的 -o 参数
{ "result_dir": "/tmp/output" }
```

**使用时机**：AI 需要回顾之前的解析结果时使用，避免重复解析。

### 典型工作流

1. AI 收到用户 PDF 解析需求
2. 调用 `mineru_parse`，传入 `-p`（文件路径）和 `-o`（输出目录）
3. 返回的 Markdown 内容直接用于后续问答/分析
4. 如需回顾，调用 `mineru_read_result` 读取已有结果
