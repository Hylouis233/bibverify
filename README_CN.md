# Bibverify

<!-- mcp-name: io.github.Hylouis233/bibverify -->

<p align="center">
  <strong>核验书目记录存在性与元数据一致性，安全整理 BibTeX。</strong>
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="#安装">安装</a> · <a href="#快速开始">快速开始</a> · <a href="#mcp-与-ai-助手">MCP</a> · <a href="#参与开发">参与开发</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/bibverify/"><img src="https://img.shields.io/pypi/v/bibverify.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/bibverify/"><img src="https://img.shields.io/pypi/pyversions/bibverify.svg" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://github.com/Hylouis233/bibverify/actions/workflows/ci.yml"><img src="https://github.com/Hylouis233/bibverify/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

Bibverify 是一个面向研究者、编辑、自动化流程和 AI 助手的 BibTeX 元数据核验工具。它优先使用 DOI、PMID、PMCID 或 arXiv ID 精确定位记录，再结合标题、作者、年份、期刊与页码等信号评估候选项。

Bibverify 判断的是“已查询数据源中的书目记录与元数据是否一致”，而不是论文结论是否真实、数据是否造假或期刊是否可信。数据库未收录也不等于文献虚构；这类结果会明确标为“未在已查询数据源中检索到”或“需要人工复核”。默认运行不会改写原始 `.bib` 文件。

## 主要能力

- 标识符优先：DOI、PMID、PMCID 和 arXiv ID 会走相应平台的精确接口。
- 多数据源：支持 Crossref、OpenAlex、Semantic Scholar、PubMed、Europe PMC、CORE、DBLP、arXiv、bioRxiv 等。
- 可解释匹配：综合标识符、标题、作者、年份、期刊和页码；DOI 指向不同标题时标记为 `identifier_conflict`，不会用标题搜索掩盖冲突。
- 结构化状态：区分正常无结果、歧义、限流、鉴权失败、网络错误和解析错误；数据源故障不会落入 `not_found`。
- 非破坏性更新：API 未返回的 `abstract`、`keywords`、`file`、`note` 及自定义字段不会删除；不同持久标识符绝不自动覆盖。
- 稳健网络层：复用连接，对 `429/5xx` 自动重试和指数退避，并尊重 `Retry-After`。
- 本地缓存：成功的 GET 响应可写入有过期时间的 SQLite 缓存；失败响应不会缓存。
- 跨平台文件处理：支持 Windows、macOS 和 Linux；正确处理空格、中文路径、UTF-8 BOM 与 CRLF。
- 适合自动化：提供 JSON 输出、稳定退出码、Python API 和基于官方 SDK 的 MCP 服务。
- 安全输出：使用原子写入；备份保留原始字节与换行，不会悄悄改写源文件。

## 系统要求

- Windows、macOS 或 Linux
- 访问学术元数据 API 的网络连接
- 使用 Python 发行版时需要 Python 3.11–3.14；npm、容器和原生包自带运行时

项目的 GitHub Actions 会在三种操作系统和四个 Python 版本上运行测试。

## 安装

当前已发布的稳定版本为 v0.3.0；本分支正在准备 v0.4.0。标为 **v0.4.0** 的 npm、GHCR
或 GitHub Release 命令，只有在相应页面与产物正式发布后才能使用。

无需长期安装即可运行：

```bash
uvx bibverify --version
```

从 v0.4.0 开始，Node.js 用户可以使用零依赖 npm 启动器。它会下载当前系统对应的
原生程序、校验 `SHA256SUMS`，并原样转发参数与退出码：

```bash
npx --yes @hylouis233/bibverify --version
pnpm dlx @hylouis233/bibverify --version
bunx @hylouis233/bibverify --version
```

需要长期使用时，推荐 `uv tool` 或 `pipx`：

```bash
uv tool install bibverify
```

```bash
pipx install bibverify
```

也可以在虚拟环境中安装：

```bash
python -m pip install --upgrade bibverify
```

每个版本还会在 [GitHub Releases](https://github.com/Hylouis233/bibverify/releases) 提供原生构建并冒烟测试的独立程序。从 v0.4.0 起，矩阵覆盖 Windows x64，以及 macOS 和 Linux 的 x64/ARM64。由于 MCP 的一个运行时依赖目前没有提供 Windows ARM64 wheel，暂不发布原生 Windows ARM64 程序；npm 会在 Windows 11 ARM 上自动选择经过实测的 x64 模拟兼容版本，也可使用 ARM64 容器。

同一版本还会发布多架构容器：

```bash
docker run --rm ghcr.io/hylouis233/bibverify:0.4.0 --version
```

Homebrew、Scoop 和 WinGet 目前尚未在外部目录上架。v0.4.0 会根据最终 Release 产物及其
哈希生成可提交清单；随后仍需完成各目录的首次接入或审核。完整进度见[分发渠道](#分发渠道)。

## 快速开始

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

仅查看核验结果、不写任何文件：

```bash
bibverify check references.bib --dry-run --json
```

确认报告后，可显式应用高置信度字段更新；Bibverify 会先做逐字节备份：

```bash
bibverify check references.bib --apply
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
    "connect_timeout": 3.05,
    "read_timeout": 20,
    "max_retries": 3,
    "backoff_factor": 0.5,
    "stop_on_first_match": true,
    "match_threshold": 0.86,
    "ambiguous_threshold": 0.68,
    "auto_update_threshold": 0.92,
    "cache_enabled": true,
    "cache_ttl_hours": 168,
    "cache_path": ".bibverify-cache.sqlite3"
  }
}
```

`connect_timeout` 和 `read_timeout` 分别限制连接与响应读取；兼容字段 `timeout` 仍保留。`match_threshold` 控制自动接受候选的最低分，`ambiguous_threshold` 控制进入人工复核的最低分，`auto_update_threshold` 进一步限制字段自动更新。阈值越高越保守。`cache_path` 的相对路径同样相对于配置文件目录。

bioRxiv 官方 `details` 路由不支持任意标题搜索，因此 Bibverify 只在存在 `10.1101/...` DOI 时直接查询 bioRxiv；纯标题检索交给 Crossref、Europe PMC 等支持该契约的数据源。

## 命令行参考

```text
bibverify check [BIB_FILE] [--config PATH] [--output-dir DIR] [--format txt|json|jsonl|csv] [--dry-run|--apply] [--json]
bibverify doi DOI [--key KEY] [--config PATH] [--json]
bibverify config init [--output PATH] [--force]
bibverify doctor [--config PATH] [--json]
bibverify providers list [--json]
bibverify cache clear [--config PATH]
bibverify benchmark [--dataset PATH]
bibverify mcp [--config PATH] [--workspace-root DIR] [--transport stdio|streamable-http]
bibverify agent init [--target generic|codex|claude|cursor] [--output PATH]
bibverify skill export [--target ...]
```

退出码：

| 退出码 | 含义 |
|---:|---|
| `0` | 核验完成，元数据一致 |
| `1` | 运行错误（保留给不可归类的命令失败） |
| `2` | 存在元数据差异或高置信度更新建议 |
| `3` | 存在歧义、未检索到或标识符冲突，需要人工复核 |
| `4` | 数据源不可用，核验不完整 |
| `5` | 输入文件、配置或条目无效 |

使用 `--json` 时，stdout 只输出 JSON；诊断信息写入 stderr，适合 CI 和脚本解析。

## 输出文件

以 `references.bib` 为例：

- `bibverify_report_<时间>.<格式>`：完整状态、候选、Provider 错误、置信度和字段级来源；支持 `txt`、`json`、`jsonl`、`csv`。
- `references_backup_<时间>.bib`：原文件逐字节备份。
- `references_updated_<时间>.bib`：非破坏性合并后的完整文献库；无更新时不生成。
- `references_review_<时间>.bib`：歧义、未检索到、数据源不可用、标识符冲突或无效条目；无待复核项时不生成。

报告顶层 `complete` 仅在所有条目均完成核验时为 `true`。Provider 限流或网络故障会令其为 `false`，即使其他来源找到了候选。`field_diffs` 会记录原值、建议值、来源、置信度、标准化等价性、动作和理由。

可通过 `output_settings` 分别关闭报告、备份、更新文件或复核文件；`--dry-run` 会覆盖这些设置并保证零写入。默认只生成建议文件，只有 `--apply` 会在完成备份后修改源文件。

## 数据源顺序

静态优先级不是唯一依据：

1. DOI 会提升 Crossref，并先走 DOI 精确接口；可解析但标题明显冲突时停止并报告 `identifier_conflict`。
2. PMID/PMCID 或生物医学线索会提升 PubMed 与 Europe PMC。
3. arXiv 标识会提升 arXiv。
4. 计算机科学会议和期刊线索会提升 DBLP。

Unpaywall 当前只作为开放获取信息补充，不作为主书目元数据源。Provider 结果会分别标为 `matched`、`no_match`、`ambiguous`、`rate_limited`、`auth_error`、`network_error`、`parse_error`、`provider_error` 或 `skipped`。

## MCP 与 AI 助手

Bibverify 使用官方 MCP Python SDK，可运行本地 stdio 或 Streamable HTTP 服务。

stdio：

```bash
bibverify mcp --config config.json --workspace-root .
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

MCP 默认将配置文件所在目录视为工作区根目录，并拒绝读取该目录之外的配置或 `.bib` 文件，也拒绝向工作区之外写报告、缓存和更新文件。需要更大的范围时必须在启动服务器时显式传入 `--workspace-root`。协议协商、Schema、结构化结果、进度和取消由官方 MCP SDK 处理。

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

## 分发渠道

| 渠道 | 命令或产物 | 状态 |
|---|---|---|
| PyPI | `python -m pip install bibverify` | 已发布 |
| uv | `uvx bibverify` / `uv tool install bibverify` | 已发布 |
| pipx | `pipx install bibverify` | 已发布 |
| npm | `npx --yes @hylouis233/bibverify` | 计划随 v0.4.0 发布；目前尚未上架 |
| pnpm / Bun | `pnpm dlx @hylouis233/bibverify` / `bunx @hylouis233/bibverify` | 计划随 v0.4.0 发布；目前尚未上架 |
| GHCR | `docker pull ghcr.io/hylouis233/bibverify:0.4.0` | 计划随 v0.4.0 发布；目前尚未上架 |
| 原生程序 | Windows x64；macOS、Linux x64/ARM64 | 计划随 v0.4.0 发布；目前尚未上架 |
| Homebrew | Release 资产 `bibverify.rb` | v0.4.0 计划生成提交清单；目录尚未上架 |
| Scoop | Release 资产 `bibverify.json` | v0.4.0 计划生成提交清单；目录尚未上架 |
| WinGet | Release 资产 `Hylouis233.Bibverify*.yaml` | v0.4.0 计划生成提交清单；目录尚未上架 |
| MCP Registry | [`io.github.Hylouis233/bibverify`](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.Hylouis233%2Fbibverify/versions/latest) | 已发布发现元数据；实际运行仍使用上方某种安装渠道 |

npm 包只是轻量分发层，不是另一套实现。PyPI、npm、原生程序和容器共享同一个 Python
核验核心；npm 会在执行前验证对应二进制，包管理器清单也固定到相同的 Release 哈希。

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
python -m ruff check src tests tools bib_check.py
python -m ruff format --check src tests tools bib_check.py
python -m mypy
python -m build
python -m twine check dist/*
python -m bibverify benchmark --dataset benchmarks/cases.json
python -m pip_audit . --strict
```

CI 会在 Windows、macOS、Linux 和 Python 3.11–3.14 上运行测试，并执行 fixture/golden 测试、lint、类型检查、覆盖率、离线 benchmark、依赖漏洞审计、包构建与 CycloneDX SBOM 生成。GitHub Actions 固定到提交 SHA；MCP Publisher 固定版本并校验 SHA-256。PyPI 发布使用 Trusted Publishing 与默认的数字证明，不在仓库中保存上传令牌。

`benchmarks/cases.json` 是用于防止匹配策略回归的最小离线标注集，覆盖短标题误匹配、DOI 冲突、预印本标题变体、Unicode/LaTeX 和虚构作者组合。它不是完整科研评测，也不能代表真实世界的最终精确率；欢迎提交更广泛、可再分发的人工标注案例。

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
