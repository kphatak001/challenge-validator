"""Post-Challenge Behavior tests (2 tests)."""

import time
from concurrent.futures import ThreadPoolExecutor

import requests

from .base import BaseTest, TestResult, Status
from .token_lifecycle import _is_challenge, _token_cookie_name


class PostChallengeTests(BaseTest):
    category = "Post-Challenge Behavior"

    def run(self) -> list[TestResult]:
        results = []
        self._test_solve_block_loop(results)
        self._test_multi_tab(results)
        return results

    def _test_solve_block_loop(self, results):
        if not self.token:
            results.append(TestResult("solve_block_loop", self.category, "No block after challenge solve",
                                      Status.SKIP, "No --token provided"))
            return

        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"
        blocked = 0
        for i in range(10):
            try:
                resp = requests.get(self.target_url, cookies={cookie_name: self.token},
                                    timeout=self.timeout, allow_redirects=True)
                if resp.status_code == 429 or _is_challenge(resp, self.profile):
                    blocked += 1
            except requests.RequestException:
                blocked += 1
            time.sleep(0.1)

        if blocked == 0:
            results.append(TestResult("solve_block_loop", self.category, "No block after challenge solve",
                                      Status.PASS, "All 10 rapid requests accepted post-challenge",
                                      details={"blocked": blocked}))
        else:
            results.append(TestResult("solve_block_loop", self.category, "No block after challenge solve",
                                      Status.FAIL,
                                      f"{blocked}/10 requests blocked — rate-limit firing on recently-challenged IP",
                                      fix_guide="docs/challenge-block-loop.md",
                                      details={"blocked": blocked}))

    def _test_multi_tab(self, results):
        if not self.token:
            results.append(TestResult("multi_tab", self.category, "Token works across concurrent sessions",
                                      Status.SKIP, "No --token provided"))
            return

        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"

        def make_request(_):
            try:
                resp = requests.get(self.target_url, cookies={cookie_name: self.token},
                                    timeout=self.timeout, allow_redirects=True)
                return not _is_challenge(resp, self.profile)
            except requests.RequestException:
                return False

        with ThreadPoolExecutor(max_workers=3) as pool:
            ok = list(pool.map(make_request, range(3)))

        if all(ok):
            results.append(TestResult("multi_tab", self.category, "Token works across concurrent sessions",
                                      Status.PASS, "All 3 concurrent requests accepted"))
        else:
            failed = ok.count(False)
            results.append(TestResult("multi_tab", self.category, "Token works across concurrent sessions",
                                      Status.FAIL,
                                      f"{failed}/3 concurrent requests challenged — token may be single-use",
                                      details={"failed": failed}))
