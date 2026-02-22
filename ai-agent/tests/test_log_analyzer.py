"""Unit tests for log_analyzer module."""

import pytest

from log_analyzer import (
    classify_errors,
    get_highest_severity,
    format_classifications_for_prompt,
)
from models import Severity, ErrorCategory


class TestClassifyErrors:
    """Tests for classify_errors function."""

    def test_oomkilled(self):
        result = classify_errors("Container OOMKilled due to memory limit")
        assert len(result) >= 1
        assert result[0]["category"] == ErrorCategory.OOM_KILLED.value
        assert result[0]["severity"] == Severity.CRITICAL.value

    def test_crash_loop(self):
        result = classify_errors("Pod is in CrashLoopBackOff state")
        assert len(result) >= 1
        assert result[0]["category"] == ErrorCategory.CRASH_LOOP.value
        assert result[0]["severity"] == Severity.CRITICAL.value

    def test_image_pull(self):
        result = classify_errors("ImagePullBackOff: failed to pull image")
        assert len(result) >= 1
        assert result[0]["category"] == ErrorCategory.IMAGE_PULL.value
        assert result[0]["severity"] == Severity.HIGH.value

    def test_readiness_probe(self):
        result = classify_errors("Readiness probe failed on port 8080")
        assert len(result) >= 1
        assert result[0]["category"] == ErrorCategory.READINESS_PROBE.value

    def test_network_error(self):
        result = classify_errors("connection refused when dial tcp 10.0.0.1:5432")
        assert len(result) >= 1
        assert result[0]["category"] == ErrorCategory.NETWORK_ERROR.value

    def test_terraform_state_lock(self):
        result = classify_errors("Error acquiring state lock. Lock ID: abc123")
        assert len(result) >= 1
        assert result[0]["category"] == ErrorCategory.TERRAFORM_STATE_LOCK.value

    def test_empty_text(self):
        result = classify_errors("")
        assert result == []

    def test_no_match(self):
        result = classify_errors("Some random log message with no known patterns")
        assert result == []

    def test_multiple_patterns_sorted_by_severity(self):
        result = classify_errors(
            "OOMKilled and ImagePullBackOff and Readiness probe failed"
        )
        assert len(result) >= 1
        # CRITICAL (OOMKilled) should appear before HIGH/MEDIUM
        assert result[0]["severity"] == Severity.CRITICAL.value


class TestGetHighestSeverity:
    """Tests for get_highest_severity function."""

    def test_empty_classifications(self):
        assert get_highest_severity([]) == Severity.INFO

    def test_single_classification(self):
        classifications = [{"severity": "HIGH", "category": "ImagePullBackOff"}]
        assert get_highest_severity(classifications) == Severity.HIGH

    def test_critical_first(self):
        classifications = [
            {"severity": "CRITICAL", "category": "OOMKilled"},
            {"severity": "MEDIUM", "category": "ReadinessProbeFailure"},
        ]
        # List is pre-sorted by severity, first is highest
        assert get_highest_severity(classifications) == Severity.CRITICAL


class TestFormatClassificationsForPrompt:
    """Tests for format_classifications_for_prompt function."""

    def test_empty(self):
        assert "No known error patterns" in format_classifications_for_prompt([])

    def test_with_classifications(self):
        classifications = [
            {"severity": "CRITICAL", "category": "OOMKilled", "hint": "Memory limit exceeded"},
            {"severity": "HIGH", "category": "ImagePullBackOff", "hint": "Check image"},
        ]
        out = format_classifications_for_prompt(classifications)
        assert "OOMKilled" in out
        assert "ImagePullBackOff" in out
        assert "Memory limit exceeded" in out
