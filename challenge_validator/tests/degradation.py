"""Degradation & Fallback tests (2 tests)."""

import requests
from bs4 import BeautifulSoup

from .base import BaseTest, TestResult, Status


class DegradationTests(BaseTest):
    category = "Degradation & Fallback"

    def run(self) -> list[TestResult]:
        results = []
        self._test_js_blocked(results)
        self._test_noscript_fallback(results)
        return results

    def _test_js_blocked(self, results):
        try:
            resp = requests.get(self.target_url, timeout=self.timeout, allow_redirects=False)
        except requests.RequestException as e:
            results.append(TestResult("js_blocked", self.category, "Site loads when JS blocked",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        # Check for redirect loops
        if resp.status_code in (301, 302, 303, 307, 308):
            results.append(TestResult("js_blocked", self.category, "Site loads when JS blocked",
                                      Status.FAIL, f"Redirect ({resp.status_code}) — possible infinite redirect without JS",
                                      details={"status_code": resp.status_code, "location": resp.headers.get("Location", "")}))
            return

        body = resp.text.strip()
        if not body or len(body) < 100:
            results.append(TestResult("js_blocked", self.category, "Site loads when JS blocked",
                                      Status.FAIL, "Blank or near-empty page without JS",
                                      details={"body_length": len(body)}))
        elif len(body) < 500:
            results.append(TestResult("js_blocked", self.category, "Site loads when JS blocked",
                                      Status.WARN, "Page loads but with minimal content",
                                      details={"body_length": len(body)}))
        else:
            results.append(TestResult("js_blocked", self.category, "Site loads when JS blocked",
                                      Status.PASS, "Page returns meaningful content without JS",
                                      details={"body_length": len(body)}))

    def _test_noscript_fallback(self, results):
        try:
            resp = requests.get(self.target_url, timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("noscript_fallback", self.category, "Noscript fallback present",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        noscripts = soup.find_all("noscript")
        meaningful = [ns for ns in noscripts if ns.get_text(strip=True)]

        if meaningful:
            results.append(TestResult("noscript_fallback", self.category, "Noscript fallback present",
                                      Status.PASS, f"Found {len(meaningful)} <noscript> tag(s) with content"))
        else:
            results.append(TestResult("noscript_fallback", self.category, "Noscript fallback present",
                                      Status.WARN, "No <noscript> fallback — non-JS users get nothing"))
