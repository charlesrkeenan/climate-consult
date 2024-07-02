# Dash page - /visualization
import dash
from dash import html, dcc, callback, Input, Output, get_app
from dash.exceptions import PreventUpdate
from utils import get_smart, generate_iframe, generate_prompt, generate_clinical_details_table, get_patient_demographics, fetch_all_resources
from figures import generate_aqi_figure, generate_weather_figure
from fhirclient.models.patient import Patient
from fhirclient.models.condition import Condition
from fhirclient.models.encounter import Encounter
from fhirclient.models.medicationadministration import MedicationAdministration
import googlemaps
from datetime import datetime, timezone
import os
import google.generativeai as genai
import pandas as pd

# TO DO: sign up for Kaiber AI, video/grant submission

dash.register_page(__name__, path='/visualization')
app = get_app()

# Define the layout
layout = html.Div(id='appcontainer', children=[
    dcc.Location(id='url'),
    dcc.Loading(parent_className='loading-div', type='cube', color = '#ff8000', fullscreen=True, children=[
        html.Div(id='header', children="🌎 CLIMATE CONSULT 🩺"),
        html.Div(id='consultation-row', children=[
            html.Div(className='left-column', children=[
                dcc.Markdown(id='patient-details'),
                html.Div(id='clinical-details-div', children=[
                    dcc.Tabs(id='clinical-details-table', children=[
                        dcc.Tab(id='conditions', label="Conditions", className='health-records-tab-label', selected_className='health-records-selected-tab-label'),
                        dcc.Tab(id='encounters', label="Encounters", className='health-records-tab-label', selected_className='health-records-selected-tab-label'),
                        dcc.Tab(id='medications', label="Medication Administrations", className='health-records-tab-label', selected_className='health-records-selected-tab-label')
                    ]),
                ]),
            ]),
            html.Div(className='right-column', children=[
                html.H3(children="⚠️ WARNING: This consultation has been generated by AI. A qualified human healthcare professional must review and validate these findings before taking any clinical action."),
                dcc.Markdown(id='gemini-response')
            ])
        ]),
        html.Div(id='environmental-data-row', children=[
            html.Div(id='location-div', children=[
                    html.H3(id='address'),
                    html.Iframe(id='map-iframe', referrerPolicy="no-referrer-when-downgrade")
                ]),
            dcc.Tabs(id='environmental-data-tabs', parent_className="environmental-data-tabs", content_className="figure-tab", children=[
                    dcc.Tab(id='aqi-tab', label="😶‍🌫️ Air Quality", className='environmental-data-tab-label', selected_className='environmental-data-selected-tab-label', children=[
                        dcc.Graph(id='aqi-graph')
                    ]),
                    dcc.Tab(id='temperature-tab', label="🌡️ Temperature", className='environmental-data-tab-label', selected_className='environmental-data-selected-tab-label', children=[
                        dcc.Graph(id='temperature-graph')
                    ]),
                ])
        ]),
    ])
])

@callback(
    Output('patient-details', 'children'),
    Output('conditions', 'children'),
    Output('encounters', 'children'),
    Output('medications', 'children'),
    Output('address', 'children'),
    Output('map-iframe', 'src'),
    Output('gemini-response', 'children'),
    Output('aqi-graph', 'figure'),
    Output('temperature-graph', 'figure'),
    Input('url', 'href')
)
def handle_callback(href):
    smart = get_smart()
    # Retrieve FHIR resources
    patient = Patient.read(rem_id=smart.patient_id, server=smart.server)
    conditions = fetch_all_resources(Condition, smart)
    medication_administrations = fetch_all_resources(MedicationAdministration, smart)
    encounters = fetch_all_resources(Encounter, smart)
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
    # Generate UI tables
    try:
        conditions_table, encounters_table, medication_administrations_table = generate_clinical_details_table(conditions, encounters, medication_administrations)
        # Convert FHIR resources retrieved to JSON serializable lists
        conditions = [condition.as_json() for condition in conditions]
        encounters = [encounter.as_json() for encounter in encounters]
        medication_administrations = [medication_administration.as_json() for medication_administration in medication_administrations]
    except Exception as e:
        app.logger.error("An error occurred while parsing the patient's FHIR resources", exc_info=True)
        raise PreventUpdate("Something went wrong processing the patient's health records")

    # Retrieve latitude + longitude of patient's address / retrieve embeddable google maps iFrame
    gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
    # Geocoding an address
    geocode_result = gmaps.geocode(address)
    latitude = geocode_result[0]['geometry']['location']['lat']
    longitude = geocode_result[0]['geometry']['location']['lng']
    # Get iFrame
    maps_iframe = generate_iframe(address)

    # Generate environmental data and figures
    current_dt = datetime.now(timezone.utc)
    aqi_figure, aqi_results = generate_aqi_figure(current_dt, latitude, longitude)
    weather_figure, weather_results = generate_weather_figure(latitude, longitude)
    combined_environmental_data = pd.merge(aqi_results, weather_results, on='time', how='outer')

    # Ask google gemini to make a recommendation for the patient, given their age, sex, health records, and AQI forecast.
    genai.configure(api_key=os.getenv('GOOGLE_GEMINI_API_KEY'))
    model = genai.GenerativeModel(os.getenv('GOOGLE_GEMINI_MODEL'))
    prompt = generate_prompt(
        patient.gender,
        patient.birthDate.isostring,
        conditions,
        encounters,
        medication_administrations,
        current_dt.strftime(format='%Y-%m-%dT%H:%M:%SZ'),
        combined_environmental_data
    )
    gemini_response = model.generate_content(prompt)

    # Render the patient's details, records, detected address, and AQI visualization
    return (
        f"""
        
        ### 👤 {name}
        Identifier: **12345** | Date of Birth: **{birthday}** | Sex: **{sex}**""",
        conditions_table,
        encounters_table,
        medication_administrations_table,
        f"📍 {address}",
        maps_iframe,
        gemini_response.text,
        aqi_figure,
        weather_figure
    )