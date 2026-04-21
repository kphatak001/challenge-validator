# Challenge Block Loop

## Problem

Users who just solved a challenge get immediately blocked by a rate-limit rule, creating a frustrating loop.

## Root Cause

Two independent rules fire on the same traffic:
1. **Challenge rule**: "This IP looks suspicious → serve challenge"
2. **Rate-limit rule**: "This IP sent a burst of requests → block"

After solving the challenge, the user's browser retries queued requests. The rate-limit rule sees a burst from an IP that was just flagged and blocks it.

## Solution

1. **Exempt recently-challenged IPs from rate-limiting** for a grace period (30-60 seconds):
   - Cloudflare: Use a custom rule that skips rate-limiting when `cf_clearance` cookie age < 60s
   - AWS WAF: Add a rate-limit exception for IPs that recently passed a CAPTCHA

2. **Increase the rate-limit threshold** for the first minute after challenge completion.

3. **Stagger retries on the client side** — don't retry all queued requests simultaneously:
   ```javascript
   async function retryQueue(requests) {
     for (const req of requests) {
       await fetch(req.url, req.options);
       await new Promise(r => setTimeout(r, 200)); // 200ms between retries
     }
   }
   ```

## Verification

Run: `challenge-validator test <url> --token <token> --suite post-challenge`

The `solve_block_loop` test should now pass.
