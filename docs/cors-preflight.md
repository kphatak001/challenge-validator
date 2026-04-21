# CORS Preflight

## Problem

Browser OPTIONS preflight requests are blocked by your challenge/WAF rules, breaking cross-origin API calls.

## Root Cause

Challenge rules match all HTTP methods including OPTIONS. Browsers send OPTIONS before any cross-origin POST/PUT/DELETE. Since OPTIONS requests can't carry challenge cookies, they get blocked.

## Solution

1. **Exempt OPTIONS from challenge rules.** In your WAF/CDN config, add a rule that allows OPTIONS requests to pass through without challenge evaluation.
2. **Cloudflare example:** Create a WAF custom rule:
   - Expression: `(http.request.method eq "OPTIONS")`
   - Action: Skip all remaining rules
3. **AWS WAF example:** Add a rule with higher priority that allows OPTIONS:
   ```json
   {
     "Name": "AllowPreflight",
     "Priority": 0,
     "Statement": {
       "ByteMatchStatement": {
         "FieldToMatch": { "Method": {} },
         "PositionalConstraint": "EXACTLY",
         "SearchString": "OPTIONS"
       }
     },
     "Action": { "Allow": {} }
   }
   ```

## Verification

Run: `challenge-validator test <url> --suite cors`

The `cors_preflight` test should now pass.
