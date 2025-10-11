"""
Tests for bibverify package.
"""

import pytest
from bibverify import BibVerifier, verify_bib_entry


class TestBibVerifier:
    """Test cases for BibVerifier class."""
    
    def test_init_default(self):
        """Test BibVerifier initialization with defaults."""
        verifier = BibVerifier()
        assert verifier.timeout == 10
        assert verifier.email is None
    
    def test_init_with_email(self):
        """Test BibVerifier initialization with email."""
        email = "test@example.com"
        verifier = BibVerifier(email=email)
        assert verifier.email == email
        assert 'User-Agent' in verifier.session.headers
    
    def test_init_with_timeout(self):
        """Test BibVerifier initialization with custom timeout."""
        verifier = BibVerifier(timeout=20)
        assert verifier.timeout == 20
    
    def test_verify_doi_valid(self):
        """Test DOI verification with a valid DOI."""
        verifier = BibVerifier()
        # Using a known valid DOI
        is_valid, metadata = verifier.verify_doi('10.1038/nature14539')
        assert is_valid is True
        assert metadata is not None
    
    def test_verify_doi_invalid(self):
        """Test DOI verification with an invalid DOI."""
        verifier = BibVerifier()
        is_valid, metadata = verifier.verify_doi('10.9999/invalid.doi.12345')
        assert is_valid is False
    
    def test_verify_arxiv_valid(self):
        """Test arXiv verification with a valid ID."""
        verifier = BibVerifier()
        # Using a known valid arXiv ID
        is_valid, metadata = verifier.verify_arxiv('1706.03762')
        assert is_valid is True
        assert metadata is not None
    
    def test_verify_arxiv_with_prefix(self):
        """Test arXiv verification with 'arXiv:' prefix."""
        verifier = BibVerifier()
        is_valid, metadata = verifier.verify_arxiv('arXiv:1706.03762')
        assert is_valid is True
    
    def test_verify_entry_with_doi(self):
        """Test verifying an entry with a DOI."""
        verifier = BibVerifier()
        entry = {
            'ID': 'test_paper',
            'doi': '10.1038/nature14539',
            'title': 'Deep Learning'
        }
        result = verifier.verify_entry(entry)
        assert result['id'] == 'test_paper'
        assert result['verified'] is True
        assert 'CrossRef' in result['sources']
    
    def test_verify_entry_with_arxiv(self):
        """Test verifying an entry with an arXiv ID."""
        verifier = BibVerifier()
        entry = {
            'ID': 'test_arxiv',
            'eprint': '1706.03762',
            'archiveprefix': 'arXiv',
            'title': 'Attention Is All You Need'
        }
        result = verifier.verify_entry(entry)
        assert result['id'] == 'test_arxiv'
        assert result['verified'] is True
        assert 'arXiv' in result['sources']
    
    def test_verify_entry_no_identifiers(self):
        """Test verifying an entry with only a title."""
        verifier = BibVerifier()
        entry = {
            'ID': 'test_title_only',
            'title': 'Deep Learning'
        }
        result = verifier.verify_entry(entry)
        assert result['id'] == 'test_title_only'
        # May or may not verify depending on OpenAlex response
        assert isinstance(result['verified'], bool)
    
    def test_verify_entry_fake_citation(self):
        """Test verifying a fake citation."""
        verifier = BibVerifier()
        entry = {
            'ID': 'fake_paper',
            'title': 'This Is A Completely Made Up Paper Title That Does Not Exist Anywhere',
            'author': 'Nobody'
        }
        result = verifier.verify_entry(entry)
        assert result['id'] == 'fake_paper'
        # Fake citation should not verify
        assert result['verified'] is False


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_verify_bib_entry(self):
        """Test verify_bib_entry convenience function."""
        entry = {
            'ID': 'test',
            'doi': '10.1038/nature14539'
        }
        result = verify_bib_entry(entry)
        assert result['id'] == 'test'
        assert isinstance(result['verified'], bool)
    
    def test_verify_bib_entry_with_email(self):
        """Test verify_bib_entry with email parameter."""
        entry = {
            'ID': 'test',
            'doi': '10.1038/nature14539'
        }
        result = verify_bib_entry(entry, email="test@example.com")
        assert result['id'] == 'test'
        assert isinstance(result['verified'], bool)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
