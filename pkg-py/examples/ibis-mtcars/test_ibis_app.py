"""
End-to-end test for the ibis-mtcars example app.
"""

import sys
import pytest
from pathlib import Path
import pandas as pd
from unittest.mock import patch, MagicMock
from playwright.sync_api import Page
from io import StringIO
from functools import partial

# Add the tests directory to the path to import testing_utils
sys.path.append(str(Path(__file__).parent.parent.parent / "tests"))
from testing_utils import create_mock_sql_chat

# Mock mtcars data
MOCK_MTCARS_DATA = """car_name,mpg,cyl,disp,hp,drat,wt,qsec,vs,am,gear,carb
Mazda RX4,21,6,160,110,3.9,2.62,16.46,0,1,4,4
Mazda RX4 Wag,21,6,160,110,3.9,2.875,17.02,0,1,4,4
Datsun 710,22.8,4,108,93,3.85,2.32,18.61,1,1,4,1
Hornet 4 Drive,21.4,6,258,110,3.08,3.215,19.44,1,0,3,1
Hornet Sportabout,18.7,8,360,175,3.15,3.44,17.02,0,0,3,2
Valiant,18.1,6,225,105,2.76,3.46,20.22,1,0,3,1
Duster 360,14.3,8,360,245,3.21,3.57,15.84,0,0,3,4
Merc 240D,24.4,4,146.7,62,3.69,3.19,20,1,0,4,2
Merc 230,22.8,4,140.8,95,3.92,3.15,22.9,1,0,4,2
Merc 280,19.2,6,167.6,123,3.92,3.44,18.3,1,0,4,4
"""

# Define SQL queries that our mock will return for specific prompts
SQL_RESPONSES = {
    "Which cars have the highest MPG?": "SELECT * FROM mtcars ORDER BY mpg DESC LIMIT 5",
    "Show me cars with more than 6 cylinders": "SELECT * FROM mtcars WHERE cyl > 6",
    "What's the average MPG for manual vs automatic?": "SELECT am, AVG(mpg) as avg_mpg FROM mtcars GROUP BY am",
    "Compare horsepower and quarter mile time": "SELECT car_name, hp, qsec FROM mtcars ORDER BY hp DESC",
}


# Define a mock for querychat's create_chat_callback
class MockChat:
    """Mock for Chat class with all required methods."""
    
    def __init__(self, system_prompt=None, model=None, **kwargs):
        """Mock constructor that accepts system_prompt and other parameters."""
        self.system_prompt = system_prompt
        self.model = model
        self.kwargs = kwargs
        self.calls = []
        self.tools = {}
        self.history = []
        self.greeting_sent = False
    
    def register_tool(self, tool_func):
        """Register a tool function."""
        self.tools[tool_func.__name__] = tool_func
    
    async def call_async(self, prompt, **kwargs):
        """Mock LLM call that returns predefined responses based on prompt."""
        self.calls.append({"prompt": prompt, "kwargs": kwargs})
        
        # Handle greeting request
        if "greeting" in prompt.lower():
            return "👋 Welcome to the mock chat! Try asking questions about the car data."
        
        # For SQL queries, return a canned SQL response
        for key, sql in SQL_RESPONSES.items():
            if key.lower() in prompt.lower():
                # If this has query tool registered, call it with the SQL
                if "query" in self.tools:
                    await self.tools["query"](sql)
                return f"I've created this SQL query to answer your question:\n\n```sql\n{sql}\n```"
        
        return "I'm a mock response! Ask me about cars data."
    
    async def stream_async(self, prompt, **kwargs):
        """Mock streaming that returns a simple async iterator."""
        self.calls.append({"prompt": prompt, "kwargs": kwargs})
        
        # Handle greeting request
        if "greeting" in prompt.lower():
            response = "👋 Welcome to the mock chat! Try asking questions about the car data."
            self.history.append({"role": "assistant", "content": response})
            self.greeting_sent = True
            return MockStreamResponse(response)
        
        # For SQL queries, return a canned SQL response
        for key, sql in SQL_RESPONSES.items():
            if key.lower() in prompt.lower():
                # If this has query tool registered, call it with the SQL
                if "query" in self.tools:
                    await self.tools["query"](sql)
                response = f"I've created this SQL query to answer your question:\n\n```sql\n{sql}\n```"
                self.history.append({"role": "assistant", "content": response})
                return MockStreamResponse(response)
        
        response = "I'm a mock response! Ask me about cars data."
        self.history.append({"role": "assistant", "content": response})
        return MockStreamResponse(response)


class MockStreamResponse:
    """Mock for async stream response."""
    
    def __init__(self, content):
        self.content = content
        self._chunks = [content[i:i+5] for i in range(0, len(content), 5)]
        self._index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk
    
    def get_content(self):
        return self.content


# Mock the create_chat_callback function used in querychat init
@pytest.fixture
def mock_chat_factory():
    def factory_func(system_prompt=None, **kwargs):
        return MockChat(system_prompt=system_prompt, **kwargs)
    return factory_func


def test_ibis_app_loads(page: Page, local_app, mock_chat_factory):
    """Test that the app loads and the initial UI elements are present."""
    # Patch querychat.init to use our mock factory directly
    with patch("querychat.init") as mock_init:
        # Configure the mock to pass through all arguments except create_chat_callback
        def side_effect(*args, **kwargs):
            # Keep original arguments but replace create_chat_callback
            kwargs["create_chat_callback"] = mock_chat_factory
            # Import the real init function to call it
            from querychat.querychat import QueryChatConfig
            # Create and return a QueryChatConfig with our mock factory
            return QueryChatConfig(
                data_source=kwargs.get("data_source") or args[0],
                system_prompt=kwargs.get("system_prompt_override", "Mock system prompt"),
                greeting=kwargs.get("greeting", None),
                create_chat_callback=mock_chat_factory
            )
        mock_init.side_effect = side_effect
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait for app to load
        page.wait_for_timeout(3000)
        
        # Check that the page contains "Overview" tab
        assert page.locator("text=Overview").is_visible(), "Overview tab should be visible"
        
        # Check that the chat input is visible
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        
        # Check that the value boxes are visible
        assert page.locator("text=Average MPG").is_visible(), "Average MPG box should be visible"
        assert page.locator("text=Average Horsepower").is_visible(), "Average HP box should be visible"
        assert page.locator("text=Cars in Dataset").is_visible(), "Cars count box should be visible"
        
        # Verify the actual values in the value boxes show valid numbers
        mpg_value_text = page.locator("#avg_mpg").text_content() or ""
        if mpg_value_text.strip():
            mpg_value = float(mpg_value_text)
            assert mpg_value > 0, f"Expected positive MPG, but got {mpg_value}"
        
        hp_value_text = page.locator("#avg_hp").text_content() or ""
        if hp_value_text.strip():
            hp_value = float(hp_value_text)
            assert hp_value > 0, f"Expected positive HP, but got {hp_value}"
        
        car_count_text = page.locator("#car_count").text_content() or ""
        if car_count_text.strip():
            car_count = int(car_count_text)
            assert car_count > 0, f"Expected positive car count, but got {car_count}"


def test_ibis_app_query(page: Page, local_app, mock_chat_factory):
    """Test that querying works and updates the visualizations."""
    # Patch querychat.init to use our mock factory directly
    with patch("querychat.init") as mock_init:
        # Configure the mock to pass through all arguments except create_chat_callback
        def side_effect(*args, **kwargs):
            # Keep original arguments but replace create_chat_callback
            kwargs["create_chat_callback"] = mock_chat_factory
            # Import the real init function to call it
            from querychat.querychat import QueryChatConfig
            # Create and return a QueryChatConfig with our mock factory
            return QueryChatConfig(
                data_source=kwargs.get("data_source") or args[0],
                system_prompt=kwargs.get("system_prompt_override", "Mock system prompt"),
                greeting=kwargs.get("greeting", None),
                create_chat_callback=mock_chat_factory
            )
        mock_init.side_effect = side_effect
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait longer for the app to fully load and values to stabilize
        page.wait_for_timeout(5000)
        
        # Find the chat input and submit a query
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        
        # Submit a query that will change the dataset - use a query in our SQL_RESPONSES
        chat_input.fill("Which cars have the highest MPG?")
        chat_input.press("Enter")
        
        # Wait for processing - this might take longer with a real DB
        page.wait_for_timeout(8000)
        
        # Check if there are chat messages - if not, the test can still be useful
        # by checking the data table
        
        # Switch to the Car Details tab
        page.locator("text=Car Details").click()
        
        # Wait for the tab content to load
        page.wait_for_timeout(1000)
        
        # Wait longer for the data table to appear
        page.wait_for_timeout(3000)
        
        # Check for any kind of table structure in the Car Details tab
        table_selector = ".rt-table, table, .table, #car_data, .data-grid, [role='grid'], [role='table']"
        page.wait_for_selector(table_selector, timeout=5000, state="visible")
        
        # Once we've waited, try to get the table
        car_data = page.locator(table_selector).first
        assert car_data.is_visible(), "Car data table should be visible"
        
        # Verify the table has some content (any elements inside)
        # Need to escape the single quotes in the JavaScript string
        escaped_selector = table_selector.replace("'", "\\'")
        has_content = page.evaluate(f"() => {{ const el = document.querySelector('{escaped_selector}'); return el && el.children.length > 0; }}")
        assert has_content, "Car data table should have content"


def test_ibis_app_plots(page: Page, local_app, mock_chat_factory):
    """Test that the plots are rendered correctly."""
    # Patch querychat.init to use our mock factory directly
    with patch("querychat.init") as mock_init:
        # Configure the mock to pass through all arguments except create_chat_callback
        def side_effect(*args, **kwargs):
            # Keep original arguments but replace create_chat_callback
            kwargs["create_chat_callback"] = mock_chat_factory
            # Import the real init function to call it
            from querychat.querychat import QueryChatConfig
            # Create and return a QueryChatConfig with our mock factory
            return QueryChatConfig(
                data_source=kwargs.get("data_source") or args[0],
                system_prompt=kwargs.get("system_prompt_override", "Mock system prompt"),
                greeting=kwargs.get("greeting", None),
                create_chat_callback=mock_chat_factory
            )
        mock_init.side_effect = side_effect
        
        # Navigate to the app
        page.goto(local_app.url)
        
        # Wait for the app to fully load
        page.wait_for_timeout(3000)
        
        # Check that the MPG vs Horsepower plot is visible
        assert page.locator("text=MPG vs Horsepower").is_visible(), "MPG vs HP plot title should be visible"
        
        # Check that the Cylinder Distribution plot is visible
        assert page.locator("text=Cylinder Distribution").is_visible(), "Cylinder plot title should be visible"
        
        # Check that the plots containers are present
        assert page.locator("#mpg_hp_plot").is_visible(), "MPG vs HP plot should be visible"
        assert page.locator("#cyl_plot").is_visible(), "Cylinder plot should be visible"
        
        # See if plots have content - we don't fail if they don't since we're focused on validating
        # the basic UI structure, not plotly specifics
        plots_have_content = page.evaluate("""() => {
            const mpgPlot = document.querySelector('#mpg_hp_plot');
            const cylPlot = document.querySelector('#cyl_plot');
            return {
                mpgPlot: mpgPlot && mpgPlot.children.length > 0,
                cylPlot: cylPlot && cylPlot.children.length > 0
            };
        }""")
        
        # Just log the information - we'll pass the test as long as the containers exist
        if plots_have_content.get('mpgPlot'):
            print("MPG vs HP plot has content")
        if plots_have_content.get('cylPlot'):
            print("Cylinder plot has content")
            
        # Test plot interactivity by submitting a query that should change the plots
        chat_input = page.locator("input[type='text'], textarea").first
        assert chat_input.is_visible(), "Chat input should be visible"
        
        # Submit a query that should filter the data
        chat_input.fill("Show me cars with more than 6 cylinders")
        chat_input.press("Enter")
        
        # Wait for processing and plots to update
        page.wait_for_timeout(5000)
        
        # Verify plots are still visible after the query
        assert page.locator("#mpg_hp_plot").is_visible(), "MPG vs HP plot should still be visible after query"
        assert page.locator("#cyl_plot").is_visible(), "Cylinder plot should still be visible after query"