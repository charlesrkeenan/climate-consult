from flask import session
from fhirclient import client
from fhirclient.models.condition import Condition
from fhirclient.models.bundle import Bundle
import os
import urllib.parse
from dash import dash_table
import json

# SMART on FHIR configuration
app_settings = {
    'app_id': os.getenv('APP_ID'),
    'app_secret': os.getenv('APP_SECRET'),
    'api_base': os.getenv('API_BASE'),
    'redirect_uri': os.getenv('REDIRECT_URI'),
    'scope': os.getenv('SCOPE')
}
def save_state(state):
    session['state'] = state

def reset():
    if 'state' in session:
        del session['state']

# Function to get FHIR client
def get_smart():
    state = session.get('state')
    if state:
        return client.FHIRClient(state=state, save_func=save_state)
    else:
        return client.FHIRClient(settings=app_settings, save_func=save_state)

def generate_clinical_details_table(conditions, encounters, medication_administrations):
    """
    A function for processing a list of FHIR resource objects and arranging
    them in a Dash table. Conditions are processed first, then Encounters, then
    Medication Administrations.
    """
    # Define the list to store condition details
    health_conditions_list = []

    # Iterate through each condition and collect the necessary details
    for condition in conditions:
        condition_name = ''
        condition_json = condition.as_json() if callable(condition.as_json) else condition
        condition = json.loads(condition_json) if isinstance(condition_json, str) else condition_json

        if 'code' in condition and condition['code']:
            code = condition['code']
            if 'text' in code:
                condition_name = code['text']
            elif 'coding' in code:
                for coding in code['coding']:
                    if 'display' in coding:
                        condition_name = coding['display']
                        break

        clinical_status = 'Unknown'
        if 'clinicalStatus' in condition and condition['clinicalStatus']:
            clinical_status = condition['clinicalStatus']['coding'][0]['code'] if condition['clinicalStatus']['coding'] else 'Unknown'

        verification_status = 'Unknown'
        if 'verificationStatus' in condition and condition['verificationStatus']:
            verification_status = condition['verificationStatus']['coding'][0]['code'] if condition['verificationStatus']['coding'] else 'Unknown'

        health_conditions_list.append({
            'condition_name': condition_name,
            'clinical_status': clinical_status,
            'verification_status': verification_status,
        })

    # Sort conditions by status
    health_conditions_list.sort(key=lambda x: x['clinical_status'])

    # Create Conditions Dash table
    conditions_table = dash_table.DataTable(
        id='conditions-table',
        columns=[
            {'name': 'Condition Name', 'id': 'condition_name'},
            {'name': 'Clinical Status', 'id': 'clinical_status'},
            {'name': 'Verification Status', 'id': 'verification_status'},
        ],
        data=health_conditions_list,
        sort_action='native',
        style_header={
            'color': 'black',
            'font-family': 'Montserrat',
            'padding': '5px',
            'border': '1px solid grey',
        },
        style_cell={
            'textAlign': 'left',
            'color': 'black',
            'border': '1px solid grey',
            'font-family': 'Montserrat',
            'padding': '5px'
        },
        style_as_list_view=True
    )

    # Define the list to store Encounter details
    encounters_list = []

    # Iterate through each encounter and collect the necessary details
    for encounter in encounters:
        encounter_description = ''
        encounter_json = encounter.as_json() if callable(encounter.as_json) else encounter
        encounter = json.loads(encounter_json) if isinstance(encounter_json, str) else encounter_json

        if 'serviceType' in encounter and encounter['serviceType']:
            service_type = encounter['serviceType']
            if 'text' in service_type:
                encounter_description = service_type['text']
            elif 'coding' in service_type:
                for coding in service_type['coding']:
                    if 'display' in coding:
                        encounter_description = coding['display']
                        break
        elif 'type' in encounter and encounter['type']:
            for codeable_concept in encounter['type']:
                if 'text' in codeable_concept:
                    encounter_description = codeable_concept['text']
                elif 'coding' in codeable_concept:
                    for coding in codeable_concept['coding']:
                        if 'display' in coding:
                            encounter_description = coding['display']
                            break
        elif 'class' in encounter and encounter['class']:
            encounter_class = encounter['class']
            if 'display' in encounter_class:
                encounter_description = encounter_class['display']
        else:
            raise Exception("An Encounter resource has no human-readable element to serve as a description")

        encounter_status = encounter.get('status', 'Unknown')
        encounters_list.append({
            'encounter_description': encounter_description,
            'encounter_status': encounter_status,
        })

    # Sort encounters by status
    encounters_list.sort(key=lambda x: x['encounter_status'])

    # Create Encounters Dash table
    encounters_table = dash_table.DataTable(
        id='encounters-table',
        columns=[
            {'name': 'Encounter Description', 'id': 'encounter_description'},
            {'name': 'Encounter Status', 'id': 'encounter_status'},
        ],
        data=encounters_list,
        sort_action='native',
        style_header={
            'color': 'black',
            'font-family': 'Montserrat',
            'padding': '5px',
            'border': '1px solid grey',
        },
        style_cell={
            'textAlign': 'left',
            'color': 'black',
            'border': '1px solid grey',
            'font-family': 'Montserrat',
            'padding': '5px'
        },
        style_as_list_view=True
    )

    # Define the list to store medication administration details
    medication_administrations_list = []

    # Iterate through each medication administration and collect the necessary details
    for medication_administration in medication_administrations:
        medication_administration_name = ''
        medication_json = medication_administration.as_json() if callable(medication_administration.as_json) else medication_administration
        medication_administration = json.loads(medication_json) if isinstance(medication_json, str) else medication_json

        if 'medicationCodeableConcept' in medication_administration and medication_administration['medicationCodeableConcept']:
            med_codeable_concept = medication_administration['medicationCodeableConcept']
            if 'text' in med_codeable_concept:
                medication_administration_name = med_codeable_concept['text']
            elif 'coding' in med_codeable_concept:
                for coding in med_codeable_concept['coding']:
                    if 'display' in coding:
                        medication_administration_name = coding['display']
                        break
        elif 'medicationReference' in medication_administration and medication_administration['medicationReference']:
            medication_administration_name = medication_administration['medicationReference'].get('display', '')
        else:
            raise Exception("A medication resource has no human-readable 'medication[x]' element")

        medication_administration_status = medication_administration.get('status', 'Unknown')

        medication_administrations_list.append({
            'medication_administration_name': medication_administration_name,
            'medication_administration_status': medication_administration_status,
        })

    # Sort medication administrations by status
    medication_administrations_list.sort(key=lambda x: x['medication_administration_status'])

    # Create Medication Administration Dash table
    medication_administrations_table = dash_table.DataTable(
        id='medications-table',
        columns=[
            {'name': 'Medication Administration Name', 'id': 'medication_administration_name'},
            {'name': 'Medication Administration Status', 'id': 'medication_administration_status'},
        ],
        data=medication_administrations_list,
        sort_action='native',
        style_header={
            'color': 'black',
            'font-family': 'Montserrat',
            'padding': '5px',
            'border': '1px solid grey',
        },
        style_cell={
            'textAlign': 'left',
            'color': 'black',
            'border': '1px solid grey',
            'font-family': 'Montserrat',
            'padding': '5px'
        },
        style_as_list_view=True
    )

    return conditions_table, encounters_table, medication_administrations_table

def generate_prompt(sex, date_of_birth, health_conditions, encounters, medication_administrations, current_dt, combined_environmental_data):
    return f""""
    -------------------------------
    Prompt Context

    You have been approached by a healthcare professional seeking consultation on how to mitigate the health risks or treat the health complications 
    associated with climate-related events, such as heat waves or forest fires. Your role as the AI specialist is to provide a consultation based on 
    the specific characteristics and surrounding environment of the patient, like their demographics, health conditions, medications, encounter history, AQI, 
    temperature, and apparent temperature.
    -------------------------------
    Patient Details

    Sex: {sex}
    Date of Birth: {date_of_birth}
    Health Conditions: {health_conditions}
    Encounters: {encounters}
    Medication Administrations: {medication_administrations}

    Here is the past, present, and forecasted environmental data (in a tabular format) for the patient's primary address. Its columns include time, 
    air quality index measurements (AQI), temperature (Fahrenheit), and apparent temperature (Fahrenheit). Right now, The current datetime is {current_dt}.
    Please note that the AQI data and temperature data may not perfectly overlap in time, as they are collected from different sources. NaN values at the 
    beginning and end of the time range should not be considered as missing data, but rather as the absence of data.
    
    {combined_environmental_data}

    -------------------------------
    """

def generate_iframe(address):
    url_escaped_address = urllib.parse.quote(address, safe='') # URL escape the address for embedding a Maps iFrame
    return f"https://www.google.com/maps/embed/v1/place?key={os.getenv('GOOGLE_MAPS_API_KEY')}&q={url_escaped_address}&zoom=11&maptype=satellite"

def get_patient_demographics(patient):
    # Selecting the official name or first available name
    name = None
    for name in patient.name:
        # Check if the name has the "official" use code
        if "official" in name.use:
            firstNames = " ".join(name.given)
            name = name.text if name.text is not None else firstNames + " " + name.family
            break  # If found, no need to check further
    # if no "official" name found, use the first one available
    if not name:
        firstNames = " ".join(patient.name[0].given)
        name = patient.name[0].text if patient.name[0].text is not None else firstNames + " " + patient.name[0].family

    # Sex (called gender in FHIR R4)
    sex = patient.gender if patient.gender else "Unknown"

    # Birthday
    birthday = patient.birthDate.isostring if patient.birthDate else "Unknown"
    """
    # Identifier
    identifier = 'UNCONFIRMED' # Initialize the identifier value as unconfirmed
    for identifierObj in patient.identifier:
        if identifierObj.type:
            for coding in identifierObj.type.coding:
                if coding.system == fhir_identifier_configuration.get('identifier.type.coding.system') and coding.code == fhir_identifier_configuration.get('identifier.type.coding.code'):
                    identifier = identifierObj.value
                    break
    """
    # Address
    if len(patient.address) == 1:
        address = patient.address[0]
        if address.text:
            address = address.text
        else:
            # If 'text' property isn't present or is empty, concatenate address fields
            lines = address.line if hasattr(address, 'line') else []
            city = address.city if (address, 'city') else ''
            district = address.district if (address, 'district') else ''
            state = address.state if (address, 'state') else ''
            postal_code = address.postalCode if (address, 'postalCode') else ''
            country = address.country if (address, 'country') else ''
            address = ', '.join(filter(None, [', '.join(lines), city, district, state, postal_code, country]))
    elif len(patient.address) > 1:
        raise Exception("Multiple addresses detected!")
    """
    latest_address = None
    latest_period_end = None

    for address in addresses:
        if address.use in ['home']: # selecting only home addresses
            # Parse period end date, if present
            period_end = None
            if 'period' in address and 'end' in address.period:
                period_end = datetime.fromisoformat(address.period.end[:-1])  # Remove 'Z' if present
            elif 'period' in address and 'start' in address.period:
                period_end = datetime.fromisoformat(address.period.start[:-1])  # Use start if end is not present

            # Check if this address has the latest period end date
            if latest_address is None or (period_end and (latest_period_end is None or period_end > latest_period_end)):
                latest_address = address
                latest_period_end = period_end

    if latest_address:
        # If 'text' property isn't present or is empty, concatenate address fields
        if not latest_address.text:
            lines = latest_address.line if 'line' in latest_address else []
            city = latest_address.city if 'city' in latest_address else ''
            district = latest_address.district if 'district' in latest_address else ''
            state = latest_address.state if 'state' in latest_address else ''
            postal_code = latest_address.postalCode if 'postalCode' in latest_address else ''
            country = latest_address.country if 'country' in latest_address else ''

            full_address = ', '.join(filter(None, [', '.join(lines), city, district, state, postal_code, country]))
            latest_address.text = full_address

    return latest_address
    """
    return (name, sex, birthday, address)

def fetch_all_resources(resource_class, smart):
    resources = []
    next_url = resource_class.where(struct={'patient': smart.patient_id}).perform(smart.server)
    
    while next_url:
        if next_url.entry:
            resources.extend(entry.resource for entry in next_url.entry)
        
        next_link = next((link.url for link in next_url.link if link.relation == 'next'), None)
        next_url = Bundle.read_from(next_link, smart.server) if next_link else None

    return resources
