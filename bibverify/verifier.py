"""
Core verification module for BibTeX citations.

This module provides the main verification logic to check citations
against multiple academic databases.
"""

import requests
import bibtexparser
from typing import Dict, List, Optional, Tuple
import time


class BibVerifier:
    """
    Main class for verifying BibTeX citations against academic databases.
    
    Supports verification through:
    - CrossRef API
    - arXiv API
    - OpenAlex API
    """
    
    def __init__(self, email: Optional[str] = None, timeout: int = 10):
        """
        Initialize the BibTeX verifier.
        
        Args:
            email: Email for CrossRef Polite Pool (optional but recommended)
            timeout: Request timeout in seconds (default: 10)
        """
        self.email = email
        self.timeout = timeout
        self.session = requests.Session()
        if email:
            self.session.headers.update({
                'User-Agent': f'BibVerify/0.1.0 (mailto:{email})'
            })
        else:
            self.session.headers.update({
                'User-Agent': 'BibVerify/0.1.0'
            })
    
    def verify_doi(self, doi: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify a citation using its DOI via CrossRef.
        
        Args:
            doi: The DOI to verify
            
        Returns:
            Tuple of (is_valid, metadata_dict)
        """
        try:
            url = f"https://api.crossref.org/works/{doi}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return True, data.get('message', {})
            else:
                return False, None
        except Exception as e:
            print(f"Error verifying DOI {doi}: {e}")
            return False, None
    
    def verify_arxiv(self, arxiv_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify a citation using arXiv ID.
        
        Args:
            arxiv_id: The arXiv identifier
            
        Returns:
            Tuple of (is_valid, metadata_dict)
        """
        try:
            # Clean arXiv ID (remove 'arXiv:' prefix if present)
            clean_id = arxiv_id.replace('arXiv:', '').strip()
            url = f"http://export.arxiv.org/api/query?id_list={clean_id}"
            
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200 and 'entry' in response.text:
                # Basic check - arXiv returns XML, we just verify it exists
                return True, {'arxiv_id': clean_id, 'source': 'arXiv'}
            else:
                return False, None
        except Exception as e:
            print(f"Error verifying arXiv ID {arxiv_id}: {e}")
            return False, None
    
    def verify_openalex(self, title: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify a citation by searching OpenAlex by title.
        
        Args:
            title: The paper title to search
            
        Returns:
            Tuple of (is_valid, metadata_dict)
        """
        try:
            url = "https://api.openalex.org/works"
            params = {
                'filter': f'title.search:{title}',
                'per-page': 1
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                if results:
                    return True, results[0]
            return False, None
        except Exception as e:
            print(f"Error verifying with OpenAlex for title '{title}': {e}")
            return False, None
    
    def verify_entry(self, entry: Dict) -> Dict:
        """
        Verify a single BibTeX entry.
        
        Args:
            entry: Dictionary representing a BibTeX entry
            
        Returns:
            Dictionary with verification results
        """
        result = {
            'id': entry.get('ID', 'unknown'),
            'verified': False,
            'sources': [],
            'metadata': {}
        }
        
        # Try DOI first
        if 'doi' in entry:
            is_valid, metadata = self.verify_doi(entry['doi'])
            if is_valid:
                result['verified'] = True
                result['sources'].append('CrossRef')
                result['metadata']['crossref'] = metadata
                return result
        
        # Try arXiv
        if 'eprint' in entry or 'archiveprefix' in entry:
            arxiv_id = entry.get('eprint', '')
            if arxiv_id:
                is_valid, metadata = self.verify_arxiv(arxiv_id)
                if is_valid:
                    result['verified'] = True
                    result['sources'].append('arXiv')
                    result['metadata']['arxiv'] = metadata
                    return result
        
        # Try title search with OpenAlex as fallback
        if 'title' in entry:
            is_valid, metadata = self.verify_openalex(entry['title'])
            if is_valid:
                result['verified'] = True
                result['sources'].append('OpenAlex')
                result['metadata']['openalex'] = metadata
        
        return result
    
    def verify_file(self, bib_file: str) -> List[Dict]:
        """
        Verify all entries in a BibTeX file.
        
        Args:
            bib_file: Path to the BibTeX file
            
        Returns:
            List of verification results for each entry
        """
        results = []
        
        try:
            with open(bib_file, 'r', encoding='utf-8') as f:
                bib_database = bibtexparser.load(f)
            
            for entry in bib_database.entries:
                result = self.verify_entry(entry)
                results.append(result)
                # Be polite to APIs
                time.sleep(0.5)
            
        except Exception as e:
            print(f"Error processing file {bib_file}: {e}")
        
        return results


def verify_bib_entry(entry: Dict, email: Optional[str] = None) -> Dict:
    """
    Convenience function to verify a single BibTeX entry.
    
    Args:
        entry: Dictionary representing a BibTeX entry
        email: Email for CrossRef Polite Pool (optional)
        
    Returns:
        Dictionary with verification results
    """
    verifier = BibVerifier(email=email)
    return verifier.verify_entry(entry)


def verify_bib_file(bib_file: str, email: Optional[str] = None) -> List[Dict]:
    """
    Convenience function to verify all entries in a BibTeX file.
    
    Args:
        bib_file: Path to the BibTeX file
        email: Email for CrossRef Polite Pool (optional)
        
    Returns:
        List of verification results for each entry
    """
    verifier = BibVerifier(email=email)
    return verifier.verify_file(bib_file)
