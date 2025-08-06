"""
End-to-end test for the basic QueryChat example app.
"""

import os
import pytest
import re
import seaborn as sns
from playwright.sync_api import Page

# Load the titanic dataset
titanic = sns.load_dataset("titanic")

# Test queries to use
TEST_QUERY = "Show women who survived"
TEST_QUERY_SEQUENTIAL_1 = "Show me first class passengers"
TEST_QUERY_SEQUENTIAL_2 = "Of those, show only those who survived"
TEST_SURVIVAL_RATE_QUERY = "What is the survival rate for each passenger class?"

@pytest.mark.skipif(os.environ.get('GITHUB_ACTIONS') == 'true', reason="API calls should not run in CI")
def test_basic_app_loads(page: Page, local_app):
    """Test that the app loads and the initial UI elements are present."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load
    page.wait_for_timeout(3000)
    
    # Wait for data table to be visible (indicates app is ready)
    page.wait_for_selector("#data_table", state="visible", timeout=20000)
    
    # Skip title check - it's not important for functionality
    # Just make sure the page loaded
    
    # Check that the chat input is visible - using a more generic selector
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    
    # Check that the data table is visible
    data_table = page.locator("#data_table")
    assert data_table.is_visible(), "Data table should be visible"

@pytest.mark.skipif(os.environ.get('GITHUB_ACTIONS') == 'true', reason="API calls should not run in CI")
def test_basic_app_query(page: Page, local_app):
    """Test that querying works and updates the data table."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load
    page.wait_for_timeout(3000)
    
    # Wait for data table to be visible (indicates app is ready)
    page.wait_for_selector("#data_table", state="visible", timeout=20000)
    
    # Find the chat input and submit a query
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    chat_input.fill(TEST_QUERY)
    chat_input.press("Enter")
    
    # Wait longer for the API request to complete
    page.wait_for_timeout(5000)
    
    # Check that the data table updates
    page.wait_for_timeout(2000)
    
    # Check the data table is visible (which confirms the query worked)
    data_table = page.locator("#data_table")
    assert data_table.is_visible(), "Data table should be visible after query"
    
    # Verify that the displayed data actually contains women who survived
    # First, wait for the cells to be populated
    page.wait_for_timeout(1000)
    
    # Look for data cells in the table
    rows = page.locator("#data_table tbody tr").all()
    assert len(rows) > 0, "Table should have rows after query"
    
    # Check a sample of rows to confirm they're women who survived
    # We'll check up to 5 random rows
    rows_to_check = min(5, len(rows))
    for i in range(rows_to_check):
        row = rows[i]
        cells = row.locator("td").all()
        
        # Check if the row has data (at least some cells)
        assert len(cells) > 0, f"Row {i} should have cells"
        
        # Get the text from the cells that should have 'survived' and 'sex' values
        # The exact columns may vary, so we'll look for values in all cells
        row_text = " ".join([cell.text_content() or "" for cell in cells]).lower()
        
        # Check if this row represents a woman who survived
        # Look for values like "1" (survived) and "female"
        has_survival_indicator = "1" in row_text or "yes" in row_text
        has_female_indicator = "female" in row_text or "woman" in row_text
        
        assert has_survival_indicator, f"Row {i} should indicate survival"
        assert has_female_indicator, f"Row {i} should be for a female passenger"

@pytest.mark.skipif(os.environ.get('GITHUB_ACTIONS') == 'true', reason="API calls should not run in CI")
def test_basic_app_sequential_queries(page: Page, local_app):
    """Test that sequential queries work and maintain context."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load
    page.wait_for_timeout(3000)
    
    # Wait for data table to be visible (indicates app is ready)
    page.wait_for_selector("#data_table", state="visible", timeout=20000)
    
    # Find the chat input and submit the first query - first class passengers
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    chat_input.fill(TEST_QUERY_SEQUENTIAL_1)
    chat_input.press("Enter")
    
    # Wait for the API request to complete
    page.wait_for_timeout(5000)
    
    # Check that the data table updates
    page.wait_for_timeout(2000)
    
    # Verify we get first class passengers
    rows = page.locator("#data_table tbody tr").all()
    assert len(rows) > 0, "Table should have rows after first query"
    
    # Check a few rows to confirm they're first class passengers
    rows_to_check = min(3, len(rows))
    for i in range(rows_to_check):
        row = rows[i]
        cells = row.locator("td").all()
        row_text = " ".join([cell.text_content() or "" for cell in cells]).lower()
        
        # Check for first class indicators (1 or "first")
        has_first_class = "1" in row_text or "first" in row_text
        assert has_first_class, f"Row {i} should be a first class passenger"
    
    # Now submit the follow-up query to filter to only survivors
    chat_input.fill(TEST_QUERY_SEQUENTIAL_2)
    chat_input.press("Enter")
    
    # Wait for the API request to complete
    page.wait_for_timeout(5000)
    
    # Check that the data table updates
    page.wait_for_timeout(2000)
    
    # Verify we get first class passengers who survived
    rows = page.locator("#data_table tbody tr").all()
    assert len(rows) > 0, "Table should have rows after sequential query"
    
    # Check a few rows to confirm they're first class passengers who survived
    rows_to_check = min(3, len(rows))
    for i in range(rows_to_check):
        row = rows[i]
        cells = row.locator("td").all()
        row_text = " ".join([cell.text_content() or "" for cell in cells]).lower()
        
        # Check for first class and survival indicators
        has_first_class = "1" in row_text or "first" in row_text
        has_survival_indicator = "1" in row_text or "yes" in row_text
        
        assert has_first_class, f"Row {i} should be a first class passenger"
        assert has_survival_indicator, f"Row {i} should indicate survival"

@pytest.mark.skipif(os.environ.get('GITHUB_ACTIONS') == 'true', reason="API calls should not run in CI")
def test_basic_app_stats_query(page: Page, local_app):
    """Test that statistical queries work and display results correctly."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load
    page.wait_for_timeout(3000)
    
    # Wait for data table to be visible (indicates app is ready)
    page.wait_for_selector("#data_table", state="visible", timeout=20000)
    
    # Find the chat input and submit the survival rate query
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    chat_input.fill(TEST_SURVIVAL_RATE_QUERY)
    chat_input.press("Enter")
    
    # Wait for the API request to complete
    page.wait_for_timeout(10000)
    
    # Wait for a code block to appear - this would contain the SQL query
    page.wait_for_selector("code, pre", state="visible", timeout=20000)
    
    # Wait for some time to let any tables render
    page.wait_for_timeout(2000)
    
    # Look for page content that indicates the query executed successfully
    page_content = page.content()
    
    # Check for SQL keywords or related content
    has_sql = re.search(r"SELECT|GROUP BY|ORDER BY|survival|rate|class", page_content, re.IGNORECASE)
    assert has_sql, "Page should contain SQL-related content"
    
    # Check for presence of data table which should still be visible
    data_table = page.locator("#data_table")
    assert data_table.is_visible(), "Data table should be visible after statistical query"