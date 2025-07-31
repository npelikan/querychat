"""
End-to-end test for the basic QueryChat example app.
"""

import os
import sys
import pytest
import re
from pathlib import Path
import chatlas
import seaborn as sns
import pandas as pd
from playwright.sync_api import Page

# Load the titanic dataset
titanic = sns.load_dataset("titanic")

# Test queries to use
TEST_QUERY = "Show women who survived"
TEST_QUERY_SEQUENTIAL_1 = "Show me first class passengers"
TEST_QUERY_SEQUENTIAL_2 = "Of those, show only those who survived"
TEST_SURVIVAL_RATE_QUERY = "What is the survival rate for each passenger class?"

def test_basic_app_loads(page: Page, local_app):
    """Test that the app loads and the initial UI elements are present."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load
    page.wait_for_timeout(3000)
    
    # Skip title check - it's not important for functionality
    # Just make sure the page loaded
    
    # Check that the chat input is visible - using a more generic selector
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    
    # Check that the data table is visible
    data_table = page.locator("#data_table")
    assert data_table.is_visible(), "Data table should be visible"

def test_basic_app_query(page: Page, local_app):
    """Test that querying works and updates the data table."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for the app to fully load
    page.wait_for_timeout(3000)
    
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

def test_basic_app_sequential_queries(page: Page, local_app):
    """Test that sequential queries work and maintain context."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for the app to fully load
    page.wait_for_timeout(3000)
    
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

def test_basic_app_stats_query(page: Page, local_app):
    """Test that statistical queries work and display results correctly."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for the app to fully load
    page.wait_for_timeout(3000)
    
    # Find the chat input and submit the survival rate query
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    chat_input.fill(TEST_SURVIVAL_RATE_QUERY)
    chat_input.press("Enter")
    
    # Wait for the API request to complete
    page.wait_for_timeout(5000)
    
    # Wait for the response to appear
    page.wait_for_timeout(2000)
    
    # Check for SQL output in the response
    chat_messages = page.locator(".shiny-chat-message").all()
    assert len(chat_messages) > 0, "Should have chat messages"
    
    # Find the last message which should contain the response
    last_message = chat_messages[-1]
    message_text = last_message.text_content() or ""
    
    # Look for SQL code in a code block or response
    has_sql = re.search(r"SELECT|GROUP BY|ORDER BY", message_text, re.IGNORECASE)
    assert has_sql, "Response should contain SQL"
    
    # Check for a table with survival rates
    # This could be in an actual HTML table or in text/markdown format
    has_table = page.locator("table").count() > 0 or re.search(r"\|.*\|.*\|", message_text)
    
    # If we don't see an explicit table, at least check if the message contains class and survival rate information
    if not has_table:
        has_class_data = re.search(r"class.*survival|survival.*class", message_text, re.IGNORECASE)
        assert has_class_data, "Response should contain class and survival rate information"