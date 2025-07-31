"""
Tests for ibis integration with QueryChat.

These tests verify that the to_ibis method works correctly with:
- SQL query execution via ibis
- Fallback to original table when no query is available
"""

import importlib.util
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from src.querychat.datasource import DataFrameSource
from src.querychat.querychat import QueryChat

# Skip tests if ibis is not installed
ibis_installed = importlib.util.find_spec("ibis") is not None
pytestmark = pytest.mark.skipif(not ibis_installed, reason="ibis not installed")


@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for testing."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "age": [25, 30, 35, 40, 45],
        "department": ["HR", "Engineering", "Sales", "Engineering", "HR"],
    })


@pytest.fixture
def mock_data_source(sample_dataframe):
    """Create a mock DataSource for testing."""
    data_source = DataFrameSource(sample_dataframe, "employees")
    return data_source


@pytest.fixture
def mock_querychat(mock_data_source):
    """Create a mock QueryChat object with controlled SQL query output."""
    # Create mock functions
    mock_chat = MagicMock()
    mock_sql = MagicMock()
    mock_title = MagicMock()
    mock_df = MagicMock()
    
    # Configure mock return values
    mock_sql.return_value = "SELECT * FROM employees WHERE department = 'Engineering'"
    mock_df.return_value = mock_data_source._df
    
    # Create QueryChat instance
    return QueryChat(mock_chat, mock_sql, mock_title, mock_df, mock_data_source)


@pytest.fixture
def mock_ibis_connection():
    """Create a mock ibis connection object."""
    mock_conn = MagicMock()
    
    # Mock the table, sql, and create_table methods
    mock_conn.table = MagicMock()
    mock_conn.sql = MagicMock()
    mock_conn.create_table = MagicMock()
    
    # For the table method, return a mock table
    mock_table = MagicMock()
    mock_conn.table.return_value = mock_table
    
    # For the sql method, return a mock table
    mock_conn.sql.return_value = mock_table
    
    # For the create_table method, return a mock table
    mock_conn.create_table.return_value = mock_table
    
    # Mock methods for the table
    mock_table.execute = MagicMock(return_value=pd.DataFrame())
    
    return mock_conn


def test_to_ibis_with_sql_query(mock_querychat, mock_ibis_connection):
    """Test that to_ibis correctly uses the current SQL query."""
    # Mock the sql method to return a SQL query
    with patch.object(mock_querychat, "sql", return_value="SELECT * FROM employees WHERE department = 'Engineering'"):
        # Get ibis table
        ibis_table = mock_querychat.to_ibis(mock_ibis_connection)
        
        # Check that sql method was called
        mock_querychat.sql.assert_called_once()
        
        # Check that conn.sql was called with the right query
        mock_ibis_connection.sql.assert_called_once_with(
            "SELECT * FROM employees WHERE department = 'Engineering'"
        )


def test_to_ibis_no_query_returns_table(mock_querychat, mock_ibis_connection):
    """Test that to_ibis falls back to original table when no query is available."""
    # Mock the sql method to return an empty string (no query)
    with patch.object(mock_querychat, "sql", return_value=""):
        # Get ibis table
        ibis_table = mock_querychat.to_ibis(mock_ibis_connection)
        
        # Check that sql method was called
        mock_querychat.sql.assert_called_once()
        
        # Check that conn.table was called with the right table name
        mock_ibis_connection.table.assert_called_once_with("employees")


def test_to_ibis_no_query_no_data_source(mock_querychat, mock_ibis_connection):
    """Test that to_ibis raises an error when no query and no data source."""
    # Set data source to None
    mock_querychat._data_source = None
    
    # Mock the sql method to return an empty string (no query)
    with patch.object(mock_querychat, "sql", return_value=""):
        # Should raise ValueError
        with pytest.raises(ValueError, match="No SQL query has been generated yet and no data source is available"):
            mock_querychat.to_ibis(mock_ibis_connection)


def test_to_ibis_no_query_no_table_name(mock_querychat, mock_ibis_connection, sample_dataframe):
    """Test that to_ibis falls back to creating a table when no table name is available."""
    # Create a data source without a table name attribute
    mock_querychat._data_source = MagicMock()
    delattr(mock_querychat._data_source, "_table_name")
    
    # Configure df method to return the sample dataframe
    mock_querychat._df = MagicMock(return_value=sample_dataframe)
    
    # Mock the sql method to return an empty string (no query)
    with patch.object(mock_querychat, "sql", return_value=""):
        # Get ibis table
        ibis_table = mock_querychat.to_ibis(mock_ibis_connection)
        
        # Check that sql method was called
        mock_querychat.sql.assert_called_once()
        
        # Check that conn.create_table was called with the right arguments
        mock_ibis_connection.create_table.assert_called_once_with(
            "querychat_data", sample_dataframe
        )


def test_to_ibis_import_error():
    """Test that to_ibis raises ImportError when ibis is not available."""
    # Skip this test if ibis is actually installed
    if ibis_installed:
        pytest.skip("ibis is installed, can't test import error")
    
    # Create a minimal QueryChat instance
    querychat = QueryChat(
        MagicMock(),  # chat
        lambda: "SELECT * FROM table",  # sql
        lambda: "Title",  # title
        lambda: pd.DataFrame(),  # df
        MagicMock(),  # data_source
    )
    
    # Mock import to raise ImportError
    with patch("importlib.import_module", side_effect=ImportError()):
        with pytest.raises(ImportError, match="The ibis package is required for this feature"):
            querychat.to_ibis(MagicMock())


@pytest.mark.skipif(not ibis_installed, reason="This test requires ibis to be installed")
def test_to_ibis_actual_execution(mock_data_source, sample_dataframe):
    """Test that the ibis table can be executed with actual ibis."""
    import ibis
    
    # Create a real ibis connection
    conn = ibis.duckdb.connect(":memory:")
    
    # Register the dataframe in DuckDB
    conn.create_table("employees", sample_dataframe)
    
    # Create a QueryChat with a real SQL query
    querychat = QueryChat(
        MagicMock(),  # chat
        lambda: "SELECT * FROM employees WHERE department = 'Engineering'",  # sql
        lambda: "Engineering employees",  # title
        lambda: mock_data_source.execute_query("SELECT * FROM employees WHERE department = 'Engineering'"),  # df
        mock_data_source,  # data_source
    )
    
    # Get ibis table
    ibis_table = querychat.to_ibis(conn)
    
    # Execute the ibis expression
    result = ibis_table.execute()
    
    # Verify the result
    assert len(result) == 2  # Only two engineering employees
    assert set(result["name"]) == {"Bob", "Diana"}  # The two engineering employees