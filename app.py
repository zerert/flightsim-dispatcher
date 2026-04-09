import streamlit as st
import requests
from datetime import datetime, timedelta
import airportsdata
import pytz

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

col1, col2, col3 = st.columns(3)
with col1:
    airport_code = st.text_input("Departure Airport (ICAO)", value="WSSS").upper()
with col2:
    hours_ahead = st.slider("Look ahead (Hours)", min_value=1, max_value=6, value=2)
with col3:
    flight_type = st.radio("Flight Type", ["Passenger", "Cargo", "Both"])

fleet_translation = {
    "A319": ["A319", "319"], 
    "A19N": ["A319 NEO", "A19N", "319N"], 
    "A320": ["A320", "320"], 
    "A20N": ["A320 NEO", "A20N", "320N"], 
    "A321": ["A321", "321"], 
    "A21N": ["A321 NEO", "A21N", "321N"], 
    "A332": ["A330-200", "332"], 
    "A333": ["A330-300", "333"], 
    "A339": ["A330-900", "339"], 
    "A343": ["A340-300", "343"], 
    "A346": ["A340-600", "346"], 
    "A359": ["A350-900", "359"], 
    "A35K": ["A350-1000", "35K"], 
    "A388": ["A380", "388"], 
    "B737": ["737-700", "73G"], 
    "B738": ["737-800", "738", "73H"], 
    "B38M": ["737 MAX 8"],
    "B39M": ["737 MAX 9"],
    "B739": ["737-900", "739", "73J"], 
    "B744": ["747-400", "744"], 
    "B748": ["747-8", "748"], 
    "B772": ["777-200", "772"], 
    "B772ER": ["777-200ER", "772ER"],
    "B77F": ["777F", "77F"], 
    "B773": ["777-300", "773"], 
    "B77W": ["777-300ER", "77W"], 
    "B788": ["787-8", "788"], 
    "B789": ["787-9", "789"], 
    "B78X": ["787-10", "78X"]
}
selected_aircraft = st.multiselect("Select Aircraft to Fly", list(fleet_translation.keys()), default=["A320", "B738", "B77W"])

# --- THE BUTTON LOGIC ---
if st.button("Search Departures"):
    
    current_search = f"{airport_code}_{hours_ahead}_{flight_type}"
    
    # Check if we ALREADY did this exact search
    if st.session_state.last_search_params == current_search and st.session_state.saved_flights is not None:
        # Shows a green box directly on your website!
        st.success("🟢 USING SAVED MEMORY. NO API CALL MADE.") 
    else:
        # Shows a red/yellow box directly on your website!
        st.warning("🛑 DANGER: FIRING LIVE API CALL TO RAPIDAPI! 🛑")
        
        try:
            # 1. Load the offline database of 10,000+ airports
            airports = airportsdata.load('ICAO')
            # 2. Look up the specific timezone string (e.g., 'America/New_York')
            tz_string = airports.get(airport_code, {}).get('tz', 'UTC')
            local_tz = pytz.timezone(tz_string)
            
            # 3. Get the exact current time in that specific timezone!
            now = datetime.now(local_tz) 
        except:
            # Fallback to server time just in case the user types a fake airport code
            now = datetime.now() 
            tz_string = "Unknown Timezone"
            
        later = now + timedelta(hours=hours_ahead)
        
        # The .strftime cuts off the timezone data, leaving just the raw local time string the API wants
        start_time = now.strftime("%Y-%m-%dT%H:%M")
        end_time = later.strftime("%Y-%m-%dT%H:%M")

        api_with_cargo = "true" if flight_type in ["Cargo", "Both"] else "false"
        
        url = f"https://aerodatabox.p.rapidapi.com/flights/airports/icao/{airport_code}/{start_time}/{end_time}"
        querystring = {"direction": "Departure", "withCancelled": "false", "withCargo": api_with_cargo}
        
        headers = {
            "X-RapidAPI-Key": st.secrets["RAPID_API_KEY"], 
            "X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
        }

        with st.spinner("Talking to ATC (Fetching data {flight_type} data for {tz_string})..."):
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

            is_cargo_flight = flight.get("isCargo", False)
            
            if flight_type == "Passenger" and is_cargo_flight:
                continue # Skip this plane, we only want passengers
            if flight_type == "Cargo" and not is_cargo_flight:
                continue # Skip this plane, we only want cargo
                
            # Grab the raw model name and instantly force it to UPPERCASE
            raw_model = flight.get("aircraft", {}).get("model", "").upper()
            
            # --- THE FUZZY SEARCH ---
            is_my_plane = False
            for selected in selected_aircraft:
                keywords = fleet_translation[selected]
                # If ANY keyword is hiding inside the raw_model string
                if any(keyword in raw_model for keyword in keywords):
                    is_my_plane = True
                    break # Stop searching, we found a match!
            
            if is_my_plane:
                found_flights = True
                airline = flight.get("airline", {}).get("name", "Unknown")
                flight_num = flight.get("number", "")
                
                destination = flight.get("movement", {}).get("airport", {}).get("name", "Unknown")
                raw_time = flight.get("movement", {}).get("scheduledTime", {}).get("local", "Unknown")
                dep_time = raw_time[11:16] if raw_time != "Unknown" else raw_time
                gate = flight.get("movement", {}).get("gate", "TBA")
                
                # Notice we use the 'raw_model' here so you see exactly what the API sent
                st.success(f"**{dep_time}** | {airline} {flight_num} to **{destination}** | 🚪 Gate: **{gate}** | 🛩️ {raw_model}")
                
        if not found_flights:
            st.warning("No flights found matching your criteria in that timeframe.")
    else:
        st.error(f"API Error {st.session_state.last_status}! Server says: {st.session_state.saved_flights}")
