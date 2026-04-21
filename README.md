# challenge-validator

> Your bot detection is blocking real users. Here's proof.

[![License: Non-Commercial](https://img.shields.io/badge/License-Non--Commercial-red.svg)]
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-18%20passing-brightgreen.svg)]()

An open-source CLI that runs **22 tests across 7 categories** against your bot-detection / CAPTCHA SDK integration and tells you exactly what's broken — with fix guides for every failure.

## The Problem

Every major bot-detection platform (Cloudflare Turnstile, reCAPTCHA Enterprise, hCaptcha, AWS WAF Bot Control, Akamai, DataDome) requires frontend integration. That integration breaks in predictable, documented-nowhere ways:

- **Challenge → Solve → Block loop** — User solves CAPTCHA, gets blocked anyway for 5-10 minutes
- **SPA token expiry** — Token expires, app doesn't refresh, all API calls fail silently
- **CORS preflight blocked** — OPTIONS requests have no token, get blocked, entire API chain fails
- **Cookie scoping** — Token scoped to `www.` but API lives on `api.` — cross-subdomain breaks
- **Performance penalty** — Challenge SDK adds 200KB+ JS and causes layout shift on every page load

These aren't edge cases. They're the default experience for anyone integrating bot detection into a modern web app.

## Quick Start

```bash
pip install challenge-validator

# Test your site (basic — checks challenge detection + degradation)
challenge-validator test https://yoursite.com

# Full test with your authenticated token
challenge-validator test https://yoursite.com --token "cf_clearance=abc123..."

# Use a vendor-specific profile for more accurate detection
challenge-validator test https://yoursite.com --profile cloudflare --token "cf_clearance=abc123..."

# Output as JSON or Markdown
challenge-validator test https://yoursite.com --format json
challenge-validator test https://yoursite.com --format markdown -o report.md
```

## Sample Output

```
═══════════════════════════════════════════════════════════════
  CHALLENGE INTEGRATION REPORT — yoursite.com
═══════════════════════════════════════════════════════════════

  TOKEN LIFECYCLE                                        3/4
  ──────────────────────────────────────────────────────────
  ✅ PASS  Initial page serves challenge/JS SDK
  ✅ PASS  Challenge token set in cookie after page load
  ❌ FAIL  Token not refreshed after expiry (tested at 300s)
           → SPA users will be blocked after 5 minutes
           → Fix: see docs/spa-token-refresh.md
  ✅ PASS  Fresh token accepted on subsequent requests

  CORS / API HANDLING                                    1/3
  ──────────────────────────────────────────────────────────
  ❌ FAIL  OPTIONS preflight returns 403 (no challenge token)
           → All cross-origin API calls will fail
           → Fix: see docs/cors-preflight.md
  ❌ FAIL  Non-HTML content type gets challenge page
           → API consumers get HTML instead of JSON error
           → Fix: see docs/api-content-type.md
  ✅ PASS  POST with valid token accepted

  SESSION / COOKIES                                      3/4
  ──────────────────────────────────────────────────────────
  ❌ FAIL  Cookie scoped to www.example.com — won't work on api.example.com
           → Fix: see docs/cookie-cross-subdomain.md
  ✅ PASS  Total cookie size under 4KB limit
  ✅ PASS  Works with third-party cookies blocked
  ✅ PASS  Clean challenge in incognito mode

  PERFORMANCE / UX                                       3/4
  ──────────────────────────────────────────────────────────
  ✅ PASS  Challenge latency: 180ms overhead
  ⚠️ WARN  SDK JS bundle: 245KB (target: <100KB)
  ✅ PASS  No layout shift from challenge widget
  ✅ PASS  Repeat visitor: no extra latency

  ══════════════════════════════════════════════════════════
  SCORE: 14/22 passed  │  5 failures  │  3 warnings
  PRIORITY: Fix CORS preflight + token refresh + cookie scope
  ══════════════════════════════════════════════════════════
```

## What It Tests (22 tests, 7 categories)

| # | Category | Tests | What it catches |
|---|---|---|---|
| 1 | **Token Lifecycle** | 4 | Token not set, not refreshed, not accepted |
| 2 | **CORS / API** | 3 | Preflight blocked, wrong content-type, token in API calls |
| 3 | **Post-Challenge** | 2 | Solve-then-block loop, multi-tab sharing |
| 4 | **Degradation** | 2 | JS failure, noscript fallback |
| 5 | **Score Handling** | 3 | Double punishment, opaque scores, threshold misconfiguration |
| 6 | **Session / Cookies** | 4 | Cross-subdomain, cookie overflow, third-party blocking, incognito |
| 7 | **Performance / UX** | 4 | Latency, bundle size, layout shift, repeat visitor penalty |

## Vendor Profiles

| Profile | Flag | What it knows |
|---|---|---|
| **Generic** | `--profile generic` (default) | Works with any challenge SDK |
| **Cloudflare** | `--profile cloudflare` | Turnstile, Bot Management, cf_clearance tokens |
| **reCAPTCHA** | `--profile recaptcha` | reCAPTCHA Enterprise, grecaptcha tokens |
| **hCaptcha** | `--profile hcaptcha` | hCaptcha widget and tokens |
| **AWS WAF** | `--profile aws-waf` | Bot Control, CAPTCHA (405), Silent Challenge (202), aws-waf-token |

Vendor profiles include specific token patterns, challenge indicators, timing defaults, and **vendor notes** — contextual guidance that appears alongside test results when relevant.

## Fix Guides

Every failure links to a fix guide with root cause, solution, and code examples:

| Guide | What it fixes |
|---|---|
| [spa-token-refresh.md](docs/spa-token-refresh.md) | SPA token expiry — polling refresh, 403 intercept, SDK-specific methods |
| [cors-preflight.md](docs/cors-preflight.md) | CORS OPTIONS blocked — exempting preflight from challenge rules |
| [api-content-type.md](docs/api-content-type.md) | HTML challenge page returned for API requests |
| [challenge-block-loop.md](docs/challenge-block-loop.md) | Blocked after solving CAPTCHA — rate-limit rule interaction |
| [score-double-punishment.md](docs/score-double-punishment.md) | Challenged AND throttled simultaneously |
| [cookie-cross-subdomain.md](docs/cookie-cross-subdomain.md) | Token cookie scoped too narrowly for cross-subdomain apps |
| [mobile-sdk-integration.md](docs/mobile-sdk-integration.md) | Platform-agnostic mobile SDK guide |
| [aws-waf-integration.md](docs/aws-waf-integration.md) | AWS WAF-specific gotchas (405 CAPTCHA, TGT_VolumetricIpTokenAbsent, etc.) |

### Framework Guides

| Guide | What it covers |
|---|---|
| [nextjs-ssr.md](docs/framework-guides/nextjs-ssr.md) | Next.js SSR + challenge SDK |
| [remix.md](docs/framework-guides/remix.md) | Remix loader/action + challenge tokens |
| [flutter-amplify.md](docs/framework-guides/flutter-amplify.md) | Flutter + Amplify + challenge SDK |
| [spa-api-gateway.md](docs/framework-guides/spa-api-gateway.md) | SPA → API Gateway with challenge tokens |

## CLI Reference

```
challenge-validator test <url> [options]

Options:
  --token TOKEN        Pre-authenticated challenge cookie value
  --profile PROFILE    Vendor: generic, cloudflare, recaptcha, hcaptcha, aws-waf
  --suite SUITE        Test suite: all, token, cors, post-challenge,
                       degradation, score, cookies, performance
  --format FORMAT      Output: terminal (default), json, markdown
  -o, --output FILE    Write report to file
  --timeout SECONDS    HTTP request timeout (default: 10)
  --token-ttl SECONDS  Override token TTL for refresh test
  -v, --verbose        Show detailed test output
```

## What This Tool Does NOT Do

- ❌ Does NOT solve CAPTCHAs or bypass challenges
- ❌ Does NOT pentest or attack your site
- ❌ Does NOT require access to your WAF/CDN admin console
- ❌ Does NOT send any data anywhere — fully local
- ❌ Does NOT replace vendor support — it supplements it

This is a diagnostic tool. It tells you what's broken so you can fix it before your users find it.

## FAQ

**"Does this solve CAPTCHAs?"**
No. You provide a pre-solved token via `--token`. The tool tests your *integration*, not the challenge itself.

**"Is this a pentesting tool?"**
No. It tests YOUR site's integration quality. It makes standard HTTP requests and analyzes responses.

**"What if my site doesn't use any challenge SDK?"**
The `token_initial` test will detect "no challenge found" and skip token-dependent tests. You'll still get results for CORS, degradation, and performance tests.

**"Can I add my own vendor profile?"**
Yes — see [CONTRIBUTING.md](CONTRIBUTING.md). Profiles are YAML files with token patterns and challenge indicators.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add vendor profiles, fix guides, and new tests.

## License

see [LICENSE](LICENSE).
