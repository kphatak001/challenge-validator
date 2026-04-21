"""Test runner — loads profile, runs test modules, collects results."""

from .profiles import load_profile
from .tests.base import TestResult, Status
from .tests.token_lifecycle import TokenLifecycleTests
from .tests.cors_api import CorsApiTests
from .tests.post_challenge import PostChallengeTests
from .tests.degradation import DegradationTests
from .tests.score_handling import ScoreHandlingTests
from .tests.session_cookies import SessionCookieTests
from .tests.performance_ux import PerformanceUxTests

SUITE_MAP = {
    "token": TokenLifecycleTests,
    "cors": CorsApiTests,
    "post-challenge": PostChallengeTests,
    "degradation": DegradationTests,
    "score": ScoreHandlingTests,
    "cookies": SessionCookieTests,
    "performance": PerformanceUxTests,
}


def run_tests(target_url: str, token: str = None, profile_name: str = "generic",
              suites: str = "all", timeout: int = 10, token_ttl: int = None) -> tuple[list[TestResult], dict]:
    """Run tests and return (results, profile)."""
    profile = load_profile(profile_name)
    if token_ttl is not None:
        profile["token_ttl_seconds"] = token_ttl

    results = []
    for suite_name, test_class in SUITE_MAP.items():
        if suites != "all" and suite_name not in suites.split(","):
            continue
        test = test_class(target_url, token, profile, timeout)
        try:
            results.extend(test.run())
        except Exception as e:
            results.append(TestResult(
                test_id=f"{suite_name}_error",
                category=test.category,
                name=f"{suite_name} suite error",
                status=Status.ERROR,
                message=str(e),
            ))
    return results, profile
