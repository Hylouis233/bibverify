"""
Basic example of using bibverify to verify a single BibTeX entry.
"""

from bibverify import verify_bib_entry

# Example BibTeX entry as a dictionary
entry = {
    'ID': 'einstein1905',
    'ENTRYTYPE': 'article',
    'title': 'On the electrodynamics of moving bodies',
    'author': 'Einstein, Albert',
    'journal': 'Annalen der Physik',
    'year': '1905',
    'doi': '10.1002/andp.19053221004'
}

# Verify the entry
print("Verifying citation...")
result = verify_bib_entry(entry, email="your@email.com")  # Replace with your email

# Display results
print(f"\nCitation ID: {result['id']}")
print(f"Verified: {result['verified']}")
print(f"Sources: {', '.join(result['sources'])}")

if result['verified']:
    print("\n✓ Citation successfully verified!")
else:
    print("\n✗ Citation could not be verified")
