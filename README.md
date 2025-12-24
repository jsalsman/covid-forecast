# COVID-19 Forecast Tool

This is a Flask application that provides a forecast of COVID-19 wastewater data.

## Features

*   **Data Retrieval:** Downloads the latest COVID-19 wastewater data from the CDC.
*   **API:**
    *   `/api/data`: Returns the historical wastewater data.
    *   `/api/forecast`: Generates a 52-week forecast using the Holt-Winters method. You can optionally provide a `cutoff_date` in the request body to train the model on a subset of the data.
*   **Frontend:** A simple frontend to visualize the data and forecast.

## How to Run

1.  **Install dependencies:**
    ```bash
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Run the development server:**
    ```bash
    ./devserver.sh
    ```

This will start the Flask development server, and you can access the application in your browser.
