"""Bot Score / Risk Score Handling tests (3 tests)."""

import time

import requests

from .base import BaseTest, TestResult, Status
from .token_lifecycle import _is_challenge, _token_cookie_name


class ScoreHandlingTests(BaseTest):
    category = "Score Handling"

    def run(self) -> list[TestResult]:
        results = []
        self._test_threshold(results)
        self._test_transparency(results)
        self._test_double_punishment(results)
        return results

    def _test_threshold(self, results):
        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"

        responses = {}
        # Trusted: with token
        if self.token:
            try:
                r = requests.get(self.target_url, cookies={cookie_name: self.token}, timeout=self.timeout)
                responses["trusted"] = r.status_code
            except requests.RequestException:
                responses["trusted"] = None
        # Unknown: no token
        try:
            r = requests.get(self.target_url, timeout=self.timeout)
            responses["unknown"] = r.status_code
        except requests.RequestException:
            responses["unknown"] = None
        # Suspicious: empty UA
        try:
            r = requests.get(self.target_url, headers={"User-Agent": "", "Referer": ""}, timeout=self.timeout)
            responses["suspicious"] = r.status_code
        except requests.RequestException:
            responses["suspicious"] = None

        codes = set(v for v in responses.values() if v is not None)
        if len(codes) >= 3:
            results.append(TestResult("score_threshold", self.category, "Risk score tiers differentiated",
                                      Status.PASS, "3 distinct response tiers observed",
                                      details=responses))
        elif len(codes) == 2:
            results.append(TestResult("score_threshold", self.category, "Risk score tiers differentiated",
                                      Status.WARN, "Only 2 tiers observed (binary pass/block)",
                                      details=responses))
        else:
            results.append(TestResult("score_threshold", self.category, "Risk score tiers differentiated",
                                      Status.FAIL, "Same response for all risk levels — scoring not actionable",
                                      details=responses))

    def _test_transparency(self, results):
        score_headers = self.profile.get("score_headers", [])
        if not score_headers:
            note = self.profile.get("score_note", "No score headers configured in profile")
            results.append(TestResult("score_transparency", self.category, "Score exposed in headers",
                                      Status.SKIP, note.strip().split("\n")[0]))
            return
        if not self.token:
            # Try without token
            try:
                resp = requests.get(self.target_url, timeout=self.timeout)
            except requests.RequestException as e:
                results.append(TestResult("score_transparency", self.category, "Score exposed in headers",
                                          Status.ERROR, f"Request failed: {e}"))
                return
        else:
            patterns = _token_cookie_name(self.profile)
            cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"
            try:
                resp = requests.get(self.target_url, cookies={cookie_name: self.token}, timeout=self.timeout)
            except requests.RequestException as e:
                results.append(TestResult("score_transparency", self.category, "Score exposed in headers",
                                          Status.ERROR, f"Request failed: {e}"))
                return

        found = {}
        for hdr in score_headers:
            val = resp.headers.get(hdr)
            if val is not None:
                found[hdr] = val

        if found:
            results.append(TestResult("score_transparency", self.category, "Score exposed in headers",
                                      Status.PASS, f"Score header(s) found: {found}",
                                      details=found))
        else:
            results.append(TestResult("score_transparency", self.category, "Score exposed in headers",
                                      Status.WARN, "No score headers found — app can't make its own risk decisions",
                                      details={"checked": score_headers}))

    def _test_double_punishment(self, results):
        if not self.token:
            results.append(TestResult("score_double_punishment", self.category, "No double punishment",
                                      Status.SKIP, "No --token provided"))
            return

        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"

        # 5 requests without token (trigger challenge)
        for _ in range(5):
            try:
                requests.get(self.target_url, timeout=self.timeout)
            except requests.RequestException:
                pass

        # 5 requests with token (post-challenge)
        rate_limited = 0
        for _ in range(5):
            try:
                resp = requests.get(self.target_url, cookies={cookie_name: self.token}, timeout=self.timeout)
                if resp.status_code == 429:
                    rate_limited += 1
            except requests.RequestException:
                rate_limited += 1

        if rate_limited == 0:
            results.append(TestResult("score_double_punishment", self.category, "No double punishment",
                                      Status.PASS, "Post-challenge requests not rate-limited",
                                      details={"rate_limited": rate_limited}))
        else:
            results.append(TestResult("score_double_punishment", self.category, "No double punishment",
                                      Status.FAIL,
                                      f"{rate_limited}/5 post-challenge requests rate-limited — double punishment",
                                      fix_guide="docs/score-double-punishment.md",
                                      details={"rate_limited": rate_limited}))
