"""Shared pytest configuration and fixtures for the Study Agent test suite."""
import sys
import pytest
from pathlib import Path

# Ensure tools directory is importable from all test files
TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: marks tests that spawn subprocesses or load FAISS — skip with -m 'not slow'"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark any test inside a TestCLI class or that calls subprocess as slow."""
    for item in items:
        cls = item.cls
        if cls is not None and cls.__name__ == "TestCLI":
            item.add_marker(pytest.mark.slow)
