# National COVID Wastewater Forecast

This repository contains a purely client-side web application that forecasts National COVID-19 Wastewater Viral Activity Levels. It utilizes [Pyodide](https://pyodide.org/) to run a Python-based [Holt-Winters Exponential Smoothing](https://www.statsmodels.org/stable/generated/statsmodels.tsa.holtwinters.ExponentialSmoothing.html) model directly in the user's browser via WebAssembly, removing the need for a dedicated backend server.

## Overview

The application fetches the latest wastewater data from the [CDC](https://www.cdc.gov/nwss/rv/COVID19-national-data.html)'s [.csv file](https://www.cdc.gov/wcms/vizdata/NCEZID_DIDRI/sc2/nwsssc2regionalactivitylevelDL.csv), processes it using `pandas`, and generates forecasts using `statsmodels`. Users can interactively select a "cut-off date" to simulate how the model would have performed at different points in the past (backtesting).

### Key Features
- **Client-Side Python:** Runs full data science stack (`pandas`, `statsmodels`, and all their dependencies) in the browser.
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
   - Python packages (the standard libraries, `pandas`, `statsmodels`, and all their dependencies) are downloaded and installed dynamically from the `custom-pyodide` files.

2. **Data Processing:**
   - The Python script fetches the CSV data from the CDC URL.
   - Data is cleaned: duplicates are removed, the index is set to `Week_Ending_Date`, and missing values are handled.

3. **Forecasting:**
   - When the user adjusts the date slider, a message is sent to the Web Worker.
   - The Python script splits the data based on the selected cut-off date.
   - An `ExponentialSmoothing` model is fitted to the training data.
   - A 52-week forecast is generated.
   - Up to 500 simulations are run to estimate the 25th and 75th percentiles (50% confidence interval).
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

Requires a modern browser with WebAssembly support (Chrome, Firefox, Safari, Edge). The first load may take a few minutes to download the Pyodide runtime and Python packages.

## File Structure

- `index.html`: The core application file containing HTML, JavaScript (UI & Worker), and Python (Model).
- `styles.css`: Manually generated TailwindCSS subset plus override styles for the slider.
- `loading.gif`: A loading indicator displayed during initialization.
- `favicon.ico`: Tab icon.
- `README.md`: This documentation.
- `AGENTS.md`: Instructions for AI agents and developers.
- `LICENSE`: MIT License.

## Building a Custom Pyodide Distribution

To improve loading time and avoid relying on external CDNs, we include a custom Pyodide distribution containing `pandas` and `statsmodels` and their dependencies. This allows us to load a single archive (`packages.tgz`) rather than downloading packages individually.

The custom distribution was built using the following commands and the [make_preload.py](make_preload.py) script:

```bash
git clone --recursive https://github.com/pyodide/pyodide
cp make_preload.py pyodide
cd pyodide
./run_docker
make
git clone https://github.com/pyodide/pyodide-recipes
pyodide build-recipes "pandas, statsmodels" --recipe-dir pyodide-recipes/packages --install
# That takes a little over an hour on a 2-core GitHub Codespace; so use 4 cores
python make_preload.py
exit
rm -rf ../custom-pyodide
cp -r custom-pyodide ..
cd ..
git add custom-pyodide
git commit -m "Update custom pyodide build"
git push
```

The `custom-pyodide` directory is then served alongside `index.html`.

## Ideas for the future

### Building a Custom Pyodide Distribution with a Memory Snapshot

To further improve loading time, we could include a memory snapshot in the distribution containing `pandas` and `statsmodels`. It would be built thusly, per https://pyodide.org/en/stable/development/building-from-sources.html#building-a-full-pyodide-distribution :

```
git clone --recursive https://github.com/pyodide/pyodide
cd pyodide
./run_docker
make
git clone https://github.com/pyodide/pyodide-recipes
pyodide build-recipes "pandas, statsmodels" --recipe-dir pyodide-recipes/packages --install
# That takes a little over an hour

cat > make_snapshot.mjs <<'EOF'
import fs from "node:fs";
import { loadPyodide } from "./dist/pyodide.mjs";

const pyodide = await loadPyodide({
  indexURL: "./dist/",
  _makeSnapshot: true,
});

// Put the expensive installs into the snapshot
await pyodide.loadPackage(["pandas", "statsmodels"]);
await pyodide.runPythonAsync("import pandas, statsmodels");

// API name varies by version
const snap =
  typeof pyodide.makeSnapshot === "function"
    ? pyodide.makeSnapshot()
    : pyodide.makeMemorySnapshot();

fs.writeFileSync("./dist/snapshot.bin", Buffer.from(snap));
EOF

node make_snapshot.mjs
```

Then serve the whole `dist` directory (minus the test files) at `/custom-pyodide/` in the Pages branch `jsport`, and use it like this:

```
<script src="custom-pyodide/pyodide.js"></script>
...
const pyodide = await loadPyodide({ indexURL: "custom-pyodide/" });
```

**HOWEVER, this is currently blocked by this issue:** https://github.com/pyodide/pyodide/issues/5195

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
