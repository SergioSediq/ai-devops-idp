"""Tests for runbook presence and structure."""

import os
import glob

import pytest


RUNBOOK_DIR = os.path.join(os.path.dirname(__file__), "..", "runbooks")
EXPECTED_RUNBOOKS = ["crashloopbackoff.md", "oomkilled.md", "imagepullbackoff.md", "terraform-state-lock.md"]


class TestRunbookExistence:
    """Ensure required runbooks exist."""

    def test_runbook_dir_exists(self):
        assert os.path.isdir(RUNBOOK_DIR), f"Runbook directory {RUNBOOK_DIR} not found"

    def test_expected_runbooks_exist(self):
        for name in EXPECTED_RUNBOOKS:
            path = os.path.join(RUNBOOK_DIR, name)
            assert os.path.isfile(path), f"Expected runbook {name} not found at {path}"

    def test_runbooks_are_markdown(self):
        files = glob.glob(os.path.join(RUNBOOK_DIR, "*.md"))
        assert len(files) >= len(EXPECTED_RUNBOOKS)


class TestRunbookStructure:
    """Basic structure validation."""

    @pytest.mark.parametrize("runbook", EXPECTED_RUNBOOKS)
    def test_runbook_has_content(self, runbook):
        path = os.path.join(RUNBOOK_DIR, runbook)
        with open(path) as f:
            content = f.read()
        assert len(content.strip()) > 50, f"Runbook {runbook} seems empty or too short"
        # Typical runbooks have headers
        assert "#" in content, f"Runbook {runbook} should have markdown headers"
