# AI Agent & Developer Guidelines

This document outlines the architecture, coding conventions, and operational details for maintaining and supporting the `index.html` application.

## Development Workflow

*   **Deep Planning Mode**: Before starting any task, ensure requirements are fully understood through iterative questioning using `request_user_input` or `message_user` before setting a plan.

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
    *   **Head**: Loads Tailwind CSS (via static `styles.css`), Plotly.js, and Pyodide.js. Defines custom styles for the slider.
    *   **Body**: UI layout.
    *   **Script**:
        *   `workerCode` (String): Contains the Python script and Web Worker logic.
        *   `initChart`, `requestForecast`, `updateChartWithForecast`: Main thread UI logic.
        *   `alignSlider`: Critical function to visually sync the HTML slider with the Plotly x-axis.

2.  **Styles**:
    *   **Static CSS**: There is no active Tailwind build system. `styles.css` is a static file containing pre-generated Tailwind utilities.
    *   **Adding Styles**: Missing utility classes must be manually added to `styles.css` when needed. Do not expect them to be generated automatically.

3.  **Python Script (embedded in `workerCode`)**:
    *   **Pyodide Loading**: The app uses a custom Pyodide distribution. Instead of `loadPackage`, it fetches and manually unpacks a `packages.tgz` archive containing the required dependencies (`pandas`, `statsmodels`, etc.).
    *   **Execution**: Complex model execution logic is offloaded to the Web Worker.
    *   **Status Updates**: Real-time status updates are implemented by importing the `js` module and calling `js.updateStatus` to post messages to the main thread.

## Operational & Support Instructions

### 1. Modifying the Python Logic
The Python code is stored as a template string (`workerCode`) within the JavaScript.
*   **Context**: Code runs inside the Pyodide environment in a Web Worker.
*   **Packages**: Only packages included in the `custom-pyodide/packages.tgz` can be used.
*   **Data Fetching**: Data is fetched directly from the CDC URL (`https://www.cdc.gov/wcms/vizdata/NCEZID_DIDRI/sc2/nwsssc2regionalactivitylevelDL.csv`).
*   **Data Processing**:
    *   **Indices**: Input data must have a unique datetime index with an inferred frequency; duplicate dates must be filtered out.
    *   **Sanitization**: `NaN` and `Infinity` values in Python **must** be converted to `None` before returning to JS, as browsers do not accept `NaN` in JSON.
*   **Forecasting Model**:
    *   **Exponential Smoothing**: The model requires at least 104 data points (two full seasonal cycles of 52 weeks) to initialize successfully using the heuristic method.
    *   **Simulation**: When calculating confidence intervals from simulations, `np.nanpercentile` must be used to ignore `NaN` values.
    *   **Clamping**: The forecast upper 50% confidence interval (75th percentile) is explicitly clamped at a maximum value of 30 to prevent y-axis distortion.

### 2. Frontend & Visualization
*   **Plotly**: The chart is rendered in the `#chart` div.
    *   **Legend**: Positioned at the top (`y: 1.1`, `orientation: 'h'`) to save vertical space.
    *   **Margins**: Explicitly set (`margin: { t: 0, ... }`) to handle layout shifts.
*   **Slider Alignment**: The custom range slider overlaying the chart relies on `alignSlider()`. This function maps the slider's start/end dates to pixels using `xaxis.c2p()`.
    *   **Dynamic Styling**: The slider's `marginLeft` and `width` are dynamically calculated based on the slider's `min` index.
    *   **Trigger**: Must be called after `Plotly.react`, on window resize, and on Plotly relayout events (zoom/pan).
*   **UI Updates**:
    *   **Async/Await**: Chart update functions should use the `async/await` pattern combined with `try...finally` blocks to ensure UI states (such as loading overlays) are reliably reset.
    *   **Loading Indicators**: Overlays on charts are preferred to be positioned near the top of the chart area (e.g., using `items-start` and top padding).
    *   **Tailwind Visibility**: When toggling visibility using `flex`, the `flex` class must be explicitly removed when adding `hidden`, and re-added when removing `hidden`.

### 3. Custom Pyodide Distribution
The application relies on a pre-built custom Pyodide distribution to optimize loading.
*   **Location**: `custom-pyodide/` directory.
*   **Build Process**: To update dependencies, you must rebuild the distribution. Follow the instructions in `README.md` which involve cloning Pyodide, building recipes, and using `make_preload.py`. The script `make_preload.py` bundles Python dependencies by staging files in `_stage_pkgs` and produces the final artifact at `custom-pyodide/packages.tgz`.

### 4. Testing & Verification
*   **Frontend Verification**: UI changes should be verified using Playwright scripts.
*   **Wait Times**: Pyodide initialization involves downloading ~20MB+ of WASM/Python data. Tests (e.g., Playwright) must use extended timeouts (60s+) to verify graph updates.
*   **UI State**: Verify loading overlays appear/disappear correctly. Use `try...finally` in async functions to ensure UI reset.
*   **Visuals**: Check that the slider aligns perfectly with the graph's x-axis.

### 5. Common Issues / Troubleshooting
*   **CORS Errors**: If data fetching fails, ensure the CDC URL allows CORS or that the app is being accessed via a proxy/correctly configured server. Note: The app fetches directly from CDC.
*   **"Port already in use"**: If running a local server (e.g., `python -m http.server`), ensure the port is free.
*   **Model Errors**: `statsmodels` is sensitive to data gaps or duplicate dates. The `get_data` function includes logic to drop duplicates and set the index frequency. Maintain this rigor.

### 6. Deployment
*   The app is a static site. Ensure `index.html`, `styles.css`, `loading.gif`, and the `custom-pyodide/` directory are present.
*   No backend is required.

## Constraints
*   **Single File**: Keep logic within `index.html` unless explicitly instructed to refactor.
*   **Root Directory**: Main files must stay at the repo root.
