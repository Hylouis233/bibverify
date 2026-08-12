# Bibverify

<!-- mcp-name: io.github.Hylouis233/bibverify -->

<p align="center">
  <strong>查证、修复并补全文献引用，让 BibTeX 更可信。</strong>
</p>

<p align="center">
  <a href="README_EN.md">English</a> · <a href="#快速开始">快速开始</a> · <a href="#mcp-与-ai-助手">MCP</a> · <a href="#参与开发">参与开发</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/bibverify/"><img src="https://img.shields.io/pypi/v/bibverify.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/bibverify/"><img src="https://img.shields.io/pypi/pyversions/bibverify.svg" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://github.com/Hylouis233/bibverify/actions/workflows/ci.yml"><img src="https://github.com/Hylouis233/bibverify/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

Bibverify 是一个面向研究者、编辑和 AI 助手的 BibTeX 文献验证工具。它优先使用 DOI 精确查询，并根据 PMID、arXiv 标识和学科线索动态调整数据源顺序；查询结果经过标题相似度校验后，才会用于生成更新建议。

原始 `.bib` 文件不会被原地覆盖。Bibverify 会在指定输出目录中生成报告、逐字节备份、更新建议和问题条目文件。

## 主要能力

- DOI 优先：有 DOI 时先查询 Crossref 精确接口，再按需回退到标题检索。
- 多数据源：支持 Crossref、OpenAlex、Semantic Scholar、PubMed、Europe PMC、CORE、DBLP、arXiv、bioRxiv 等。
- 降低误匹配：结合字符序列、词元重叠和长度比例计算标题相似度，阈值可配置。
- 稳健网络层：复用连接，对 `429/5xx` 自动重试和指数退避，并尊重 `Retry-After`。
- 跨平台文件处理：支持 Windows、macOS 和 Linux；正确处理空格、中文路径、UTF-8 BOM 与 CRLF。
- 适合自动化：提供 JSON 输出、稳定退出码、Python API 和基于官方 SDK 的 MCP 服务。
- 安全输出：使用原子写入；备份保留原始字节与换行，不会悄悄改写源文件。

## 系统要求

- Python 3.11–3.14
- Windows、macOS 或 Linux
- 访问学术元数据 API 的网络连接

项目的 GitHub Actions 会在三种操作系统和四个 Python 版本上运行测试。

## 快速开始

### 安装

命令行工具推荐使用 `pipx` 或 `uv tool`，它们会创建独立环境：

```bash
pipx install bibverify
```

```bash
uv tool install bibverify
```

也可以在虚拟环境中安装：

```bash
python -m pip install --upgrade bibverify
```

每个版本还会在 GitHub Releases 提供由对应系统原生构建并冒烟测试的 Windows、macOS 和 Linux 独立程序包。

### 由 DOI 生成 BibTeX

```bash
bibverify doi 10.1038/nature12373 --key example2013
```

机器可读输出：

```bash
bibverify doi 10.1038/nature12373 --json
```

### 验证 `.bib` 文件

先创建配置：

```bash
bibverify config init
```

将 `references.bib` 放在配置文件旁边，然后运行：

```bash
bibverify check --config config.json
```

也可以直接覆盖输入文件和输出目录：

```bash
bibverify check references.bib --config config.json --output-dir bibverify-output
```

PowerShell 示例：

```powershell
py -m bibverify check '.\文献\references.bib' --output-dir '.\验证结果'
```

旧版调用方式仍然可用，但新脚本建议使用子命令：

```bash
bibverify config.json
bibverify --doi 10.1038/nature12373 --key example2013
```

## 配置

最小配置如下：

```json
{
  "language": "CN",
  "bib_file": "references.bib",
  "encoding": "auto",
  "output_dir": "bibverify-output",
  "user_info": {
    "email": "your_email@example.com",
    "app_name": "Bibverify"
  }
}
```

完整示例见 [`config_template.json`](config_template.json)。

需要注意的路径规则：

- `bib_file` 和 `output_dir` 的相对路径均相对于 `config.json` 所在目录，而不是当前终端目录。
- 没有设置 `output_dir` 时，输出写到输入 `.bib` 文件旁边。
- `encoding: "auto"` 依次尝试 UTF-8 BOM、UTF-8 和 GB18030，不再用 Latin-1 掩盖未知编码。

### API 密钥与邮箱

密钥可以写入本地配置，但更推荐环境变量；这样不会误提交到 Git：

| 环境变量 | 用途 |
|---|---|
| `BIBVERIFY_EMAIL` | Crossref polite pool 和联系信息 |
| `BIBVERIFY_OPENALEX_API_KEY` | OpenAlex |
| `BIBVERIFY_SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar |
| `BIBVERIFY_PUBMED_API_KEY` | PubMed/NCBI |
| `BIBVERIFY_CORE_API_KEY` | CORE |

PowerShell：

```powershell
$env:BIBVERIFY_EMAIL = 'you@example.com'
$env:BIBVERIFY_OPENALEX_API_KEY = '...'
bibverify check --config config.json
```

Bash/Zsh：

```bash
export BIBVERIFY_EMAIL='you@example.com'
export BIBVERIFY_OPENALEX_API_KEY='...'
bibverify check --config config.json
```

### 查询与匹配设置

```json
{
  "query_settings": {
    "delay_between_requests": 0.5,
    "timeout": 10,
    "max_retries": 3,
    "backoff_factor": 0.5,
    "stop_on_first_match": true,
    "title_match_threshold": 0.86
  }
}
```

阈值越高，匹配越保守。除非你理解误匹配风险，否则不建议低于 `0.80`。

## 命令行参考

```text
bibverify check [BIB_FILE] [--config PATH] [--output-dir DIR] [--json]
bibverify doi DOI [--key KEY] [--config PATH] [--json]
bibverify config init [--output PATH] [--force]
bibverify doctor [--config PATH] [--json]
bibverify providers list [--json]
bibverify mcp [--config PATH] [--transport stdio|streamable-http]
bibverify agent init [--target generic|codex|claude|cursor]
bibverify skill export [--target ...]
```

退出码：

| 退出码 | 含义 |
|---:|---|
| `0` | 全部处理成功 |
| `1` | 处理完成，但有条目未找到 |
| `2` | 配置、路径、编码或参数错误 |
| `3` | 处理过程中出现错误 |

使用 `--json` 时，stdout 只输出 JSON；诊断信息写入 stderr，适合 CI 和脚本解析。

## 输出文件

以 `references.bib` 为例：

- `bib_check_report_<时间>.txt`：验证摘要与字段差异。
- `references_backup_<时间>.bib`：原文件逐字节备份。
- `references_updated_<时间>.bib`：更新后的完整可用文献库；无更新时不生成。
- `references_wrong_<时间>.bib`：未找到或处理失败的条目；无问题时不生成。

可通过 `output_settings` 分别关闭报告、备份、更新文件或问题文件。

## 数据源顺序

静态优先级不是唯一依据：

1. DOI 会提升 Crossref，并先走 DOI 精确接口。
2. PMID/PMCID 或生物医学线索会提升 PubMed 与 Europe PMC。
3. arXiv 标识会提升 arXiv。
4. 计算机科学会议和期刊线索会提升 DBLP。

Unpaywall 当前只作为开放获取信息补充，不作为主书目元数据源。

## MCP 与 AI 助手

Bibverify 使用官方 MCP Python SDK，可运行本地 stdio 或 Streamable HTTP 服务。

stdio：

```bash
bibverify mcp --config config.json
```

MCP 客户端配置：

```json
{
  "mcpServers": {
    "bibverify": {
      "command": "bibverify",
      "args": ["mcp", "--config", "config.json"]
    }
  }
}
```

Streamable HTTP：

```bash
bibverify mcp --transport streamable-http --config config.json
```

提供的工具：

- `doi_to_bibtex`
- `rank_lookup_sources`
- `explain_update_diff`
- `verify_bib_file`

生成适配 Codex、Claude、Cursor 或通用 MCP 客户端的说明文件：

```bash
bibverify agent init --target codex --output .bibverify-agent --config config.json
bibverify doctor --config config.json
```

## Python API

```python
from bibverify.checker import BibTeXChecker

checker = BibTeXChecker("config.json")
summary = checker.run()
print(summary["counts"])
```

`from bib_check import BibTeXChecker` 会在 0.3 系列继续兼容，但新代码应使用包内导入路径。

## 参与开发

```bash
git clone https://github.com/Hylouis233/bibverify.git
cd bibverify
python -m venv .venv
```

激活环境后安装开发依赖：

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests bib_check.py
python -m ruff format --check src tests bib_check.py
python -m mypy
python -m build
python -m twine check dist/*
```

CI 会在 Windows、macOS、Linux 和 Python 3.11–3.14 上运行测试，并独立执行 lint、现代接口边界的严格类型检查、覆盖率和包构建验证。发布使用 PyPI Trusted Publishing，不在仓库中保存上传令牌。

## 引用

如果 Bibverify 对你的研究有帮助，请引用：

```bibtex
@software{bibverify2025,
  title = {Bibverify: A Multi-Platform BibTeX Reference Verification Tool},
  author = {Hong Liu},
  year = {2025},
  url = {https://github.com/Hylouis233/bibverify},
  doi = {10.5281/zenodo.17338090}
}
```

## 许可证

[MIT License](LICENSE)
