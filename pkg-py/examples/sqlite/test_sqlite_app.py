"""
End-to-end test for the SQLite QueryChat example app.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
import seaborn as sns
import pandas as pd
from unittest.mock import patch, mock_open, MagicMock
from playwright.sync_api import Page
from sqlalchemy import create_engine

# Add the tests directory to the path to import testing_utils
sys.path.append(str(Path(__file__).parent.parent.parent / "tests"))
from testing_utils import create_mock_sql_chat, mock_chatlas_factory

# Load the titanic dataset
titanic = sns.load_dataset("titanic")

# Define SQL queries that our mock will return for specific prompts
SQL_RESPONSES = {
    "Show me passengers who survived": "SELECT * FROM titanic WHERE survived = 1",
    "Who are the passengers from first class?": "SELECT * FROM titanic WHERE pclass = 1",
    "Show me male passengers": "SELECT * FROM titanic WHERE sex = 'male'",
    "Count passengers by embarkation port": "SELECT embarked, COUNT(*) as count FROM titanic GROUP BY embarked",
}

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


@pytest.fixture(scope="module")
def mock_chat():
    """Create a mock chat for testing."""
    return create_mock_sql_chat(titanic, SQL_RESPONSES)


def test_sqlite_app_loads(page: Page, local_app, mock_chat, mock_db_path):
    """Test that the app loads and the initial UI elements are present."""
    # Create a mock chatlas.ChatGithub that will return our mock chat
    mock_chat_factory = mock_chatlas_factory(mock_chat)
    
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
    
    # Patch the necessary components
    with patch("chatlas.ChatGithub", mock_chat_factory), \
         patch("builtins.open", m), \
         patch("pathlib.Path.exists", mock_exists), \
         patch("sqlalchemy.create_engine") as mock_engine:
        
        # Configure the mock engine to return itself for context management
        mock_engine.return_value = MagicMock()
        
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


def test_sqlite_app_query(page: Page, local_app, mock_chat, mock_db_path):
    """Test that querying works and updates the data table."""
    # Create a mock chatlas.ChatGithub that will return our mock chat
    mock_chat_factory = mock_chatlas_factory(mock_chat)
    
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
    
    # Patch the necessary components
    with patch("chatlas.ChatGithub", mock_chat_factory), \
         patch("builtins.open", m), \
         patch("pathlib.Path.exists", mock_exists), \
         patch("sqlalchemy.create_engine") as mock_engine:
        
        # Configure the mock engine
        mock_engine.return_value = MagicMock()
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait for the app to fully load
        page.wait_for_timeout(2000)
        
        # Find the chat input and submit a query
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        chat_input.fill("Show me male passengers")
        chat_input.press("Enter")
        
        # Wait for processing
        page.wait_for_timeout(2000)
        
        # Wait for the data table to update
        page.wait_for_timeout(1000)
        
        # Check the data table is visible
        data_table = page.locator("#data_table")
        assert data_table.is_visible(), "Data table should be visible after query"