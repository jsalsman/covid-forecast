# National COVID Wastewater Forecast

This repository contains a purely client-side web application that forecasts National COVID-19 Wastewater Viral Activity Levels. It utilizes [Pyodide](https://pyodide.org/) to run a Python-based **Holt-Winters Exponential Smoothing** model directly in the user's browser via WebAssembly, removing the need for a dedicated backend server.

## Overview

The application fetches the latest wastewater data from the [CDC](https://www.cdc.gov/wcms/vizdata/NCEZID_DIDRI/sc2/nwsssc2regionalactivitylevelDL.csv), processes it using `pandas`, and generates forecasts using `statsmodels`. Users can interactively select a "cut-off date" to simulate how the model would have performed at different points in the past (backtesting).

### Key Features
- **Client-Side Python:** Runs full data science stack (`pandas`, `scipy`, `statsmodels`) in the browser.
- **Interactive Visualization:** Uses [Plotly.js](https://plotly.com/javascript/) for interactive charts.
- **Forecast Model:** Implements Holt-Winters Exponential Smoothing with 52-week seasonality and damped trend.
- **Confidence Intervals:** Calculates 50% confidence intervals using Monte Carlo simulations.
- **Responsive UI:** Built with [Tailwind CSS](https://tailwindcss.com/) for a clean, mobile-friendly interface.
- **Zero-Backend:** Hosted entirely as a static HTML file.

## How It Works

The entire application logic is contained within `index.html`.

1. **Initialization:**
   - The browser loads `index.html`.
   - A **Web Worker** is spawned to initialize the Pyodide environment without blocking the main UI thread.
   - Python packages (`pandas`, `statsmodels`, `scipy`) are downloaded and installed dynamically.

2. **Data Processing:**
   - The Python script fetches the CSV data from the CDC URL.
   - Data is cleaned: duplicates are removed, the index is set to `Week_Ending_Date`, and missing values are handled.
   - The frequency of the time series is inferred to satisfy `statsmodels` requirements.

3. **Forecasting:**
   - When the user adjusts the date slider, a message is sent to the Web Worker.
   - The Python script splits the data based on the selected cut-off date.
   - An `ExponentialSmoothing` model is fitted to the training data.
   - A 52-week forecast is generated.
   - 500 simulations are run to estimate the 25th and 75th percentiles (50% confidence interval).
   - The upper bound is clamped at 30 (high activity level) for visualization purposes.

4. **Visualization:**
   - The forecast data is sent back to the main thread.
   - Plotly renders the historical data, the forecast line, and the confidence interval bands.
   - A custom slider is aligned with the x-axis of the chart to allow intuitive date selection.

## Usage

### Running Locally

Since this application uses Web Workers and fetches external data, it must be served over HTTP(S) rather than opening the file directly (due to CORS and worker restrictions).

You can use Python's built-in HTTP server:

```bash
# Run a simple HTTP server on port 8000
python3 -m http.server 8000
```

Then navigate to `http://localhost:8000` in your web browser.

### Browser Compatibility

Requires a modern browser with WebAssembly support (Chrome, Firefox, Safari, Edge). The first load may take a few moments to download the Pyodide runtime and Python packages.

## File Structure

- `index.html`: The core application file containing HTML, CSS (Tailwind), JavaScript (UI & Worker), and Python (Model).
- `loading.gif`: A loading indicator displayed during initialization.
- `AGENTS.md`: Instructions for AI agents and developers.
- `README.md`: This documentation.
- `LICENSE`: MIT License.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
