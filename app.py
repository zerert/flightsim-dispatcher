import streamlit as st
import requests
from datetime import datetime, timedelta

# --- UI SETUP ---
st.set_page_config(page_title="FlightSim Dispatcher", page_icon="✈️")
st.title("✈️ FlightSim Dispatcher")
st.write("Find real-world flights departing right now for your simulator.")

# --- USER INPUTS (The Frontend) ---
col1, col2 = st.columns(2)
with col1:
    airport_code = st.text_input("Departure Airport (ICAO)", value="WSSS").upper()
with col2:
    hours_ahead = st.slider("Look ahead (Hours)", min_value=1, max_value=5, value=2)

# A Dictionary to translate UI codes into API search terms
fleet_translation = {
    "A318": "A318",
    "A319": "A319",
    "A320": "A320",
    "A321": "A321",
    "A332": "A330-200",
    "A333": "A330-300",
    "A339": "A330-900",
    "A343": "A340-300",
    "A346": "A340-600",
    "A359": "A350-900",
    "A35K": "A350-1000",
    "A388": "A380",
    "B737": "737-700",
    "B738": "737-800",
    "B739": "737-900",
    "B744": "747-400",
    "B748": "747-8",
    "B772": "777-200",
    "B772ER": "777-200ER",
    "B77F": "777F",
    "B773": "777-300",
    "B77W": "777-300ER",
    "B788": "787-8",
    "B789": "787-9",
    "B78X": "787-10",
}

# The dropdown now uses the keys (the ICAO codes) from our dictionary
selected_aircraft = st.multiselect( "Select Aircraft to Fly", list(fleet_translation.keys()), default=["A320", "B738", "B77W"])

# The "ttl=300" means this data is saved in memory for 300 seconds (5 minutes)
@st.cache_data(ttl=300)
def fetch_flight_data(url, _headers, querystring):
    response = requests.get(url, headers=_headers, params=querystring)
    if response.status_code == 200:
        return response.json(), 200
    else:
        return response.text, response.status_code

# --- THE BUTTON (The Action) ---
if st.button("Search Departures"):
    
    # Calculate dynamic times based on your PC's current clock
    now = datetime.now()
    later = now + timedelta(hours=hours_ahead)
    start_time = now.strftime("%Y-%m-%dT%H:%M")
    end_time = later.strftime("%Y-%m-%dT%H:%M")
    
    # Setup the API request
    url = f"https://aerodatabox.p.rapidapi.com/flights/airports/icao/{airport_code}/{start_time}/{end_time}"
    querystring = {"direction": "Departure", "withCancelled": "false", "withCargo": "false"}
    
    headers = {
        # This looks for the key in Streamlit's "Advanced Settings" vault
        "X-RapidAPI-Key": st.secrets["RAPID_API_KEY"], 
        "X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
    }

    with st.spinner("Talking to ATC (Fetching data)..."):
        response = requests.get(url, headers=headers, params=querystring)
        flight_data, status_code = fetch_flight_data(url, headers, querystring)

    # --- DISPLAY RESULTS ---
    if response.status_code == 200:
        found_flights = False
        
        for flight in flight_data.get("departures", []):
            
            # FIXED 1: Filter out ghost flights / codeshares
            if flight.get("codeshareStatus") == "IsCodeshared":
                continue 
                
            aircraft_model = flight.get("aircraft", {}).get("model", "")
            
            # Translate the UI selections into the terms the API actually uses
            search_terms = [fleet_translation[plane] for plane in selected_aircraft]
            
            # If the translated search term matches the API's aircraft model
            if any(term in aircraft_model for term in search_terms):
                found_flights = True
                
                airline = flight.get("airline", {}).get("name", "Unknown")
                flight_num = flight.get("number", "")
                
                #Tell Streamlit to look in the "movement" section for destination & time
                destination = flight.get("movement", {}).get("airport", {}).get("name", "Unknown")
                raw_time = flight.get("movement", {}).get("scheduledTime", {}).get("local", "Unknown")
                
                # Chop the long date string down to just HH:MM
                dep_time = raw_time[11:16] if raw_time != "Unknown" else raw_time

                # --- NEW: Grab the gate number (default to "TBA" if the airport hasn't assigned it yet) ---
                gate = flight.get("movement", {}).get("gate", "TBA")
                
                # --- UPDATED: Add the gate to the UI output ---
                st.success(f"**{dep_time}** | {airline} {flight_num} to **{destination}** | 🚪 Gate: **{gate}** | 🛩️ {aircraft_model}")
                
        if not found_flights:
            st.warning("No flights found matching your selected aircraft in that timeframe.")
    else:
        st.error(f"API Error {response.status_code}! Server says: {response.text}")
