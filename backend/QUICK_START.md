# Quick Start - Testing PDF Parser

## Fastest Way to Test

```bash
# 1. Go to backend directory
cd backend

# 2. Install dependencies (if not already done)
pip install -r requirements.txt

# 3. Run test script with your PDF
python test_parser.py /path/to/your/file.pdf
```

That's it! The script will:
- Parse your PDF
- Show a summary of what was extracted
- Save full results to `<filename>_parsed.json`

## Example

```bash
# If your PDF is in the parent directory
python test_parser.py ../my_dct_file.pdf

# Output will show:
# - Number of questions found
# - Metadata extracted
# - First 10 questions
# - Full JSON saved to my_dct_file_parsed.json
```

## Debug Mode

To see what patterns the parser detects:

```bash
python test_parser.py ../my_dct_file.pdf --debug
```

## Check Results

After running, check the generated JSON file:

```bash
# View the JSON output
cat my_dct_file_parsed.json | python -m json.tool | less

# Or open in your editor
open my_dct_file_parsed.json  # macOS
# or
code my_dct_file_parsed.json  # VS Code
```

## Need Help?

See `README_TESTING.md` for detailed troubleshooting and advanced usage.
