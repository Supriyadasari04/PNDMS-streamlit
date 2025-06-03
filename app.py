# streamlit_app.py
import ipywidgets as widgets
import streamlit as st
import joblib
import numpy as np
import json
from datetime import datetime
import requests
import folium
from streamlit_folium import st_folium
import hashlib
import sqlite3
from pathlib import Path
import re 
import bcrypt
import urllib.parse
# Password strength configuration
MIN_PASSWORD_LENGTH = 8
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_NUMBERS = True
REQUIRE_SPECIAL_CHARS = True
SPECIAL_CHARS = r'[!@#$%^&*(),.?":{}|<>]'

def is_password_strong(password):
    """Enforce strong password requirements"""
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    
    checks = []
    messages = []
    
    if REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        checks.append(False)
        messages.append("uppercase letter")
    if REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        checks.append(False)
        messages.append("lowercase letter")
    if REQUIRE_NUMBERS and not re.search(r'[0-9]', password):
        checks.append(False)
        messages.append("number")
    if REQUIRE_SPECIAL_CHARS and not re.search(SPECIAL_CHARS, password):
        checks.append(False)
        messages.append("special character")
    
    if checks:
        return False, f"Password must contain: {', '.join(messages)}"
    
    return True, "Password meets strength requirements"


# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            email TEXT
        )''')
    
    conn.commit()
    conn.close()

# Password hashing functions using bcrypt
def make_hashes(password):
    # Generate salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')  # Store as string in database

def check_hashes(password, hashed_password):
    # Convert string back to bytes for verification
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# Database functions with enforced password strength
def create_user(username, password, email):
    is_strong, message = is_password_strong(password)
    if not is_strong:
        st.error(f"Password too weak: {message}")
        return False

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        c.execute('INSERT INTO users(username, password, email) VALUES (?, ?, ?)', 
                  (username, hashed_pw.decode('utf-8'), email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("Username already exists")
        return False
    finally:
        conn.close()


def authenticate_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    
    if result:
        stored_hash = result[0].encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
    return False

# Session state management
if 'page' not in st.session_state:
    st.session_state.page = 'auth'
    
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def auth_page():
    st.title("🔐 Secure Login")
    
    # Create tabs
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
    
    # Login Tab
    with login_tab:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_btn"):
            if authenticate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.page = 'home'
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    # Sign Up Tab
    with signup_tab:
        signup_email = st.text_input("Email", key="signup_email")
        new_user = st.text_input("Choose Username", key="signup_username")
        new_pass = st.text_input("Create Password", type="password", key="signup_pass",
                               help="Must include: 8+ chars, uppercase, lowercase, number, and special character")
        confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_pass")
        
        # Real-time password strength feedback
        password_status = st.empty()
        if new_pass:
            is_strong, msg = is_password_strong(new_pass)
            if is_strong:
                password_status.success("✓ Strong password")
            else:
                password_status.warning(f"⚠️ {msg}")
        
        if st.button("Create Account", key="signup_btn"):
            # Clear previous messages
            password_status.empty()
            
            # Validate inputs
            if not new_user or not new_pass or not signup_email:
                st.error("All fields are required")
            elif new_pass != confirm_pass:
                st.error("Passwords don't match!")
            else:
                is_strong, msg = is_password_strong(new_pass)
                if not is_strong:
                    st.error(f"Password too weak: {msg}")
                elif create_user(new_user, new_pass,signup_email):
                    st.success("Account created successfully! Please login.")
            
# Initialize the database
init_db()

# Only show the rest of the app if authenticated
if not st.session_state.authenticated:
    auth_page()
    st.stop()

# if 'page' not in st.session_state:
#     st.session_state.page = 'home'

# 🚀 **Cache Earthquake Data for Faster Loading**
@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_earthquake_data():
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
    response = requests.get(url)

    if response.status_code != 200:
        return []

    try:
        data = response.json()
    except:
        return []

    earthquakes = data.get("features", [])
    earthquake_list = []

    for quake in earthquakes[:10]:  # 🌍 Limit to first 10 for speed
        coords = quake["geometry"]["coordinates"]  # [lon, lat, depth]
        earthquake_list.append({
            "place": quake["properties"]["place"],
            "magnitude": quake["properties"]["mag"],
            "latitude": coords[1],
            "longitude": coords[0],
        })

    return earthquake_list
# 📖 **Earthquake Information Page**
def earthquake_info():
    st.title("🌍 Learn About Earthquakes")

    with st.expander("📖 What is an Earthquake?"):
        st.write("""
        An **earthquake** is the shaking of the Earth's surface caused by the sudden release of energy in the Earth's crust. 
        This energy release occurs due to movements along faults, volcanic activity, or human activities like mining.
        """)

    with st.expander("🌎 How Do Earthquakes Occur?"):
        st.write("""
        1️⃣ **Tectonic Plates Move:** The Earth's crust is made of large plates that move.  
        2️⃣ **Stress Builds Up:** When plates collide or slide past each other, stress builds.  
        3️⃣ **Faults Slip:** The stress is suddenly released, causing the ground to shake.  
        4️⃣ **Aftershocks Follow:** Smaller quakes may occur after the main earthquake.  
        """)

    with st.expander("📏 Earthquake Magnitude Scale (Richter Scale)"):
        st.write("""
        - **Minor (Below 3.0):** Usually not felt.  
        - **Light (3.0 - 3.9):** Rarely causes damage.  
        - **Moderate (4.0 - 4.9):** Can shake buildings slightly.  
        - **Strong (5.0 - 5.9):** May cause structural damage.  
        - **Major (6.0 - 6.9):** Can cause severe damage in populated areas.  
        - **Great (7.0+):** Causes widespread destruction.  
        """)

    with st.expander("⚠️ Earthquake Safety Tips"):
        st.write("""
        ✔️ **Drop, Cover, and Hold On:** Protect yourself during shaking.  
        ✔️ **Secure Heavy Objects:** Prevent falling hazards.  
        ✔️ **Have an Emergency Kit:** Water, food, flashlight, and first-aid supplies.  
        ✔️ **Know Safe Zones:** Identify safe spots indoors and outdoors.  
        ✔️ **Stay Away from Windows & Power Lines:** Avoid falling debris.  
        """)

    with st.expander("🌍 Major Earthquakes in History"):
        st.write("""
        - **Great Chile Earthquake (1960):** Strongest earthquake ever recorded (9.5 magnitude).  
        - **Indian Ocean Earthquake (2004):** Triggered a massive tsunami.  
        - **Haiti Earthquake (2010):** Caused devastating damage and loss of life.  
        - **Japan Earthquake & Tsunami (2011):** Led to the Fukushima nuclear disaster.  
        """)

    if st.button("🔙 Back to Earthquake Tracking"):
        st.session_state.page = "earthquakes"
        st.rerun()
# 🌍 **Earthquake Map Page**
def earthquakes():
    st.title("🌋 Earthquake Updates")

    # Fetch earthquake data
    earthquake_data = fetch_earthquake_data()
    if not earthquake_data:
        st.write("No recent earthquakes detected.")
        if st.button("Back to Home"):
            st.session_state.page = "home"
            st.rerun()
        return

    # Dropdown with only Place & Magnitude
    earthquake_dict = {f"{quake['place']} | Magnitude: {quake['magnitude']}": quake for quake in earthquake_data}
    selected_label = st.selectbox("📌 Select an Earthquake to Zoom In:", list(earthquake_dict.keys()))

    selected_quake = earthquake_dict[selected_label]
    center_lat, center_lon = selected_quake["latitude"], selected_quake["longitude"]
    magnitude = selected_quake["magnitude"]
    place = selected_quake["place"]

    # 🌎 **Use Faster Tile Layer**
    earthquake_map = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=6, 
        control_scale=True
    )

    # 📍 **Set marker color based on magnitude**
    color = "green" if magnitude < 4 else "orange" if magnitude < 6 else "red"

    # 📌 **Add Earthquake Marker**
    folium.CircleMarker(
        location=[center_lat, center_lon],
        radius=magnitude * 2,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.6,
        popup=f"<b>{place}</b><br>💥 Magnitude: {magnitude}",
    ).add_to(earthquake_map)

    # 🗺 **Render Map**
    st_folium(earthquake_map, width=700, height=500)

    # 🌍 **Buttons: Back to Home + Learn About earthquakes**
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Back to Home"):
            st.session_state.page = "home"
            st.rerun()

    with col2:
        if st.button("📖 Learn About Earthquakes"):
            st.session_state.page = "earthquake_info"
            st.rerun()



# Fetch Wildfire Data
# 🚀 **Cache Wildfire Data for Faster Loading**
@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_wildfire_data():
    url = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&category=wildfires"
    response = requests.get(url)

    if response.status_code != 200:
        return []

    try:
        data = response.json()
    except:
        return []

    events = data.get("events", [])
    wildfire_list = []

    for event in events[:10]:  # 🔥 Limit to first 10 wildfires for speed
        for g in event.get("geometry", []):
            coords = g.get("coordinates", [])
            if len(coords) == 2:
                wildfire_list.append({
                    "title": event.get("title", "Wildfire"),
                    "latitude": coords[1],
                    "longitude": coords[0],
                    "source": event.get("sources", [{}])[0].get("url", "No source available")
                })

    return wildfire_list
# 📖 **Wildfire Information Page**
def wildfire_info():
    st.title("🔥 Learn About Wildfires")

    with st.expander("📖 What is a Wildfire?"):
        st.write("""
        A **wildfire** is an uncontrolled fire that rapidly spreads across vegetation in forests, grasslands, and other areas. 
        Wildfires can be caused by natural factors like lightning or human activities.
        """)

    with st.expander("🌍 How Do Wildfires Start?"):
        st.write("""
        1️⃣ **Heat Source:** Lightning, campfires, or even the sun's heat can ignite dry vegetation.  
        2️⃣ **Fuel:** Dry grass, trees, and leaves provide fuel for the fire.  
        3️⃣ **Oxygen Supply:** Wind can rapidly spread the fire by supplying oxygen.  
        4️⃣ **Drought Conditions:** Prolonged dry weather increases wildfire risk.
        """)

    with st.expander("🔥 Wildfire Categories"):
        st.write("""
        - **Ground Fires:** Burn organic material beneath the surface.  
        - **Surface Fires:** Spread across vegetation and low-lying plants.  
        - **Crown Fires:** Reach treetops and spread rapidly through forest canopies.  
        """)

    with st.expander("⚠️ Wildfire Safety Tips"):
        st.write("""
        ✔️ **Create a Defensible Space:** Clear vegetation near homes.  
        ✔️ **Prepare an Emergency Plan:** Know evacuation routes.  
        ✔️ **Avoid Fire-Prone Activities:** No campfires in dry areas.  
        ✔️ **Monitor Weather Reports:** Stay updated on wildfire risks.  
        ✔️ **Use Fire-Resistant Materials:** Protect homes with fire-resistant roofing and landscaping.  
        """)

    with st.expander("🔥 Major Wildfires in History"):
        st.write("""
        - **Australia’s Black Summer (2019-2020):** Burned over 46 million acres.  
        - **California Camp Fire (2018):** Deadliest wildfire in California history.  
        - **Amazon Rainforest Fires (2019):** Destroyed vast areas of the Amazon.  
        - **Siberian Wildfires (2021):** Massive fires fueled by climate change.  
        """)

    if st.button("🔙 Back to Wildfire Tracking"):
        st.session_state.page = "wildfires"
        st.rerun()
# 🌍 **Wildfire Map Page**
def wildfires():
    st.title("🔥 Wildfire Updates")

    # Fetch wildfire data
    wildfire_data = fetch_wildfire_data()
    if not wildfire_data:
        st.write("No active wildfires.")
        if st.button("Back to Home"):
            st.session_state.page = "home"
            st.rerun()
        return

    # Dropdown for wildfire selection
    wildfire_dict = {fire["title"]: fire for fire in wildfire_data}
    selected_fire = st.selectbox("📌 Select a Wildfire to Zoom In:", list(wildfire_dict.keys()))

    selected_event = wildfire_dict[selected_fire]
    center_lat, center_lon = selected_event["latitude"], selected_event["longitude"]
    source_url = selected_event["source"]

    # 🌎 **Use Faster Tile Layer**
    wildfire_map = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=5,  # 🔍 Start at lower zoom for faster loading
        control_scale=True
    )

    # 🔥 **Replace Slow NASA FIRMS Layer with Faster OpenStreetMap**
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="&copy; OpenStreetMap contributors",
        name="Fast OSM Map",
        control=True
    ).add_to(wildfire_map)

    # 📍 **Add Selected Wildfire Marker**
    folium.Marker(
        location=[center_lat, center_lon],
        popup=f"<b>{selected_event['title']}</b><br><a href='{source_url}' target='_blank'>More Info</a>",
        tooltip="Click for details",
        icon=folium.Icon(color="red", icon="fire", prefix="fa")
    ).add_to(wildfire_map)

    # 🛠 **Enable Layer Control**
    folium.LayerControl().add_to(wildfire_map)

    # 🗺 **Render Map**
    st_folium(wildfire_map, width=700, height=500)

    # 🌍 **Buttons: Back to Home + Learn About wildfires**
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Back to Home"):
            st.session_state.page = "home"
            st.rerun()

    with col2:
        if st.button("📖 Learn About Wildfires"):
            st.session_state.page = "wildfire_info"
            st.rerun()


# 🚀 **Cache Hurricane Data for Faster Loading**
@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_hurricane_data():
    url = "https://www.nhc.noaa.gov/CurrentStorms.json"  # NHC Active Storms API
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Failed to fetch hurricane data: {e}")
        return []

    hurricanes = []
    
    # Parse hurricane data
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates", [0, 0])
        storm_name = properties.get("name", "Unknown Storm")
        advisory = properties.get("fullIssue", "No advisory available.")
        wind_speed = properties.get("windMph", "Unknown Speed")
        storm_category = properties.get("category", "Unknown Category")

        hurricanes.append({
            "name": storm_name,
            "latitude": coordinates[1],
            "longitude": coordinates[0],
            "advisory": advisory,
            "wind_speed": wind_speed,
            "category": storm_category
        })

    return hurricanes
# 📖 **Hurricane Information Page**
def hurricane_info():
    st.title("📚 Learn About Hurricanes")

    with st.expander("📖 What is a Hurricane?"):
        st.write("""
        A **hurricane** is a powerful storm system that forms over warm ocean waters. It is characterized by 
        strong winds, heavy rain, and storm surges. Hurricanes are also known as **tropical cyclones** 
        or **typhoons** depending on the region.
        """)

    with st.expander("🌍 How Do Hurricanes Form?"):
        st.write("""
        1️⃣ Warm ocean water (at least 80°F / 27°C) evaporates, creating humid air.  
        2️⃣ This warm, moist air rises, causing low pressure near the surface.  
        3️⃣ As the air rises, it cools and condenses, forming clouds and releasing heat.  
        4️⃣ The Coriolis effect makes the storm rotate, forming a **hurricane** if it reaches 74 mph or more.
        """)

    with st.expander("🌀 Hurricane Categories (Saffir-Simpson Scale)"):
        st.write("""
        - **Category 1:** 74-95 mph (119-153 km/h) - Some damage  
        - **Category 2:** 96-110 mph (154-177 km/h) - Extensive damage  
        - **Category 3:** 111-129 mph (178-208 km/h) - Devastating damage  
        - **Category 4:** 130-156 mph (209-251 km/h) - Catastrophic damage  
        - **Category 5:** 157+ mph (252+ km/h) - Total destruction possible  
        """)

    with st.expander("⚠️ Hurricane Safety Tips"):
        st.write("""
        ✔️ **Prepare an Emergency Kit:** Water, food, flashlight, and batteries.  
        ✔️ **Evacuate if Necessary:** Follow local government warnings.  
        ✔️ **Stay Indoors:** Avoid windows and doors during a storm.  
        ✔️ **Secure Loose Objects:** Prevent flying debris in strong winds.  
        ✔️ **Monitor Weather Updates:** Stay informed through news and official sources.  
        """)

    with st.expander("🌊 Major Hurricanes in History"):
        st.write("""
        - **Hurricane Katrina (2005):** One of the most devastating hurricanes in U.S. history.  
        - **Hurricane Harvey (2017):** Caused catastrophic flooding in Texas.  
        - **Hurricane Irma (2017):** A powerful Category 5 storm in the Atlantic.  
        - **Hurricane Maria (2017):** Severely impacted Puerto Rico.  
        - **Hurricane Sandy (2012):** Hit the U.S. East Coast, causing major damage.  
        """)

    if st.button("🔙 Back to Hurricane Tracking"):
        st.session_state.page = "hurricanes"
        st.rerun()

# 🌪️ **Hurricane Tracking Page**
def hurricanes():
    st.title("🌪️ Real-Time Hurricane Updates")

    # Fetch hurricane data
    hurricane_data = fetch_hurricane_data()

    # 🌍 **Dropdown for Hurricane Selection (Only if hurricanes exist)**
    if hurricane_data:
        hurricane_dict = {f"{storm['name']} (Category {storm['category']})": storm for storm in hurricane_data}
        selected_hurricane = st.selectbox("📌 Select a Hurricane to Zoom In:", list(hurricane_dict.keys()))

        # Get selected hurricane details
        selected_event = hurricane_dict[selected_hurricane]
        center_lat, center_lon = selected_event["latitude"], selected_event["longitude"]
        advisory_text = selected_event["advisory"]
        wind_speed = selected_event["wind_speed"]
        category = selected_event["category"]

        # 🔴 **Set Marker Color Based on Hurricane Category**
        category_colors = {
            "Tropical Depression": "green",
            "Tropical Storm": "orange",
            "Category 1": "yellow",
            "Category 2": "gold",
            "Category 3": "red",
            "Category 4": "darkred",
            "Category 5": "purple"
        }
        marker_color = category_colors.get(category, "blue")

        # 🗺 **Create Map Centered on Selected Hurricane**
        hurricane_map = folium.Map(location=[center_lat, center_lon], zoom_start=5, control_scale=True)

        # 📍 **Add Hurricane Marker**
        folium.Marker(
            location=[center_lat, center_lon],
            popup=f"🌀 <b>{selected_hurricane}</b><br>🌪️ <b>Category:</b> {category}<br>💨 <b>Wind Speed:</b> {wind_speed} mph<br>📜 <b>Advisory:</b> {advisory_text}",
            tooltip=selected_hurricane,
            icon=folium.Icon(color=marker_color, icon="cloud", prefix="fa")
        ).add_to(hurricane_map)

        # 🗺 **Render Map**
        st_folium(hurricane_map, width=700, height=500)

    else:
        st.subheader("✅ No active hurricanes detected.")

    # 🌍 **Buttons: Back to Home + Learn About Hurricanes**
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Back to Home"):
            st.session_state.page = "home"
            st.rerun()

    with col2:
        if st.button("📖 Learn About Hurricanes"):
            st.session_state.page = "hurricane_info"
            st.rerun()


# NOAA Tsunami API Endpoint
TSUNAMI_API_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/tsunamis"

@st.cache_data(ttl=600)  # Cache data for 10 minutes
def fetch_tsunami_data():
    try:
        response = requests.get(TSUNAMI_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        tsunamis = []

        # Iterate through tsunami events
        for event in data:
            tsunamis.append({
                "location": event.get("locationName", "Unknown Location"),
                "latitude": event.get("latitude"),
                "longitude": event.get("longitude"),
                "magnitude": event.get("earthquakeMagnitude", "N/A"),
                "depth": event.get("depth", "N/A"),
                "year": event.get("year", "Unknown Year"),
                "cause": event.get("cause", "No Advisory Available"),
            })

        return tsunamis

    except requests.exceptions.RequestException as e:
        return []
# 📖 **Tsunami Information Page**
def tsunami_info():
    st.title("📚 Learn About Tsunamis")

    with st.expander("📖 What is a Tsunami?"):
        st.write("""
        A **tsunami** is a series of powerful ocean waves caused by underwater disturbances such as earthquakes, 
        volcanic eruptions, or landslides. Unlike regular waves, tsunamis can travel across entire ocean basins 
        at extremely high speeds, causing massive destruction upon reaching coastal areas.
        """)

    with st.expander("🌍 How Do Tsunamis Form?"):
        st.write("""
        1️⃣ **Seafloor Disturbance:** Earthquakes, volcanic eruptions, or landslides displace a large volume of water.  
        2️⃣ **Wave Generation:** The displaced water forms waves that spread outward in all directions.  
        3️⃣ **Rapid Movement:** Tsunami waves travel at speeds up to **500-800 km/h (310-500 mph)** in deep water.  
        4️⃣ **Coastal Impact:** As the waves approach shallow waters, they **slow down** but increase in height, 
            sometimes reaching **over 30 meters (100 feet)** before crashing onto land.
        """)

    with st.expander("🌊 Characteristics of a Tsunami"):
        st.write("""
        - **High Speed:** In deep oceans, tsunamis travel as fast as **jet planes** (500-800 km/h).  
        - **Low Waves in Open Ocean:** In deep water, tsunami waves may be only **a few inches to a few feet high**, making them hard to detect.  
        - **Massive Coastal Impact:** As they approach land, their height increases dramatically.  
        - **Multiple Waves:** A tsunami is **not just one wave**—it often arrives in a series, with the largest wave sometimes hitting **hours later**.  
        """)

    with st.expander("⚠️ Tsunami Warning Signs & Safety Tips"):
        st.write("""
        ### **🔴 Tsunami Warning Signs**
        🚨 **Sudden ocean withdrawal:** The sea may recede dramatically before a tsunami wave strikes.  
        🚨 **Strong, long earthquake:** If an earthquake lasts **more than 20 seconds**, a tsunami may follow.  
        🚨 **Loud roaring noise:** A tsunami may sound like a **jet engine or train** as it approaches.  

        ### **🛑 Safety Tips**
        ✔️ **Move to Higher Ground:** Immediately move at least **100 feet (30 meters) above sea level**.  
        ✔️ **Follow Official Warnings:** Pay attention to **tsunami alerts and sirens**.  
        ✔️ **Never Go Back:** The first wave is **not always the biggest**—stay away until officials declare safety.  
        ✔️ **Know Evacuation Routes:** If you live in a coastal area, plan your **fastest escape route** in advance.  
        ✔️ **Do NOT Wait to See the Wave:** If you notice the ocean receding abnormally, **evacuate immediately**.  
        """)

    with st.expander("📜 Major Tsunamis in History"):
        st.write("""
        - **2004 Indian Ocean Tsunami:** One of the deadliest tsunamis, killing over **230,000 people** across 14 countries.  
        - **2011 Japan Tsunami (Tohoku Earthquake):** A **9.1 magnitude earthquake** triggered a tsunami that devastated Japan, causing the **Fukushima nuclear disaster**.  
        - **1960 Chile Tsunami:** The largest earthquake ever recorded (**9.5 magnitude**) caused massive tsunamis across the Pacific.  
        - **1755 Lisbon Tsunami:** Followed a **massive earthquake**, wiping out coastal Portugal and affecting the Atlantic.  
        - **1883 Krakatoa Tsunami:** A volcanic eruption in Indonesia triggered waves over **40 meters (130 feet)** high.  
        """)

    if st.button("🔙 Back to Tsunami Tracking"):
        st.session_state.page = "tsunamis"
        st.rerun()

import streamlit as st
import folium
from streamlit_folium import st_folium

# 🌊 **Streamlit App for Live Tsunami Tracking**
def tsunamis():
    st.title("🌊 Live Tsunami Tracker")

    # Fetch tsunami data
    tsunami_events = fetch_tsunami_data()

    if not tsunami_events:
        st.subheader("✅ No active tsunami alerts at this time.")
    else:
        # Initialize Folium Map
        tsunami_map = folium.Map(location=[0, -160], zoom_start=2, control_scale=True)

        # Extract valid tsunami events
        valid_events = [event for event in tsunami_events if event["latitude"] is not None and event["longitude"] is not None]

        if valid_events:
            locations = [(event["latitude"], event["longitude"]) for event in valid_events]
            popups = [
                folium.Popup(
                    f"<b>🌊 Tsunami Event</b><br>"
                    f"<b>Location:</b> {event['location']}<br>"
                    f"<b>Magnitude:</b> {event['magnitude']}<br>"
                    f"<b>Depth:</b> {event['depth']} km<br>"
                    f"<b>Date:</b> {event['year']}-01-01<br>"
                    f"<b>Advisory:</b> {event['cause']}",
                    max_width=300
                ) for event in valid_events
            ]

            marker_colors = [
                "blue" if event["magnitude"] == "N/A"
                else "darkred" if float(event["magnitude"]) >= 8.0
                else "red" if float(event["magnitude"]) >= 6.5
                else "orange" if float(event["magnitude"]) >= 5.0
                else "yellow"
                for event in valid_events
            ]

            # Add markers using zip()
            for (lat, lon), popup, color in zip(locations, popups, marker_colors):
                folium.Marker(
                    location=[lat, lon],
                    popup=popup,
                    tooltip="🌊 Tsunami Event",
                    icon=folium.Icon(color=color, icon="info-sign")
                ).add_to(tsunami_map)

            # Display the map
            st_folium(tsunami_map, width=700, height=500)
            
    # Create two columns (left and right)
    col1, col2 = st.columns([1, 1])

    # Left button (Back to Home)
    with col1:
        if st.button("⬅️ Back to Home"):
            st.session_state.page = "home"
            st.rerun()

    # Right button (Learn About Tsunamis)
    with col2:
        if st.button("📖 Learn About Tsunamis"):
            st.session_state.page = "tsunami_info"
            st.rerun()




# Home Page
def home():
    # st.image("your_logo.png", width=150)  # Replace with your actual logo path
    st.title("Welcome to Disaster Prediction App")
    st.subheader("Predict natural disasters with AI-based analysis.")
    
    st.write("Discover, analyze, and predict natural disasters based on historical and real-time data.")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.header("🌍 Predict Disasters")
        st.write("Use AI models to predict the likelihood of disasters like floods, wildfires, and cyclones.")
    
    with col2:
        st.header("📊 Data Insights")
        st.write("Get detailed insights into disaster-prone regions and patterns.")
    
    with col3:
        st.header("🚀 Easy to Use")
        st.write("Enter key parameters and get instant predictions.")

    left_col, spacer, right_col = st.columns([1, 3, 1])
    with left_col:
        if st.button("Get Started", key="get_started_button"):
            st.session_state.page = 'prediction'
            st.rerun()
    with right_col:
        if st.button("News", key="news_button"): 
            st.session_state.page = 'news'
            st.rerun()

    # Add Small Description Below
    st.markdown("---")
    st.markdown("## 🌍 Real-Time Disaster Monitoring")
    st.write(
        "Stay updated with real-time data on **Earthquakes, Wildfires, Storms, and Tsunamis.** "
        "Click on a disaster below to see live updates."
    )

    # Buttons for Different Disasters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🌋 Earthquakes"):
            st.session_state.page = 'earthquakes'
            st.rerun()

    with col2:
        if st.button("🔥 Wildfires"):
            st.session_state.page = 'wildfires'
            st.rerun()

    with col3:
        if st.button("🌪️ Hurricanes"):
            st.session_state.page = 'hurricanes'
            st.rerun()

    with col4:
        if st.button("🌊 Tsunamis"):
            st.session_state.page = 'tsunamis'
            st.rerun()

    st.markdown("---")
    # Single centered column approach
    center_col = st.columns([1, 2, 1])[1]  # Get the middle column
    with center_col:
        st.markdown("<h3 style='text-align: center;'>Account Actions</h3>", unsafe_allow_html=True)
        # Center the button using CSS
        st.markdown("""
        <style>
            .stButton>button {
                margin: 0 auto;
                display: block;
            }
        </style>
        """, unsafe_allow_html=True)
        if st.button("👤 User Profile", key="user_btn"):
            st.session_state.page = "profile"
            st.rerun()
def profile_page():
    st.title("👤 User Profile")

    # Connect to database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Fetch current user data
    c.execute("SELECT username, email FROM users WHERE username = ?", (st.session_state.username,))
    user_data = c.fetchone()

    if user_data:
        current_username, current_email = user_data

        # Editable user fields
        new_username = st.text_input("Username", current_username, key="edit_username")
        new_email = st.text_input("Email", current_email if current_email else "", key="edit_email")

        # Save Changes Button
        if st.button("💾 Save Changes", key="save_profile"):
            try:
                # Update user info in database
                c.execute("UPDATE users SET username = ?, email = ? WHERE username = ?", 
                          (new_username, new_email, st.session_state.username))
                conn.commit()

                # Update session state
                st.session_state.username = new_username

                st.success("Profile updated successfully!")
                st.rerun()  # Refresh page to reflect changes

            except sqlite3.Error as e:
                st.error(f"Error updating profile: {e}")

        st.markdown("---")

        # Centering the logout button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚪 Logout", key="logout_btn"):
                st.session_state.page = "logout"
                st.session_state.authenticated = False
                st.session_state.username = None
                st.rerun()

    else:
        st.error("User data not found!")

    # Close database connection
    conn.close()

def logout_page():
    st.title("Logged Out")
    st.success("You've been successfully logged out.")
    
    # Clear the session state (except for page)
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_data = None
    left_col, spacer, right_col = st.columns([1, 3, 1])
    with left_col:
        if st.button("Login Again"):
            st.session_state.page = 'auth'
            st.rerun()
    with right_col:
        if st.button("Sign Up"):
            st.session_state.page = 'auth'
            st.session_state.auth_choice = "Sign Up"
            st.rerun()


# --------------------------------------- should look at it later ---------------------------------------------


# Use your Mediastack API key stored in Streamlit secrets (set it in .streamlit/secrets.toml)
# API_KEY = st.secrets["mediastack"]["MEDIASTACK_API_KEY"]  # ✅ Correct
# URL = f"http://api.mediastack.com/v1/news?access_key={API_KEY}&languages=en&keywords=disaster,earthquake,flood,hurricane,wildfire,tsunami,cyclone,landslide,volcano,storm,tornado"
def mediastack_news():
    st.markdown("<h1 style='text-align: center;'>📰 Real-Time Disaster News</h1>", unsafe_allow_html=True)
    API_KEY = st.secrets["mediastack"]["MEDIASTACK_API_KEY"]

    disaster_keywords = ["earthquake", "flood", "hurricane", "wildfire", "tsunami", "cyclone", "landslide", "volcano", "storm", "tornado"]
    all_articles = []

    for keyword in disaster_keywords:
        url = f"http://api.mediastack.com/v1/news?access_key={API_KEY}&languages=en&keywords={keyword}&limit=10"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            all_articles.extend(data.get("data", []))

    # Remove duplicate URLs
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        url = article.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)

    # Sort by published date descending
    def parse_date(article):
        try:
            return datetime.strptime(article["published_at"], "%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            return datetime.min

    sorted_articles = sorted(unique_articles, key=parse_date, reverse=True)[:5]

    if not sorted_articles:
        st.warning("No news articles found.")
    else:
        for article in sorted_articles:
            st.subheader(article.get("title", "No Title"))

            # Format date
            published = article.get("published_at")
            if published:
                try:
                    dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%S%z")
                    st.caption(f"Published on: {dt.strftime('%Y-%m-%d %I:%M %p')}")
                except Exception:
                    pass

            st.write(article.get("description", "No description available."))
            st.markdown(f"[Read full article]({article.get('url')})", unsafe_allow_html=True)
            st.markdown("---")

    # Footer Buttons
    cols = st.columns([3, 1])
    with cols[0]:
        if st.button("🔄 Reload News"):
            st.rerun()
    with cols[1]:
        if st.button("🏠 Back to Home"):
            st.session_state.page = 'home'
            st.rerun()




if "page" not in st.session_state:
    st.session_state.page = "home"
if st.session_state.page == "home":
    home()
    st.stop()
elif st.session_state.page == "news":
    mediastack_news()   
    st.stop()
elif st.session_state.page == "earthquakes":
    earthquakes()
    st.stop()
elif st.session_state.page == "earthquake_info":
    earthquake_info()
    st.stop()
elif st.session_state.page == "wildfires":
    wildfires()
    st.stop()
elif st.session_state.page == "wildfire_info":
    wildfire_info()
    st.stop()
elif st.session_state.page == "hurricanes":
    hurricanes()
    st.stop()
elif st.session_state.page == "hurricane_info":
    hurricane_info()
    st.stop()
elif st.session_state.page == "tsunamis":
    tsunamis()
    st.stop()
elif st.session_state.page == "tsunami_info":
    tsunami_info()
    st.stop()
if st.session_state.page == "profile":
    profile_page()
    st.stop()
elif st.session_state.page == "logout":
    logout_page()
    st.stop()

else:

    # Load the trained model and preprocessing objects
    loaded_model = joblib.load('random_forest_model.joblib')
    loaded_oversampler = joblib.load('oversampler.joblib')
    loaded_label_encoder = joblib.load('disaster_type_label_encoder.joblib')
    scaler = joblib.load('scaler.joblib')

    # Define the mapping of encoded labels to disaster names
    mapping_dict = {
        0: "Other",
        1: "Drought",
        2: "Earthquake",
        3: "Epidemic",
        4: "Extreme temperature",
        5: "Flood",
        6: "Fog",
        7: "Glacial lake outburst",
        8: "Impact",
        9: "Insect infestation",
        10: "Landslide",
        11: "Mass movement (dry)",
        12: "Storm",
        13: "Volcanic activity",
        14: "Wildfire",
    }

    # Define the magnitude scale mapping
    magnitude_scale_mapping = {
        0: "Km²",
        1: "Richter Scale",
        2: "Wind Speed (km/h)",
        3: "Water Level (m)",
        4: "Temperature (°C)",
        5: "Rainfall (mm)"
    }

    country_code_mapping = {0: 'Afghanistan', 1: 'Albania', 2: 'Algeria', 3: 'American Samoa', 4: 'Angola', 5: 'Anguilla', 6: 'Antigua and Barbuda', 7: 'Argentina', 
    8: 'Armenia', 9: 'Australia', 10: 'Austria', 11: 'Azerbaijan', 12: 'Azores Islands', 13: 'Bahamas (the)', 14: 'Bahrain', 15: 'Bangladesh', 
    16: 'Barbados', 17: 'Belarus', 18: 'Belgium', 19: 'Belize', 20: 'Benin', 21: 'Bermuda', 22: 'Bhutan', 23: 'Bolivia (Plurinational State of)',
    24: 'Bosnia and Herzegovina', 25: 'Botswana', 26: 'Brazil', 27: 'Brunei Darussalam', 28: 'Bulgaria', 29: 'Burkina Faso', 30: 'Burundi', 
    31: 'Cabo Verde', 32: 'Cambodia', 33: 'Cameroon', 34: 'Canada', 35: 'Canary Is', 36: 'Cayman Islands (the)', 37: 'Central African Republic', 
    38: 'Chad', 39: 'Chile', 40: 'China', 41: 'Colombia', 42: 'Comoros (the)', 43: 'Congo (the Democratic Republic of the)', 44: 'Congo (the)', 
    45: 'Cook Islands (the)', 46: 'Costa Rica', 47: 'Croatia', 48: 'Cuba', 49: 'Cyprus', 50: 'Czech Republic (the)', 51: 'Czechoslovakia', 
    52: 'Côte d’Ivoire', 53: 'Denmark', 54: 'Djibouti', 55: 'Dominica', 56: 'Dominican Republic (the)', 57: 'Ecuador', 58: 'Egypt', 59: 'El Salvador',
    60: 'Equatorial Guinea', 61: 'Eritrea', 62: 'Estonia', 63: 'Ethiopia', 64: 'Fiji', 65: 'Finland', 66: 'France', 67: 'French Guiana', 
    68: 'French Polynesia', 69: 'Gabon', 70: 'Gambia (the)', 71: 'Georgia', 72: 'Germany', 73: 'Germany Dem Rep', 74: 'Germany Fed Rep', 
    75: 'Ghana', 76: 'Greece', 77: 'Grenada', 78: 'Guadeloupe', 79: 'Guam', 80: 'Guatemala', 81: 'Guinea', 82: 'Guinea-Bissau', 83: 'Guyana', 
    84: 'Haiti', 85: 'Honduras', 86: 'Hong Kong', 87: 'Hungary', 88: 'Iceland', 89: 'India', 90: 'Indonesia', 91: 'Iran (Islamic Republic of)', 
    92: 'Iraq', 93: 'Ireland', 94: 'Isle of Man', 95: 'Israel', 96: 'Italy', 97: 'Jamaica', 98: 'Japan', 99: 'Jordan', 100: 'Kazakhstan',
    101: 'Kenya', 102: 'Kiribati', 103: "Korea (the Democratic People's Republic of)", 104: 'Korea (the Republic of)', 105: 'Kuwait', 106: 'Kyrgyzstan',
    107: "Lao People's Democratic Republic (the)", 108: 'Latvia', 109: 'Lebanon', 110: 'Lesotho', 111: 'Liberia', 112: 'Libya', 113: 'Lithuania',
    114: 'Luxembourg', 115: 'Macao', 116: 'Macedonia (the former Yugoslav Republic of)', 117: 'Madagascar', 118: 'Malawi', 119: 'Malaysia', 
    120: 'Maldives', 121: 'Mali', 122: 'Marshall Islands (the)', 123: 'Martinique', 124: 'Mauritania', 125: 'Mauritius', 126: 'Mexico', 
    127: 'Micronesia (Federated States of)', 128: 'Moldova (the Republic of)', 129: 'Mongolia', 130: 'Montenegro', 131: 'Montserrat', 132: 'Morocco', 
    133: 'Mozambique', 134: 'Myanmar', 135: 'Namibia', 136: 'Nepal', 137: 'Netherlands (the)', 138: 'Netherlands Antilles', 139: 'New Caledonia',
    140: 'New Zealand', 141: 'Nicaragua', 142: 'Niger (the)', 143: 'Nigeria', 144: 'Niue', 145: 'Northern Mariana Islands (the)', 146: 'Norway',
    147: 'Oman', 148: 'Pakistan', 149: 'Palau', 150: 'Palestine, State of', 151: 'Panama', 152: 'Papua New Guinea', 153: 'Paraguay', 154: 'Peru', 
    155: 'Philippines (the)', 156: 'Poland', 157: 'Portugal', 158: 'Puerto Rico', 159: 'Qatar', 160: 'Romania', 161: 'Russian Federation (the)', 
    162: 'Rwanda', 163: 'Réunion', 164: 'Saint Barthélemy', 165: 'Saint Helena, Ascension and Tristan da Cunha', 166: 'Saint Kitts and Nevis', 
    167: 'Saint Lucia', 168: 'Saint Martin (French Part)', 169: 'Saint Vincent and the Grenadines', 170: 'Samoa', 171: 'Sao Tome and Principe', 
    172: 'Saudi Arabia', 173: 'Senegal', 174: 'Serbia', 175: 'Serbia Montenegro', 176: 'Seychelles', 177: 'Sierra Leone', 178: 'Singapore', 
    179: 'Sint Maarten (Dutch part)', 180: 'Slovakia', 181: 'Slovenia', 182: 'Solomon Islands', 183: 'Somalia', 184: 'South Africa', 
    185: 'South Sudan', 186: 'Soviet Union', 187: 'Spain', 188: 'Sri Lanka', 189: 'Sudan (the)', 190: 'Suriname', 191: 'Swaziland',
    192: 'Sweden', 193: 'Switzerland', 194: 'Syrian Arab Republic', 195: 'Taiwan (Province of China)', 196: 'Tajikistan', 
    197: 'Tanzania, United Republic of', 198: 'Thailand', 199: 'Timor-Leste', 200: 'Togo', 201: 'Tokelau', 202: 'Tonga', 
    203: 'Trinidad and Tobago', 204: 'Tunisia', 205: 'Turkey', 206: 'Turkmenistan', 207: 'Turks and Caicos Islands (the)', 
    208: 'Tuvalu', 209: 'Uganda', 210: 'Ukraine', 211: 'United Arab Emirates (the)', 212: 'United Kingdom of Great Britain and Northern Ireland (the)', 
    213: 'United States of America (the)', 214: 'Uruguay', 215: 'Uzbekistan', 216: 'Vanuatu', 217: 'Venezuela (Bolivarian Republic of)', 
    218: 'Viet Nam', 219: 'Virgin Island (British)', 220: 'Virgin Island (U.S.)', 221: 'Wallis and Futuna', 222: 'Yemen', 223: 'Yemen Arab Rep', 
    224: 'Yemen P Dem Rep', 225: 'Yugoslavia', 226: 'Zambia', 227: 'Zimbabwe'}

    # Streamlit app
    st.title("Disaster Prediction App")

    # User inputs
    year = st.number_input("Year", min_value=1900, step=1)
    # Year dropdown displaying key:value pairs (you can customize the range or use a fixed set of years)
    # year_options = [str(year) for year in range(1900, 2023)]  # Adjust the year range if needed
    # year = st.selectbox("Year", year_options)
    # year = int(year)  

    # Magnitude scale dropdown displaying key:value pairs
    mag_scale_options = [f"{key}: {value}" for key, value in magnitude_scale_mapping.items()]
    mag_scale = st.selectbox("Magnitude Scale", mag_scale_options)
    mag_scale_index = int(mag_scale.split(":")[0])  # Extract the key from the "key: value" pair

    dis_mag_value = st.number_input("Disaster Magnitude Value")
    longitude = st.number_input("Longitude")
    latitude = st.number_input("Latitude")

    # Country dropdown displaying key:value pairs
    country_options = [f"{key}: {value}" for key, value in country_code_mapping.items()]
    country_code = st.selectbox("Country", country_options)
    country_code_index = int(country_code.split(":")[0])  # Extract the key from the "key: value" pair
    cols = st.columns([3, 1])  # Adjust the ratio as needed; here 3:1 gives more space to the Predict button
    with cols[0]:
    # Predict button
        if st.button("Predict Disaster"):
            # Prepare the data for prediction
            user_data = np.array([[year, mag_scale_index, dis_mag_value, country_code_index, longitude, latitude]])
            user_data_scaled = scaler.transform(user_data)

            # Make prediction
            predicted_label = loaded_model.predict(user_data_scaled)
            predicted_disaster_name = mapping_dict.get(int(predicted_label[0]), "Unknown")
            
            st.success(f"🚨 Predicted Disaster: {predicted_disaster_name} ({predicted_label[0]})")
    with cols[1]:
        if st.button("Back to Home"):
            st.session_state.page = 'home'
            st.rerun()
