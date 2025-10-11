"""
Example of verifying all citations in a BibTeX file.
"""

from bibverify import verify_bib_file
import json

# Example: Create a sample BibTeX file for testing
sample_bib = """
@article{einstein1905,
    title={On the electrodynamics of moving bodies},
    author={Einstein, Albert},
    journal={Annalen der Physik},
    year={1905},
    doi={10.1002/andp.19053221004}
}

@article{arxiv_example,
    title={Attention Is All You Need},
    author={Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
    journal={arXiv preprint arXiv:1706.03762},
    year={2017},
    eprint={1706.03762},
    archiveprefix={arXiv}
}
"""

# Save sample file
with open('sample.bib', 'w') as f:
    f.write(sample_bib)

# Verify all entries in the file
print("Verifying citations in sample.bib...")
results = verify_bib_file('sample.bib', email="your@email.com")  # Replace with your email

# Display summary
verified_count = sum(1 for r in results if r['verified'])
total_count = len(results)

print(f"\nVerification Summary:")
print(f"Total citations: {total_count}")
print(f"Verified: {verified_count}")
print(f"Failed: {total_count - verified_count}")
print("-" * 50)

# Display details for each entry
for result in results:
    status = "✓" if result['verified'] else "✗"
    sources = ", ".join(result['sources']) if result['sources'] else "None"
    print(f"{status} {result['id']}: {sources}")

# Save detailed results to JSON
with open('verification_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nDetailed results saved to verification_results.json")
