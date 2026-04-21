"""Session / Cookie Behavior tests (4 tests)."""

import requests

from .base import BaseTest, TestResult, Status
from .token_lifecycle import _token_cookie_name


class SessionCookieTests(BaseTest):
    category = "Session / Cookies"

    def run(self) -> list[TestResult]:
        results = []
        self._test_cookie_scope(results)
        self._test_cookie_size(results)
        self._test_third_party(results)
        self._test_incognito(results)
        return results

    def _get_response(self):
        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"
        cookies = {cookie_name: self.token} if self.token else {}
        return requests.get(self.target_url, cookies=cookies, timeout=self.timeout, allow_redirects=True)

    def _test_cookie_scope(self, results):
        try:
            resp = self._get_response()
        except requests.RequestException as e:
            results.append(TestResult("cookie_scope", self.category, "Token cookie scoped correctly",
                                      Status.ERROR, f"Request failed: {e}", fix_guide="docs/cookie-cross-subdomain.md"))
            return

        issues = []
        for cookie in resp.cookies:
            if cookie.domain and not cookie.domain.startswith("."):
                issues.append(f"Cookie '{cookie.name}' domain={cookie.domain} (not dot-prefixed)")
            if cookie.path and cookie.path != "/":
                issues.append(f"Cookie '{cookie.name}' path={cookie.path} (not /)")

        # Also check Set-Cookie headers for SameSite
        for hdr in resp.headers.getlist("Set-Cookie") if hasattr(resp.headers, "getlist") else resp.raw.headers.getlist("Set-Cookie") if hasattr(resp.raw.headers, "getlist") else []:
            lower = hdr.lower()
            if "samesite=strict" in lower:
                name = hdr.split("=")[0].strip()
                issues.append(f"Cookie '{name}' SameSite=Strict (blocks cross-origin API use)")

        if not issues:
            results.append(TestResult("cookie_scope", self.category, "Token cookie scoped correctly",
                                      Status.PASS, "Cookie scope allows cross-subdomain and cross-path access"))
        else:
            results.append(TestResult("cookie_scope", self.category, "Token cookie scoped correctly",
                                      Status.FAIL, "; ".join(issues),
                                      fix_guide="docs/cookie-cross-subdomain.md",
                                      details={"issues": issues}))

    def _test_cookie_size(self, results):
        try:
            resp = self._get_response()
        except requests.RequestException as e:
            results.append(TestResult("cookie_size", self.category, "Cookie size within browser limit",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        total = sum(len(f"{c.name}={c.value}") for c in resp.cookies)
        if self.token:
            total += len(self.token) + 20  # approximate name overhead

        if total > 4000:
            results.append(TestResult("cookie_size", self.category, "Cookie size within browser limit",
                                      Status.FAIL, f"Total cookie size {total} bytes > 4000 — browsers will drop cookies",
                                      details={"total_bytes": total}))
        elif total > 3000:
            results.append(TestResult("cookie_size", self.category, "Cookie size within browser limit",
                                      Status.WARN, f"Total cookie size {total} bytes — close to 4KB limit",
                                      details={"total_bytes": total}))
        else:
            results.append(TestResult("cookie_size", self.category, "Cookie size within browser limit",
                                      Status.PASS, f"Total cookie size {total} bytes",
                                      details={"total_bytes": total}))

    def _test_third_party(self, results):
        try:
            resp = requests.get(self.target_url, headers={
                "Origin": "https://different-domain.example.com",
                "Sec-Fetch-Site": "cross-site",
            }, cookies={_token_cookie_name(self.profile)[0].replace("*", ""): self.token} if self.token else {},
               timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("third_party_cookie", self.category, "Works with third-party cookies blocked",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        from .token_lifecycle import _is_challenge
        if _is_challenge(resp, self.profile):
            results.append(TestResult("third_party_cookie", self.category, "Works with third-party cookies blocked",
                                      Status.WARN,
                                      "Token rejected in cross-site context — breaks Safari ITP, Firefox ETP",
                                      details={"status_code": resp.status_code}))
        else:
            results.append(TestResult("third_party_cookie", self.category, "Works with third-party cookies blocked",
                                      Status.PASS, "Token accepted in cross-site context",
                                      details={"status_code": resp.status_code}))

    def _test_incognito(self, results):
        try:
            session = requests.Session()
            session.cookies.clear()
            resp = session.get(self.target_url, timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as e:
            results.append(TestResult("incognito_behavior", self.category, "Clean challenge in incognito",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        from .token_lifecycle import _is_challenge
        body = resp.text.lower()

        if resp.status_code in (200,) and not _is_challenge(resp, self.profile):
            # No challenge at all — might be fine if path isn't protected
            results.append(TestResult("incognito_behavior", self.category, "Clean challenge in incognito",
                                      Status.PASS, "Page loaded cleanly (no challenge on this path)"))
        elif _is_challenge(resp, self.profile) and len(resp.text.strip()) > 100:
            # Check for fingerprinting indicators
            fp_indicators = ["canvas", "webgl", "fingerprint"]
            has_fp = any(ind in body for ind in fp_indicators)
            if has_fp:
                results.append(TestResult("incognito_behavior", self.category, "Clean challenge in incognito",
                                          Status.WARN,
                                          "Challenge served but uses fingerprinting that may not work in incognito"))
            else:
                results.append(TestResult("incognito_behavior", self.category, "Clean challenge in incognito",
                                          Status.PASS, "Clean challenge page served without prior state"))
        elif len(resp.text.strip()) < 100:
            results.append(TestResult("incognito_behavior", self.category, "Clean challenge in incognito",
                                      Status.FAIL, "Error page or blank response — SDK assumes prior state",
                                      details={"body_length": len(resp.text.strip())}))
        else:
            results.append(TestResult("incognito_behavior", self.category, "Clean challenge in incognito",
                                      Status.PASS, "Challenge page served"))
