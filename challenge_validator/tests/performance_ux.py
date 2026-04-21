"""Performance / UX Impact tests (4 tests)."""

import re
import time

import requests
from bs4 import BeautifulSoup

from .base import BaseTest, TestResult, Status
from .token_lifecycle import _is_challenge, _token_cookie_name


class PerformanceUxTests(BaseTest):
    category = "Performance / UX"

    def run(self) -> list[TestResult]:
        results = []
        self._test_latency(results)
        self._test_bundle_size(results)
        self._test_layout_shift(results)
        self._test_repeat_visitor(results)
        return results

    def _test_latency(self, results):
        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"

        # With token
        t_with = None
        if self.token:
            try:
                start = time.monotonic()
                requests.get(self.target_url, cookies={cookie_name: self.token}, timeout=self.timeout)
                t_with = (time.monotonic() - start) * 1000
            except requests.RequestException:
                pass

        # Without token
        try:
            start = time.monotonic()
            requests.get(self.target_url, timeout=self.timeout)
            t_without = (time.monotonic() - start) * 1000
        except requests.RequestException as e:
            results.append(TestResult("challenge_latency", self.category, "Challenge latency overhead",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        delta = (t_without - t_with) if t_with is not None else t_without
        details = {"with_token_ms": round(t_with, 1) if t_with else None,
                   "without_token_ms": round(t_without, 1), "delta_ms": round(delta, 1)}

        if delta < 500:
            results.append(TestResult("challenge_latency", self.category, "Challenge latency overhead",
                                      Status.PASS, f"Overhead: {delta:.0f}ms", details=details))
        elif delta < 2000:
            results.append(TestResult("challenge_latency", self.category, "Challenge latency overhead",
                                      Status.WARN, f"Overhead: {delta:.0f}ms (500-2000ms)", details=details))
        else:
            results.append(TestResult("challenge_latency", self.category, "Challenge latency overhead",
                                      Status.FAIL, f"Overhead: {delta:.0f}ms (>2000ms)", details=details))

    def _test_bundle_size(self, results):
        try:
            resp = requests.get(self.target_url, timeout=self.timeout)
        except requests.RequestException as e:
            results.append(TestResult("js_bundle_size", self.category, "SDK JavaScript bundle size",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        sdk_patterns = self.profile.get("sdk_script_patterns", [])
        scripts = []
        total = 0

        for tag in soup.find_all("script", src=True):
            src = tag["src"]
            if any(pat.lower() in src.lower() for pat in sdk_patterns):
                url = src if src.startswith("http") else requests.compat.urljoin(self.target_url, src)
                try:
                    sr = requests.get(url, timeout=self.timeout)
                    size = len(sr.content)
                    scripts.append({"url": url, "bytes": size})
                    total += size
                except requests.RequestException:
                    scripts.append({"url": url, "bytes": None, "error": "fetch failed"})

        size_kb = round(total / 1000)
        vendor_benchmarks = {
            "Cloudflare Turnstile": 35,
            "reCAPTCHA Enterprise": 150,
            "hCaptcha": 65,
            "AWS WAF JS SDK": 20,
            "DataDome": 95,
        }
        mitigation = [
            "Lazy-load the SDK so it doesn't block initial render",
            "Use async/defer on the script tag",
            "Only load the SDK on pages that actually need challenges",
        ]
        benchmark_str = "Turnstile ~35KB, reCAPTCHA ~150KB, hCaptcha ~65KB"
        fix_guide = (
            "→ This is the vendor's bundle — you can't reduce it\n"
            "→ Mitigate: lazy-load the SDK, use async/defer, only load on pages that need challenges"
        )
        details = {
            "scripts": scripts,
            "total_bytes": total,
            "bundle_size_kb": size_kb,
            "vendor_benchmarks": vendor_benchmarks,
            "mitigation": mitigation,
        }

        msg = f"SDK JS bundle: {size_kb}KB — For reference: {benchmark_str}"

        if not scripts:
            results.append(TestResult("js_bundle_size", self.category, "SDK JavaScript bundle size",
                                      Status.INFO, "No SDK scripts detected on page", details=details))
        elif size_kb > 200:
            results.append(TestResult("js_bundle_size", self.category, "SDK JavaScript bundle size",
                                      Status.WARN, f"{msg} — may impact page load",
                                      fix_guide=fix_guide, details=details))
        else:
            results.append(TestResult("js_bundle_size", self.category, "SDK JavaScript bundle size",
                                      Status.INFO, msg, fix_guide=fix_guide, details=details))

    def _test_layout_shift(self, results):
        try:
            resp = requests.get(self.target_url, timeout=self.timeout)
        except requests.RequestException as e:
            results.append(TestResult("layout_shift", self.category, "Challenge widget layout shift",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        widget_patterns = self.profile.get("widget_patterns", [])
        issues = []

        for pat in widget_patterns:
            for el in soup.find_all(class_=re.compile(pat, re.I)):
                style = (el.get("style") or "").lower()
                has_dims = ("width" in style and "height" in style)
                is_positioned = any(p in style for p in ("position: absolute", "position: fixed",
                                                          "position:absolute", "position:fixed"))
                w = el.get("width")
                h = el.get("height")
                if not (has_dims or is_positioned or (w and h)):
                    issues.append(f"Element class='{pat}' has no explicit dimensions")

            for el in soup.find_all(id=re.compile(pat, re.I)):
                style = (el.get("style") or "").lower()
                has_dims = ("width" in style and "height" in style)
                is_positioned = any(p in style for p in ("position: absolute", "position: fixed",
                                                          "position:absolute", "position:fixed"))
                w = el.get("width")
                h = el.get("height")
                if not (has_dims or is_positioned or (w and h)):
                    issues.append(f"Element id='{pat}' has no explicit dimensions")

        if issues:
            results.append(TestResult("layout_shift", self.category, "Challenge widget layout shift",
                                      Status.WARN, "; ".join(issues), details={"issues": issues}))
        else:
            results.append(TestResult("layout_shift", self.category, "Challenge widget layout shift",
                                      Status.PASS, "All challenge elements have explicit dimensions or are positioned"))

    def _test_repeat_visitor(self, results):
        if not self.token:
            results.append(TestResult("repeat_visitor_penalty", self.category, "No repeat visitor penalty",
                                      Status.SKIP, "No --token provided"))
            return

        patterns = _token_cookie_name(self.profile)
        cookie_name = patterns[0].replace("*", "") if patterns else "challenge_token"

        try:
            start1 = time.monotonic()
            requests.get(self.target_url, cookies={cookie_name: self.token}, timeout=self.timeout)
            t1 = (time.monotonic() - start1) * 1000

            start2 = time.monotonic()
            requests.get(self.target_url, cookies={cookie_name: self.token}, timeout=self.timeout)
            t2 = (time.monotonic() - start2) * 1000
        except requests.RequestException as e:
            results.append(TestResult("repeat_visitor_penalty", self.category, "No repeat visitor penalty",
                                      Status.ERROR, f"Request failed: {e}"))
            return

        delta = t2 - t1
        details = {"request_1_ms": round(t1, 1), "request_2_ms": round(t2, 1), "delta_ms": round(delta, 1)}

        if delta <= 100:
            results.append(TestResult("repeat_visitor_penalty", self.category, "No repeat visitor penalty",
                                      Status.PASS, f"No penalty: {t1:.0f}ms → {t2:.0f}ms", details=details))
        elif delta <= 500:
            results.append(TestResult("repeat_visitor_penalty", self.category, "No repeat visitor penalty",
                                      Status.WARN, f"Slight penalty: {t1:.0f}ms → {t2:.0f}ms (+{delta:.0f}ms)",
                                      details=details))
        else:
            results.append(TestResult("repeat_visitor_penalty", self.category, "No repeat visitor penalty",
                                      Status.FAIL, f"Significant penalty: {t1:.0f}ms → {t2:.0f}ms (+{delta:.0f}ms)",
                                      details=details))
