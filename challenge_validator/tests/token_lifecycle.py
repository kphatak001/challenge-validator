"""Token Lifecycle tests (4 tests)."""

import time
import sys
from fnmatch import fnmatch

import requests

from .base import BaseTest, TestResult, Status


def _is_challenge(resp, profile):
    indicators = profile.get("challenge_indicators", {})
    if resp.status_code in indicators.get("status_codes", []):
        return True
    body = resp.text.lower()
    for pat in indicators.get("html_patterns", []):
        if pat.lower() in body:
            return True
    for hdr in indicators.get("headers", []):
        if ":" in hdr:
            k, v = hdr.split(":", 1)
            if resp.headers.get(k.strip(), "").strip().lower() == v.strip().lower():
                return True
        elif hdr.lower() in (h.lower() for h in resp.headers):
            return True
    return False


def _token_cookie_name(profile):
    """Return list of cookie name patterns from profile."""
    return [c["pattern"] for c in profile.get("token_cookies", [])]


class TokenLifecycleTests(BaseTest):
    category = "Token Lifecycle"

    def run(self) -> list[TestResult]:
        results = []
        challenge_detected = self._test_initial(results)
        self._test_set(results, challenge_detected)
        self._test_refresh(results, challenge_detected)
        self._test_reuse(results, challenge_detected)
        return results

    def _test_initial(self, results):
        try:
            resp = requests.get(self.target_url, cookies={}, timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("token_initial", self.category, "Challenge served on first visit",
                                      Status.ERROR, f"Request failed: {e}"))
            return False

        if _is_challenge(resp, self.profile):
            results.append(TestResult("token_initial", self.category, "Challenge served on first visit",
                                      Status.PASS, "Challenge page detected on unauthenticated request",
                                      details={"status_code": resp.status_code}))
            return True

        results.append(TestResult("token_initial", self.category, "Challenge served on first visit",
                                  Status.FAIL, "No challenge detected — path may not be protected or SDK not active"))
        return False

    def _test_set(self, results, challenge_detected):
        if not self.token:
            results.append(TestResult("token_set", self.category, "Token cookie accepted",
                                      Status.SKIP, "No --token provided"))
            return
        if not challenge_detected:
            results.append(TestResult("token_set", self.category, "Token cookie accepted",
                                      Status.SKIP, "No challenge detected on initial request"))
            return

        patterns = _token_cookie_name(self.profile)
        # Find a cookie name that matches profile patterns to set
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"
        try:
            resp = requests.get(self.target_url, cookies={cookie_name: self.token},
                                timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("token_set", self.category, "Token cookie accepted",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        if _is_challenge(resp, self.profile):
            results.append(TestResult("token_set", self.category, "Token cookie accepted",
                                      Status.FAIL, "Token not accepted — still getting challenged",
                                      details={"status_code": resp.status_code}))
        else:
            results.append(TestResult("token_set", self.category, "Token cookie accepted",
                                      Status.PASS, f"Token accepted, got {resp.status_code}",
                                      details={"status_code": resp.status_code}))

    def _test_refresh(self, results, challenge_detected):
        if not self.token:
            results.append(TestResult("token_refresh", self.category, "Token auto-refreshed before expiry",
                                      Status.SKIP, "No --token provided"))
            return
        if not challenge_detected:
            results.append(TestResult("token_refresh", self.category, "Token auto-refreshed before expiry",
                                      Status.SKIP, "No challenge detected on initial request"))
            return

        ttl = self.profile.get("token_ttl_seconds", 300)
        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"

        # First request
        try:
            resp1 = requests.get(self.target_url, cookies={cookie_name: self.token},
                                 timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("token_refresh", self.category, "Token auto-refreshed before expiry",
                                      Status.ERROR, f"First request failed: {e}",
                                      fix_guide="docs/spa-token-refresh.md"))
            return

        if _is_challenge(resp1, self.profile):
            results.append(TestResult("token_refresh", self.category, "Token auto-refreshed before expiry",
                                      Status.SKIP, "Token not accepted on first request",
                                      fix_guide="docs/spa-token-refresh.md"))
            return

        # Wait for TTL
        print(f"  ⏳ Waiting {ttl}s for token TTL...", end="", flush=True)
        for remaining in range(ttl, 0, -1):
            print(f"\r  ⏳ Waiting {remaining}s for token TTL...  ", end="", flush=True)
            time.sleep(1)
        print("\r  ⏳ TTL elapsed, testing refresh...       ")

        # Second request
        try:
            resp2 = requests.get(self.target_url, cookies={cookie_name: self.token},
                                 timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("token_refresh", self.category, "Token auto-refreshed before expiry",
                                      Status.ERROR, f"Second request failed: {e}",
                                      fix_guide="docs/spa-token-refresh.md"))
            return

        if _is_challenge(resp2, self.profile):
            results.append(TestResult("token_refresh", self.category, "Token auto-refreshed before expiry",
                                      Status.FAIL, "Token expired with no refresh — second request got challenged",
                                      fix_guide="docs/spa-token-refresh.md"))
        else:
            results.append(TestResult("token_refresh", self.category, "Token auto-refreshed before expiry",
                                      Status.PASS, "Token still valid or auto-refreshed after TTL"))

    def _test_reuse(self, results, challenge_detected):
        if not self.token:
            results.append(TestResult("token_reuse", self.category, "Subsequent requests accepted",
                                      Status.SKIP, "No --token provided"))
            return
        if not challenge_detected:
            results.append(TestResult("token_reuse", self.category, "Subsequent requests accepted",
                                      Status.SKIP, "No challenge detected on initial request"))
            return

        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"

        passed = 0
        failed = 0
        for i in range(5):
            try:
                resp = requests.get(self.target_url, cookies={cookie_name: self.token},
                                    timeout=self.timeout, allow_redirects=True)
                if _is_challenge(resp, self.profile):
                    failed += 1
                else:
                    passed += 1
            except requests.RequestException:
                failed += 1
            if i < 4:
                time.sleep(1)

        if failed == 0:
            results.append(TestResult("token_reuse", self.category, "Subsequent requests accepted",
                                      Status.PASS, f"All 5 requests accepted",
                                      details={"passed": passed, "failed": failed}))
        elif passed == 0:
            results.append(TestResult("token_reuse", self.category, "Subsequent requests accepted",
                                      Status.FAIL, "All requests challenged — token not reusable",
                                      details={"passed": passed, "failed": failed}))
        else:
            results.append(TestResult("token_reuse", self.category, "Subsequent requests accepted",
                                      Status.WARN, f"Intermittent: {passed}/5 passed — possible rate-limit interaction",
                                      details={"passed": passed, "failed": failed}))
