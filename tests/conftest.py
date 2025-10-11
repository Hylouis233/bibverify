"""Test configuration and fixtures for pytest."""

import pytest
import os
import tempfile


@pytest.fixture
def sample_bib_content():
    """Sample BibTeX content for testing."""
    return """
@article{einstein1905,
    title={On the electrodynamics of moving bodies},
    author={Einstein, Albert},
    journal={Annalen der Physik},
    year={1905},
    doi={10.1002/andp.19053221004}
}

@article{attention,
    title={Attention Is All You Need},
    author={Vaswani, Ashish and Shazeer, Noam},
    journal={arXiv preprint},
    year={2017},
    eprint={1706.03762},
    archiveprefix={arXiv}
}
"""


@pytest.fixture
def sample_bib_file(sample_bib_content):
    """Create a temporary BibTeX file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
        f.write(sample_bib_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_entry():
    """Sample BibTeX entry as dictionary."""
    return {
        'ID': 'test_entry',
        'ENTRYTYPE': 'article',
        'title': 'Deep Learning',
        'author': 'LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey',
        'year': '2015',
        'doi': '10.1038/nature14539'
    }
