"""
Integration tests for bibverify package.
These tests make real API calls and may be slow.
"""

import pytest
from bibverify import verify_bib_file


@pytest.mark.integration
@pytest.mark.slow
def test_verify_file_integration(sample_bib_file):
    """Integration test: Verify a real BibTeX file."""
    results = verify_bib_file(sample_bib_file)
    
    assert len(results) > 0
    
    # Check structure of results
    for result in results:
        assert 'id' in result
        assert 'verified' in result
        assert 'sources' in result
        assert 'metadata' in result
        assert isinstance(result['verified'], bool)
        assert isinstance(result['sources'], list)
