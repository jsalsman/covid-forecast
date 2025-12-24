# AI Agent & Developer Guidelines

This document outlines the architecture, coding conventions, and operational details for maintaining and supporting the `index.html` application.

## Architecture

The application is a **Single-Page Application (SPA)** contained primarily in `index.html`. It uses a **Web Worker** to run Python code via **Pyodide**, keeping the main UI thread responsive.

Since this application uses Web Workers and fetches external data, it must be served over HTTP(S) rather than opening the file directly (due to CORS and worker restrictions).

You can use Python's built-in HTTP server:

```bash
# Run a simple HTTP server on port 8000
python3 -m http.server 8000
```

Then navigate to `http://localhost:8000` in your web browser.

### Key Components

1.  **`index.html`**:
    *   **Head**: Loads Tailwind CSS, Plotly.js, and Pyodide.js from CDNs. Defines custom styles for the slider.
    *   **Body**: UI layout.
    *   **Script**:
        *   `workerCode` (String): Contains the Python script and Web Worker logic.
        *   `initChart`, `requestForecast`, `updateChartWithForecast`: Main thread UI logic.
        *   `alignSlider`: Critical function to visually sync the HTML slider with the Plotly x-axis.

2.  **Python Script (embedded in `workerCode`)**:
    *   `get_data()`: Fetches and cleans CDC data. **Critical**: Must ensure unique index and inferred frequency for `statsmodels`.
    *   `run_forecast(cutoff_date_str)`: Runs the Holt-Winters model. Handles model failures with a fallback configuration.
    *   **Data Serialization**: `clean_val` function handles `NaN`/`Infinity` -> `None` conversion for JSON safety.

## Operational & Support Instructions

### 1. Modifying the Python Logic
The Python code is stored as a template string (`workerCode`) within the JavaScript.
*   **Context**: Code runs inside the Pyodide environment in a Web Worker.
*   **Packages**: Only packages supported by Pyodide (installed via `micropip` or standard library) can be used. Currently uses `pandas`, `statsmodels`, `scipy`.
*   **Data Types**: Be careful with data types passed between Python and JS. `NaN` values in Python **must** be converted to `None` before returning to JS, or JSON serialization will fail.

### 2. Frontend & Visualization
*   **Plotly**: The chart is rendered in the `#chart` div.
    *   **Legend**: Positioned at the top (`y: 1.1`, `orientation: 'h'`) to save vertical space.
    *   **Margins**: Explicitly set (`margin: { t: 0, ... }`) to handle layout shifts.
*   **Slider Alignment**: The custom range slider overlaying the chart relies on `alignSlider()`. This function maps the slider's start/end dates to pixels using `xaxis.c2p()`.
    *   **Trigger**: Must be called after `Plotly.react`, on window resize, and on Plotly relayout events (zoom/pan).

### 3. Testing & Verification
*   **Wait Times**: Pyodide initialization involves downloading ~20MB+ of WASM/Python data. Tests (e.g., Playwright) must use extended timeouts (60s+).
*   **UI State**: Verify loading overlays appear/disappear correctly. Use `try...finally` in async functions to ensure UI reset.
*   **Visuals**: Check that the slider aligns perfectly with the graph's x-axis.

### 4. Common Issues / Troubleshooting
*   **CORS Errors**: If data fetching fails, ensure the CDC URL allows CORS or that the app is being accessed via a proxy/correctly configured server. Note: The app fetches directly from CDC.
*   **"Port already in use"**: If running a local server (e.g., `python -m http.server`), ensure the port is free.
*   **Model Errors**: `statsmodels` is sensitive to data gaps or duplicate dates. The `get_data` function includes logic to drop duplicates and set the index frequency. Maintain this rigor.

### 5. Deployment
*   The app is a static site. Ensure `index.html` and `loading.gif` are present.
*   No backend is required.

## Constraints
*   **Single File**: Keep logic within `index.html` unless explicitly instructed to refactor.
*   **Root Directory**: Main files must stay at the repo root.
