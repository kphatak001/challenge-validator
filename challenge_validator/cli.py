"""CLI entry point for challenge-validator."""

import argparse
import sys

from . import __version__
from .profiles import list_profiles
from .runner import run_tests, SUITE_MAP
from .reporter import report_terminal, report_json, report_markdown


def main():
    parser = argparse.ArgumentParser(
        prog="challenge-validator",
        description="Test your bot-detection / CAPTCHA SDK integration. "
                    "22 tests, 7 categories, fix guides included.",
    )
    parser.add_argument("command", choices=["test"], help="Command to run")
    parser.add_argument("url", help="Target URL to test")
    parser.add_argument("--token", help="Pre-authenticated challenge cookie value")
    parser.add_argument("--profile", default="generic",
                        choices=list_profiles(),
                        help="Vendor profile (default: generic)")
    parser.add_argument("--suite", default="all",
                        help=f"Test suite: all (default), {', '.join(SUITE_MAP.keys())}")
    parser.add_argument("--format", dest="fmt", default="terminal",
                        choices=["terminal", "json", "markdown"],
                        help="Output format (default: terminal)")
    parser.add_argument("-o", "--output", help="Write report to file (default: stdout)")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP request timeout in seconds (default: 10)")
    parser.add_argument("--token-ttl", type=int, default=None,
                        help="Override token TTL for refresh test (default: from profile)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed test output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    results, profile = run_tests(
        target_url=args.url,
        token=args.token,
        profile_name=args.profile,
        suites=args.suite,
        timeout=args.timeout,
        token_ttl=args.token_ttl,
    )

    out = open(args.output, "w") if args.output else sys.stdout
    try:
        if args.fmt == "json":
            report_json(results, file=out, profile=profile)
        elif args.fmt == "markdown":
            report_markdown(results, file=out, profile=profile)
        else:
            report_terminal(results, verbose=args.verbose, file=out, profile=profile)
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    main()
