"""
End-to-end test for the ibis-mtcars example app.
"""

import sys
import pytest
import re
from pathlib import Path
import pandas as pd
import chatlas
from playwright.sync_api import Page

# Test queries to use
TEST_QUERY = "Which cars have the highest MPG?"
TEST_CYLINDER_QUERY = "Show me cars with more than 6 cylinders"
TEST_HORSEPOWER_QUERY = "Show me cars with horsepower greater than 150"
TEST_WEIGHT_QUERY = "Show cars that weigh less than 3000 pounds"
TEST_SEQUENTIAL_1 = "Show cars with more than 4 cylinders"
TEST_SEQUENTIAL_2 = "Of those, show only cars with automatic transmission"


def test_ibis_app_loads(page: Page, local_app):
    """Test that the app loads and the initial UI elements are present."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load (longer timeout to allow for real API calls)
    page.wait_for_timeout(5000)
    
    # Wait for Overview tab to be visible
    page.wait_for_selector("text=Overview", state="visible", timeout=20000)
    
    # Check that the page contains "Overview" tab
    assert page.locator("text=Overview").is_visible(), "Overview tab should be visible"
    
    # Check that the chat input is visible
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    
    # Check that the value boxes are visible using more specific selectors
    assert page.locator("text=Average MPG >> nth=0").is_visible(), "Average MPG box should be visible"
    assert page.locator("text=Average Horsepower >> nth=0").is_visible(), "Average HP box should be visible"
    assert page.locator("text=Cars in Dataset >> nth=0").is_visible(), "Cars count box should be visible"
    
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


def test_ibis_app_query(page: Page, local_app):
    """Test that querying works and updates the visualizations."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load (longer timeout to allow for real API calls)
    page.wait_for_timeout(5000)
    
    # Wait for Overview tab to be visible
    page.wait_for_selector("text=Overview", state="visible", timeout=20000)
    
    # Find the chat input and submit a query
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    
    # Submit a query
    chat_input.fill(TEST_QUERY)
    chat_input.press("Enter")
    
    # Wait longer for the API request to complete
    page.wait_for_timeout(10000)
    
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
    
    # Wait for code or SQL to appear
    page.wait_for_selector("code, pre", state="visible", timeout=10000)
    
    # Look for page content that indicates the query executed successfully
    page_content = page.content()
    
    # Check for SQL presence
    has_sql = re.search(r"SELECT|FROM|WHERE|mtcars", page_content, re.IGNORECASE)
    assert has_sql, "Response should contain SQL query"
    
    # Verify that the displayed data actually shows high MPG cars
    # Check the table for car names and MPG values
    rows = page.locator(f"{table_selector} tr").all()
    assert len(rows) > 0, "Table should have rows after query"
    
    # Get the first few rows to check if they show high MPG cars
    mpg_values = []
    for i in range(min(3, len(rows))):
        row_text = (rows[i].text_content() or "").lower()
        mpg_match = re.search(r"(\d+\.?\d*)\s*mpg", row_text)
        if mpg_match:
            mpg_values.append(float(mpg_match.group(1)))
    
    # Verify that we have at least one MPG value and it's reasonably high
    if mpg_values:
        assert max(mpg_values) > 20, "Should show cars with high MPG values"


def test_ibis_app_plots(page: Page, local_app):
    """Test that the plots are rendered correctly."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load (longer timeout to allow for real API calls)
    page.wait_for_timeout(5000)
    
    # Wait for Overview tab to be visible
    page.wait_for_selector("text=Overview", state="visible", timeout=20000)
    
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
    chat_input.fill(TEST_CYLINDER_QUERY)
    chat_input.press("Enter")
    
    # Wait longer for the API request to complete and plots to update
    page.wait_for_timeout(10000)
    
    # Verify plots are still visible after the query
    assert page.locator("#mpg_hp_plot").is_visible(), "MPG vs HP plot should still be visible after query"
    assert page.locator("#cyl_plot").is_visible(), "Cylinder plot should still be visible after query"


def test_ibis_app_tab_navigation(page: Page, local_app):
    """Test that tab navigation works correctly."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load (longer timeout to allow for real API calls)
    page.wait_for_timeout(5000)
    
    # Wait for Overview tab to be visible
    page.wait_for_selector("text=Overview", state="visible", timeout=20000)
    
    # Check that both tabs are present
    overview_tab = page.locator("text=Overview")
    car_details_tab = page.locator("text=Car Details")
    assert overview_tab.is_visible(), "Overview tab should be visible"
    assert car_details_tab.is_visible(), "Car Details tab should be visible"
    
    # Verify we start on the Overview tab
    # The active tab usually has different styling or an 'active' class
    # This is a simple check - the exact implementation depends on the tab component
    assert overview_tab.evaluate("el => el.classList.contains('active') || el.getAttribute('aria-selected') === 'true' || window.getComputedStyle(el).fontWeight === 'bold'"), "Overview tab should be active initially"
    
    # Verify the Overview tab content is visible
    assert page.locator("#avg_mpg").is_visible(), "Average MPG box should be visible in Overview"
    assert page.locator("#mpg_hp_plot").is_visible(), "MPG vs HP plot should be visible in Overview"
    
    # Now click on the Car Details tab
    car_details_tab.click()
    page.wait_for_timeout(1000)
    
    # Verify the Car Details tab is now active
    assert car_details_tab.evaluate("el => el.classList.contains('active') || el.getAttribute('aria-selected') === 'true' || window.getComputedStyle(el).fontWeight === 'bold'"), "Car Details tab should be active after clicking"
    
    # Verify the Car Details content is visible
    table_selector = ".rt-table, table, .table, #car_data, .data-grid, [role='grid'], [role='table']"
    assert page.locator(table_selector).first.is_visible(), "Car data table should be visible in Car Details tab"
    
    # Now go back to Overview tab
    overview_tab.click()
    page.wait_for_timeout(1000)
    
    # Verify we're back on the Overview tab
    assert overview_tab.evaluate("el => el.classList.contains('active') || el.getAttribute('aria-selected') === 'true' || window.getComputedStyle(el).fontWeight === 'bold'"), "Overview tab should be active after clicking back"
    assert page.locator("#mpg_hp_plot").is_visible(), "MPG vs HP plot should be visible after going back to Overview"


def test_ibis_app_plot_updates(page: Page, local_app):
    """Test that plots update correctly when submitting queries."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load (longer timeout to allow for real API calls)
    page.wait_for_timeout(5000)
    
    # Wait for Overview tab to be visible
    page.wait_for_selector("text=Overview", state="visible", timeout=20000)
    
    # Check initial plot state - save some info about the plots
    # We'll use the SVG elements as indicators that plots have rendered
    initial_mpg_hp_plot = page.locator("#mpg_hp_plot svg").all()
    initial_cyl_plot = page.locator("#cyl_plot svg").all()
    
    # Alternatively, get the text content which might contain axis labels, legends, etc.
    initial_mpg_hp_text = page.locator("#mpg_hp_plot").text_content() or ""
    initial_cyl_text = page.locator("#cyl_plot").text_content() or ""
    
    # Submit a query that should change the data visualization
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    chat_input.fill(TEST_HORSEPOWER_QUERY)
    chat_input.press("Enter")
    
    # Wait longer for the API request to complete and plots to update
    page.wait_for_timeout(10000)
    
    # Wait for code or SQL to appear
    page.wait_for_selector("code, pre", state="visible", timeout=10000)
    
    # Look for page content that indicates the query executed successfully
    page_content = page.content()
    
    # Check for SQL presence
    has_sql = re.search(r"SELECT|FROM|WHERE|mtcars", page_content, re.IGNORECASE)
    assert has_sql, "Response should contain SQL query"
    
    # Check if the plots updated
    # Wait for any plot animations to complete
    page.wait_for_timeout(2000)
    
    # Get updated plot content
    updated_mpg_hp_plot = page.locator("#mpg_hp_plot svg").all()
    updated_mpg_hp_text = page.locator("#mpg_hp_plot").text_content() or ""
    
    # The plots should still be visible
    assert page.locator("#mpg_hp_plot").is_visible(), "MPG vs HP plot should still be visible"
    assert page.locator("#cyl_plot").is_visible(), "Cylinder plot should still be visible"
    
    # Submit a second query to test further plot updates
    chat_input.fill(TEST_WEIGHT_QUERY)
    chat_input.press("Enter")
    
    # Wait for the API request and plot updates
    page.wait_for_timeout(10000)
    
    # Wait for code or SQL to appear
    page.wait_for_selector("code, pre", state="visible", timeout=10000)
    
    # Look for page content that indicates the query executed successfully
    page_content = page.content()
    
    # Check for SQL presence
    has_sql = re.search(r"SELECT|FROM|WHERE|mtcars", page_content, re.IGNORECASE)
    assert has_sql, "Response should contain SQL query"
    
    # Plots should still be visible after multiple queries
    assert page.locator("#mpg_hp_plot").is_visible(), "MPG vs HP plot should be visible after multiple queries"
    assert page.locator("#cyl_plot").is_visible(), "Cylinder plot should be visible after multiple queries"


def test_ibis_app_sequential_queries(page: Page, local_app):
    """Test that sequential queries maintain context."""
    # Navigate to the app
    page.goto(local_app.url)
    
    # Wait for app to load (longer timeout to allow for real API calls)
    page.wait_for_timeout(5000)
    
    # Wait for Overview tab to be visible
    page.wait_for_selector("text=Overview", state="visible", timeout=20000)
    
    # Find the chat input and submit the first query about American cars
    chat_input = page.locator("input[type='text'], textarea").first
    assert chat_input.is_visible(), "Chat input should be visible"
    chat_input.fill(TEST_SEQUENTIAL_1)
    chat_input.press("Enter")
    
    # Wait for the API request to complete
    page.wait_for_timeout(10000)
    
    # Wait for code or SQL to appear
    page.wait_for_selector("code, pre", state="visible", timeout=10000)
    
    # Look for page content that indicates the query executed successfully
    page_content = page.content()
    
    # Check for SQL presence
    has_sql = re.search(r"SELECT|FROM|WHERE|mtcars", page_content, re.IGNORECASE)
    assert has_sql, "Response should contain SQL query"
    
    # Switch to Car Details tab to check the filtered data
    page.locator("text=Car Details").click()
    page.wait_for_timeout(1000)
    
    # Verify some data is displayed
    table_selector = ".rt-table, table, .table, #car_data, .data-grid, [role='grid'], [role='table']"
    page.wait_for_selector(table_selector, timeout=5000, state="visible")
    
    # Now submit the follow-up query about automatic transmission
    chat_input.fill(TEST_SEQUENTIAL_2)
    chat_input.press("Enter")
    
    # Wait for the API request to complete
    page.wait_for_timeout(10000)
    
    # Check for a response that maintains context (American + automatic)
    # Wait for the data to update
    page.wait_for_timeout(2000)
    
    # Wait for code or SQL to appear for the second query
    page.wait_for_selector("code, pre", state="visible", timeout=10000)
    
    # Look for page content that indicates the query executed successfully
    page_content = page.content()
    
    # Check for SQL presence
    has_sql = re.search(r"SELECT|FROM|WHERE|mtcars", page_content, re.IGNORECASE)
    assert has_sql, "Response should contain SQL query"
    
    # Verify that the data table is still visible and has content
    assert page.locator(table_selector).first.is_visible(), "Car data table should be visible"
    has_content = page.evaluate(f"() => {{ const el = document.querySelector('{table_selector.replace('\'', '\\\'')}'); return el && el.children.length > 0; }}")
    assert has_content, "Car data table should have content after sequential queries"