"""Unit tests for challenge-validator with mocked HTTP responses."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from challenge_validator.tests.base import Status
from challenge_validator.tests.token_lifecycle import TokenLifecycleTests, _is_challenge
from challenge_validator.tests.cors_api import CorsApiTests
from challenge_validator.tests.degradation import DegradationTests
from challenge_validator.tests.score_handling import ScoreHandlingTests
from challenge_validator.tests.session_cookies import SessionCookieTests
from challenge_validator.tests.performance_ux import PerformanceUxTests
from challenge_validator.profiles import load_profile

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "sample_responses.json").read_text())


def _mock_response(fixture_key):
    """Create a mock requests.Response from fixture data."""
    data = FIXTURES[fixture_key]
    resp = MagicMock()
    resp.status_code = data["status_code"]
    resp.headers = data["headers"]
    resp.text = data["body"]
    resp.content = data["body"].encode()
    resp.cookies = MagicMock()
    resp.cookies.__iter__ = MagicMock(return_value=iter([]))
    resp.raw = MagicMock()
    resp.raw.headers = MagicMock()
    resp.raw.headers.getlist = MagicMock(return_value=[])
    return resp


@pytest.fixture
def profile():
    return load_profile("cloudflare")


class TestIsChallenge:
    def test_detects_403_challenge(self, profile):
        resp = _mock_response("challenge_page")
        assert _is_challenge(resp, profile) is True

    def test_passes_200(self, profile):
        resp = _mock_response("success_page")
        assert _is_challenge(resp, profile) is False

    def test_detects_html_pattern(self, profile):
        resp = _mock_response("challenge_page")
        resp.status_code = 200  # Even with 200, HTML patterns should match
        assert _is_challenge(resp, profile) is True


class TestTokenLifecycle:
    @patch("challenge_validator.tests.token_lifecycle.requests.get")
    def test_initial_challenge_detected(self, mock_get, profile):
        mock_get.return_value = _mock_response("challenge_page")
        t = TokenLifecycleTests("https://example.com", profile=profile)
        results = t.run()
        initial = next(r for r in results if r.test_id == "token_initial")
        assert initial.status == Status.PASS

    @patch("challenge_validator.tests.token_lifecycle.requests.get")
    def test_initial_no_challenge(self, mock_get, profile):
        mock_get.return_value = _mock_response("success_page")
        t = TokenLifecycleTests("https://example.com", profile=profile)
        results = t.run()
        initial = next(r for r in results if r.test_id == "token_initial")
        assert initial.status == Status.FAIL

    @patch("challenge_validator.tests.token_lifecycle.requests.get")
    def test_token_set_accepted(self, mock_get, profile):
        # First call: challenge detected; second call: token accepted
        mock_get.side_effect = [_mock_response("challenge_page"), _mock_response("success_page")]
        t = TokenLifecycleTests("https://example.com", token="test_token", profile=profile)
        results = []
        t._test_initial(results)
        t._test_set(results, challenge_detected=True)
        token_set = next(r for r in results if r.test_id == "token_set")
        assert token_set.status == Status.PASS

    @patch("challenge_validator.tests.token_lifecycle.requests.get")
    def test_no_token_skips(self, mock_get, profile):
        mock_get.return_value = _mock_response("challenge_page")
        t = TokenLifecycleTests("https://example.com", profile=profile)
        results = t.run()
        skipped = [r for r in results if r.status == Status.SKIP]
        assert len(skipped) >= 2  # token_set, token_refresh, token_reuse


class TestCorsApi:
    @patch("challenge_validator.tests.cors_api.requests.options")
    @patch("challenge_validator.tests.cors_api.requests.get")
    @patch("challenge_validator.tests.cors_api.requests.post")
    def test_preflight_pass(self, mock_post, mock_get, mock_options, profile):
        resp_ok = _mock_response("success_page")
        resp_ok.status_code = 204
        mock_options.return_value = resp_ok
        mock_get.return_value = _mock_response("json_error")
        mock_post.return_value = _mock_response("success_page")
        t = CorsApiTests("https://example.com", token="test", profile=profile)
        results = t.run()
        preflight = next(r for r in results if r.test_id == "cors_preflight")
        assert preflight.status == Status.PASS

    @patch("challenge_validator.tests.cors_api.requests.options")
    @patch("challenge_validator.tests.cors_api.requests.get")
    @patch("challenge_validator.tests.cors_api.requests.post")
    def test_api_json_content_type(self, mock_post, mock_get, mock_options, profile):
        mock_options.return_value = _mock_response("success_page")
        mock_get.return_value = _mock_response("json_error")
        mock_post.return_value = _mock_response("success_page")
        t = CorsApiTests("https://example.com", token="test", profile=profile)
        results = t.run()
        ct = next(r for r in results if r.test_id == "api_content_type")
        assert ct.status == Status.PASS


class TestDegradation:
    @patch("challenge_validator.tests.degradation.requests.get")
    def test_noscript_found(self, mock_get, profile):
        mock_get.return_value = _mock_response("challenge_page")
        t = DegradationTests("https://example.com", profile=profile)
        results = t.run()
        ns = next(r for r in results if r.test_id == "noscript_fallback")
        assert ns.status == Status.PASS

    @patch("challenge_validator.tests.degradation.requests.get")
    def test_blank_page_fails(self, mock_get, profile):
        mock_get.return_value = _mock_response("blank_page")
        t = DegradationTests("https://example.com", profile=profile)
        results = t.run()
        js = next(r for r in results if r.test_id == "js_blocked")
        assert js.status == Status.FAIL


class TestScoreHandling:
    @patch("challenge_validator.tests.score_handling.requests.get")
    def test_score_transparency_found(self, mock_get, profile):
        mock_get.return_value = _mock_response("with_score_header")
        t = ScoreHandlingTests("https://example.com", token="test", profile=profile)
        results = []
        t._test_transparency(results)
        assert results[0].status == Status.PASS

    @patch("challenge_validator.tests.score_handling.requests.get")
    def test_score_transparency_missing(self, mock_get, profile):
        mock_get.return_value = _mock_response("success_page")
        t = ScoreHandlingTests("https://example.com", token="test", profile=profile)
        results = []
        t._test_transparency(results)
        assert results[0].status == Status.WARN

    def test_score_transparency_skips_when_no_headers(self):
        """AWS WAF profile has empty score_headers — test should SKIP."""
        aws_profile = load_profile("aws_waf")
        t = ScoreHandlingTests("https://example.com", token="test", profile=aws_profile)
        results = []
        t._test_transparency(results)
        assert results[0].status == Status.SKIP


class TestVendorNotes:
    def test_vendor_note_surfaced_on_fail(self):
        from challenge_validator.reporter import _get_vendor_note
        aws_profile = load_profile("aws_waf")
        note = _get_vendor_note("cors_preflight", Status.FAIL, aws_profile)
        assert note is not None
        assert "TGT_VolumetricIpTokenAbsent" in note

    def test_vendor_note_not_surfaced_on_pass(self):
        from challenge_validator.reporter import _get_vendor_note
        aws_profile = load_profile("aws_waf")
        note = _get_vendor_note("cors_preflight", Status.PASS, aws_profile)
        assert note is None

    def test_no_vendor_note_for_generic(self):
        from challenge_validator.reporter import _get_vendor_note
        generic = load_profile("generic")
        note = _get_vendor_note("cors_preflight", Status.FAIL, generic)
        assert note is None


class TestReporter:
    def test_json_output(self, profile):
        from challenge_validator.reporter import report_json
        from challenge_validator.tests.base import TestResult
        from io import StringIO

        results = [
            TestResult("test1", "Cat", "Test 1", Status.PASS, "OK"),
            TestResult("test2", "Cat", "Test 2", Status.FAIL, "Bad", fix_guide="docs/fix.md"),
        ]
        buf = StringIO()
        report_json(results, file=buf)
        data = json.loads(buf.getvalue())
        assert data["total"] == 2
        assert data["passed"] == 1
        assert data["failed"] == 1
