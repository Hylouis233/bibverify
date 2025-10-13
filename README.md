# Bibverify - BibTeX 文献检查工具

<p align="center">
<a href="README_EN.md"><img src="https://img.shields.io/badge/English-README-blue.svg" alt="English README"></a> | <a href="README.md"><img src="https://img.shields.io/badge/中文-README-red.svg" alt="中文 README"></a>
</p>

> 🔍 **English**: A multi平台 BibTeX reference verification and update tool that automatically checks and improves reference information through multiple academic database APIs.  
> 📚 **中文**: 一个支持多平台的 BibTeX 文献验证和更新工具，通过多个学术数据库 API 自动检查和完善文献信息。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/) [![Stars](https://img.shields.io/github/stars/Hylouis233/bibverify?style=social)](https://github.com/Hylouis233/bibverify)



## 🚀 支持的学术平台

| 平台 | 优先级 | 学科覆盖 | API要求 | 特殊功能 |
|------|--------|----------|---------|----------|
| **CrossRef** | 1 | 全学科 | 无需API | Polite Pool |
| **OpenAlex** | 2 | 全学科 | 无需API | 引用关系 |
| **Semantic Scholar** | 3 | 全学科 | 推荐API | AI 驱动 |
| **PubMed** | 4 | 生物医学 | 可选API | 医学专业 |
| **Europe PMC** | 5 | 生物医学 | 无需API | 欧洲医学 |
| **CORE** | 6 | 开放获取 | 推荐API | 开放论文 |
| **Unpaywall** | 7 | 全学科 | 需要邮箱 | 开放版本 |
| **DBLP** | 8 | 计算机科学 | 无需API | CS 专业 |
| **arXiv** | 9 | 预印本 | 无需API | 预印本 |
| **bioRxiv** | 10 | 生物医学预印本 | 无需API | 生物预印本 |

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## ⚙️ 配置设置

### 1. 复制配置文件

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

### 基本使用

```bash
python bib_check.py
```

### 指定配置文件

```bash
python bib_check.py config.json
```

## 📁 输出文件

程序会生成以下文件：

1. **检查报告** (`bib_check_report_YYYYMMDD_HHMMSS.txt`)
   - 验证通过的文献列表
   - 需要更新的文献及其差异详情
   - 未找到的文献列表

2. **备份文件** (`references_backup_YYYYMMDD_HHMMSS.bib`)
   - 原始 BibTeX 文件的完整备份

3. **更新文件** (`references_updated_YYYYMMDD_HHMMSS.bib`)
   - 包含所有更新后的文献条目

4. **问题文件** (`references_wrong_YYYYMMDD_HHMMSS.bib`)
   - 包含未找到或处理错误的文献

## 🔄 工作流程

```
开始
 ↓
加载 BibTeX 文件
 ↓
对每个条目：
 ├─ 提取标题
 ├─ 按优先级查询各平台
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

### API API设置

部分平台需要 API API以获得更高访问速度：

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

欢迎提交 [GitHub Issues](https://github.com/Hylouis233/bibverify/issues) 和 [Pull Request](https://github.com/Hylouis233/bibverify/issues)！
