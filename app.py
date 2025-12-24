import os
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, render_template
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import requests
from io import StringIO
from datetime import datetime, timedelta

app = Flask(__name__)

DATA_URL = "https://www.cdc.gov/wcms/vizdata/NCEZID_DIDRI/sc2/nwsssc2regionalactivitylevelDL.csv"
LOCAL_FILE = "covid_data.csv"

def get_data():
    should_download = False
    if not os.path.exists(LOCAL_FILE):
        should_download = True
    else:
        file_mod_time = os.path.getmtime(LOCAL_FILE)
        if (datetime.now() - datetime.fromtimestamp(file_mod_time)) > timedelta(weeks=1):
            should_download = True
            
    if should_download:
        print("Downloading data...")
        response = requests.get(DATA_URL)
        if response.status_code == 200:
            with open(LOCAL_FILE, 'wb') as f:
                f.write(response.content)
        else:
            raise Exception("Failed to download data")
    
    df = pd.read_csv(LOCAL_FILE)
    # Clean data
    df['Week_Ending_Date'] = pd.to_datetime(df['Week_Ending_Date'])
    df = df.sort_values('Week_Ending_Date')
    
    # We only care about National_WVAL and Week_Ending_Date
    df = df[['Week_Ending_Date', 'National_WVAL']].dropna()

    # Drop duplicates to ensure unique index
    df = df.drop_duplicates(subset=['Week_Ending_Date'])

    df = df.set_index('Week_Ending_Date')
    
    # Set frequency to Weekly (Week Ending Saturday seems to be the pattern based on data, but let's just infer)
    # Actually, statsmodels likes explicit frequency.
    # The diffs were 7 days.
    try:
        df.index.freq = pd.infer_freq(df.index)
    except:
        pass # Fallback

    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def api_data():
    df = get_data()
    data = []
    for date, row in df.iterrows():
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'value': row['National_WVAL']
        })
    return jsonify(data)

@app.route('/api/forecast', methods=['POST'])
def api_forecast():
    req_data = request.json
    cutoff_date_str = req_data.get('cutoff_date')
    
    df = get_data()
    
    if cutoff_date_str:
        cutoff_date = pd.to_datetime(cutoff_date_str)
        train_df = df[df.index <= cutoff_date]
    else:
        train_df = df

    if len(train_df) < 52 * 2: 
        # Fallback if not enough data for 52 week seasonality? 
        # Holt-Winters needs enough data points. 
        # But let's assume we have enough.
        pass

    # Model
    # Explicitly setting frequency if possible, or letting statsmodels infer
    # The data is weekly.
    try:
        model = ExponentialSmoothing(
            train_df['National_WVAL'],
            seasonal_periods=52,
            trend='add',
            seasonal='add',
            damped_trend=True, # Often good for long horizons
            use_boxcox=True, # Wastewater data is often non-negative and can benefit from transformation
            initialization_method="estimated"
        )
        model_fit = model.fit()
    except Exception as e:
        # Fallback parameters if the above fails
        model = ExponentialSmoothing(
            train_df['National_WVAL'],
            seasonal_periods=52,
            trend='add',
            seasonal='add'
        )
        model_fit = model.fit()

    # Forecast
    forecast_steps = 52
    forecast = model_fit.forecast(forecast_steps)
    
    # Confidence Intervals via Simulation
    # We simulate multiple paths to get the distribution
    n_simulations = 500
    simulations = np.zeros((forecast_steps, n_simulations))
    
    for i in range(n_simulations):
        # simulate() returns a series
        sim = model_fit.simulate(forecast_steps, anchor='end')
        simulations[:, i] = sim.values

    # Calculate percentiles for 50% CI (25th to 75th percentile)
    lower_bound = np.percentile(simulations, 25, axis=1)
    upper_bound = np.percentile(simulations, 75, axis=1)
    
    # Prepare response
    forecast_data = []
    # Get the last date of training data
    last_date = train_df.index[-1]
    
    for i in range(forecast_steps):
        # Weekly steps
        next_date = last_date + pd.Timedelta(weeks=i+1)
        forecast_data.append({
            'date': next_date.strftime('%Y-%m-%d'),
            'forecast': float(forecast.iloc[i]),
            'lower': float(lower_bound[i]),
            'upper': float(upper_bound[i])
        })
        
    return jsonify({
        'forecast': forecast_data,
        'cutoff_date': train_df.index[-1].strftime('%Y-%m-%d')
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
