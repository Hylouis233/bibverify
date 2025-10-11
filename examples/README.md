# BibVerify Examples

This directory contains example scripts demonstrating various uses of the bibverify package.

## Examples

### 1. verify_single.py
Demonstrates how to verify a single BibTeX entry.

```bash
python verify_single.py
```

### 2. verify_file.py
Shows how to verify all citations in a BibTeX file and save results to JSON.

```bash
python verify_file.py
```

This will:
- Create a sample BibTeX file (`sample.bib`)
- Verify all entries
- Save detailed results to `verification_results.json`

### 3. advanced_usage.py
Demonstrates advanced features including:
- Custom BibVerifier configuration
- Error handling
- Detecting fake citations
- Generating detailed reports

```bash
python advanced_usage.py
```

## Customization

Remember to replace `"your@email.com"` with your actual email address in the examples. Using your email gives you access to CrossRef's Polite Pool with better rate limits.

## Output Files

The examples may create the following files:
- `sample.bib` - Sample BibTeX file
- `verification_results.json` - Verification results
- `advanced_report.json` - Detailed verification report

## Tips

- Always provide your email when making many requests
- Check the JSON output files for detailed metadata
- The examples can be modified to use your own BibTeX files
