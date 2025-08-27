"""
Configuration file for Playwright tests with VCR.

This file uses Shiny's built-in pytest fixtures and adds VCR support.
"""

from pathlib import Path

import pytest
import vcr

# Configure VCR for LLM API calls
# Use standard record mode values that VCR recognizes
RECORD_MODE = "once"  # Default to once (create if missing, reuse if exists)

# Create cassette directory
CONFTEST_CASSETTE_DIR = Path(__file__).parent / "cassettes"
CONFTEST_CASSETTE_DIR.mkdir(parents=True, exist_ok=True)

llm_vcr = vcr.VCR(
    cassette_library_dir=str(CONFTEST_CASSETTE_DIR),
    record_mode=RECORD_MODE,
    filter_headers=["authorization", "x-goog-api-key", "api-key"],
    match_on=["uri", "method"],
    ignore_localhost=True,  # Important: don't record local Shiny server traffic
)

# Use the built-in Shiny fixture for local app
# 'local_app' fixture is provided automatically by shiny.pytest plugin


@pytest.fixture(autouse=True)
def vcr_cassette(request):
    """Automatically use VCR cassettes for all tests."""
    # Determine cassette path based on test name
    test_name = request.node.name.split("[")[0]  # Remove parametrization part if any
    module_name = request.module.__name__.split(".")[-1]
    cassette_path = f"{module_name}/{test_name}"

    print(f"\nTest: {cassette_path} - Using VCR cassette")
    print(f"Cassette path: {cassette_path}")

    # Create cassette directory if needed
    cassette_dir = Path(CONFTEST_CASSETTE_DIR) / module_name
    cassette_dir.mkdir(parents=True, exist_ok=True)

    # Use VCR for external API calls
    with llm_vcr.use_cassette(cassette_path):
        yield
