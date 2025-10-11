"""
Advanced example showing how to use the BibVerifier class directly
with custom configuration and error handling.
"""

from bibverify import BibVerifier
import json

def main():
    # Initialize verifier with custom settings
    verifier = BibVerifier(
        email="your@email.com",  # Replace with your email
        timeout=15  # Longer timeout for slow connections
    )
    
    # Example entries to verify
    entries = [
        {
            'ID': 'turing1950',
            'title': 'Computing Machinery and Intelligence',
            'author': 'Turing, Alan M.',
            'journal': 'Mind',
            'year': '1950',
            'doi': '10.1093/mind/LIX.236.433'
        },
        {
            'ID': 'deep_learning',
            'title': 'Deep Learning',
            'author': 'LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey',
            'year': '2015',
            'doi': '10.1038/nature14539'
        },
        {
            'ID': 'fake_citation',
            'title': 'This Is A Completely Made Up Paper That Does Not Exist',
            'author': 'Nobody, John',
            'year': '2025'
        }
    ]
    
    # Verify each entry
    results = []
    for entry in entries:
        print(f"\nVerifying: {entry['ID']}")
        result = verifier.verify_entry(entry)
        results.append(result)
        
        if result['verified']:
            print(f"  ✓ Verified via: {', '.join(result['sources'])}")
        else:
            print(f"  ✗ Could not verify - possible fake citation")
    
    # Generate report
    print("\n" + "=" * 60)
    print("VERIFICATION REPORT")
    print("=" * 60)
    
    verified = [r for r in results if r['verified']]
    unverified = [r for r in results if not r['verified']]
    
    print(f"\nTotal Citations: {len(results)}")
    print(f"Verified: {len(verified)}")
    print(f"Unverified: {len(unverified)}")
    
    if unverified:
        print("\n⚠️  Suspicious Citations (Could Not Verify):")
        for result in unverified:
            print(f"  - {result['id']}")
    
    # Save detailed report
    report = {
        'summary': {
            'total': len(results),
            'verified': len(verified),
            'unverified': len(unverified)
        },
        'results': results
    }
    
    with open('advanced_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\nDetailed report saved to advanced_report.json")

if __name__ == "__main__":
    main()
