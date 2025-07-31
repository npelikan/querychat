from pathlib import Path

import chatlas
import querychat as qc
from seaborn import load_dataset
from shiny import App, render, ui

titanic = load_dataset("titanic")

greeting = Path(__file__).parent / "greeting.md"
data_desc = Path(__file__).parent / "data_description.md"

# 1. Configure querychat

def use_google_models(system_prompt: str) -> chatlas.Chat:
    # Use Google's Gemini models
    # You may want to change this to use your preferred model
    return chatlas.ChatGoogle(
        model="gemini-2.5-flash-lite",
        system_prompt=system_prompt,
    )

querychat_config = qc.init(
    titanic,
    "titanic",
    greeting=greeting,
    data_description=data_desc,
    create_chat_callback=use_google_models,
)

# Create UI
app_ui = ui.page_sidebar(
    # 2. Place the chat component in the sidebar
    qc.sidebar("chat"),
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
    chat = qc.server("chat", querychat_config)

    # 4. Display the filtered dataframe
    @render.data_frame
    def data_table():
        # Access filtered data via chat.df() reactive
        return chat.df()


# Create Shiny app
app = App(app_ui, server)
