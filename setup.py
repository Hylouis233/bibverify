"""Setup configuration for bibverify package."""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding='utf-8') as f:
        return f.read()

setup(
    name="bibverify",
    version="0.1.0",
    author="Hong Liu",
    author_email="",
    description="A BibTeX citation verification tool to detect fake references",
    long_description=read_file('README.md'),
    long_description_content_type="text/markdown",
    url="https://github.com/Hylouis233/bibverify",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering",
        "Topic :: Text Processing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.0",
        "bibtexparser>=1.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.9",
            "mypy>=0.900",
        ],
    },
    entry_points={
        "console_scripts": [
            "bibverify=bibverify.cli:main",
        ],
    },
    keywords="bibtex citation verification crossref arxiv openalex academic research",
    project_urls={
        "Bug Reports": "https://github.com/Hylouis233/bibverify/issues",
        "Source": "https://github.com/Hylouis233/bibverify",
    },
)
