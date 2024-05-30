# Dash page - /visualization
import dash
from dash import html, dcc, callback, Input, Output, get_app
from dash.exceptions import PreventUpdate
from utils import get_smart, retrieve_address_string, generate_iframe, generate_prompt, retrieve_health_conditions_list
from fhirclient.models.patient import Patient
from fhirclient.models.condition import Condition
import concurrent.futures
import googlemaps
import requests
import json
from datetime import datetime, timezone, timedelta
import os
import google.generativeai as genai


dash.register_page(__name__, path='/visualization')
app = get_app()

layout = html.Div(id='page-content', children=[
    dcc.Location(id='url')
])

@callback(
    Output('page-content', 'children'),
    Input('url', 'href')
)
def handle_callback(href):
    smart = get_smart()
    # Retrieve Patient resource and patient's Condition resources. Use ThreadPoolExecutor to run the tasks concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks to the executor
        patient_future = executor.submit(lambda: Patient.read(rem_id=smart.patient_id, server=smart.server))
        conditions_future = executor.submit(lambda: Condition.where(struct={'patient': smart.patient_id}).perform_resources(smart.server)) 
        # Retrieve the results
        patient = patient_future.result()
        conditions = conditions_future.result()

    if not (hasattr(patient, 'address') and len(patient.address) != 0):
        raise PreventUpdate("No address found for the patient.")
    try:
        address = retrieve_address_string(patient.address)
        app.logger.debug(f'Address:\n{address}')
    except Exception as e:
        app.logger.error(f"An error occurred while parsing the patient's address: {e}")
        raise PreventUpdate("Something went wrong processing the patient's address")
    
    # Need to implement exception handling here
    health_conditions_list = retrieve_health_conditions_list(conditions)
    
    # Retrieve latitude + longitude of patient's address / embeddable google maps iFrame
    gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
    # Geocoding an address
    geocode_result = gmaps.geocode(address)
    latitude = geocode_result[0]['geometry']['location']['lat']
    print(latitude)
    longitude = geocode_result[0]['geometry']['location']['lng']
    print(longitude)
    # Get iFrame
    maps_iframe = generate_iframe(address)

    # retrieve AQI history, current conditions, and forecast. PLOT ON VIZ IN THIS CODE.
    aqi_results = {}
    current_dt = datetime.now(timezone.utc)
    print(f"Current datetime: {current_dt}")
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
    # Sort the AQI results in ascending order
    sorted_aqi_results = dict(sorted(aqi_results.items()))

    # Ask google gemini to make a recommendation for the patient, given their age, sex, conditions, and AQI forecast. Gemini needs to be prompted with AQI background.
    genai.configure(api_key=os.getenv('GOOGLE_GEMINI_API_KEY'))
    model = genai.GenerativeModel(os.getenv('GOOGLE_GEMINI_MODEL'))
    gemini_response = model.generate_content(
        patient.sex,
        patient.birthDate,
        conditions,
        current_dt,
        sorted_aqi_results
    )
    print(gemini_response.text) # When designing the UI, you should convert this response to markdown. See documentation.

    # Render the patient's details, detected address, and AQI viz