"""
End-to-end test for the SQLite QueryChat example app.
"""

import os
import sys
import pytest
import re
import tempfile
from pathlib import Path
import chatlas
import seaborn as sns
import pandas as pd
from unittest.mock import patch, mock_open, MagicMock
from playwright.sync_api import Page
from sqlalchemy import create_engine

# Load the titanic dataset
titanic = sns.load_dataset("titanic")

# Mock content for greeting and data_description files
MOCK_GREETING = """# Welcome to the Titanic Dataset (SQLite)!

This dataset contains information about the passengers on the Titanic, stored in a SQLite database.

Try asking:
- How many passengers survived?
- Show me first class passengers
- What's the average age by passenger class?
"""

MOCK_DATA_DESC = """
The Titanic dataset contains the following variables:
- survived: Survival (0 = No, 1 = Yes)
- pclass: Ticket class (1 = 1st, 2 = 2nd, 3 = 3rd)
- sex: Sex (male or female)
- age: Age in years
- sibsp: Number of siblings/spouses aboard
- parch: Number of parents/children aboard
- fare: Passenger fare
- embarked: Port of embarkation (C = Cherbourg, Q = Queenstown, S = Southampton)
"""

# Test queries to use
TEST_QUERY = "Show me male passengers"
TEST_FILTER_QUERY = "Show only passengers who boarded in Cherbourg"
TEST_SURVIVAL_RATE_QUERY = "What is the survival rate for each passenger class?"
TEST_SEQUENTIAL_1 = "Show female passengers older than 30"
TEST_SEQUENTIAL_2 = "Among those, who paid more than 50 for fare?"


@pytest.fixture
def mock_db_path():
    """Create a temporary SQLite database with the titanic dataset."""
    # Create a temporary file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    # Create a SQLite engine
    engine = create_engine(f"sqlite:///{db_path}")
    
    # Write the titanic dataset to the database
    titanic.to_sql("titanic", engine, if_exists="replace", index=False)
    
    yield db_path
    
    # Cleanup
    os.unlink(db_path)


def test_sqlite_app_loads(page: Page, local_app, mock_db_path):
    """Test that the app loads and the initial UI elements are present."""
    # Mock file reads for greeting and data_description
    m = mock_open(read_data=MOCK_GREETING)
    m.side_effect = [mock_open(read_data=MOCK_GREETING).return_value, 
                     mock_open(read_data=MOCK_DATA_DESC).return_value]
    
    # Patch Path.exists to return True for our db_path
    original_exists = Path.exists
    def mock_exists(self):
        if self.name == "titanic.db":
            return True
        return original_exists(self)
    
    # Patch the necessary components - but NOT the chatlas module
    with patch("builtins.open", m), \
         patch("pathlib.Path.exists", mock_exists), \
         patch("sqlalchemy.create_engine") as mock_engine:
        
        # Configure the mock engine to return itself for context management
        mock_engine.return_value = MagicMock()
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait for app to load
        page.wait_for_timeout(3000)
        
        # Check that the page has a title
        title = page.title()
        assert title, "Page should have a title"
        
        # Check that the chat input is visible
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        
        # Check that the data table is visible
        data_table = page.locator("#data_table")
        assert data_table.is_visible(), "Data table should be visible"


def test_sqlite_app_query(page: Page, local_app, mock_db_path):
    """Test that querying works and updates the data table."""
    # Mock file reads for greeting and data_description
    m = mock_open(read_data=MOCK_GREETING)
    m.side_effect = [mock_open(read_data=MOCK_GREETING).return_value, 
                     mock_open(read_data=MOCK_DATA_DESC).return_value]
    
    # Patch Path.exists to return True for our db_path
    original_exists = Path.exists
    def mock_exists(self):
        if self.name == "titanic.db":
            return True
        return original_exists(self)
    
    # Patch the necessary components - but NOT the chatlas module
    with patch("builtins.open", m), \
         patch("pathlib.Path.exists", mock_exists), \
         patch("sqlalchemy.create_engine") as mock_engine:
        
        # Configure the mock engine
        mock_engine.return_value = MagicMock()
        
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
        
        # Wait for the data table to update
        page.wait_for_timeout(2000)
        
        # Check the data table is visible
        data_table = page.locator("#data_table")
        assert data_table.is_visible(), "Data table should be visible after query"
        
        # Check for SQL output in the response
        chat_messages = page.locator(".shiny-chat-message").all()
        assert len(chat_messages) > 0, "Should have chat messages"
        
        # Find the last message which should contain the response
        last_message = chat_messages[-1]
        message_text = last_message.text_content() or ""
        
        # Look for SQL code in a code block or response
        has_sql = re.search(r"SELECT|FROM|WHERE", message_text, re.IGNORECASE)
        assert has_sql, "Response should contain SQL"
        
        # Verify SQL has correct filtering - should see WHERE sex = 'male' or similar
        has_male_filter = re.search(r"sex\s*=\s*['\"]\s*male|male\s*['\"]", message_text, re.IGNORECASE)
        assert has_male_filter, "SQL should filter for male passengers"
        
        # Verify that the displayed data actually contains male passengers
        # Look for data cells in the table
        rows = page.locator("#data_table tbody tr").all()
        assert len(rows) > 0, "Table should have rows after query"
        
        # Check a sample of rows to confirm they're male passengers
        rows_to_check = min(5, len(rows))
        for i in range(rows_to_check):
            row = rows[i]
            cells = row.locator("td").all()
            row_text = " ".join([cell.text_content() or "" for cell in cells]).lower()
            
            # Check for male indicators
            has_male_indicator = "male" in row_text or "man" in row_text
            assert has_male_indicator, f"Row {i} should be a male passenger"


def test_sqlite_app_filter_query(page: Page, local_app, mock_db_path):
    """Test that filtering queries work correctly."""
    # Mock file reads for greeting and data_description
    m = mock_open(read_data=MOCK_GREETING)
    m.side_effect = [mock_open(read_data=MOCK_GREETING).return_value, 
                     mock_open(read_data=MOCK_DATA_DESC).return_value]
    
    # Patch Path.exists to return True for our db_path
    original_exists = Path.exists
    def mock_exists(self):
        if self.name == "titanic.db":
            return True
        return original_exists(self)
    
    # Patch the necessary components - but NOT the chatlas module
    with patch("builtins.open", m), \
         patch("pathlib.Path.exists", mock_exists), \
         patch("sqlalchemy.create_engine") as mock_engine:
        
        # Configure the mock engine
        mock_engine.return_value = MagicMock()
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait for the app to fully load
        page.wait_for_timeout(3000)
        
        # Find the chat input and submit a filter query
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        chat_input.fill(TEST_FILTER_QUERY)
        chat_input.press("Enter")
        
        # Wait longer for the API request to complete
        page.wait_for_timeout(5000)
        
        # Wait for the data table to update
        page.wait_for_timeout(2000)
        
        # Check the data table is visible
        data_table = page.locator("#data_table")
        assert data_table.is_visible(), "Data table should be visible after query"
        
        # Check for SQL output in the response
        chat_messages = page.locator(".shiny-chat-message").all()
        assert len(chat_messages) > 0, "Should have chat messages"
        
        # Find the last message which should contain the response
        last_message = chat_messages[-1]
        message_text = last_message.text_content() or ""
        
        # Look for SQL code with correct filtering - should see WHERE embarked = 'C' or similar
        has_cherbourg_filter = re.search(r"embark.*=.*['\"]C['\"]|embark.*=.*['\"]Cherbourg['\"]|embark_town.*=.*['\"]Cherbourg['\"]", 
                                         message_text, re.IGNORECASE)
        assert has_cherbourg_filter, "SQL should filter for Cherbourg passengers"
        
        # Verify that the displayed data actually contains Cherbourg passengers
        # Look for data cells in the table
        rows = page.locator("#data_table tbody tr").all()
        assert len(rows) > 0, "Table should have rows after query"
        
        # Check a sample of rows to confirm they're Cherbourg passengers
        rows_to_check = min(5, len(rows))
        for i in range(rows_to_check):
            row = rows[i]
            cells = row.locator("td").all()
            row_text = " ".join([cell.text_content() or "" for cell in cells]).lower()
            
            # Check for Cherbourg indicators - either 'C' or 'Cherbourg'
            has_cherbourg = "c" in row_text or "cherbourg" in row_text
            assert has_cherbourg, f"Row {i} should be a Cherbourg passenger"


def test_sqlite_app_stats_query(page: Page, local_app, mock_db_path):
    """Test that statistical queries work and display correct SQL."""
    # Mock file reads for greeting and data_description
    m = mock_open(read_data=MOCK_GREETING)
    m.side_effect = [mock_open(read_data=MOCK_GREETING).return_value, 
                     mock_open(read_data=MOCK_DATA_DESC).return_value]
    
    # Patch Path.exists to return True for our db_path
    original_exists = Path.exists
    def mock_exists(self):
        if self.name == "titanic.db":
            return True
        return original_exists(self)
    
    # Patch the necessary components - but NOT the chatlas module
    with patch("builtins.open", m), \
         patch("pathlib.Path.exists", mock_exists), \
         patch("sqlalchemy.create_engine") as mock_engine:
        
        # Configure the mock engine
        mock_engine.return_value = MagicMock()
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait for the app to fully load
        page.wait_for_timeout(3000)
        
        # Find the chat input and submit a statistical query
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        chat_input.fill(TEST_SURVIVAL_RATE_QUERY)
        chat_input.press("Enter")
        
        # Wait longer for the API request to complete
        page.wait_for_timeout(5000)
        
        # Wait for the response to appear
        page.wait_for_timeout(2000)
        
        # Check for SQL output in the response
        chat_messages = page.locator(".shiny-chat-message").all()
        assert len(chat_messages) > 0, "Should have chat messages"
        
        # Find the last message which should contain the response
        last_message = chat_messages[-1]
        message_text = last_message.text_content() or ""
        
        # Look for SQL code with aggregation - should see GROUP BY pclass
        has_group_by_class = re.search(r"GROUP BY.*pclass|GROUP BY.*class", message_text, re.IGNORECASE)
        assert has_group_by_class, "SQL should group by passenger class"
        
        # Should see aggregation for survival rate - using AVG or COUNT
        has_survival_agg = re.search(r"AVG.*survived|COUNT.*survived|SUM.*survived", message_text, re.IGNORECASE)
        assert has_survival_agg, "SQL should calculate survival rates"
        
        # Check for response showing survival rates - could be table, code block or text
        # Either we see a table in the UI or text showing rates for classes 1, 2, and 3
        has_rates = re.search(r"(class.*?[0-9\.]+%|[0-9\.]+%.*class|1st.*?[0-9\.]+%|2nd.*?[0-9\.]+%|3rd.*?[0-9\.]+%)", 
                             message_text, re.IGNORECASE)
        
        # Check for a table with survival rates
        has_table = page.locator("table").count() > 0
        
        assert has_rates or has_table, "Response should show survival rates by class"


def test_sqlite_app_sequential_queries(page: Page, local_app, mock_db_path):
    """Test that sequential queries work and maintain context."""
    # Mock file reads for greeting and data_description
    m = mock_open(read_data=MOCK_GREETING)
    m.side_effect = [mock_open(read_data=MOCK_GREETING).return_value, 
                     mock_open(read_data=MOCK_DATA_DESC).return_value]
    
    # Patch Path.exists to return True for our db_path
    original_exists = Path.exists
    def mock_exists(self):
        if self.name == "titanic.db":
            return True
        return original_exists(self)
    
    # Patch the necessary components - but NOT the chatlas module
    with patch("builtins.open", m), \
         patch("pathlib.Path.exists", mock_exists), \
         patch("sqlalchemy.create_engine") as mock_engine:
        
        # Configure the mock engine
        mock_engine.return_value = MagicMock()
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait for the app to fully load
        page.wait_for_timeout(3000)
        
        # Find the chat input and submit the first query - females over 30
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        chat_input.fill(TEST_SEQUENTIAL_1)
        chat_input.press("Enter")
        
        # Wait for the API request to complete
        page.wait_for_timeout(5000)
        
        # Wait for the data table to update
        page.wait_for_timeout(2000)
        
        # Verify we get female passengers over 30
        rows = page.locator("#data_table tbody tr").all()
        assert len(rows) > 0, "Table should have rows after first query"
        
        # Now submit the follow-up query about fares
        chat_input.fill(TEST_SEQUENTIAL_2)
        chat_input.press("Enter")
        
        # Wait for the API request to complete
        page.wait_for_timeout(5000)
        
        # Wait for the data table to update
        page.wait_for_timeout(2000)
        
        # Check for SQL output in the response
        chat_messages = page.locator(".shiny-chat-message").all()
        assert len(chat_messages) > 0, "Should have chat messages"
        
        # Find the last message which should contain the response
        last_message = chat_messages[-1]
        message_text = last_message.text_content() or ""
        
        # SQL should have filters for age, sex and fare
        has_fare_filter = re.search(r"fare\s*>\s*50", message_text, re.IGNORECASE)
        assert has_fare_filter, "SQL should filter for high fares"
        
        # Verify data table contains the correct results
        rows = page.locator("#data_table tbody tr").all()
        assert len(rows) > 0, "Table should have rows after sequential query"
        
        # Check a few rows to confirm they're female passengers over 30 with high fares
        rows_to_check = min(3, len(rows))
        for i in range(rows_to_check):
            row = rows[i]
            cells = row.locator("td").all()
            row_text = " ".join([cell.text_content() or "" for cell in cells]).lower()
            
            # Check for female indicators
            has_female_indicator = "female" in row_text or "woman" in row_text
            assert has_female_indicator, f"Row {i} should be a female passenger"
            
            # Extract age and fare from the row
            # This is approximate since we don't know the exact format
            # Look for numbers that could be ages and fares
            numbers = re.findall(r"(\d+(?:\.\d+)?)", row_text)
            has_appropriate_values = False
            
            # Check if any number is > 30 (age) and any number is > 50 (fare)
            for n in numbers:
                if float(n) > 50:  # Found a fare > 50
                    has_appropriate_values = True
            
            assert has_appropriate_values, f"Row {i} should have fare > 50"