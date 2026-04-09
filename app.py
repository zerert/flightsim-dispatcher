import streamlit as st
import requests
from datetime import datetime, timedelta

# --- UI SETUP ---
st.set_page_config(page_title="FlightSim Dispatcher", page_icon="✈️")
st.title("✈️ FlightSim Dispatcher")
st.write("Find real-world flights departing right now for your simulator.")

# --- USER INPUTS ---
col1, col2 = st.columns(2)
with col1:
    airport_code = st.text_input("Departure Airport (ICAO)", value="WSSS").upper()
with col2:
    hours_ahead = st.slider("Look ahead (Hours)", min_value=1, max_value=6, value=2)

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

selected_aircraft = st.multiselect("Select Aircraft to Fly", list(fleet_translation.keys()), default=["A320", "B738", "B77W"])

# --- CACHING THE API CALL ---
@st.cache_data(ttl=300)
def fetch_flight_data(airport, hours):
    now = datetime.now()
    later = now + timedelta(hours=hours)
    start_time = now.strftime("%Y-%m-%dT%H:%M")
    end_time = later.strftime("%Y-%m-%dT%H:%M")
    
    url = f"https://aerodatabox.p.rapidapi.com/flights/airports/icao/{airport}/{start_time}/{end_time}"
    querystring = {"direction": "Departure", "withCancelled": "false", "withCargo": "false"}
    
    # We also moved the secret key inside to keep everything tidy
    headers = {
        "X-RapidAPI-Key": st.secrets["RAPID_API_KEY"], 
        "X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        try:
            return response.json(), 200
        except:
            return {}, 200 
    else:
        return response.text, response.status_code

# --- THE BUTTON ---
if st.button("Search Departures"):
    with st.spinner("Talking to ATC (Fetching data)..."):
        # Look how clean this is now! We just pass the two UI variables.
        flight_data, status_code = fetch_flight_data(airport_code, hours_ahead)

    # --- DISPLAY RESULTS ---
    if status_code == 200:
        found_flights = False
        
        # --- THE FIX: BULLETPROOF SAFEGUARD ---
        # We force Python to double-check that the data is a dictionary before using .get()
        if isinstance(flight_data, dict):
            departures_list = flight_data.get("departures", [])
        elif isinstance(flight_data, list):
            departures_list = flight_data # Backup plan if the API just returns a raw list
        else:
            departures_list = [] # Backup plan if the API returns None
        
        for flight in departures_list:
            if flight.get("codeshareStatus") == "IsCodeshared":
                continue 
                
            aircraft_model = flight.get("aircraft", {}).get("model", "")
            search_terms = [fleet_translation[plane] for plane in selected_aircraft]
            
            if any(term in aircraft_model for term in search_terms):
                found_flights = True
                airline = flight.get("airline", {}).get("name", "Unknown")
                flight_num = flight.get("number", "")
                
                destination = flight.get("movement", {}).get("airport", {}).get("name", "Unknown")
                raw_time = flight.get("movement", {}).get("scheduledTime", {}).get("local", "Unknown")
                dep_time = raw_time[11:16] if raw_time != "Unknown" else raw_time
                gate = flight.get("movement", {}).get("gate", "TBA")
                
                st.success(f"**{dep_time}** | {airline} {flight_num} to **{destination}** | 🚪 Gate: **{gate}** | 🛩️ {aircraft_model}")
                
        if not found_flights:
            st.warning("No flights found matching your criteria in that timeframe.")
    else:
        st.error(f"API Error {status_code}! Server says: {flight_data}")
