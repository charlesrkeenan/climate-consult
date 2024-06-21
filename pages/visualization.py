# Dash page - /visualization
import dash
from dash import html, dcc, callback, Input, Output, get_app
from dash.exceptions import PreventUpdate
from utils import get_smart, generate_iframe, generate_prompt, generate_clinical_details_table, get_patient_demographics, fetch_all_resources
from figure import generate_figure
from fhirclient.models.patient import Patient
from fhirclient.models.condition import Condition
from fhirclient.models.medicationadministration import MedicationAdministration
import googlemaps
import requests
import json
import pandas as pd
from datetime import datetime, timezone, timedelta
import os
import google.generativeai as genai

# TO DO: message casper/sheazin, temperature data, rebrand as "Climate Consult", video submission?
# https://open-meteo.com/en/docs#current=temperature_2m&past_days=31

dash.register_page(__name__, path='/visualization')
app = get_app()

# Define the layout
layout = html.Div(id='appcontainer', children=[
    dcc.Location(id='url'),
    dcc.Loading(parent_className='loading-div', type='cube', color = '#ff8000', fullscreen=True, children=[
        html.Div(id='header', children="🔥 SMOKE SPECIALIST"),
        html.Div(id='consultation-row', children=[
            html.Div(className='left-column', children=[
                dcc.Markdown(id='patient-details'),
                html.Div(id='clinical-details-div', children=[
                    dcc.Tabs(id='clinical-details-table', children=[
                        dcc.Tab(id='conditions', label="Conditions"),
                        dcc.Tab(id='medications', label="Medication Administrations")
                    ]),
                ]),
            ]),
            html.Div(className='right-column', children=[
                html.H3(children="⚠️ WARNING: This consultation has been generated by AI. A qualified human healthcare professional must review and validate these findings before taking any clinical action."),
                dcc.Markdown(id='gemini-response')
            ])
        ]),
        html.Div(id='aqi-row', children=[
            html.Div(id='location-div', children=[
                    html.H3(id='address'),
                    html.Iframe(id='map-iframe', referrerPolicy="no-referrer-when-downgrade")
                ]),
            dcc.Graph(id='aqi-graph')
        ]),
    ])
])

@callback(
    Output('patient-details', 'children'),
    Output('conditions', 'children'),
    Output('medications', 'children'),
    Output('address', 'children'),
    Output('map-iframe', 'src'),
    Output('gemini-response', 'children'),
    Output('aqi-graph', 'figure'),
    Input('url', 'href')
)
def handle_callback(href):
    smart = get_smart()
    # Retrieve Patient, Condition, and Medication Administration resources
    patient = Patient.read(rem_id=smart.patient_id, server=smart.server)
    conditions = fetch_all_resources(Condition, smart)
    medication_administrations = fetch_all_resources(MedicationAdministration, smart)
    # Check if address is not null
    if not (hasattr(patient, 'address') and len(patient.address) != 0):
        raise PreventUpdate("No address found for the patient.")
    # Get patient demographics
    try:
        name, sex, birthday, address = get_patient_demographics(patient)
        app.logger.debug(f'Patient demographics:\n{name, sex, birthday, address}')
    except Exception as e:
        app.logger.error("An error occurred while parsing the patient's demographics", exc_info=True)
        raise PreventUpdate("Something went wrong processing the patient's demographics")
    # generate tables
    try:
        conditions_table, medication_administrations_table = generate_clinical_details_table(conditions, medication_administrations)
        # Convert conditions and medications to JSON serializable list
        conditions = [condition.as_json() for condition in conditions]
        medication_administrations = [medication_administration.as_json() for medication_administration in medication_administrations]
    except Exception as e:
        app.logger.error("An error occurred while parsing the patient's Condition or Medication Administration resources", exc_info=True)
        raise PreventUpdate("Something went wrong processing the patient's health conditions or medication administrations")

    # Retrieve latitude + longitude of patient's address / retrieve embeddable google maps iFrame
    gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
    # Geocoding an address
    geocode_result = gmaps.geocode(address)
    latitude = geocode_result[0]['geometry']['location']['lat']
    longitude = geocode_result[0]['geometry']['location']['lng']
    # Get iFrame
    maps_iframe = generate_iframe(address)

    # retrieve AQI history, current conditions, and forecast, then generate figure
    aqi_results = {} # aqi_results = pd.DataFrame(columns=['Time', 'AQI'])
    current_dt = datetime.now(timezone.utc)
    app.logger.debug(f"Current datetime: {current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ')}")
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
    # sorted_aqi_results = dict(sorted(aqi_results.items()))
    # Generate figure
    figure = generate_figure(aqi_results, current_dt)

    # Ask google gemini to make a recommendation for the patient, given their age, sex, conditions, and AQI forecast. Gemini needs to be prompted with AQI background.
    genai.configure(api_key=os.getenv('GOOGLE_GEMINI_API_KEY'))
    model = genai.GenerativeModel(os.getenv('GOOGLE_GEMINI_MODEL'))
    prompt = generate_prompt(
        patient.gender,
        patient.birthDate.isostring,
        conditions,
        medication_administrations,
        current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ'),
        aqi_results
    )
    gemini_response = model.generate_content(prompt)

    # Render the patient's details, detected address, and AQI viz
    return (
        f"""
        
        ### 👤 {name}
        Identifier: **12345** | Date of Birth: **{birthday}** | Sex: **{sex}**""",
        conditions_table,
        medication_administrations_table,
        f"📍 {address}",
        maps_iframe,
        gemini_response.text,
        figure
    )