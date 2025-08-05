"""
Example of using QueryChat with ibis integration on the mtcars dataset

This example shows how to:
1. Set up a basic QueryChat app with the mtcars dataset
2. Use SQLite as the database backend
3. Use the to_ibis method to create an ibis table from the current query

Requirements:
- pip install querychat[ibis]
- pip install ibis-sqlite pandas plotly
"""

from pathlib import Path
from shiny import App, reactive, render, ui
import chatlas
import ibis
import pandas as pd
import querychat
import plotly.express as px
from shinywidgets import output_widget, render_widget
import tempfile
import sqlite3
from sqlalchemy import create_engine
import os

# Load the mtcars dataset
data = pd.read_csv('https://gist.githubusercontent.com/ZeccaLehn/4e06d2575eb9589dbe8c365d61cb056c/raw/64f1660f38ef523b2a1a13be77b002b98665cdfe/mtcars.csv')
data.rename(columns={'Unnamed: 0': 'car_name'}, inplace=True)  # Rename the index column

# Set up SQLite database in memory
db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
conn = sqlite3.connect(db_file)
data.to_sql('mtcars', conn, if_exists='replace', index=False)
conn.close()

# Create SQLAlchemy engine for QueryChat
engine = create_engine(f"sqlite:///{db_file}")

# Create ibis connection for SQLite
ibis_conn = ibis.sqlite.connect(db_file)

# Load greeting and data description from markdown files
greeting = Path(__file__).parent / "greeting.md"
data_desc = Path(__file__).parent / "data_description.md"

# Create UI
app_ui = ui.page_sidebar(
    querychat.sidebar("chat"),
    ui.navset_tab(
        ui.nav_panel(
            "Overview",
            ui.layout_column_wrap(
                ui.value_box(
                    "Average MPG",
                    ui.output_text("avg_mpg"),
                    showcase=ui.HTML(
                        '<i class="fa fa-gas-pump" style="font-size: 40px;"></i>'
                    ),
                    theme="primary",
                ),
                ui.value_box(
                    "Average Horsepower",
                    ui.output_text("avg_hp"),
                    showcase=ui.HTML(
                        '<i class="fa fa-tachometer-alt" style="font-size: 40px;"></i>'
                    ),
                    theme="secondary",
                ),
                ui.value_box(
                    "Cars in Dataset",
                    ui.output_text("car_count"),
                    showcase=ui.HTML(
                        '<i class="fa fa-car" style="font-size: 40px;"></i>'
                    ),
                    theme="success",
                ),
                width=1/3,
            ),
            ui.layout_column_wrap(
                ui.card(
                    ui.card_header("MPG vs Horsepower"),
                    output_widget("mpg_hp_plot"),
                ),
                ui.card(
                    ui.card_header("Cylinder Distribution"),
                    output_widget("cyl_plot"),
                ),
                width=1/2,
            ),
        ),
        ui.nav_panel(
            "Car Details",
            ui.card(
                ui.card_header("Car Data"), 
                ui.output_data_frame("car_data")
            ),
        ),
    ),
)

def server(input, output, session):
    # Function to create chat model
    def use_google_models(system_prompt: str) -> chatlas.Chat:
        # Use Google's Gemini models
        return chatlas.ChatGoogle(
            model="gemini-2.5-flash-lite",
            system_prompt=system_prompt,
        )
        
    # Initialize QueryChat
    querychat_config = querychat.init(
        engine,
        table_name="mtcars",
        greeting=greeting,
        data_description=data_desc,
        create_chat_callback=use_google_models,
    )
    
    # Initialize querychat server object
    chat = querychat.server("chat", querychat_config)
    
    # Get Ibis table reference
    @reactive.Calc
    def car_table():
        return chat.to_ibis(ibis_conn)
    
    # Overview tab outputs
    @output
    @render.text
    def avg_mpg():
        # Use Ibis to calculate average MPG
        table = car_table()
        avg = table["mpg"].mean().to_pandas()
        return f"{avg:.1f}"
    
    @output
    @render.text
    def avg_hp():
        # Use Ibis to calculate average horsepower
        table = car_table()
        avg = table["hp"].mean().to_pandas()
        return f"{avg:.0f}"
    
    @output
    @render.text
    def car_count():
        # Use Ibis to count cars
        table = car_table()
        count = table.count().to_pandas()
        return f"{count}"
    
    @output
    @render_widget
    def mpg_hp_plot():
        # Create scatter plot of MPG vs Horsepower
        table = car_table()
        data = table.select(["car_name", "mpg", "hp", "cyl"]).to_pandas()
        
        fig = px.scatter(
            data, 
            x="hp", 
            y="mpg", 
            color="cyl", 
            hover_name="car_name",
            labels={"hp": "Horsepower", "mpg": "Miles Per Gallon", "cyl": "Cylinders"},
            template="simple_white"
        )
        return fig
    
    @output
    @render_widget
    def cyl_plot():
        # Create bar chart of cylinder distribution
        table = car_table()
        cyl_counts = (
            table.group_by("cyl")
            .aggregate(count=table.count())
            .to_pandas()
        )
        
        fig = px.bar(
            cyl_counts, 
            x="cyl", 
            y="count", 
            labels={"cyl": "Cylinders", "count": "Number of Cars"},
            template="simple_white"
        )
        return fig
    
    @output
    @render.data_frame
    def car_data():
        # Show the filtered car data
        table = car_table()
        car_df = table.to_pandas()
        return render.DataGrid(car_df)

app = App(app_ui, server)