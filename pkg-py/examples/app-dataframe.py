from pathlib import Path

from seaborn import load_dataset
from shiny import App, render, ui

import querychat

titanic = load_dataset("titanic")

greeting = (Path(__file__).parent / "greeting.md").read_text()
data_desc = (Path(__file__).parent / "data_description.md").read_text()

# 1. Configure querychat
querychat_config = querychat.init(
    titanic,
    "titanic",
    greeting=greeting,
    data_description=data_desc,
)

# Create UI
app_ui = ui.page_sidebar(
    # 2. Place the chat component in the sidebar
    querychat.sidebar("chat"),
    # Main panel with data viewer
    ui.card(
        ui.output_data_frame("data_table"),
        fill=True,
    ),
    title="querychat with Python",
    fillable=True,
)


# Define server logic
def server(input, output, session):
    # 3. Initialize querychat server with the config from step 1
    chat = querychat.server("chat", querychat_config)

    # 4. Display the filtered dataframe
    @render.data_frame
    def data_table():
        # Access filtered data via chat.df() reactive
        return chat.df()


# Create Shiny app
app = App(app_ui, server)
