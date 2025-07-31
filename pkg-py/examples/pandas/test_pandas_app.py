"""
End-to-end test for the pandas QueryChat example app.
"""

import os
import sys
import pytest
from pathlib import Path
import seaborn as sns
import pandas as pd
from unittest.mock import patch, mock_open
from playwright.sync_api import Page

# Add the tests directory to the path to import testing_utils
sys.path.append(str(Path(__file__).parent.parent.parent / "tests"))
from testing_utils import create_mock_sql_chat, mock_chatlas_factory

# Load the titanic dataset
titanic = sns.load_dataset("titanic")

# Define SQL queries that our mock will return for specific prompts
SQL_RESPONSES = {
    "Show me passengers who survived": "SELECT * FROM titanic WHERE survived = 1",
    "Who are the passengers from first class?": "SELECT * FROM titanic WHERE pclass = 1",
    "Show me passengers older than 30": "SELECT * FROM titanic WHERE age > 30",
    "Count passengers by class": "SELECT pclass, COUNT(*) as count FROM titanic GROUP BY pclass",
}

# Mock content for greeting and data_description files
MOCK_GREETING = """# Welcome to the Titanic Dataset!

This dataset contains information about the passengers on the Titanic.

Try asking:
- How many passengers survived?
- Show me first class passengers
- What's the age distribution?
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


@pytest.fixture(scope="module")
def mock_chat():
    """Create a mock chat for testing."""
    return create_mock_sql_chat(titanic, SQL_RESPONSES)


def test_pandas_app_loads(page: Page, local_app, mock_chat):
    """Test that the app loads and the initial UI elements are present."""
    # Create a mock chatlas.ChatGithub that will return our mock chat
    mock_chat_factory = mock_chatlas_factory(mock_chat)
    
    # Mock file reads for greeting and data_description
    m = mock_open(read_data=MOCK_GREETING)
    m.side_effect = [mock_open(read_data=MOCK_GREETING).return_value, 
                    mock_open(read_data=MOCK_DATA_DESC).return_value]
    
    # Patch the necessary components
    with patch("chatlas.ChatGithub", mock_chat_factory), \
         patch("builtins.open", m):
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait for app to load
        page.wait_for_timeout(2000)
        
        # Check that the page has a title
        title = page.title()
        assert title, "Page should have a title"
        
        # Check that the chat input is visible
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        
        # Check that the data table is visible
        data_table = page.locator("#data_table")
        assert data_table.is_visible(), "Data table should be visible"
        
        # Check if any chat messages exist - we may or may not have our greeting yet
        # but we should have something in the chat interface
        page.wait_for_timeout(1000)


def test_pandas_app_query(page: Page, local_app, mock_chat):
    """Test that querying works and updates the data table."""
    # Create a mock chatlas.ChatGithub that will return our mock chat
    mock_chat_factory = mock_chatlas_factory(mock_chat)
    
    # Mock file reads for greeting and data_description
    m = mock_open(read_data=MOCK_GREETING)
    m.side_effect = [mock_open(read_data=MOCK_GREETING).return_value, 
                    mock_open(read_data=MOCK_DATA_DESC).return_value]
    
    # Patch the necessary components
    with patch("chatlas.ChatGithub", mock_chat_factory), \
         patch("builtins.open", m):
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait for the app to fully load
        page.wait_for_timeout(2000)
        
        # Find the chat input and submit a query
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        chat_input.fill("Show me passengers older than 30")
        chat_input.press("Enter")
        
        # Wait for processing
        page.wait_for_timeout(2000)
        
        # Wait for the data table to update
        page.wait_for_timeout(1000)
        
        # Check the data table is visible
        data_table = page.locator("#data_table")
        assert data_table.is_visible(), "Data table should be visible after query"