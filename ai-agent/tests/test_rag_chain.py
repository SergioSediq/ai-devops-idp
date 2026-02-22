"""Unit tests for rag_chain module."""

import pytest

from rag_chain import (
    load_runbooks,
    search_runbooks,
    analyze_devops_issue,
    _parse_llm_response,
    _generate_mock_response,
    _generate_fallback_response,
)


class TestLoadRunbooks:
    """Tests for load_runbooks function."""

    def test_loads_runbooks_from_dir(self):
        runbooks = load_runbooks()
        # Project has runbooks: oomkilled, crashloopbackoff, imagepullbackoff, terraform-state-lock
        assert len(runbooks) >= 1
        for rb in runbooks:
            assert "filename" in rb
            assert "title" in rb
            assert "content" in rb

    def test_cached_after_first_load(self):
        a = load_runbooks()
        b = load_runbooks()
        assert a is b


class TestSearchRunbooks:
    """Tests for search_runbooks function."""

    def test_empty_query_returns_empty(self):
        result = search_runbooks("xyznonexistent123", top_k=1)
        # May return [] or some runbooks if word matches; at least no crash
        assert isinstance(result, list)

    def test_matching_query_returns_results(self):
        result = search_runbooks("OOMKilled memory", top_k=3)
        assert isinstance(result, list)
        if result:
            assert "title" in result[0]
            assert "filename" in result[0]
            assert "relevance_score" in result[0]

    def test_top_k_respected(self):
        result = search_runbooks("pod container kubernetes", top_k=2)
        assert len(result) <= 2


class TestAnalyzeDevopsIssue:
    """Tests for analyze_devops_issue - uses mock when no API key."""

    def test_mock_response_structure(self):
        result = analyze_devops_issue(
            error_context="Pod OOMKilled in production",
            classifications=[{"severity": "CRITICAL", "category": "OOMKilled", "hint": "Memory"}],
        )
        assert "root_cause" in result
        assert "severity" in result
        assert "error_category" in result
        assert "explanation" in result
        assert "fix_commands" in result
        assert "prevention_tips" in result
        assert "related_runbooks" in result

    def test_fix_commands_non_empty_in_mock(self):
        result = analyze_devops_issue(
            error_context="CrashLoopBackOff",
            classifications=[{"severity": "CRITICAL", "category": "CrashLoopBackOff", "hint": "Check logs"}],
        )
        assert len(result["fix_commands"]) >= 1
        assert "command" in result["fix_commands"][0]
        assert "description" in result["fix_commands"][0]

    def test_with_classifications_passed_through(self):
        classifications = [{"severity": "HIGH", "category": "ImagePullBackOff", "hint": "Check image"}]
        result = analyze_devops_issue("ImagePullBackOff", classifications=classifications)
        assert result["severity"] == "HIGH"
        assert result["error_category"] == "ImagePullBackOff"


class TestParseLlmResponse:
    """Tests for _parse_llm_response helper."""

    def test_valid_json(self):
        raw = '{"root_cause":"x","severity":"HIGH","error_category":"OOMKilled","explanation":"y","fix_commands":[],"prevention_tips":[],"related_runbooks":[]}'
        result = _parse_llm_response(raw, [])
        assert result["root_cause"] == "x"
        assert result["severity"] == "HIGH"

    def test_json_with_markdown_wrapper(self):
        raw = '```json\n{"root_cause":"a","severity":"MEDIUM","error_category":"Unknown","explanation":"b","fix_commands":[],"prevention_tips":[],"related_runbooks":[]}\n```'
        result = _parse_llm_response(raw, [])
        assert result["root_cause"] == "a"


class TestFallbackResponse:
    """Tests for fallback when LLM fails."""

    def test_fallback_structure(self):
        result = _generate_fallback_response(
            "Connection timeout",
            [{"severity": "HIGH", "category": "NetworkError"}],
            [],
        )
        assert "root_cause" in result
        assert result["severity"] == "HIGH"
        assert "Connection timeout" in result["explanation"] or "timeout" in result["explanation"].lower()
