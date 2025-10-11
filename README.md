# bibverify

[![PyPI version](https://badge.fury.io/py/bibverify.svg)](https://badge.fury.io/py/bibverify)
[![Python Support](https://img.shields.io/pypi/pyversions/bibverify.svg)](https://pypi.org/project/bibverify/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**BibTeX文献验证工具** - 通过CrossRef/arXiv/OpenAlex验证引用真实性

**BibVerify** is a Python package for verifying BibTeX citations against multiple academic databases to detect fake, incorrect, or questionable references in academic papers.

## ✨ Features

- 🔍 **Multi-source verification**: Checks citations against CrossRef, arXiv, and OpenAlex APIs
- 📚 **BibTeX support**: Direct parsing and verification of BibTeX files
- 🚀 **Easy to use**: Simple API and command-line interface
- 🔄 **Batch processing**: Verify multiple citations at once
- 📊 **Detailed reports**: Get comprehensive verification results
- 🌐 **API-friendly**: Respects rate limits and supports CrossRef Polite Pool

## 🚀 Installation

### From PyPI (recommended)

```bash
pip install bibverify
```

### From source

```bash
git clone https://github.com/Hylouis233/bibverify.git
cd bibverify
pip install -e .
```

### Requirements

- Python 3.7+
- requests
- bibtexparser

## 📖 Quick Start

### Command Line Usage

Verify a BibTeX file:

```bash
bibverify references.bib
```

With email for better API rate limits (recommended):

```bash
bibverify references.bib --email your@email.com
```

Save results to a JSON file:

```bash
bibverify references.bib --output results.json
```

Show detailed output:

```bash
bibverify references.bib --verbose
```

### Python API Usage

#### Verify a single entry

```python
from bibverify import verify_bib_entry

entry = {
    'ID': 'einstein1905',
    'title': 'On the electrodynamics of moving bodies',
    'author': 'Einstein, Albert',
    'year': '1905',
    'doi': '10.1002/andp.19053221004'
}

result = verify_bib_entry(entry, email="your@email.com")
print(f"Verified: {result['verified']}")
print(f"Sources: {result['sources']}")
```

#### Verify a BibTeX file

```python
from bibverify import verify_bib_file

results = verify_bib_file('references.bib', email="your@email.com")

for result in results:
    if result['verified']:
        print(f"✓ {result['id']}: Verified via {', '.join(result['sources'])}")
    else:
        print(f"✗ {result['id']}: Could not verify")
```

#### Advanced usage with BibVerifier class

```python
from bibverify import BibVerifier

# Initialize with custom settings
verifier = BibVerifier(email="your@email.com", timeout=15)

# Verify individual citations
entry = {
    'ID': 'paper2023',
    'title': 'Example Paper Title',
    'doi': '10.1234/example.doi'
}

result = verifier.verify_entry(entry)

# Check DOI directly
is_valid, metadata = verifier.verify_doi('10.1234/example.doi')

# Check arXiv ID
is_valid, metadata = verifier.verify_arxiv('2301.12345')

# Search by title in OpenAlex
is_valid, metadata = verifier.verify_openalex('Example Paper Title')
```

## 🔧 How It Works

BibVerify verifies citations through a multi-step process:

1. **DOI Verification**: If a DOI is present, it's checked against CrossRef API
2. **arXiv Verification**: If an arXiv ID is present, it's verified via arXiv API
3. **Title Search**: As a fallback, the title is searched in OpenAlex database
4. **Result Compilation**: Returns verification status and metadata from sources

## 📚 Examples

See the [examples/](examples/) directory for more detailed usage examples:

- `verify_single.py` - Verify a single BibTeX entry
- `verify_file.py` - Verify all entries in a BibTeX file
- `advanced_usage.py` - Advanced features and custom configuration

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📋 API Reference

### `BibVerifier` Class

Main class for citation verification.

**Methods:**

- `__init__(email=None, timeout=10)` - Initialize verifier
- `verify_doi(doi)` - Verify using DOI via CrossRef
- `verify_arxiv(arxiv_id)` - Verify using arXiv ID
- `verify_openalex(title)` - Verify by searching title in OpenAlex
- `verify_entry(entry)` - Verify a single BibTeX entry dict
- `verify_file(bib_file)` - Verify all entries in a BibTeX file

### Convenience Functions

- `verify_bib_entry(entry, email=None)` - Quick verification of single entry
- `verify_bib_file(bib_file, email=None)` - Quick verification of file

## 🔒 Privacy & Ethics

- **Rate Limiting**: Built-in delays to respect API rate limits
- **Polite Pool**: Supports CrossRef Polite Pool with email registration
- **No Data Storage**: Does not store or transmit citation data beyond verification
- **Open Source**: Fully transparent verification process

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [CrossRef](https://www.crossref.org/) for DOI resolution
- [arXiv](https://arxiv.org/) for preprint verification  
- [OpenAlex](https://openalex.org/) for academic metadata

## 📞 Contact

- **Author**: Hong Liu
- **Repository**: [https://github.com/Hylouis233/bibverify](https://github.com/Hylouis233/bibverify)
- **Issues**: [https://github.com/Hylouis233/bibverify/issues](https://github.com/Hylouis233/bibverify/issues)

## 🚀 Roadmap

- [ ] Support for more academic databases (PubMed, Semantic Scholar, etc.)
- [ ] Confidence scoring for verification results
- [ ] HTML/PDF report generation
- [ ] Integration with reference managers
- [ ] Web interface
- [ ] Duplicate detection
- [ ] Citation quality metrics
