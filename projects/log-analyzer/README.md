# Log Analyzer

A small Python tool for looking through login logs.

I made it to practice parsing logs and detecting repeated failed logins.

### Example

```bash
python analyze.py sample.log
```

If one IP has too many failed attempts, the script prints an alert.

### Built with

Python, regex and collections.

The next step would be turning this into a small API and dashboard.
