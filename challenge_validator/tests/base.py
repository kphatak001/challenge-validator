"""Core data model for test results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Status(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class TestResult:
    test_id: str
    category: str
    name: str
    status: Status
    message: str
    fix_guide: Optional[str] = None
    details: dict = field(default_factory=dict)


class BaseTest:
    """Base class for all test modules."""

    category: str = "Uncategorized"

    def __init__(self, target_url: str, token: str = None, profile: dict = None, timeout: int = 10):
        self.target_url = target_url
        self.token = token
        self.profile = profile or {}
        self.timeout = timeout

    def run(self) -> list[TestResult]:
        raise NotImplementedError
