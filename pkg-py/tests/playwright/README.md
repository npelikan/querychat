# CI-Friendly Playwright Tests with VCR

This directory contains Playwright tests for querychat that use VCR.py to record and replay HTTP interactions,
making them suitable for running in CI environments.

## Overview

These tests are designed to:

1. Work in CI environments without requiring real API calls
2. Record HTTP interactions the first time they are run
3. Replay recorded interactions on subsequent runs
4. Use Shiny's built-in Playwright testing tools

## Directory Structure

```
tests/playwright/
├── conftest.py               # Shared fixtures and configuration
├── basic/                    # Basic app tests
│   ├── app.py               # Modified app with VCR integration
│   ├── test_basic_app.py    # Playwright tests
│   ├── vcr_helper.py        # VCR helpers for the app
│   └── cassettes/           # Recorded HTTP interactions
└── ibis-mtcars/             # Ibis-mtcars app tests
    ├── app.py               # Modified app with VCR integration
    ├── test_ibis_app.py     # Playwright tests
    ├── vcr_helper.py        # VCR helpers for the app
    └── cassettes/           # Recorded HTTP interactions
```

## Running Tests

To run the tests:

```bash
# Run all Playwright tests
pytest pkg-py/tests/playwright/ -v

# Run specific test file
pytest pkg-py/tests/playwright/basic/test_basic_app.py -v

# Run a specific test
pytest pkg-py/tests/playwright/basic/test_basic_app.py::test_basic_app_query -v
```

## How It Works

1. **VCR Integration**: Each app has been modified to use VCR.py for recording and replaying HTTP interactions.
   The `vcr_helper.py` file provides utilities for VCR integration.

2. **Cassettes**: HTTP interactions are stored in the `cassettes/` directory. The first time tests run, they will
   make real API calls and record the interactions. Subsequent runs will use the recorded interactions.

3. **Fixtures**: The `conftest.py` file provides two key fixtures:
   - `local_app`: Launches a Shiny app for testing
   - `vcr_app`: Combines `local_app` with VCR integration

## Creating New Tests

1. Copy your app to a new directory under `tests/playwright/`
2. Add `vcr_helper.py` to the directory
3. Modify your app to use VCR integration (see existing examples)
4. Create your tests using the `vcr_app` fixture
5. Run your tests to generate cassettes

## Updating Cassettes

If you need to update the cassettes:

1. Delete the relevant cassettes from the `cassettes/` directory
2. Run the tests again to generate new cassettes

## CI Configuration

In CI environments, tests will use the recorded cassettes and will not make real API calls.
This is configured in `vcr_helper.py` which sets `record_mode='none'` when running in CI.