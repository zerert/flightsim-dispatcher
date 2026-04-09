import streamlit as st
import requests
from datetime import datetime, timedelta

# --- MANUAL MEMORY VAULT ---
# This forces Streamlit to remember our data even if the page refreshes
if "saved_flights" not in st.session_state:
    st.session_state.saved_flights = None
if "last_search_params" not in st.session_state:
    st.session_state.last_search_params = ""
if "last_status" not in st.session_state:
    st.session_state.last_status = 200

# --- UI SETUP ---
st.set_page_config(page_title="FlightSim Dispatcher", page_icon="✈️")
st.title("✈️ FlightSim Dispatcher")
st.write("Find real-world flights departing right now for your simulator.")

col1, col2 = st.columns(2)
with col1:
    airport_code = st.text_input("Departure Airport (ICAO)", value="WSSS").upper()
with col2:
    hours_ahead = st.slider("Look ahead (Hours)", min_value=1, max_value=6, value=2)

fleet_translation = {
    "A319": "A319", "A320": "A320", "A321": "A321", "A332": "A330-200", "A333": "A330-300", "A339": "A330-900", 
    "A343": "A340-300", "A346": "A340-600", "A359": "A350-900", "A35K": "A350-1000", "A388": "A380", "B737": "737-700",
    "B738": "737-800", "B739": "737-900", "B744": "747-400", "B748": "747-8", "B772": "777-200", "B772ER": "777-200ER",
    "B77F": "777F", "B773": "777-300", "B77W": "777-300ER", "B788": "787-8", "B789": "787-9", "B78X": "787-10",
}
selected_aircraft = st.multiselect("Select Aircraft to Fly", list(fleet_translation.keys()), default=["A320", "B738", "B77W"])

# --- THE BUTTON LOGIC ---
if st.button("Search Departures"):
    
    current_search = f"{airport_code}_{hours_ahead}"
    
    # Check if we ALREADY did this exact search
    if st.session_state.last_search_params == current_search and st.session_state.saved_flights is not None:
        # NEW: Shows a green box directly on your website!
        st.success("🟢 USING SAVED MEMORY. NO API CALL MADE.") 
    else:
        # NEW: Shows a red/yellow box directly on your website!
        st.warning("🛑 DANGER: FIRING LIVE API CALL TO RAPIDAPI! 🛑")
        
        now = datetime.now()
        later = now + timedelta(hours=hours_ahead)
        start_time = now.strftime("%Y-%m-%dT%H:%M")
        end_time = later.strftime("%Y-%m-%dT%H:%M")
        
        url = f"https://aerodatabox.p.rapidapi.com/flights/airports/icao/{airport_code}/{start_time}/{end_time}"
        querystring = {"direction": "Departure", "withCancelled": "false",}
        
        headers = {
            "X-RapidAPI-Key": st.secrets["RAPID_API_KEY"], 
            "X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
        }

        with st.spinner("Talking to ATC (Fetching data)..."):
            response = requests.get(url, headers=headers, params=querystring)
            
            # Save the results to our physical vault
            st.session_state.last_status = response.status_code
            if response.status_code == 200:
                try:
                    st.session_state.saved_flights = response.json()
                except:
                    st.session_state.saved_flights = {}
            else:
                st.session_state.saved_flights = response.text
                
            st.session_state.last_search_params = current_search

# --- DISPLAY RESULTS (Reads from the Vault) ---
if st.session_state.saved_flights is not None:
    if st.session_state.last_status == 200:
        found_flights = False
        flight_data = st.session_state.saved_flights
        
        if isinstance(flight_data, dict):
            departures_list = flight_data.get("departures", [])
        elif isinstance(flight_data, list):
            departures_list = flight_data 
        else:
            departures_list = [] 
        
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
        st.error(f"API Error {st.session_state.last_status}! Server says: {st.session_state.saved_flights}")
