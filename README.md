# Bibverify - BibTeX 文献检查工具

<!-- mcp-name: io.github.hylouis233/bibverify -->

<p align="center">
<a href="README_EN.md"><img src="https://img.shields.io/badge/English-README-blue.svg" alt="English README"></a> | <a href="README.md"><img src="https://img.shields.io/badge/中文-README-red.svg" alt="中文 README"></a>
</p>

> **中文**: 一个支持多平台的 BibTeX 文献验证和更新工具，通过 DOI 精确查询、动态检索排序和多个学术数据库 API 自动检查、补全和解释文献信息。
>
> **English**: A multi-platform BibTeX reference verification and update tool with DOI-first lookup, dynamic source ranking, MCP tools, and skill export for AI assistants.

[![PyPI](https://img.shields.io/pypi/v/bibverify.svg)](https://pypi.org/project/bibverify/) [![Release](https://img.shields.io/github/v/release/Hylouis233/bibverify)](https://github.com/Hylouis233/bibverify/releases) [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/) [![Stars](https://img.shields.io/github/stars/Hylouis233/bibverify?style=social)](https://github.com/Hylouis233/bibverify) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17338090.svg)](https://doi.org/10.5281/zenodo.17338090)

## 快速开始

### 安装

```bash
pip install -U bibverify
```

### DOI 转 BibTeX

```bash
bibverify --doi 10.1038/nature12373 --key example2013
```

### 检查一个 `.bib` 文件

创建 `config.json`：

```json
{
  "language": "CN",
  "bib_file": "references.bib",
  "user_info": {
    "email": "your_email@example.com",
    "app_name": "Bibverify"
  }
}
```

然后运行：

```bash
bibverify config.json
```

### 一键生成大模型接入文件

```bash
bibverify agent init --target codex --output .bibverify-agent --config config.json
bibverify agent doctor --config config.json
```

生成的 `.bibverify-agent/` 目录包含 MCP 配置片段、`SKILL.md` 和本地接入说明。

## 核心能力

- DOI 优先：有 DOI 的条目优先走 Crossref 精确查询，再回退到标题检索。
- 动态排序：根据 DOI、PMID/PMCID、arXiv、学科线索动态提升 Crossref、PubMed、Europe PMC、arXiv、DBLP。
- 多平台校验：支持 Crossref、OpenAlex、Semantic Scholar、PubMed、Europe PMC、CORE、DBLP、arXiv、bioRxiv 等平台。
- AI 接入：内置 MCP stdio server，可导出 skill，让 Codex、Claude、Cursor 等支持 MCP 的助手调用 Bibverify。
- 安全输出：不会原地覆盖源 `.bib` 文件，而是生成备份、更新条目和问题条目文件。

## 🚀 支持的学术平台

| 平台 | 优先级 | 学科覆盖 | API要求 | 特殊功能 |
|------|--------|----------|---------|----------|
| **CrossRef** | 1 | 全学科 | 无需API | Polite Pool |
| **OpenAlex** | 2 | 全学科 | 建议/需要 API key | 引用关系 |
| **Semantic Scholar** | 3 | 全学科 | 推荐API | AI 驱动 |
| **PubMed** | 4 | 生物医学 | 可选API | 医学专业 |
| **Europe PMC** | 5 | 生物医学 | 无需API | 欧洲医学 |
| **CORE** | 6 | 开放获取 | 推荐API | 开放论文 |
| **Unpaywall** | 后处理 | 全学科 | 需要邮箱 | 开放版本补充，不作为主元数据源 |
| **DBLP** | 8 | 计算机科学 | 无需API | CS 专业 |
| **arXiv** | 9 | 预印本 | 无需API | 预印本 |
| **bioRxiv** | 10 | 生物医学预印本 | 无需API | 生物预印本 |

## 📦 安装

### 从 PyPI 安装

```bash
pip install -U bibverify
```

### 从源码开发/运行

```bash
git clone https://github.com/Hylouis233/bibverify.git
cd bibverify
pip install -e .
```

如果只需要安装运行依赖：

```bash
pip install -r requirements.txt
```

当前发布版本：

- PyPI: https://pypi.org/project/bibverify/
- GitHub Releases: https://github.com/Hylouis233/bibverify/releases

## ⚙️ 配置设置

### 1. 创建配置文件

从 PyPI 安装后，可以手动创建一个最小 `config.json`：

```json
{
  "language": "CN",
  "bib_file": "references.bib",
  "user_info": {
    "email": "your_email@example.com",
    "app_name": "Bibverify"
  }
}
```

如果你在源码仓库中使用，也可以复制模板后再编辑：

```bash
cp config_template.json config.json
```

### 2. 基本配置

编辑 `config.json` 文件：

```json
{
  "language": "CN",
  "bib_file": "references.bib",
  "user_info": {
    "email": "your_email@example.com",
    "app_name": "Bibverify"
  }
}
```

### 3. 平台配置

根据需要启用/禁用平台：

```json
{
  "platforms": {
    "crossref": {
      "enabled": true,
      "priority": 1,
      "use_polite_pool": true
    },
    "semantic_scholar": {
      "enabled": true,
      "priority": 3,
      "requires_api_key": true,
      "api_key": "your_api_key_here"
    }
  }
}
```

### 4. 语言设置

- `"CN"`: 中文界面
- `"EN"`: 英文界面

## 🎯 使用方法

### 命令速查

| 命令 | 用途 |
|------|------|
| `bibverify config.json` | 按配置检查 `.bib` 文件 |
| `bibverify --doi DOI --key KEY` | 通过 DOI 生成单条 BibTeX |
| `bibverify mcp --config config.json` | 启动 MCP stdio server |
| `bibverify agent init --target codex` | 生成 MCP/Skill 接入文件 |
| `bibverify agent doctor --config config.json` | 检查本地集成是否可用 |
| `bibverify skill export --target codex` | 单独导出 `SKILL.md` |

### 检查 `.bib` 文件

```bash
bibverify config.json
```

### 通过 DOI 生成单条 BibTeX

```bash
bibverify --doi 10.1038/nature12373 --key example2013
```

该模式会直接调用 Crossref DOI 精确查询，并将结果打印为 BibTeX。

### 一键接入大模型 / MCP / Skill

为小白用户准备本地集成文件：

```bash
bibverify agent init --target codex --output .bibverify-agent --config config.json
```

生成内容：

- `.bibverify-agent/SKILL.md`: 给大模型看的 Bibverify 调用说明
- `.bibverify-agent/mcp.json`: MCP server 配置片段
- `.bibverify-agent/README.md`: 本地接入说明

启动 MCP stdio server：

```bash
bibverify mcp --config config.json
```

单独导出 skill：

```bash
bibverify skill export --target codex --output .bibverify-agent/SKILL.md
```

检查本地环境：

```bash
bibverify agent doctor --config config.json
```

MCP 当前暴露四个工具：`doi_to_bibtex`、`rank_lookup_sources`、`explain_update_diff`、`verify_bib_file`。大模型接入 MCP 后，可以直接调用这些工具完成 DOI 转 BibTeX、检索源排序解释、条目差异解释和 `.bib` 文件检查。

可复制的 MCP 配置片段：

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

## 📁 输出文件

程序会生成以下文件。当前版本的 `.bib` 输出文件名使用固定前缀 `sample_`，不会原地覆盖你的源文件：

1. **检查报告** (`bib_check_report_YYYYMMDD_HHMMSS.txt`)
   - 验证通过的文献列表
   - 需要更新的文献及其差异详情
   - 未找到的文献列表

2. **备份文件** (`sample_backup_YYYYMMDD_HHMMSS.bib`)
   - 原始 BibTeX 文件的完整备份

3. **更新文件** (`sample_updated_YYYYMMDD_HHMMSS.bib`)
   - 包含所有更新后的文献条目

4. **问题文件** (`sample_wrong_YYYYMMDD_HHMMSS.bib`)
   - 包含未找到或处理错误的文献

## 🔄 工作流程

```
开始
 ↓
加载 BibTeX 文件
 ↓
对每个条目：
 ├─ 提取标题
 ├─ 根据 DOI/PMID/arXiv 等标识符动态调整平台顺序
 ├─ 按调整后的优先级查询各平台
 ├─ 智能匹配文献信息
 ├─ 保持原有键值
 ├─ 比对字段差异
 └─ 记录结果
 ↓
生成检查报告
 ↓
生成更新文件
 ↓
完成
```

## 📝 BibTeX 格式标准

### 字段顺序

程序生成的 BibTeX 文件遵循标准字段顺序：

```bibtex
@article{key,
  title={...},
  author={...},
  journal={...},
  volume={...},
  number={...},
  pages={...},
  year={...},
  publisher={...},
  doi={...}
}
```

### 文献类型映射

| 平台类型 | BibTeX 类型 |
|----------|------------|
| journal-article | article |
| book-chapter | incollection |
| book | book |
| proceedings-article | inproceedings |
| posted-content | unpublished |

## 🎯 智能匹配规则

### 标题匹配策略

1. **完全相同**（忽略大小写、标点符号）
2. **原标题包含在新标题中**
3. **严格不匹配**：避免误匹配

### 标题规范化过程

```
"{{Detecting Influenza Epidemics}}"
↓ 移除大括号
"Detecting Influenza Epidemics"
↓ 转小写
"detecting influenza epidemics"
↓ 移除标点符号
"detecting influenza epidemics"
↓ 规范化空格
"detecting influenza epidemics"
```

## 🔧 高级配置

### API 设置

部分平台需要 API key 以获得更高访问速度或稳定访问：

#### OpenAlex
```json
"openalex": {
  "api_key": "your_api_key_here"
}
```
注册地址: https://docs.openalex.org/how-to-use-the-api/getting-started/authentication

#### Semantic Scholar
```json
"semantic_scholar": {
  "api_key": "your_api_key_here"
}
```
注册地址: https://www.semanticscholar.org/product/api#api-key-form

#### PubMed
```json
"pubmed": {
  "api_key": "your_api_key_here"
}
```
注册地址: https://www.ncbi.nlm.nih.gov/account/

#### CORE
```json
"core": {
  "api_key": "your_api_key_here"
}
```
注册地址: https://core.ac.uk/services/api

### Polite Pool 设置

为获得更高访问速度，建议设置邮箱：

```json
"user_info": {
  "email": "your_email@example.com"
}
```

### 查询设置

```json
"query_settings": {
  "delay_between_requests": 0.5,
  "timeout": 10,
  "max_retries": 3,
  "stop_on_first_match": true
}
```

检索顺序不是单纯静态表格顺序：如果条目已有 DOI，会优先走 Crossref DOI 精确查询；如果有 PMID/PMCID，会提升 PubMed 和 Europe PMC；如果有 arXiv 标识，会提升 arXiv。Unpaywall 当前只适合作为开放获取链接补充，不作为主文献元数据源。

## 📊 项目统计

![GitHub stars](https://img.shields.io/github/stars/Hylouis233/bibverify?style=social) ![GitHub forks](https://img.shields.io/github/forks/Hylouis233/bibverify?style=social) ![GitHub issues](https://img.shields.io/github/issues/Hylouis233/bibverify) ![GitHub pull requests](https://img.shields.io/github/issues-pr/Hylouis233/bibverify)

[![Star History Chart](https://api.star-history.com/svg?repos=Hylouis233/bibverify&type=Date)](https://www.star-history.com/#Hylouis233/bibverify&Date)

## 📖 学术引用

如果您在学术研究或项目中使用 Bibverify，请您引用本项目：

### BibTeX 格式
```bibtex
@software{bibverify2025,
  title={Bibverify: A Multi-Platform BibTeX Reference Verification Tool},
  author={Hong Liu},
  year={2025},
  url={https://github.com/Hylouis233/bibverify},
  note={DOI: 10.5281/zenodo.17338090}
}
```

### 文本格式
```
Hong Liu. (2025). Bibverify: A Multi-Platform BibTeX Reference Verification Tool. 
GitHub. https://github.com/Hylouis233/bibverify. DOI: 10.5281/zenodo.17338090
```

**Bibverify** - 让文献管理更简单、更准确！

⭐ **如果这个工具对您有帮助，请给个 Star！**


## 🤝 贡献

欢迎提交 [GitHub Issues](https://github.com/Hylouis233/bibverify/issues) 和 [Pull Request](https://github.com/Hylouis233/bibverify/pulls)！
