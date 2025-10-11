"""
Command-line interface for bibverify.
"""

import argparse
import json
import sys
from .verifier import BibVerifier


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Verify BibTeX citations against academic databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bibverify references.bib
  bibverify references.bib --email your@email.com
  bibverify references.bib --output results.json
  bibverify references.bib --verbose
        """
    )
    
    parser.add_argument(
        "bibfile",
        help="Path to the BibTeX file to verify"
    )
    
    parser.add_argument(
        "--email",
        help="Email for CrossRef Polite Pool (recommended for better rate limits)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file for results (JSON format)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed verification results"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Create verifier
    verifier = BibVerifier(email=args.email, timeout=args.timeout)
    
    # Verify the file
    print(f"Verifying citations in {args.bibfile}...")
    results = verifier.verify_file(args.bibfile)
    
    # Count verified and unverified
    verified_count = sum(1 for r in results if r['verified'])
    total_count = len(results)
    
    # Display results
    print(f"\nResults: {verified_count}/{total_count} citations verified")
    print("-" * 60)
    
    for result in results:
        status = "✓" if result['verified'] else "✗"
        sources = ", ".join(result['sources']) if result['sources'] else "None"
        print(f"{status} {result['id']}: {sources}")
        
        if args.verbose and not result['verified']:
            print(f"  Warning: Could not verify this citation")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed results saved to {args.output}")
    
    # Exit with error code if any citations failed
    if verified_count < total_count:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
