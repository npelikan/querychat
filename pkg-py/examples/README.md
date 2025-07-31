# QueryChat Examples

This directory contains examples of how to use QueryChat in various scenarios.

## Available Examples

### Basic Example
A simple example of using QueryChat with a pandas DataFrame.

```bash
cd basic
pip install -r requirements.txt
shiny run app.py
```

### Pandas Example
An example showing how to use QueryChat with a pandas DataFrame with additional customization.

```bash
cd pandas
pip install -r requirements.txt
shiny run app.py
```

### SQLite Example
An example of using QueryChat with a SQLite database.

```bash
cd sqlite
pip install -r requirements.txt
shiny run app.py
```

### ibis with mtcars Example
A more advanced example showing how to integrate QueryChat with the ibis library for enhanced data processing using the mtcars dataset.

```bash
cd ibis-mtcars
pip install -r requirements.txt
shiny run app.py
```

## Example Structure

Each example is organized into its own directory with the following files:
- `app.py`: The main application file
- `requirements.txt`: Dependencies needed to run the example
- `greeting.md` and `data_description.md`: Configuration files for QueryChat
- `README.md`: Documentation specific to the example (for some examples)