#!/home/gengtianhao/mineru-env/.venv/bin/python
"""MCP MinerU server — 完整透传 mineru CLI 参数"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ── 日志 ──────────────────────────────────────────────────
log_level = os.environ.get("MCP_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────────
MINERU_BIN = "/home/gengtianhao/mineru-env/.venv/bin/mineru"
MINERU_TIMEOUT = 3600  # 1 小时，应对超大 PDF

mcp = FastMCP("mcp-mineru")


# ── 辅助函数 ──────────────────────────────────────────────

def _get_arg(args: list[str], *flags: str) -> str | None:
    """从 args 列表中提取某个 flag 后面的值。"""
    for i, a in enumerate(args):
        if a in flags and i + 1 < len(args):
            return args[i + 1]
    return None


def _has_flag(args: list[str], *flags: str) -> bool:
    """检查 args 中是否存在某个 flag。"""
    return any(a in flags for a in args)


def _find_output_md(output_dir: str, pdf_path: str | None) -> str | None:
    """在 output_dir 下找到 mineru 生成的 .md 文件。"""
    if pdf_path:
        stem = Path(pdf_path).stem
        candidates = [
            Path(output_dir) / stem / "vlm" / f"{stem}.md",
            Path(output_dir) / stem / f"{stem}.md",
            Path(output_dir) / "vlm" / f"{stem}.md",
        ]
        for p in candidates:
            if p.is_file():
                return str(p)

    # 兜底：递归搜索
    for md in sorted(Path(output_dir).rglob("*.md")):
        return str(md)

    return None


def _list_files_tree(directory: str, max_depth: int = 3) -> str:
    """生成目录树（限制深度）。"""
    lines = []

    def walk(path: Path, depth: int = 0, prefix: str = ""):
        if depth > max_depth:
            return
        entries = sorted(path.iterdir())
        for i, p in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            if p.is_dir():
                lines.append(f"{prefix}{connector}{p.name}/")
                next_prefix = prefix + ("    " if is_last else "│   ")
                walk(p, depth + 1, next_prefix)
            else:
                size = p.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/1024/1024:.1f} MB"
                lines.append(f"{prefix}{connector}{p.name}  ({size_str})")

    walk(Path(directory))
    return "\n".join(lines)


def _file_list(vlm_dir: str) -> str:
    """生成 vlm 目录内的文件清单。"""
    path = Path(vlm_dir)
    if not path.is_dir():
        return "(目录不存在)"
    lines = []
    for f in sorted(path.iterdir()):
        if f.is_file():
            sz = f.stat().st_size / 1024
            lines.append(f"- {f.name} ({sz:.1f} KB)")
        elif f.is_dir():
            cnt = len(list(f.rglob("*"))) if f.name == "images" else len(list(f.iterdir()))
            lines.append(f"- {f.name}/ ({cnt} files)")
    return "\n".join(lines)


# ── MCP Tools ──────────────────────────────────────────────

@mcp.tool()
async def mineru_parse(args: list[str]) -> str:
    """使用 MinerU 解析 PDF/文档，透传全部 CLI 参数。

    本 tool 不做参数解析——你传入什么参数，它原封不动地传给 mineru CLI。
    这样 mineru 升级新增任何 CLI 选项都不需要更新 server。

    Args:
        args: mineru CLI 参数列表。
              必需参数（由 mineru 要求）：
                -p / --path <path>       — 输入文件或目录（pdf/image/docx/pptx/xlsx）
                -o / --output <dir>      — 输出目录
              常用可选参数：
                -b / --backend           — 解析后端：pipeline / vlm-engine / hybrid-engine / vlm-http-client / hybrid-http-client（默认 vlm-engine）
                --effort                 — 解析力度：medium / high（仅 hybrid-* 和 vlm-engine 有效，默认 high）
                -m / --method            — 解析方法：auto / txt / ocr（仅 pipeline 和 hybrid-*）
                -l / --lang              — 文档语言（改善 OCR 精度，仅 pipeline）
                -u / --url               — 远程 API URL（vlm/hybrid-http-client 时必填）
                -s / --start <int>       — 起始页码（从 0 开始）
                -e / --end <int>         — 结束页码（从 0 开始）
                -f / --formula           — 公式解析，默认 True
                -t / --table             — 表格解析，默认 True
                --image-analysis         — 启用图片/图表分析，默认 True
                --client-side-output-generation — 本地生成 markdown
                --api-url                — 使用已有的 mineru-api 服务
                -v / --version           — 显示版本
                --help                   — 显示帮助

    示例:
        ["-p", "/path/to/doc.pdf", "-o", "/tmp/out", "--backend", "vlm-engine", "--effort", "high"]
        ["-p", "/path/to/dir", "-o", "/tmp/out", "--backend", "hybrid-engine"]
        ["-p", "/path/to/doc.pdf", "-o", "/tmp/out", "--api-url", "http://127.0.0.1:8000"]
        ["--help"]
    """
    if not args:
        return "错误: 参数列表为空。请至少提供 -p 和 -o 参数。"

    # 提取 -p 和 -o 用于定位输出文件
    pdf_path = _get_arg(args, "-p", "--path")
    output_dir = _get_arg(args, "-o", "--output")

    # 处理 --help 或 --version
    if _has_flag(args, "--help"):
        cmd = [MINERU_BIN, "--help"]
    elif _has_flag(args, "-v", "--version"):
        cmd = [MINERU_BIN, "--version"]
    else:
        # 注入默认参数（用户未指定时使用 vlm-engine + high effort）
        if not _has_flag(args, "-b", "--backend"):
            args = list(args) + ["--backend", "vlm-engine"]
        if not _has_flag(args, "--effort"):
            args = list(args) + ["--effort", "high"]
        cmd = [MINERU_BIN] + args

    logger.info(f"执行: {' '.join(cmd)}")
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        # 传递 venv 环境给子进程（mineru 内部 spawn 的子进程依赖 venv 的 PATH）
        env = os.environ.copy()
        venv_bin = os.path.join(os.path.dirname(MINERU_BIN))
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
        env["VIRTUAL_ENV"] = os.path.dirname(venv_bin)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=MINERU_TIMEOUT
        )

        if process.returncode != 0:
            err = stderr_bytes.decode("utf-8", errors="replace")[:3000]
            logger.error(f"MinerU 失败 (code={process.returncode}): {err[:200]}")
            return f"MinerU 执行失败 (退出码 {process.returncode}):\n{err}"

        logger.info("MinerU 执行成功")

    except asyncio.TimeoutError:
        return f"错误: MinerU 执行超时 ({MINERU_TIMEOUT} 秒)"
    except Exception as e:
        logger.error(f"执行出错: {e}")
        return f"执行出错: {str(e)}"

    # 非解析类命令（--help / --version）直接返回 stdout
    if _has_flag(args, "--help", "-v", "--version"):
        out = stdout_bytes.decode("utf-8", errors="replace")
        return out

    # 查找生成的 markdown
    if not output_dir:
        return "MinerU 执行完成，但未指定 -o 参数，无法定位输出文件。"

    md_file = _find_output_md(output_dir, pdf_path)

    if not md_file:
        tree = _list_files_tree(output_dir)
        return (
            f"MinerU 执行完成，但未找到 markdown 输出文件。\n"
            f"输出目录结构:\n{tree}"
        )

    # 返回 markdown 内容
    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()

    vlm_dir = str(Path(md_file).parent)
    files_idx = _file_list(vlm_dir)

    return (
        f"# MinerU 解析结果\n\n"
        f"**命令**: `{' '.join(cmd)}`\n"
        f"**输出目录**: {output_dir}\n\n"
        f"## 文件清单\n\n{files_idx}\n\n"
        f"## Markdown 内容\n\n{content}"
    )


@mcp.tool()
async def mineru_read_result(result_dir: str) -> str:
    """读取 MinerU 已有解析结果。

    Args:
        result_dir: 之前传给 mineru_parse 的 -o / --output 目录
    """
    result_dir = os.path.abspath(result_dir)

    if not os.path.isdir(result_dir):
        return f"错误: 目录不存在: {result_dir}"

    # 查找所有 vlm/ 子目录
    vlm_dirs = sorted(Path(result_dir).rglob("vlm"))
    if not vlm_dirs:
        tree = _list_files_tree(result_dir)
        return f"目录下未找到 vlm/ 结果子目录:\n{tree}"

    results = []
    for vlm_dir in vlm_dirs:
        md_files = list(vlm_dir.glob("*.md"))
        if not md_files:
            continue

        md_file = md_files[0]
        pdf_stem = md_file.stem

        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        files_idx = _file_list(str(vlm_dir))

        # 读取 content_list.json 摘要
        cl_json = vlm_dir / f"{pdf_stem}_content_list.json"
        summary = ""
        if cl_json.exists():
            try:
                with open(cl_json) as f:
                    cl_data = json.load(f)
                summary = f"**结构化元素**: {len(cl_data) if isinstance(cl_data, list) else '已生成'}\n"
            except Exception:
                pass

        results.append(
            f"## 结果: {pdf_stem}\n\n"
            f"**输出目录**: {vlm_dir.parent}\n"
            f"{summary}"
            f"{files_idx}\n\n"
            f"### Markdown 内容\n\n{content}"
        )

    if not results:
        return f"找到了 vlm/ 子目录但未发现 .md 文件:\n{_list_files_tree(result_dir)}"

    return "\n\n---\n\n".join(results)


# ── 入口 ──────────────────────────────────────────────────

def main():
    logger.info("启动 MCP MinerU 服务器 (透传模式)...")
    logger.info(f"mineru: {MINERU_BIN} 存在={os.path.isfile(MINERU_BIN)}")
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("关闭中...")
    except Exception as e:
        logger.error(f"出错: {e}")
        raise


if __name__ == "__main__":
    main()
