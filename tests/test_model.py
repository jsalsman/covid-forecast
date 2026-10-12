"""Exercise the actual embedded Python; optional statsmodels checks are dev-only."""
import csv
import io
import json
from pathlib import Path
import random
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_model():
    js = types.ModuleType('js')
    js.updateStatus = lambda message: None
    js.baseUrl = 'https://example.test/'
    http = types.ModuleType('pyodide.http')
    http.open_url = lambda url: None
    modules = {'js': js, 'pyodide': types.ModuleType('pyodide'), 'pyodide.http': http}
    old = {name: sys.modules.get(name) for name in modules}
    sys.modules.update(modules)
    try:
        source = (ROOT / 'index.html').read_text().split('const pythonScript = \\`\n', 1)[1].split('\\`;', 1)[0]
        namespace = {}
        exec(source, namespace)
        return namespace
    finally:
        for name, module in old.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.model = load_model()

    def historical(self, dtype):
        with (ROOT / ('historical_' + dtype + '.csv')).open() as file:
            return self.model['clean_rows'](csv.DictReader(file))

    def test_cleaning_and_live_precedence(self):
        rows = [{'Week_Ending_Date': '2024-01-06', 'National_WVAL': '1'},
                {'Week_End': '2024-01-06T00:00:00Z', 'National_WVAL': '2'},
                {'Week_End': '2024-01-13', 'National_WVAL': 'NaN'},
                {'Week_End': 'invalid', 'National_WVAL': '4'},
                {'Week_End': '2024-01-20', 'National_WVAL': 'Infinity'}]
        result = self.model['clean_rows'](rows)
        self.assertEqual(self.model['prepare_js_data'](result), [{'date': '2024-01-06', 'value': 2.0}])

    def test_fetch_cache_and_pathogens(self):
        calls = []
        live = [{'Week_End': '2024-01-06', 'National_WVAL': '2', 'Pathogen_Target': 'SARS-CoV-2'},
                {'Week_End': '2024-01-06', 'National_WVAL': '3', 'Pathogen_Target': 'Influenza A virus'}]
        def fetch(url):
            calls.append(url)
            return io.StringIO(json.dumps(live) if url.endswith('.json') else
                               'Week_Ending_Date,National_WVAL\n2024-01-06,1\n')
        self.model['open_url'] = fetch
        self.assertEqual(self.model['get_data']('covid')[0]['value'], 2)
        self.assertEqual(self.model['get_data']('flu')[0]['value'], 3)
        self.assertEqual(len(calls), 3)
        self.assertIn('error', self.model['get_data']('unknown'))

    def test_percentile_and_boxcox_domain(self):
        self.assertEqual(self.model['percentile']([None, float('nan'), 1, 2, 3, 4], 25), 1.75)
        self.assertIsNone(self.model['percentile']([None], 25))
        self.assertIsNone(self.model['inverse_boxcox'](-2, 1))
        with self.assertRaises(ValueError):
            self.model['boxcox_values']([0, 1])

    def test_constant_series_forecasts_preserve_level(self):
        for level in (0.5, 1.0, 5.0):
            for count in (104, 156):
                for perturbation in (0.0, level * 1e-13):
                    with self.subTest(level=level, count=count, perturbation=perturbation):
                        values = [level + (perturbation if i % 2 else 0.0) for i in range(count)]
                        transformed, lam = self.model['boxcox_values'](values)
                        self.assertEqual(lam, 1.0)
                        for original, value in zip(values, transformed):
                            self.assertAlmostEqual(self.model['inverse_boxcox'](value, lam), original, places=12)
                        model = self.model['fit_model'](values)
                        forecast = self.model['model_path'](model, count)
                        simulation = self.model['model_path'](model, count, rng=random.Random(0))
                        for value in forecast + simulation:
                            self.assertIsNotNone(value)
                            self.assertAlmostEqual(value, level, places=10)

    def test_cutoffs_and_forecast_contract(self):
        for dtype in ('covid', 'flu'):
            rows = self.historical(dtype)
            self.model['current_df'] = rows
            self.model['current_dataset_type'] = dtype
            for count in (0, 103, 104, len(rows)):
                with self.subTest(dataset=dtype, count=count):
                    cutoff = '1900-01-01' if count == 0 else rows[count-1][0].isoformat()
                    result = self.model['run_forecast'](cutoff)
                    self.assertNotIn('error', result)
                    self.assertEqual(len(result['forecast']), 52 if count >= 104 else 0)
                    json.dumps(result, allow_nan=False)
                    if count >= 104:
                        self.assertTrue(any(item['forecast'] is not None for item in result['forecast']))
                        self.assertTrue(any(item['lower'] is not None and item['upper'] is not None
                                            for item in result['forecast']))
                        if dtype == 'covid':
                            self.assertTrue(all(item['upper'] is None or item['upper'] <= 30 for item in result['forecast']))

    def test_intervals_for_both_datasets_and_covid_only_cap(self):
        self.model['current_df'] = self.historical('flu')[:104]
        self.model['fit_model'] = lambda values: None
        for dtype, expected_upper in (('covid', 30), ('flu', 40)):
            with self.subTest(dataset=dtype):
                simulation_count = 0
                def paths(model, count, rng=None):
                    nonlocal simulation_count
                    if rng is None:
                        return [32.0] * 52
                    simulation_count += 1
                    return [20.0 if simulation_count % 2 else 40.0] * 52
                self.model['model_path'] = paths
                self.model['current_dataset_type'] = dtype
                result = self.model['run_forecast'](None)
                self.assertNotIn('error', result)
                self.assertEqual(len(result['forecast']), 52)
                self.assertEqual(simulation_count, 20)  # Stable quartiles converge at the second check.
                for item in result['forecast']:
                    self.assertEqual(item['forecast'], 32)
                    self.assertEqual(item['lower'], 20)
                    self.assertEqual(item['upper'], expected_upper)

    def test_reference_equations(self):
        try:
            import numpy as np
            from scipy.stats import boxcox
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            from statsmodels.tsa.exponential_smoothing.initialization import _initialization_heuristic
        except ImportError:
            self.skipTest('Optional NumPy/SciPy/statsmodels reference packages are not installed')
        values = [value for _, value in self.historical('covid')]
        y, lam = self.model['boxcox_values'](values)
        reference, reference_lam = boxcox(values)
        self.assertAlmostEqual(lam, reference_lam, places=5)
        np.testing.assert_allclose(y, reference, rtol=1e-5)
        state = self.model['initial_state'](y)
        level, slope, seasons = _initialization_heuristic(np.array(y), trend='add', seasonal='add', seasonal_periods=52)
        np.testing.assert_allclose(state, [level, slope, *seasons], atol=1e-10)
        params = [.4, .2, .3, .97, *state]
        _, level, slope, seasons, errors = self.model['smooth'](y, params)
        fit = ExponentialSmoothing(values, trend='add', seasonal='add', seasonal_periods=52,
            damped_trend=True, use_boxcox=lam, initialization_method='known',
            initial_level=state[0], initial_trend=state[1], initial_seasonal=state[2:]).fit(
                smoothing_level=.4, smoothing_trend=.08, smoothing_seasonal=.18,
                damping_trend=.97, optimized=False)
        np.testing.assert_allclose([level, slope], [fit.level[-1], fit.trend[-1]], atol=1e-9)
        model = (params, level, slope, seasons, 1.0, lam)
        # statsmodels 0.15 uses a stale seasonal state at the week-52 point boundary.
        np.testing.assert_allclose(self.model['model_path'](model, len(values))[:51], fit.forecast(52)[:51], atol=1e-8)
        class FixedErrors:
            def gauss(self, mean, sigma):
                return .03
        np.testing.assert_allclose(self.model['model_path'](model, len(values), rng=FixedErrors()),
            fit.simulate(52, anchor='end', random_errors=np.full((52, 1), .03)), atol=1e-8)


if __name__ == '__main__':
    unittest.main()
