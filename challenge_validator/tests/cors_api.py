"""CORS / API Handling tests (3 tests)."""

import requests

from .base import BaseTest, TestResult, Status
from .token_lifecycle import _is_challenge, _token_cookie_name


class CorsApiTests(BaseTest):
    category = "CORS / API Handling"

    def run(self) -> list[TestResult]:
        results = []
        self._test_preflight(results)
        self._test_content_type(results)
        self._test_api_with_token(results)
        return results

    def _test_preflight(self, results):
        try:
            resp = requests.options(self.target_url, headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type, authorization",
            }, timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("cors_preflight", self.category, "OPTIONS preflight not blocked",
                                      Status.ERROR, f"Request failed: {e}", fix_guide="docs/cors-preflight.md"))
            return

        if resp.status_code in (200, 204):
            results.append(TestResult("cors_preflight", self.category, "OPTIONS preflight not blocked",
                                      Status.PASS, f"Preflight returned {resp.status_code} with CORS headers",
                                      details={"status_code": resp.status_code}))
        elif _is_challenge(resp, self.profile):
            results.append(TestResult("cors_preflight", self.category, "OPTIONS preflight not blocked",
                                      Status.FAIL, "Preflight blocked by challenge rules",
                                      fix_guide="docs/cors-preflight.md",
                                      details={"status_code": resp.status_code}))
        else:
            results.append(TestResult("cors_preflight", self.category, "OPTIONS preflight not blocked",
                                      Status.WARN, f"Preflight returned {resp.status_code}",
                                      fix_guide="docs/cors-preflight.md",
                                      details={"status_code": resp.status_code}))

    def _test_content_type(self, results):
        try:
            resp = requests.get(self.target_url, headers={"Accept": "application/json"},
                                timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("api_content_type", self.category, "API returns JSON errors, not HTML",
                                      Status.ERROR, f"Request failed: {e}", fix_guide="docs/api-content-type.md"))
            return

        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct:
            results.append(TestResult("api_content_type", self.category, "API returns JSON errors, not HTML",
                                      Status.PASS, f"Response Content-Type: {ct}",
                                      details={"content_type": ct, "status_code": resp.status_code}))
        elif "text/html" in ct:
            results.append(TestResult("api_content_type", self.category, "API returns JSON errors, not HTML",
                                      Status.FAIL, "Got HTML challenge page for API request (Accept: application/json)",
                                      fix_guide="docs/api-content-type.md",
                                      details={"content_type": ct, "status_code": resp.status_code}))
        else:
            results.append(TestResult("api_content_type", self.category, "API returns JSON errors, not HTML",
                                      Status.WARN, f"Unexpected Content-Type: {ct}",
                                      fix_guide="docs/api-content-type.md",
                                      details={"content_type": ct, "status_code": resp.status_code}))

    def _test_api_with_token(self, results):
        if not self.token:
            results.append(TestResult("api_with_token", self.category, "API request with token succeeds",
                                      Status.SKIP, "No --token provided"))
            return

        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"
        try:
            resp = requests.post(self.target_url, cookies={cookie_name: self.token},
                                 headers={"Content-Type": "application/json"},
                                 json={}, timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("api_with_token", self.category, "API request with token succeeds",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        if _is_challenge(resp, self.profile):
            results.append(TestResult("api_with_token", self.category, "API request with token succeeds",
                                      Status.FAIL, "POST with valid token still returns challenge",
                                      details={"status_code": resp.status_code}))
        else:
            results.append(TestResult("api_with_token", self.category, "API request with token succeeds",
                                      Status.PASS, f"API request accepted ({resp.status_code})",
                                      details={"status_code": resp.status_code}))
