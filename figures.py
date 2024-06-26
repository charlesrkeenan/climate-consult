import plotly.graph_objects as go
import requests
import os
import json
from datetime import timedelta, datetime
import pandas as pd

def generate_aqi_figure(current_dt, latitude, longitude):
    # retrieve AQI history, current conditions, and forecast, then generate figure and return results
    aqi_results = {}
    for time in ['forecast', 'currentConditions', 'history']:
        url = f'https://airquality.googleapis.com/v1/{time}:lookup?key={os.getenv('GOOGLE_MAPS_API_KEY')}'
        match time:
            case 'history': # Retrieve historical AQI
                data = {
                        "hours": 720,
                        "pageSize": 720,
                        "location": {
                            "latitude": latitude,
                            "longitude": longitude
                        }
                    }
                while True: # A while loop to handle pagination
                    response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))
                    for hourly_result in response.json()['hoursInfo']:
                        if 'dateTime' in hourly_result and 'indexes' in hourly_result: aqi_results.update({hourly_result['dateTime']: hourly_result['indexes'][0]['aqi']})
                    if 'nextPageToken' in response.json():
                        data.update({'pageToken': response.json()['nextPageToken']})
                    else:
                        break
            case 'currentConditions': # Retrieve current AQI
                data = {
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude
                    }
                }
                response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))
                aqi_results.update({response.json()['dateTime']: response.json()['indexes'][0]['aqi']})
            case 'forecast': # Retrieve forecasted AQI
                data = {
                    "universalAqi": "true",
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "period": {
                        "startTime": (current_dt + timedelta(hours=1)).strftime(format='%Y-%m-%dT%H:%M:%SZ'),
                        "endTime": (current_dt + timedelta(hours=96)).strftime(format='%Y-%m-%dT%H:%M:%SZ')
                    },
                }
                while True: # A while loop to handle pagination
                    response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))
                    for hourly_forecast in response.json()['hourlyForecasts']:
                        aqi_results.update({hourly_forecast['dateTime']: hourly_forecast['indexes'][0]['aqi']})
                    if 'nextPageToken' in response.json():
                        data.update({'pageToken': response.json()['nextPageToken']})
                    else:
                        break
    # Create figure object
    figure = go.Figure()

    # Create the AQI line graph traces
    figure.add_trace(go.Scatter(
        showlegend=False,
        name = "History",
        x=[dt for dt in aqi_results.keys() if dt <= current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ')],
        y=[aqi_results[dt] for dt in aqi_results.keys() if dt <= current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ')],
        mode='lines',
        line=dict(width=2, color='black')
    ))
    figure.add_trace(go.Scatter(
        showlegend=False,
        name = "Forecast",
        x=[dt for dt in aqi_results.keys() if dt >= current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ')],
        y=[aqi_results[dt] for dt in aqi_results.keys() if dt >= current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ')],
        mode='lines',
        line=dict(dash='dot', width=2, color='black')
    ))

    # Add the AQI range shapes
    aqi_ranges = [
    {"range": [300, 500], "color": "maroon", "air pollution level": "Hazardous"},
    {"range": [200, 300], "color": "purple", "air pollution level": "Very Unhealthy"},
    {"range": [150, 200], "color": "red", "air pollution level": "Unhealthy"},
    {"range": [100, 150], "color": "orange", "air pollution level": "Unhealthy for Sensitive Groups"},
    {"range": [50, 100], "color": "yellow", "air pollution level": "Moderate"},
    {"range": [0, 50], "color": "green", "air pollution level": "Good"}
    ]

    # Add shapes for each AQI range
    for aqi_range in aqi_ranges:
        figure.add_hrect(
            showlegend=True,
            name=aqi_range["air pollution level"],
            layer= 'below',
            line_width = 0,
            y0 = aqi_range["range"][0],
            y1 = aqi_range["range"][1],
            fillcolor= aqi_range["color"],
            opacity= 0.66
        )

    # Add the "NOW" indicator
    figure.add_shape(
        type = "line",
        x0 = current_dt,
        x1 = current_dt,
        y0 = 0,
        y1 = 500,
        line = dict(
            color = "#2f2f2d",
            width = 3, 
        ), 
        label = dict(
            text = "TODAY",
            textangle = 0,
            xanchor = "left",
            yanchor = "middle",
            padding = 5,
            font=dict(
                size=13,
                color="black",
                family='Montserrat'
            ),
        ),
    )

    # Update X and Y axis
    figure.update_xaxes(
        zeroline = False,
        minor = dict(
            dtick = 86400000.0,
            ticks = "inside",
            ticklen = 5,
            tickcolor = "black",
        )
    )
    figure.update_yaxes(
        zeroline = False,
    )

    # Update figure layout
    figure.update_layout(
        xaxis=dict(tickformat='%B %-e', type = "date"),
        yaxis = dict(
            tickmode = "array",
            tickvals = [0, 50, 100, 150, 200, 300, 500],
            tick0 = 0,
        ),
        showlegend=True,
        legend=dict(
            itemclick=False,
            itemdoubleclick=False,
        ),
        legend_font=dict(
                family='Montserrat',
                size=13
        ),
        font=dict(
                size=13,
                color="black",
                family='Montserrat'
        ),
        title_font=dict(
            size=17,
            color='black',
            weight='bold',
            family='Montserrat'
        ),
        hovermode = "x",
        plot_bgcolor = 'white',
        paper_bgcolor = '#F1F1F1',
        margin=dict(l=70, r=70, t=0, b=42),
    )

    aqi_df = pd.DataFrame(list(aqi_results.items()), columns=['time', 'aqi'])
    
    return figure, aqi_df

def generate_weather_figure(latitude, longitude):

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "apparent_temperature"],
        "hourly": ["temperature_2m", "apparent_temperature"],
        "temperature_unit": "fahrenheit",
        "past_days": 29,
        "forecast_days": 5
    }

    response = requests.get(url, params=params)
    response = json.loads(response.content)

    # Extract current data
    current_data = {
        "time": [response["current"]["time"]],
        "temperature_2m": [response["current"]["temperature_2m"]],
        "apparent_temperature": [response["current"]["apparent_temperature"]]
    }

    # Extract hourly data
    hourly_data = {
        "time": response["hourly"]["time"],
        "temperature_2m": response["hourly"]["temperature_2m"],
        "apparent_temperature": response["hourly"]["apparent_temperature"]
    }

    # Combine current data and hourly data
    combined_data = {
        "time": current_data["time"] + hourly_data["time"],
        "temperature_2m": current_data["temperature_2m"] + hourly_data["temperature_2m"],
        "apparent_temperature": current_data["apparent_temperature"] + hourly_data["apparent_temperature"]
    }

    # Create DataFrame
    weather_df = pd.DataFrame(combined_data)

    # Convert time to datetime for consistent formatting
    weather_df["time"] = weather_df["time"].apply(lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M').strftime('%Y-%m-%dT%H:%M:%SZ'))
    # Sort by time
    weather_df = weather_df.sort_values(by="time").reset_index(drop=True)

    current_time = response["current"]["time"]
    # Convert the datetime string to the desired format '%Y-%m-%dT%H:%M:%SZ'
    current_time = datetime.strptime(current_time, '%Y-%m-%dT%H:%M').strftime('%Y-%m-%dT%H:%M:%SZ')

    # Identify the top and bottom of the temperature range before plotting
    max_temperature = max(max(weather_df['temperature_2m']), max(weather_df['apparent_temperature']))
    min_temperature = min(min(weather_df['temperature_2m']), min(weather_df['apparent_temperature']))

    # Split the data into historical and forecast
    history_mask = weather_df['time'] <= current_time
    forecast_mask = weather_df['time'] >= current_time

    # Create the Dash Plotly figure
    figure = go.Figure()

    # Temperature history
    figure.add_trace(go.Scatter(
        showlegend=True,
        name="Temperature History",
        x=weather_df[history_mask]['time'],
        y=weather_df[history_mask]['temperature_2m'],
        mode='lines',
        line=dict(width=2, color='black')
    ))

    # Temperature forecast
    figure.add_trace(go.Scatter(
        showlegend=True,
        name="Temperature Forecast",
        x=weather_df[forecast_mask]['time'],
        y=weather_df[forecast_mask]['temperature_2m'],
        mode='lines',
        line=dict(dash='dot', width=2, color='black')
    ))

    # Apparent temperature history
    figure.add_trace(go.Scatter(
        showlegend=True,
        name='"Feels like" History',
        x=weather_df[history_mask]['time'],
        y=weather_df[history_mask]['apparent_temperature'],
        mode='lines',
        line=dict(width=2, color='red')
    ))

    # Apparent temperature forecast
    figure.add_trace(go.Scatter(
        showlegend=True,
        name='"Feels like" Forecast',
        x=weather_df[forecast_mask]['time'],
        y=weather_df[forecast_mask]['apparent_temperature'],
        mode='lines',
        line=dict(dash='dot', width=2, color='red')
    ))

# Add the "NOW" indicator
    figure.add_shape(
        type = "line",
        x0 = current_time,
        x1 = current_time,
        y0 = min_temperature,
        y1 = max_temperature,
        line = dict(
            color = "#2f2f2d",
            width = 3, 
        ), 
        label = dict(
            text = "TODAY",
            textangle = 0,
            xanchor = "left",
            yanchor = "middle",
            padding = 5,
            font=dict(
                size=13,
                color="black",
                family='Montserrat'
            ),
        ),
    )

    # Update X and Y axis
    figure.update_xaxes(
        zeroline = False,
        minor = dict(
            dtick = 86400000.0,
            ticks = "inside",
            ticklen = 5,
            tickcolor = "black",
        )
    )
    figure.update_yaxes(
        zeroline = False,
        range=[min_temperature, max_temperature],
        tickmode='auto',
        ticks='outside',
        ticklen=5,
        tickcolor='black',
    )

    # Update figure layout
    figure.update_layout(
        xaxis=dict(tickformat='%B %-e', type = "date"),
        showlegend=True,
        legend=dict(
            itemclick=False,
            itemdoubleclick=False,
        ),
        legend_font=dict(
                family='Montserrat',
                size=13
        ),
        font=dict(
                size=13,
                color="black",
                family='Montserrat'
        ),
        title_font=dict(
            size=17,
            color='black',
            weight='bold',
            family='Montserrat'
        ),
        hovermode = "x",
        plot_bgcolor = '#F1F1F1',
        paper_bgcolor = '#F1F1F1',
        margin=dict(l=70, r=70, t=0, b=42),
    )
    
    return figure, weather_df