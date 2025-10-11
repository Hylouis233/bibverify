# Contributing to BibVerify

Thank you for your interest in contributing to BibVerify! This document provides guidelines and instructions for contributing.

## 🎯 Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.7 or higher
- Git
- pip

### Setting Up Development Environment

1. **Fork the repository**
   ```bash
   # Click the 'Fork' button on GitHub
   ```

2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/bibverify.git
   cd bibverify
   ```

3. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

5. **Install development dependencies**
   ```bash
   pip install pytest pytest-cov black flake8 mypy
   ```

## 🔧 Development Workflow

### Creating a Branch

Create a feature branch for your work:

```bash
git checkout -b feature/your-feature-name
```

Use prefixes for branch names:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `docs/` - Documentation updates
- `test/` - Test additions or modifications

### Making Changes

1. **Write clean code**
   - Follow PEP 8 style guidelines
   - Use meaningful variable and function names
   - Add docstrings to functions and classes
   - Keep functions focused and modular

2. **Format your code**
   ```bash
   black bibverify/
   ```

3. **Check code style**
   ```bash
   flake8 bibverify/
   ```

4. **Type checking** (optional but recommended)
   ```bash
   mypy bibverify/
   ```

### Testing

1. **Write tests** for new features
   - Place tests in the `tests/` directory
   - Use descriptive test names
   - Test both success and failure cases

2. **Run tests**
   ```bash
   pytest
   ```

3. **Check coverage**
   ```bash
   pytest --cov=bibverify --cov-report=html
   ```

### Committing Changes

1. **Stage your changes**
   ```bash
   git add .
   ```

2. **Commit with a descriptive message**
   ```bash
   git commit -m "Add feature: description of what you did"
   ```

   Commit message guidelines:
   - Use present tense ("Add feature" not "Added feature")
   - Be descriptive but concise
   - Reference issues if applicable (#123)

3. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 Pull Request Process

1. **Create a Pull Request**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill in the PR template

2. **PR Description should include:**
   - Summary of changes
   - Related issue numbers
   - Testing performed
   - Screenshots (if UI changes)

3. **PR Checklist:**
   - [ ] Code follows project style guidelines
   - [ ] Self-reviewed the code
   - [ ] Commented complex code sections
   - [ ] Updated documentation if needed
   - [ ] Added tests for new features
   - [ ] All tests pass locally
   - [ ] No breaking changes (or documented)

4. **Review Process**
   - Maintainers will review your PR
   - Address any requested changes
   - Once approved, your PR will be merged

## 🐛 Reporting Bugs

### Before Submitting a Bug Report

- Check if the bug has already been reported
- Verify it's reproducible in the latest version
- Collect relevant information (version, OS, Python version, etc.)

### Submitting a Bug Report

Create an issue with:

1. **Clear title** describing the bug
2. **Steps to reproduce** the issue
3. **Expected behavior**
4. **Actual behavior**
5. **Environment details**
   - BibVerify version
   - Python version
   - Operating system
6. **Relevant code** or BibTeX files (if applicable)
7. **Error messages** or logs

Example:
```markdown
## Bug Description
BibVerify crashes when verifying a file with non-UTF8 characters

## Steps to Reproduce
1. Create a .bib file with non-UTF8 characters
2. Run `bibverify file.bib`
3. Program crashes

## Expected Behavior
Should handle encoding gracefully or show helpful error

## Environment
- BibVerify: 0.1.0
- Python: 3.9.5
- OS: Ubuntu 20.04
```

## 💡 Suggesting Features

### Before Suggesting a Feature

- Check if the feature already exists
- Verify it hasn't been suggested before
- Consider if it fits the project scope

### Suggesting a Feature

Create an issue with:

1. **Clear title** describing the feature
2. **Use case** - Why is this needed?
3. **Proposed solution** - How should it work?
4. **Alternatives considered**
5. **Additional context** - Examples, mockups, etc.

## 📚 Documentation

Documentation improvements are always welcome!

- Fix typos or clarify existing documentation
- Add examples for common use cases
- Improve API documentation
- Translate documentation (if applicable)

## 🎨 Code Style Guidelines

### Python Style

- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 88 characters (Black default)
- Use type hints where appropriate

### Docstring Style

Use Google-style docstrings:

```python
def verify_entry(entry: Dict) -> Dict:
    """
    Verify a single BibTeX entry.
    
    Args:
        entry: Dictionary representing a BibTeX entry
        
    Returns:
        Dictionary with verification results
        
    Raises:
        ValueError: If entry is invalid
    """
```

### Naming Conventions

- `snake_case` for functions and variables
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Prefix private methods with `_`

## 🔍 Code Review Guidelines

When reviewing PRs:

- Be respectful and constructive
- Focus on the code, not the person
- Explain why changes are needed
- Suggest improvements with examples
- Acknowledge good practices

## 📦 Release Process

(For maintainers)

1. Update version in `setup.py` and `__init__.py`
2. Update CHANGELOG.md
3. Create release tag
4. Build and upload to PyPI
5. Create GitHub release

## 🤔 Questions?

- Open an issue for questions
- Check existing issues and documentation
- Be patient and respectful

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be acknowledged in:
- README.md
- Release notes
- GitHub contributors page

Thank you for contributing to BibVerify! 🎉
