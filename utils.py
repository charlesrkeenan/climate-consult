from flask import session
from fhirclient import client
from fhirclient.models.condition import Condition
import os
from datetime import datetime
import urllib.parse

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

def retrieve_address_string(addresses):
    # Check how many addresses are available
    if len(addresses) == 1:
        address = addresses[0]
        if address.text:
            return address.text
        else:
            print(address)
            # If 'text' property isn't present or is empty, concatenate address fields
            lines = address.line if hasattr(address, 'line') else []
            city = address.city if (address, 'city') else ''
            district = address.district if (address, 'district') else ''
            state = address.state if (address, 'state') else ''
            postal_code = address.postalCode if (address, 'postalCode') else ''
            country = address.country if (address, 'country') else ''
            full_address = ', '.join(filter(None, [', '.join(lines), city, district, state, postal_code, country]))
            return full_address
    elif len(addresses) > 1:
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
def retrieve_health_conditions_list(Condition):
    # Check modifier elements, then append the code (text or coding.display) to a list and return
    pass

def generate_prompt(sex, date_of_birth, health_conditions, current_dt, aqi_results):
    return f""""
    -------------------------------
    Prompt Context

    Imagine you're approached by healthcare professionals seeking guidance on how to mitigate the health risks associated with wildfire smoke exposure for their patients. 
    These patients may include individuals with respiratory conditions, cardiovascular diseases, or other health issues that can be exacerbated by poor air quality during 
    wildfires. Your role as the AI specialist is to provide a tailored consultation based on the specific needs and conditions of the patient. 
    Consider factors such as sex, age, existing health conditions, and the air quality conditions surrounding the patient's address.

    Your consultation should fulfill the following criteria:

    Understanding Patient Profiles: Gather information about each patient, including their medical history, age, pre-existing conditions, and any medications they may be taking.

    Assessment of Risk Factors: Assess the level of risk for each patient based on their individual profile and the severity of the wildfire smoke exposure in their area.

    Personalized Recommendations: Offer personalized recommendations to healthcare professionals, including advice on indoor air quality improvement, use of air purifiers, 
    proper ventilation techniques, medication adjustments, and lifestyle modifications to minimize exposure and mitigate health risks.

    Follow-up and Monitoring: Suggest follow-up measures for healthcare professionals to monitor patients' health status, adjust interventions as needed 
    and provide ongoing support during periods of heightened wildfire smoke exposure.

    Additional Considerations:

    Emphasize the importance of proactive measures to reduce exposure to wildfire smoke, especially for vulnerable populations.
    Provide evidence-based recommendations supported by scientific research and guidelines from relevant health authorities.
    Address any potential limitations or challenges in implementing recommended interventions, considering factors such as cost, accessibility, and patient compliance.
    -------------------------------
    Patient Details

    Sex: {sex}
    Date of Birth: {date_of_birth}
    Health Conditions: {health_conditions}

    Here are the past, present, and forecasted Air Quality Index measurements for the patient's primary address. It is a list of key-value pairs, 
    where the key is the datetime and the value is the AQI. Right now, The current datetime is {current_dt}.
    
    {aqi_results}

    Please generate a tailored consultation for this patient.
    -------------------------------

    """

def generate_iframe(address):
    url_escaped_address = urllib.parse.quote(address, safe='') # URL escape the address for embedding a Maps iFrame
    return f"""
    <iframe
        width="450"
        height="250"
        frameborder="0" style="border:0"
        referrerpolicy="no-referrer-when-downgrade"
        src="https://www.google.com/maps/embed/v1/place?key={os.getenv('GOOGLE_MAPS_API_KEY')}&q={url_escaped_address}"
        allowfullscreen>
    </iframe>
    """