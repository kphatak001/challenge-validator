# Contributing to challenge-validator

Thanks for helping make bot-detection integrations less painful for everyone.

## Adding a Vendor Profile

Vendor profiles live in `challenge_validator/profiles/` as YAML files.

### Quick start

1. Copy `profiles/generic.yaml` as a starting point
2. Rename to your vendor (e.g., `datadome.yaml`)
3. Fill in:
   - `name` — Vendor display name
   - `description` — What the profile covers
   - `token_cookies` — Cookie patterns the vendor sets (list of `pattern:` entries)
   - `challenge_indicators` — How to detect a challenge page:
     - `status_codes` — HTTP status codes returned for challenges
     - `html_patterns` — Strings found in challenge HTML
     - `headers` — Response headers indicating a challenge
   - `score_headers` — Bot score headers (empty list `[]` if vendor uses labels instead)
   - `token_ttl_seconds` — Default token lifetime
   - `sdk_script_patterns` — URL patterns for the vendor's JS SDK
   - `widget_patterns` — CSS class/ID patterns for challenge widgets
4. Optionally add `vendor_notes` — a dict of test_id → contextual notes that appear when tests fail

### Testing your profile

```bash
challenge-validator test https://example.com --profile your-vendor --token "your_token"
```

### Submit a PR

- Add the YAML file to `challenge_validator/profiles/`
- Add the profile name to the `--profile` choices in `cli.py`
- Add a row to the Vendor Profiles table in `README.md`

## Adding a Fix Guide

Fix guides live in `docs/` as Markdown files.

### Structure

Every fix guide should follow this template:

```markdown
# [Problem Name] — Fix Guide

## The Problem
What the user experiences. One paragraph.

## Why This Happens
Root cause. Explain the mechanics.

## The Fix

### Option A: [simplest approach]
[code examples]

### Option B: [most robust approach]
[code examples]

### Option C: [vendor-specific]
[code examples per vendor]

## Verification
How to confirm the fix works (ideally: re-run challenge-validator).
```

### Submit a PR

- Add the Markdown file to `docs/` or `docs/framework-guides/`
- Link it from the relevant test's `fix_guide` field
- Add a row to the Fix Guides table in `README.md`

## Adding a Test

Tests live in `challenge_validator/tests/` as Python modules.

### Requirements

1. Subclass `BaseTest` from `tests/base.py`
2. Set `category` class attribute
3. Implement `run()` → returns `list[TestResult]`
4. Every `FAIL` result should include a `fix_guide` path
5. Tests must be independent (no cross-test dependencies)
6. Tests should be non-destructive (read-only HTTP requests)

### Adding to the runner

Register your test class in the `SUITE_MAP` dict in `runner.py`.

## Code Style

- Python 3.10+, type hints encouraged
- No external dependencies beyond `requests`, `beautifulsoup4`, `pyyaml` (core) and `rich` (optional)
- Run tests: `python -m pytest tests/`

## Questions?

Open an issue — happy to help.
