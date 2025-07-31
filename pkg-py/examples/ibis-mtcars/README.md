# QueryChat with ibis and mtcars Dataset Example

This example demonstrates how to use QueryChat with the ibis integration to perform advanced data transformations. 

## Features

- Natural language querying of the mtcars dataset using QueryChat
- Integration with ibis for advanced data transformations
- Interactive visualizations with Plotly
- SQLite database backend

## Running the Example

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Shiny app:
```bash
shiny run app.py
```

## How it Works

This example:

1. Loads the mtcars dataset and stores it in a SQLite database
2. Sets up QueryChat to allow natural language queries against the data
3. Creates an ibis connection to the SQLite database
4. Uses the `to_ibis()` method to convert QueryChat queries into ibis tables
5. Performs additional transformations on the data using ibis operations
6. Visualizes the results using Plotly

## Key Components

- **QueryChat**: Handles natural language processing and SQL generation
- **ibis**: Provides a unified interface for data manipulation across different backends
- **SQLite**: Serves as the database backend for this example
- **Shiny**: Creates the interactive web interface

## Example Queries

Try asking questions like:

- "Which cars have the highest MPG?"
- "Show me cars with more than 6 cylinders"
- "What's the average MPG for cars with manual vs automatic transmission?"
- "Is there a relationship between weight and fuel efficiency?"