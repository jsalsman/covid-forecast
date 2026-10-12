# U.S. National COVID and Influenza Wastewater Forecast

This repository contains a purely client-side web application that forecasts National COVID-19 and Influenza A Wastewater Viral Activity Levels. It utilizes [Pyodide](https://pyodide.org/) to run a Python-based [Holt-Winters Exponential Smoothing](https://www.statsmodels.org/stable/generated/statsmodels.tsa.holtwinters.ExponentialSmoothing.html) model directly in the user's browser via WebAssembly, removing the need for a dedicated backend server.

## Overview

The application fetches the latest wastewater data from the CDC (for both [COVID-19 and Influenza A](https://www.cdc.gov/wcms/vizdata/NCEZID_DIDRI/NWSS_WVAL_metric/NWSSWVALRegionalActivityLevel.json)), processes it and generates forecasts using only Python’s standard library. Users can interactively select a "cut-off date" to simulate how the model would have performed at different points in the past (backtesting).

### Key Features
- **Client-Side Python:** Runs dependency-free Python in the browser; no pandas, NumPy, SciPy, or statsmodels downloads or imports.
- **Interactive Visualization:** Uses [Plotly.js](https://plotly.com/javascript/) for interactive charts.
- **Forecast Model:** Implements Holt-Winters Exponential Smoothing with 52-week seasonality and damped trend.
- **Confidence Intervals:** Calculates 50% confidence intervals using Monte Carlo simulations for both COVID-19 and Influenza A.
- **Responsive UI:** Built with [Tailwind CSS](https://tailwindcss.com/) for a clean, mobile-friendly interface.
- **Zero-Backend:** Hosted entirely as a static HTML file.

## How It Works

The entire application logic is contained within `index.html`.

1. **Initialization:**
   - The browser loads `index.html`.
   - A **Web Worker** is spawned to initialize the Pyodide environment without blocking the main UI thread.
   - Only the Pyodide runtime and Python standard library are loaded from `custom-pyodide`; no package archive is fetched or unpacked.

2. **Data Processing:**
   - The Python script fetches the JSON data from the CDC URL.
   - Data is cleaned: duplicates are removed, the index is set to `Week_Ending_Date` (from `Week_End`), and missing values are handled.

3. **Forecasting:**
   - When the user adjusts the date slider, a message is sent to the Web Worker.
   - The Python script splits the data based on the selected cut-off date.
   - A Box–Cox transformed, additive Holt–Winters model with damped trend is fitted to the training data. Smoothing coefficients and initial level, trend, and seasonal states are estimated with bounded Powell-style direction search.
   - A 52-week forecast is generated.
   - Up to 500 simulations are run to estimate the 25th and 75th percentiles (50% confidence interval for both datasets).
   - The COVID-19 upper bound is clamped at 30 (high activity level) for visualization purposes.

4. **Visualization:**
   - The forecast data is sent back to the main thread.
   - Plotly renders the historical data, the forecast line, and the confidence interval bands.
   - A custom slider is aligned with the x-axis of the chart to allow intuitive date selection.

## File Structure

- `index.html`: The core application file containing HTML, JavaScript (UI & Worker), and Python (Model).
- `styles.css`: Manually generated TailwindCSS subset plus override styles for the slider.
- `loading.gif`: A spinning indicator displayed during initialization.
- `custom-pyodide/`: Tailored Pyodide distribution files (see below.)
- `favicon.ico`: Tab icon.
- `README.md`: This documentation.
- `AGENTS.md`: Instructions for AI agents and developers.

## Usage

### Browser Compatibility

This Pyodide web app equires a modern browser with WebAssembly support (Chrome, Firefox, Safari, Edge). The browser downloads roughly 11 MB of WASM and standard-library data, plus the runtime JavaScript. The former 34 MB package archive is no longer needed.

### Running Locally

Since this application uses Web Workers and fetches external data, it must be served over HTTP(S) rather than opening the file directly (due to CORS and worker restrictions).

You can use Python's built-in HTTP server:

```bash
# Run a simple HTTP server on port 8000
python3 -m http.server 8000
```

Then navigate to `http://localhost:8000` in your web browser.

## Pre-built Custom Pyodide Distribution

The bundled runtime is served locally. The model and data processing use `csv`, `datetime`, `math`, `random`, and other standard-library modules. No third-party Python recipes are required.

To update an existing Pyodide build, run `python make_preload.py` from its build directory, with the runtime files in `dist/`. The script copies only the six runtime essentials into `custom-pyodide/` and removes any legacy `packages.tgz`. Serve that directory alongside `index.html`.

## Model compatibility and validation

The Python implementation follows statsmodels’ Box–Cox maximum-likelihood transform, centered-moving-average initialization, additive seasonal smoothing, damped trend, and additive Gaussian-error simulations. It retains the 104-observation minimum, 52-week horizon, intervals for both datasets, NaN-ignoring percentiles, simulation convergence check, and COVID-only upper interval cap of 30. CSV and JSON values are cleaned into sorted date/value pairs; current CDC values win over historical values on duplicate dates.

Fitting uses bounded Powell-style direction search implemented in standard-library Python rather than SciPy’s optimizer, so fitted parameters and forecasts can differ. Simulations remain random. The final seasonal step uses the latest fitted seasonal state, including at week 52 (statsmodels 0.15’s point-forecast routine uses an older state at that boundary). These are model implementation changes, not a promise of identical forecasts.

Run the standard-library checks with:

```bash
python -m unittest discover -s tests
```

Optional numerical compatibility checks use locally installed NumPy, SciPy, and statsmodels; these are development-only dependencies and are never loaded by the application. Browser verification should serve the app over HTTP and check both datasets, slider cutoffs, loading states, and the absence of requests for `packages.tgz`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
