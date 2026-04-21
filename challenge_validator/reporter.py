"""Output: terminal (rich), JSON, Markdown."""

import json
import sys
from collections import defaultdict
from dataclasses import asdict

from .tests.base import TestResult, Status

STATUS_ICONS = {
    Status.PASS: "✅",
    Status.FAIL: "❌",
    Status.WARN: "⚠️",
    Status.SKIP: "⏭️",
    Status.ERROR: "💥",
}

# Map test_id → vendor_notes key to surface when that test fails/warns/skips
_VENDOR_NOTE_MAP = {
    "cors_preflight": "cors_preflight",
    "token_refresh": "token_refresh_spa",
    "solve_block_loop": "rate_limit_interaction",
    "score_double_punishment": "rate_limit_interaction",
    "score_threshold": "score_not_available",
    "score_transparency": "score_not_available",
    "token_initial": "captcha_vs_challenge",
}


def _get_vendor_note(test_id: str, status: Status, profile: dict) -> str | None:
    """Return vendor note text if relevant for this test result."""
    if status == Status.PASS:
        return None
    notes = profile.get("vendor_notes", {})
    key = _VENDOR_NOTE_MAP.get(test_id)
    return notes.get(key) if key else None


def report_terminal(results: list[TestResult], verbose: bool = False, file=None, profile: dict = None):
    out = file or sys.stdout
    profile = profile or {}
    grouped = defaultdict(list)
    for r in results:
        grouped[r.category].append(r)

    total = len(results)
    passed = sum(1 for r in results if r.status == Status.PASS)
    failed = sum(1 for r in results if r.status == Status.FAIL)
    warned = sum(1 for r in results if r.status == Status.WARN)

    print("\n" + "=" * 60, file=out)
    print("  challenge-validator report", file=out)
    if profile.get("name"):
        print(f"  Profile: {profile['name']}", file=out)
    print("=" * 60, file=out)

    for category, tests in grouped.items():
        cat_pass = sum(1 for t in tests if t.status == Status.PASS)
        print(f"\n── {category} ({cat_pass}/{len(tests)} passed) ──", file=out)
        for t in tests:
            icon = STATUS_ICONS.get(t.status, "?")
            label = t.status.value.upper()
            print(f"  {icon} {label:5s} {t.name}", file=out)
            if t.status in (Status.FAIL, Status.WARN, Status.ERROR, Status.SKIP) or verbose:
                print(f"         → {t.message}", file=out)
            if t.fix_guide and t.status == Status.FAIL:
                print(f"         → Fix: see {t.fix_guide}", file=out)
            if verbose and t.details:
                for k, v in t.details.items():
                    print(f"         {k}: {v}", file=out)
            # Vendor-specific note
            note = _get_vendor_note(t.test_id, t.status, profile)
            if note:
                for line in note.strip().splitlines():
                    print(f"         ℹ️  {line.strip()}", file=out)

    print("\n" + "=" * 60, file=out)
    print(f"  SCORE: {passed}/{total} passed | {failed} failures | {warned} warnings", file=out)

    failures = [r for r in results if r.status == Status.FAIL]
    if failures:
        print(f"  PRIORITY:", file=out)
        for f in failures[:2]:
            guide = f" → {f.fix_guide}" if f.fix_guide else ""
            print(f"    • {f.name}{guide}", file=out)
    print("=" * 60 + "\n", file=out)


def report_json(results: list[TestResult], file=None, profile: dict = None):
    out = file or sys.stdout
    profile = profile or {}
    data = {
        "profile": profile.get("name", "unknown"),
        "total": len(results),
        "passed": sum(1 for r in results if r.status == Status.PASS),
        "failed": sum(1 for r in results if r.status == Status.FAIL),
        "warned": sum(1 for r in results if r.status == Status.WARN),
        "results": [],
    }
    for r in results:
        entry = asdict(r)
        note = _get_vendor_note(r.test_id, r.status, profile)
        if note:
            entry["vendor_note"] = note.strip()
        data["results"].append(entry)
    print(json.dumps(data, indent=2, default=str), file=out)


def report_markdown(results: list[TestResult], file=None, profile: dict = None):
    out = file or sys.stdout
    profile = profile or {}
    grouped = defaultdict(list)
    for r in results:
        grouped[r.category].append(r)

    total = len(results)
    passed = sum(1 for r in results if r.status == Status.PASS)
    failed = sum(1 for r in results if r.status == Status.FAIL)
    warned = sum(1 for r in results if r.status == Status.WARN)

    print(f"# challenge-validator Report\n", file=out)
    if profile.get("name"):
        print(f"**Profile:** {profile['name']}\n", file=out)
    print(f"**{passed}/{total}** passed | **{failed}** failures | **{warned}** warnings\n", file=out)

    for category, tests in grouped.items():
        print(f"## {category}\n", file=out)
        print("| Status | Test | Message |", file=out)
        print("|--------|------|---------|", file=out)
        for t in tests:
            icon = STATUS_ICONS.get(t.status, "?")
            guide = f" ([fix]({t.fix_guide}))" if t.fix_guide and t.status == Status.FAIL else ""
            print(f"| {icon} {t.status.value.upper()} | {t.name} | {t.message}{guide} |", file=out)
        print(file=out)

        # Vendor notes block after table
        notes_printed = set()
        for t in tests:
            note = _get_vendor_note(t.test_id, t.status, profile)
            if note and t.test_id not in notes_printed:
                notes_printed.add(t.test_id)
                print(f"> **Vendor note ({t.name}):** {note.strip()}\n", file=out)
