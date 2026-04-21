# Score Double Punishment

## Problem

Medium-risk requests trigger both a challenge AND a rate-limit, punishing the user twice for the same traffic pattern.

## Root Cause

Challenge rules and rate-limit rules are configured independently. A request that scores "medium risk" triggers the challenge rule. The same request also counts toward the rate-limit counter. After solving the challenge, the user has already accumulated rate-limit hits and gets throttled.

## Solution

1. **Make rate-limit rules challenge-aware.** Don't count requests that resulted in a challenge toward the rate-limit:
   - Cloudflare: Use `cf-mitigated` header to identify challenged requests and exclude them from rate-limit counters
   - AWS WAF: Configure rate-limit rules to only count requests that weren't CAPTCHA-challenged

2. **Use a single decision point.** Instead of independent challenge + rate-limit rules, use a combined rule:
   - Score < 30 → Block
   - Score 30-70 → Challenge (no rate-limit)
   - Score > 70 → Allow

3. **Reset rate-limit counters after challenge completion.**

## Verification

Run: `challenge-validator test <url> --token <token> --suite score`

The `score_double_punishment` test should now pass.
