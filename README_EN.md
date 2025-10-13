# Bibverify - BibTeX Reference Verification Tool

<p align="center">
<a href="README_EN.md"><img src="https://img.shields.io/badge/English-README-blue.svg" alt="English README"></a> | <a href="README.md"><img src="https://img.shields.io/badge/中文-README-red.svg" alt="中文 README"></a>
</p>

> 🔍 **English**: A multi-platform BibTeX reference verification and update tool that automatically checks and improves reference information through multiple academic database APIs.  
> 📚 **Chinese**: A multi-platform BibTeX reference verification and update tool that automatically checks and improves reference information through multiple academic database APIs.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/) [![Stars](https://img.shields.io/github/stars/Hylouis233/bibverify?style=social)](https://github.com/Hylouis233/bibverify)



## 🚀 Supported Academic Platforms

| Platform | Priority | Discipline Coverage | API Requirement | Special Feature |
|------|--------|----------|---------|----------|
| **CrossRef** | 1 | All disciplines | No API | Polite Pool |
| **OpenAlex** | 2 | All disciplines | No API | Citation graph |
| **Semantic Scholar** | 3 | All disciplines | API recommended | AI-driven |
| **PubMed** | 4 | Biomedicine | Optional API | Medical focus |
| **Europe PMC** | 5 | Biomedicine | No API | European medical |
| **CORE** | 6 | Open access | API recommended | Open papers |
| **Unpaywall** | 7 | All disciplines | Email required | Open versions |
| **DBLP** | 8 | Computer Science | No API | CS-focused |
| **arXiv** | 9 | Preprints | No API | Preprints |
| **bioRxiv** | 10 | Biomedical preprints | No API | Biomedical preprints |

## 📦 Installation

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Copy the config template

```bash
cp config_template.json config.json
```

### 2. Basic settings

Edit `config.json`:

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

### 3. Platform settings

Enable/disable platforms as needed:

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

### 4. Language

- `"CN"`: Chinese UI
- `"EN"`: English UI

## 🎯 Usage

### Basic

```bash
python bib_check.py
```

### Specify a config file

```bash
python bib_check.py config.json
```

## 📁 Output Files

The program will generate the following files:

1. **Check report** (`bib_check_report_YYYYMMDD_HHMMSS.txt`)
   - List of references that passed verification
   - References that need updates with detailed differences
   - List of references not found

2. **Backup file** (`references_backup_YYYYMMDD_HHMMSS.bib`)
   - Full backup of the original BibTeX file

3. **Updated file** (`references_updated_YYYYMMDD_HHMMSS.bib`)
   - All updated reference entries

4. **Problem file** (`references_wrong_YYYYMMDD_HHMMSS.bib`)
   - Entries not found or failed during processing

## 🔄 Workflow

```
Start
 ↓
Load BibTeX file
 ↓
For each entry:
 ├─ Extract title
 ├─ Query platforms by priority
 ├─ Intelligently match bibliographic info
 ├─ Preserve original key
 ├─ Compare field differences
 └─ Record results
 ↓
Generate check report
 ↓
Generate updated file
 ↓
Done
```

## 📝 BibTeX Formatting Standards

### Field order

The generated BibTeX files follow a standard field order:

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

### Reference type mapping

| Platform Type | BibTeX Type |
|----------|------------|
| journal-article | article |
| book-chapter | incollection |
| book | book |
| proceedings-article | inproceedings |
| posted-content | unpublished |

## 🎯 Intelligent Matching Rules

### Title matching strategy

1. **Exact match** (case- and punctuation-insensitive)
2. **Original title is a substring of the new title**
3. **Strict non-match**: avoid false positives

### Title normalization steps

```
"{{Detecting Influenza Epidemics}}"
↓ Remove braces
"Detecting Influenza Epidemics"
↓ Lowercase
"detecting influenza epidemics"
↓ Remove punctuation
"detecting influenza epidemics"
↓ Normalize whitespace
"detecting influenza epidemics"
```

## 🔧 Advanced Settings

### API settings

Some platforms require an API key for higher rate limits:

#### Semantic Scholar
```json
"semantic_scholar": {
  "api_key": "your_api_key_here"
}
```
Registration page: https://www.semanticscholar.org/product/api#api-key-form

#### PubMed
```json
"pubmed": {
  "api_key": "your_api_key_here"
}
```
Registration page: https://www.ncbi.nlm.nih.gov/account/

#### CORE
```json
"core": {
  "api_key": "your_api_key_here"
}
```
Registration page: https://core.ac.uk/services/api

### Polite Pool

For better throughput, set your email:

```json
"user_info": {
  "email": "your_email@example.com"
}
```

### Query settings

```json
"query_settings": {
  "delay_between_requests": 0.5,
  "timeout": 10,
  "max_retries": 3,
  "stop_on_first_match": true
}
```

## 📊 Project Stats

![GitHub stars](https://img.shields.io/github/stars/Hylouis233/bibverify?style=social) ![GitHub forks](https://img.shields.io/github/forks/Hylouis233/bibverify?style=social) ![GitHub issues](https://img.shields.io/github/issues/Hylouis233/bibverify) ![GitHub pull requests](https://img.shields.io/github/issues-pr/Hylouis233/bibverify)

[![Star History Chart](https://api.star-history.com/svg?repos=Hylouis233/bibverify&type=Date)](https://www.star-history.com/#Hylouis233/bibverify&Date)

## 📖 Academic Citation

If you use Bibverify in your research or project, please cite it:

### BibTeX
```bibtex
@software{bibverify2025,
  title={Bibverify: A Multi-Platform BibTeX Reference Verification Tool},
  author={Hong Liu},
  year={2025},
  url={https://github.com/Hylouis233/bibverify},
  note={DOI: 10.5281/zenodo.17338090}
}
```

### Text
```
Hong Liu. (2025). Bibverify: A Multi-Platform BibTeX Reference Verification Tool. 
GitHub. https://github.com/Hylouis233/bibverify. DOI: 10.5281/zenodo.17338090
```

**Bibverify** - Make reference management simpler and more accurate!

⭐ **If this tool helps you, please give it a star!**



## 🤝 Contributing

Contributions are welcome via [GitHub Issues](https://github.com/Hylouis233/bibverify/issues) and [Pull Requests](https://github.com/Hylouis233/bibverify/issues)!
