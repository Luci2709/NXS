import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import glob
import requests
import textwrap
from streamlit_gsheets import GSheetsConnection
import uuid
import base64
import calendar
import io
import numpy as np
import time
from datetime import datetime, date, timedelta
from PIL import Image, ImageDraw

# ==============================================================================
# 🔧 ROBUST MONKEY PATCH (Fix für Component Error & Streamlit 1.40+)
# Dieser Block MUSS VOR dem Import von st_canvas stehen.
# ==============================================================================
import streamlit.elements.image as st_image
import io
import base64
from PIL import Image

# Verbindung zum Google Sheet herstellen
conn = st.connection("gsheets", type=GSheetsConnection)

def custom_image_to_url(image, width=None, clamp=False, channels="RGB", output_format="JPEG", image_id=None, allow_emoji=False):
    """
    Ersetzt die interne Streamlit-Funktion, die in 1.40+ entfernt wurde.
    Konvertiert PIL Images direkt zu Base64 Strings.
    """
    if not isinstance(image, Image.Image):
        return ""
    
    img_byte_arr = io.BytesIO()
    # Format bestimmen
    fmt = output_format.upper() if output_format else "JPEG"
    if fmt == "JPG": fmt = "JPEG"
    
    # Bild speichern
    image.save(img_byte_arr, format=fmt)
    img_byte_arr = img_byte_arr.getvalue()
    
    # Zu Base64 konvertieren
    b64_encoded = base64.b64encode(img_byte_arr).decode()
    mime = f"image/{fmt.lower()}"
    
    # Als Data-URL zurückgeben
    return f"data:{mime};base64,{b64_encoded}"

# Patch anwenden
st_image.image_to_url = custom_image_to_url

# ⚠️ JETZT ERST DIE CANVAS LIBRARY IMPORTIEREN
from streamlit_drawable_canvas import st_canvas

# ==============================================================================
# 🔐 AUTHENTICATION SYSTEM
# ==============================================================================

# User credentials (in production, use proper database/authentication)
USER_CREDENTIALS = {
    # Visitors - only dashboard access
    "visitor1": {"password": "visitor123", "role": "visitor"},
    "visitor2": {"password": "visitor123", "role": "visitor"},

    # Players - all except database and match entry
    "Luggi": {"password": "1", "role": "player"},
    "Andrei": {"password": "player123", "role": "player"},
    "Benni": {"password": "player123", "role": "player"},
    "Sofi": {"password": "player123", "role": "player"},
    "Luca": {"password": "player123", "role": "player"},
    "Remus": {"password": "player123", "role": "player"},
    
    # Coaches - full access
    "coach1": {"password": "coach123", "role": "coach"},
    "coach2": {"password": "coach123", "role": "coach"},

    # Testing - access to both coach and player features
    "testing": {"password": "test123", "role": "testing"},
}

def check_credentials(username, password):
    """Check if username/password combination is valid"""
    if username in USER_CREDENTIALS:
        if USER_CREDENTIALS[username]["password"] == password:
            return USER_CREDENTIALS[username]["role"]
    return None

def get_allowed_pages(role):
    """Return list of allowed pages for a given role"""
    if role == "visitor":
        return ["🏠 DASHBOARD"]
    elif role == "player":
        return ["🏠 DASHBOARD", "👥 COACHING", "⚽ SCRIMS", "🗺️ MAP ANALYZER", "📘 STRATEGY BOARD", "📚 RESOURCES", "📅 CALENDAR", "📊 PLAYERS"]
    elif role == "coach":
        return ["🏠 DASHBOARD", "👥 COACHING", "⚽ SCRIMS", "📝 MATCH ENTRY", "🗺️ MAP ANALYZER", "📘 STRATEGY BOARD", "📚 RESOURCES", "📅 CALENDAR", "📊 PLAYERS", "💾 DATABASE"]
    elif role == "testing":
        return ["🏠 DASHBOARD", "👥 COACHING", "⚽ SCRIMS", "📝 MATCH ENTRY", "🗺️ MAP ANALYZER", "📘 STRATEGY BOARD", "📚 RESOURCES", "📅 CALENDAR", "📊 PLAYERS", "💾 DATABASE"]
    return []

def login_page():
    """Display login page"""
    st.title("🔐 NEXUS LOGIN")

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Welcome to NEXUS")
        st.markdown("Please enter your credentials to access the system.")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            submitted = st.form_submit_button("Login", type="primary")

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    role = check_credentials(username, password)
                    if role:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.role = role
                        st.session_state.allowed_pages = get_allowed_pages(role)
                        st.success(f"Welcome {username}! Redirecting...")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

      

def logout():
    """Logout user"""
    for key in ['authenticated', 'username', 'role', 'allowed_pages']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ==============================================================================
st.set_page_config(page_title="NXS Dashboard", layout="wide", page_icon="💠")

# Check authentication first - must happen after page config
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    login_page()
    st.stop()

st.markdown("""
<style>
    /* --- GLOBAL THEME --- */
    .stApp { 
        background-color: #050505; 
        background-image: radial-gradient(circle at 50% 0%, #1a1a2e 0%, #050505 60%);
        color: #e0e0e0; 
    }
    [data-testid="stSidebar"] { 
        background-color: #080810; 
        border-right: 1px solid #333; 
    }
    
    /* --- TYPOGRAPHY & GRADIENTS --- */
    h1, h2, h3 {
        background: linear-gradient(90deg, #00BFFF 0%, #FF1493 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900 !important;
        text-transform: uppercase;
        font-family: 'Segoe UI', sans-serif;
        letter-spacing: 1px;
    }
    
    /* --- NEON CARDS & BOXES --- */
    div.stContainer {
        border-radius: 12px;
    }

    /* Stat Box (Map Analyzer) */
    .stat-box { 
        border-radius: 12px; 
        padding: 20px; 
        text-align: center; 
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.1); 
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        backdrop-filter: blur(5px);
        transition: all 0.3s ease;
    }
    .stat-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 0 20px rgba(0, 191, 255, 0.2);
    }
    .stat-val { font-size: 2.5em; font-weight: 800; color: white; text-shadow: 0 0 10px rgba(255,255,255,0.3); }
    .stat-lbl { font-size: 0.8em; text-transform: uppercase; letter-spacing: 2px; color: rgba(255,255,255,0.6); margin-top: 5px; }
    
    /* Playbook Cards */
    .pb-card {
        background: linear-gradient(90deg, #0f0f16 0%, #161625 100%);
        border: 1px solid #333;
        border-left: 4px solid #00BFFF;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        transition: all 0.3s;
    }
    .pb-card:hover {
        border-color: #FF1493;
        box-shadow: 0 0 15px rgba(255, 20, 147, 0.2);
        transform: translateX(5px);
    }

    /* --- CONFIDENCE SCALE --- */
    .conf-scroll-wrapper {
        display: flex; overflow-x: auto; padding-bottom: 15px; margin-bottom: 20px; gap: 15px;
        scrollbar-width: thin; scrollbar-color: #00BFFF #111;
    }
    .conf-card {
        flex: 0 0 170px; 
        background: #101018; 
        border-radius: 12px; overflow: hidden;
        border: 1px solid #333; text-align: center; 
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .conf-card:hover { transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.5); border-color: #666; }
    .conf-img-container { width: 100%; height: 90px; overflow: hidden; border-bottom: 1px solid #333; }
    .conf-img-container img { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.8); transition: filter 0.3s; }
    .conf-card:hover img { filter: brightness(1.1); }
    .conf-body { padding: 12px; }
    .conf-val { font-size: 1.6em; font-weight: bold; text-shadow: 0 2px 5px rgba(0,0,0,0.8); }
    
    /* --- RECENT MATCHES --- */
    .rec-card { 
        background: linear-gradient(to right, rgba(255,255,255,0.03), transparent); 
        border-left: 4px solid #555; 
        padding: 12px; margin-bottom: 10px; border-radius: 6px; 
        border-top: 1px solid rgba(255,255,255,0.05);
    }

    /* --- PROTOCOLS (IF/THEN) --- */
    .proto-box { 
        background: rgba(20,20,30,0.6); 
        border-left: 3px solid #00BFFF; 
        padding: 12px; margin-bottom: 8px; border-radius: 0 8px 8px 0; 
        border: 1px solid rgba(0,191,255,0.1);
    }
    .proto-if { color: #FFD700; font-size: 0.85em; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
    .proto-then { color: #fff; font-size: 1em; margin-top: 4px; padding-left: 10px; border-left: 1px solid #444; }

    /* Inputs */
    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
        background-color: #1a1a25;
        color: white;
        border: 1px solid #444;
    }
    div[data-testid="stSelectbox"] > div > div {
        background-color: #1a1a25;
        color: white;
    }
    
    /* Button Primary override for canvas save */
    button[kind="primary"] {
        background: linear-gradient(90deg, #00BFFF, #FF1493) !important;
        border: none !important;
        color: white !important;
        font-weight: bold !important;
    }
        /* --- VALORANT STYLE MATCH CARD (REVISED LAYOUT) --- */
.val-card {
    background-color: #121212;
    border-radius: 4px;
    margin-bottom: 8px;
    display: flex; /* Flexbox aktiviert: Elemente liegen nebeneinander */
    align-items: center;
    height: 90px;
    overflow: hidden;
    border: 1px solid #222;
    position: relative;
    transition: transform 0.2s, background-color 0.2s;
}
.val-card:hover {
    transform: translateX(4px);
    background-color: #1a1a1a;
}
.val-bar {
    width: 6px;
    height: 100%;
    flex-shrink: 0; /* Darf nicht schrumpfen */
}

/* ZONE 1: MAP & NAME */
.val-map-section {
    width: 180px; /* Feste Breite für den Map-Bereich */
    height: 100%;
    position: relative;
    flex-shrink: 0;
    margin-right: 15px;
}
.val-map-bg {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background-size: cover;
    background-position: center;
    /* Verlauf damit Text lesbar ist, aber rechts hart endet für Trennung */
    background: linear-gradient(to right, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.9) 100%);
    z-index: 0;
}
.val-map-text {
    position: absolute;
    top: 50%; left: 15px;
    transform: translateY(-50%);
    z-index: 1;
}
.val-map-name {
    font-weight: 900;
    font-size: 1.4em;
    color: white;
    text-transform: uppercase;
    line-height: 1;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
}

/* ZONE 2: COMPS (Nach Links gerückt) */
.val-comps-section {
    display: flex;
    flex-direction: column; /* Teams untereinander statt nebeneinander für Platz */
    justify-content: center;
    gap: 4px;
    margin-right: 20px;
    flex-shrink: 0;
}
.val-agent-row {
    display: flex;
    align-items: center;
    gap: 2px;
}
.val-team-label {
    font-size: 0.6em;
    color: #666;
    width: 20px;
    text-align: right;
    margin-right: 4px;
    font-weight: bold;
}
.val-agent-img {
    width: 32px; /* Etwas kleiner damit sie untereinander passen */
    height: 32px;
    border-radius: 3px;
    border: 1px solid #333;
    background: #000;
}

/* ZONE 3: STATS (Die Mitte - Der neue "Freie Platz") */
.val-stats-section {
    flex-grow: 1; /* Nimmt den restlichen Platz ein */
    display: flex;
    flex-direction: row;
    justify-content: center; /* Zentriert die Stats */
    align-items: center;
    gap: 20px; /* Abstand zwischen den Stat-Gruppen */
    color: #ccc;
    font-family: 'Segoe UI', sans-serif;
}
.stat-group {
    display: flex;
    flex-direction: column;
    align-items: center;
}
.stat-label {
    font-size: 0.65em;
    text-transform: uppercase;
    color: #777;
    letter-spacing: 1px;
    margin-bottom: 2px;
}
.stat-value {
    font-size: 0.9em;
    font-weight: 700;
    color: #eee;
}
.stat-date {
    font-size: 0.8em;
    color: #aaa;
    font-style: italic;
}

/* ZONE 4: SCORE (Rechts) */
.val-score-section {
    width: 120px;
    text-align: right;
    padding-right: 20px;
    flex-shrink: 0;
}
.val-score {
    font-weight: 900;
    font-size: 2.2em;
    line-height: 1;
}
.val-vod-link {
    font-size: 0.75em;
    font-weight: 700;
    text-transform: uppercase;
    display: block;
    margin-top: 4px;
    text-decoration: none;
    opacity: 0.7;
}
.val-vod-link:hover { opacity: 1; text-decoration: underline; }
/* --- POWER RANKING CARD DESIGN (FIXED & COMPACT) --- */
    .rank-row {
        background-color: #121212;
        border: 1px solid #222;
        border-radius: 4px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        padding: 4px 8px;         /* Etwas mehr seitliches Padding */
        height: 54px;             /* Kompakte Höhe */
        transition: transform 0.2s, background-color 0.2s;
        overflow: hidden;
    }
    .rank-row:hover {
        background-color: #1a1a1a;
        transform: translateX(4px);
        border-color: #333;
    }
    
    /* Map Bild */
    .rank-img-box {
        width: 120px;
        height: 100%;
        border-radius: 3px;
        overflow: hidden;
        margin-right: 12px;
        flex-shrink: 0;
    }
    .rank-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    /* Map Name - Schriftgröße angepasst */
    .rank-name {
        width: 80px;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        font-size: 14px;          /* Fest auf 14px gesetzt */
        color: white;
        text-transform: uppercase;
        margin-right: 10px;
        flex-shrink: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Stats Container */
    .rank-stats {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 4px;                 /* Kleiner Abstand zwischen den Balken */
    }
    
    /* Einzelne Zeile (Label - Balken - Zahl) */
    .stat-line {
        display: flex;
        align-items: center;
        height: 18px;             /* Fixe Höhe pro Zeile */
    }
    
    /* Label (RATING / WIN%) */
    .stat-label {
        width: 50px;              /* Etwas breiter damit nichts umbricht */
        color: #666;
        font-weight: 700;
        font-size: 10px;          /* Sehr klein und fein */
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Balken Hintergrund */
    .prog-bg {
        flex-grow: 1;
        height: 6px;              /* Dünner Balken */
        background-color: #252525;
        border-radius: 3px;
        margin: 0 10px;
        overflow: hidden;
    }
    
    /* Balken Füllung */
    .prog-fill {
        height: 100%;
        border-radius: 3px;
    }
    
    /* Die Zahl am Ende (WICHTIG!) */
    .stat-val {
        width: 45px;              /* Verbreitert! Vorher 30px -> zu eng */
        text-align: right;
        font-weight: 800;
        font-family: 'Consolas', 'Monaco', monospace; /* Monospace für saubere Ausrichtung */
        font-size: 12px;          /* Gut lesbare Größe */
        line-height: 1;
    }
</style>
""", unsafe_allow_html=True)

# --- PFADE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR_JSON = os.path.join(BASE_DIR, "data", "matches")
# Die Pfade zu lokalen CSVs werden hier eigentlich nicht mehr gebraucht, außer als Referenz oder für Heatmap JSONs
ASSET_DIR = os.path.join(BASE_DIR, "assets")
STRAT_IMG_DIR = os.path.join(ASSET_DIR, "strats")
PLAYBOOKS_FILE = os.path.join(BASE_DIR, "data", "playbooks.csv")
TEAM_PLAYBOOKS_FILE = os.path.join(BASE_DIR, "data", "nexus_playbooks.csv")

# Verzeichnisse erstellen
for d in [DATA_DIR_JSON, os.path.join(BASE_DIR, "data"), STRAT_IMG_DIR, os.path.join(ASSET_DIR, "maps"), os.path.join(ASSET_DIR, "agents")]:
    if not os.path.exists(d): os.makedirs(d)

OUR_TEAM = ["Trashies", "Luggi", "Umbra", "Noctis", "n0thing", "Gengar"]

# --- HELPER ---
def get_map_img(map_name, type='list'):
    """
    Lädt Map-Bilder. 
    type='list' -> assets/maps/[map]_list.png (für Banner/Dashboard)
    type='icon' -> assets/maps/[map]_icon.png (für Minimap/Whiteboard)
    """
    if not map_name or pd.isna(map_name): return None
    name_clean = str(map_name).lower().strip()
    
    # Exakter Pfad (z.B. ascent_list.png oder ascent_icon.png)
    target_path = os.path.join(ASSET_DIR, "maps", f"{name_clean}_{type}.png")
    
    if os.path.exists(target_path):
        return target_path
    
    # Fallback: Versuche generisches .png
    simple_path = os.path.join(ASSET_DIR, "maps", f"{name_clean}.png")
    if os.path.exists(simple_path):
        return simple_path
        
    return None

def get_agent_img(agent_name):
    if not agent_name or pd.isna(agent_name) or str(agent_name).lower() == 'nan': return None
    clean = str(agent_name).lower().replace("/", "").strip()
    path = os.path.join(ASSET_DIR, "agents", f"{clean}.png")
    return path if os.path.exists(path) else None

def img_to_b64(img_path):
    if not img_path or not os.path.exists(img_path): return ""
    with open(img_path, "rb") as f: data = f.read()
    return base64.b64encode(data).decode()

def get_yt_thumbnail(url):
    if not url or "youtu" not in str(url): return None
    vid_id = None
    if "v=" in url: vid_id = url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url: vid_id = url.split("youtu.be/")[1].split("?")[0]
    return f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg" if vid_id else None

def load_csv_generic(filepath, cols):
    if os.path.exists(filepath): return pd.read_csv(filepath)
    return pd.DataFrame(columns=cols)

def render_visual_selection(options, type_item, key_prefix, default=None, multi=True, key_state=None):
    """
    Renders a grid of images for selection instead of a dropdown.
    """
    selected = default if default is not None else []
    if not multi and key_state and key_state in st.session_state:
        current_selection = st.session_state[key_state]
    else:
        current_selection = default

    # CSS to center checkboxes/buttons
    st.markdown("<style>div[data-testid='stColumn'] {text-align: center;} div[data-testid='stCheckbox'] {display: inline-block;}</style>", unsafe_allow_html=True)

    cols = st.columns(6 if type_item == 'map' else 8)
    for i, opt in enumerate(options):
        with cols[i % len(cols)]:
            # Image
            if type_item == 'agent':
                img_path = get_agent_img(opt)
                if img_path:
                    try:
                        with Image.open(img_path) as img:
                            img = img.convert("RGBA")
                            img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                            
                            # Agent Colors
                            ac = {
                                "astra": "#653491", "breach": "#bc5434", "brimstone": "#d56e23", "chamber": "#e3b62d",
                                "clove": "#e882a8", "cypher": "#d6d6d6", "deadlock": "#bcc6cc", "fade": "#4c4c4c",
                                "gekko": "#b6ff59", "harbor": "#2d6e68", "iso": "#4b48ac", "jett": "#90e0ef",
                                "kay/o": "#4bb0a8", "killjoy": "#f7d336", "neon": "#2c4f9e", "omen": "#4f4f8f",
                                "phoenix": "#ff7f50", "raze": "#ff6a00", "reyna": "#b74b8e", "sage": "#52ffce",
                                "skye": "#8fbc8f", "sova": "#6fa8dc", "viper": "#32cd32", "yoru": "#334488", "vyse": "#7b68ee"
                            }
                            bg_col = ac.get(opt.lower(), "#2c003e")
                            
                            # Circular Icon with Dynamic Background
                            bg = Image.new("RGBA", (100, 100), bg_col)
                            offset = ((100 - img.width) // 2, (100 - img.height) // 2)
                            bg.paste(img, offset, img)
                            mask = Image.new("L", (100, 100), 0)
                            draw = ImageDraw.Draw(mask)
                            draw.ellipse((0, 0, 100, 100), fill=255)
                            final = Image.new("RGBA", (100, 100), (0,0,0,0))
                            final.paste(bg, (0,0), mask=mask)
                            st.image(final, width=55)
                    except: st.image(img_path, width=55)
                else: st.info(opt[:3])
            else:
                img_path = get_map_img(opt, 'list')
                if img_path: st.image(img_path, use_container_width=True)
                else: st.info(opt[:3])
            
            # Selection Mechanism
            if multi:
                if st.checkbox(" ", key=f"{key_prefix}_{opt}", value=(opt in selected), label_visibility="collapsed"):
                    if opt not in selected: selected.append(opt)
                elif opt in selected:
                    selected.remove(opt)
            else:
                # Single Select (Button acts as selector)
                if st.button("Select", key=f"{key_prefix}_{opt}"):
                    if key_state: st.session_state[key_state] = opt
                    st.rerun()
    
    return selected

# --- SPEICHER FUNKTIONEN (GOOGLE SHEETS) ---
# WICHTIG: Diese Funktionen müssen VOR der UI definiert sein

def save_matches(df_new):
    try:
        conn.update(worksheet="nexus_matches", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_player_stats(df_new):
    """Saves player stats. Tries to update, if fails (missing sheet), tries to create."""
    worksheet_name = "Premier - PlayerStats"
    try:
        # 1. Read existing data
        try:
            df_existing = conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
        except Exception:
            # If sheet is empty or doesn't exist, start fresh
            df_existing = pd.DataFrame()

        # 2. Combine new data with existing data
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        
        # Drop duplicates based on MatchID and Player to prevent re-imports
        if 'MatchID' in df_combined.columns and 'Player' in df_combined.columns:
            df_combined.drop_duplicates(subset=['MatchID', 'Player'], keep='last', inplace=True)

        # 3. Clean the ENTIRE combined DataFrame
        expected_types = {
            'Kills': int, 'Deaths': int, 'Assists': int, 'Score': int, 'Rounds': int, 'HS': float
        }
        for col, dtype in expected_types.items():
            if col in df_combined.columns:
                df_combined[col] = pd.to_numeric(df_combined[col], errors='coerce').fillna(0)
                df_combined[col] = df_combined[col].astype(dtype)

        # 4. Try to Update. If sheet missing (KeyError), try Create.
        try:
            conn.update(worksheet=worksheet_name, data=df_combined)
        except Exception as update_err:
            # Check for KeyError (Sheet not found) or if the error message contains the sheet name
            if isinstance(update_err, KeyError) or worksheet_name in str(update_err):
                conn.create(worksheet=worksheet_name, data=df_combined)
            else:
                raise update_err

        time.sleep(1)
        st.cache_data.clear()

    except Exception as e:
        st.error(f"Save Error for '{worksheet_name}': {e}")
        st.info("Check if the worksheet name in Google Sheets matches 'Premier - PlayerStats' exactly (watch out for spaces!).")

def save_scrims(df_new):
    try:
        conn.update(worksheet="scrims", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_scrim_availability(df_new):
    try:
        conn.update(worksheet="scrim_availability", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_player_todos(df_new):
    try:
        conn.update(worksheet="player_todos", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_player_messages(df_new):
    try:
        conn.update(worksheet="player_messages", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_team_playbooks(df_new):
    try:
        conn.update(worksheet="nexus_playbooks", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_legacy_playbooks(df_new):
    try:
        conn.update(worksheet="playbooks", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_pb_strats(df_new):
    try:
        conn.update(worksheet="nexus_pb_strats", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_map_theory(df_new):
    try:
        conn.update(worksheet="nexus_map_theory", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_resources(df_new):
    try:
        conn.update(worksheet="resources", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_calendar(df_new):
    try:
        conn.update(worksheet="calendar", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def save_simple_todos(df_new):
    try:
        conn.update(worksheet="todo", data=df_new); time.sleep(1); st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

def update_availability(scrim_id, player, status):
    """Update or create availability entry for a player (GSheet Version)"""
    try:
        df_avail = conn.read(worksheet="scrim_availability", ttl=0)
        if df_avail.empty or 'ScrimID' not in df_avail.columns:
            df_avail = pd.DataFrame(columns=['ScrimID', 'Player', 'Available', 'UpdatedAt'])
    except:
        df_avail = pd.DataFrame(columns=['ScrimID', 'Player', 'Available', 'UpdatedAt'])
    
    mask = (df_avail['ScrimID'] == scrim_id) & (df_avail['Player'] == player)
    
    if mask.any():
        df_avail.loc[mask, 'Available'] = status
        df_avail.loc[mask, 'UpdatedAt'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        new_entry = {
            'ScrimID': scrim_id,
            'Player': player,
            'Available': status,
            'UpdatedAt': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        df_avail = pd.concat([df_avail, pd.DataFrame([new_entry])], ignore_index=True)
    
    save_scrim_availability(df_avail)

def delete_scrim(scrim_id):
    """Delete a scrim and all its availability data (GSheet Version)"""
    try:
        df_scrims = conn.read(worksheet="scrims", ttl=0)
        if not df_scrims.empty and 'ID' in df_scrims.columns:
            df_scrims = df_scrims[df_scrims['ID'] != scrim_id]
            save_scrims(df_scrims)
        
        # Delete availability
        df_avail = conn.read(worksheet="scrim_availability", ttl=0)
        if not df_avail.empty and 'ScrimID' in df_avail.columns:
            df_avail = df_avail[df_avail['ScrimID'] != scrim_id]
            save_scrim_availability(df_avail)
    except Exception as e:
        st.error(f"Error deleting scrim: {e}")

# ==============================================================================
# 🛠️ UPDATE: PARSER MIT UTILITY & AGENT STATS
# ==============================================================================
def parse_tracker_json(file_input):
    try:
        if isinstance(file_input, str):
            with open(file_input, 'r', encoding='utf-8') as f: data = json.load(f)
        else:
            data = json.load(file_input)

        parsed_data = []
        
        # --- MODUS 1: MATCH HISTORY (Liste von Matches) ---
        matches = data.get('data', {}).get('matches', [])
        
        # Fallback: Einzelnes Match (Tracker v2)
        if not matches:
            d = data.get('data', {})
            if 'metadata' in d and 'segments' in d and 'matches' not in d:
                 if 'matchId' in d.get('metadata', {}) or 'id' in d.get('attributes', {}):
                     matches = [d]
        
        if matches:
            for m in matches:
                meta = m.get('metadata', {})
                segments = m.get('segments', [])
                
                # Suche Player Stats (alle Spieler durchgehen, Filter passiert später)
                p_segs = [s for s in segments if s.get('type') == 'player-summary']
                
                for p_seg in p_segs:
                    stats = p_seg.get('stats', {})
                    attrs = p_seg.get('attributes', {})
                    
                    # Core Stats
                    kills = stats.get('kills', {}).get('value', 0)
                    deaths = stats.get('deaths', {}).get('value', 1)
                    assists = stats.get('assists', {}).get('value', 0)
                    
                    # Aiming
                    hs = stats.get('headshots', {}).get('value', 0)
                    total_hits = hs + stats.get('bodyshots', {}).get('value', 0) + stats.get('legshots', {}).get('value', 0)
                    hs_percent = (hs / total_hits * 100) if total_hits > 0 else 0
                    
                    # Utility
                    c_grenade = stats.get('grenadeCasts', {}).get('value', 0)
                    c_abil1 = stats.get('ability1Casts', {}).get('value', 0)
                    c_abil2 = stats.get('ability2Casts', {}).get('value', 0)
                    c_ult = stats.get('ultimateCasts', {}).get('value', 0)
                    
                    # Result
                    res = "Unknown"
                    if 'result' in meta: res = meta['result']
                    elif 'hasWon' in stats: res = "Victory" if stats['hasWon']['value'] else "Defeat"
                    elif 'hasWon' in p_seg.get('metadata', {}): res = "Victory" if p_seg['metadata']['hasWon'] else "Defeat"
                    
                    parsed_data.append({
                        'MatchID': m.get('attributes', {}).get('id', 'Unknown'),
                        'Date': meta.get('modeName', 'Ranked'),
                        'Map': meta.get('mapName', 'Unknown'),
                        'Player': attrs.get('platformUserIdentifier', 'Unknown').split('#')[0],
                        'Agent': p_seg.get('metadata', {}).get('agentName', 'Unknown'),
                        'Result': res,
                        'Kills': kills, 'Deaths': deaths, 'Assists': assists,
                        'KD': kills/deaths if deaths>0 else kills,
                        'HS%': hs_percent,
                        'ADR': stats.get('damagePerRound', {}).get('value', 0),
                        'Rounds': stats.get('roundsPlayed', {}).get('value', 1),
                        'Cast_Grenade': c_grenade, 'Cast_Abil1': c_abil1,
                        'Cast_Abil2': c_abil2, 'Cast_Ult': c_ult,
                        'Total_Util': c_grenade + c_abil1 + c_abil2 + c_ult,
                        'MatchesPlayed': 1,
                        'Wins': 1 if res == "Victory" else 0
                    })

        # --- MODUS 2: PROFILE EXPORT (Aggregierte Segmente) ---
        if not parsed_data:
            segments = data.get('data', {}).get('segments', [])
            # Wir bevorzugen 'agent-top-map' Segmente für Map-Details, sonst 'agent'
            map_segs = [s for s in segments if s.get('type') == 'agent-top-map']
            if not map_segs:
                map_segs = [s for s in segments if s.get('type') == 'agent']
            
            player_name = data.get('data', {}).get('platformInfo', {}).get('platformUserIdentifier', 'Unknown').split('#')[0]
            
            for s in map_segs:
                stats = s.get('stats', {})
                meta = s.get('metadata', {})
                attrs = s.get('attributes', {})
                
                # Map Name (aus mapKey oder 'All')
                map_name = attrs.get('mapKey', 'All').capitalize() if 'mapKey' in attrs else 'All'
                
                # Utility
                c_grenade = stats.get('grenadeCasts', {}).get('value', 0)
                c_abil1 = stats.get('ability1Casts', {}).get('value', 0)
                c_abil2 = stats.get('ability2Casts', {}).get('value', 0)
                c_ult = stats.get('ultimateCasts', {}).get('value', 0)
                
                parsed_data.append({
                    'MatchID': 'Profile_Aggregated',
                    'Date': 'Aggregated',
                    'Map': map_name,
                    'Player': player_name,
                    'Agent': meta.get('name', 'Unknown'),
                    'Result': 'Aggregated',
                    'Kills': stats.get('kills', {}).get('value', 0),
                    'Deaths': stats.get('deaths', {}).get('value', 0),
                    'Assists': stats.get('assists', {}).get('value', 0),
                    'KD': stats.get('kdRatio', {}).get('value', 0),
                    'HS%': stats.get('headshotsPercentage', {}).get('value', 0),
                    'ADR': stats.get('damagePerRound', {}).get('value', 0),
                    'Rounds': stats.get('roundsPlayed', {}).get('value', 0),
                    'Cast_Grenade': c_grenade, 'Cast_Abil1': c_abil1,
                    'Cast_Abil2': c_abil2, 'Cast_Ult': c_ult,
                    'Total_Util': c_grenade + c_abil1 + c_abil2 + c_ult,
                    'MatchesPlayed': stats.get('matchesPlayed', {}).get('value', 0),
                    'Wins': stats.get('matchesWon', {}).get('value', 0)
                })
                
        return pd.DataFrame(parsed_data)
    except Exception as e:
        print(f"Parser Error: {e}")
        return pd.DataFrame() # Silent fail oder st.error(e) zum Debuggen
# ==============================================================================
# 💾 GOOGLE SHEETS DATA LOADER (MIT RATE LIMIT SCHUTZ)
# ==============================================================================

@st.cache_data(ttl=3600)
def load_data(dummy=None):
    # Hilfsfunktion mit Retry-Logik (Wartet bei Fehler 429)
    def get_sheet(worksheet_name, cols=None):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Versuche zu lesen
                df = conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
                if df.empty and cols:
                    return pd.DataFrame(columns=cols)
                
                # Ensure columns exist
                if cols:
                    for col in cols:
                        if col not in df.columns:
                            df[col] = None
                            
                return df
            except Exception as e:
                # Prüfen ob es ein Rate Limit Fehler ist (Code 429)
                if "429" in str(e) or "Quota exceeded" in str(e):
                    wait_time = (attempt + 1) * 2  # Warte 2s, dann 4s, dann 6s
                    print(f"⚠️ Google API Rate Limit bei '{worksheet_name}'. Warte {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Bei anderen Fehlern, versuche lokale CSV zu laden
                    local_path = os.path.join(BASE_DIR, "data", f"{worksheet_name}.csv")
                    if os.path.exists(local_path):
                        try:
                            df_local = pd.read_csv(local_path, encoding='utf-8')
                            print(f"⚠️ Loaded {worksheet_name} from local CSV.")
                            return df_local.dropna(how="all")
                        except Exception as e2:
                            print(f"⚠️ Failed to load local CSV for {worksheet_name}: {e2}")
                    # Wenn alles fehlschlägt -> Leeres DF
                    return pd.DataFrame(columns=cols) if cols else pd.DataFrame()
        
        # Wenn es nach 3 Versuchen nicht klappt -> Leeres DF zurückgeben
        return pd.DataFrame(columns=cols) if cols else pd.DataFrame()

    # --- DATEN LADEN (Mit kleiner Pause zwischen schweren Blöcken) ---
    
    # Block 1: Wichtige Match Daten
    df = get_sheet("nexus_matches", ['Date', 'Map', 'Result', 'Score_Us', 'Score_Enemy'])
    if not df.empty and 'Date' in df.columns:
        df['DateObj'] = pd.to_datetime(df['Date'], format="%d.%m.%Y", errors='coerce')
        for c in ['Score_Us', 'Score_Enemy', 'Atk_R_W', 'Def_R_W', 'Atk_R_L', 'Def_R_L']:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Delta'] = df['Score_Us'] - df['Score_Enemy']
    
    # Kleine Pause um API zu schonen
    time.sleep(0.5)

    # Block 2: Statistiken & Scrims
    df_p = get_sheet("Premier - PlayerStats")
    df_scrims = get_sheet("scrims", ['ID', 'Title', 'Date', 'Time', 'Map', 'Description', 'CreatedBy', 'CreatedAt', 'PlaybookLink', 'VideoLink'])
    if not df_scrims.empty:
        df_scrims['DateTimeObj'] = pd.to_datetime(df_scrims['Date'] + ' ' + df_scrims['Time'], format="%Y-%m-%d %H:%M", errors='coerce')
    
    df_availability = get_sheet("scrim_availability", ['ScrimID', 'Player', 'Available', 'UpdatedAt'])

    # Kleine Pause
    time.sleep(0.5)

    # Block 3: Player Management
    df_todos = get_sheet("player_todos", ['ID', 'Player', 'Title', 'Description', 'PlaybookLink', 'YoutubeLink', 'AssignedBy', 'AssignedAt', 'Completed', 'CompletedAt'])
    if not df_todos.empty and 'Completed' in df_todos.columns:
        df_todos['Completed'] = df_todos['Completed'].astype(str).str.lower() == 'true'

    df_messages = get_sheet("player_messages", ['ID', 'FromUser', 'ToUser', 'Message', 'SentAt', 'Read'])
    if not df_messages.empty and 'Read' in df_messages.columns:
        df_messages['Read'] = df_messages['Read'].astype(str).str.lower() == 'true'

    # Block 4: Playbooks & Content
    df_team_pb = get_sheet("nexus_playbooks", ['ID', 'Map', 'Name', 'Agent_1', 'Agent_2', 'Agent_3', 'Agent_4', 'Agent_5'])
    df_legacy_pb = get_sheet("playbooks", ['Map', 'Name', 'Link', 'Agent_1', 'Agent_2', 'Agent_3', 'Agent_4', 'Agent_5'])
    df_pb_strats = get_sheet("nexus_pb_strats", ['PB_ID', 'Strat_ID', 'Name', 'Image', 'Protocols'])
    df_theory = get_sheet("nexus_map_theory", ['Map', 'Section', 'Content', 'Image'])
    
    # Block 5: Misc
    df_res = get_sheet("resources", ['Title', 'Link', 'Category', 'Note'])
    df_cal = get_sheet("calendar", ['Date', 'Time', 'Event', 'Map', 'Type'])
    df_simple_todos = get_sheet("todo", ['Task', 'Done'])
    if not df_simple_todos.empty and 'Done' in df_simple_todos.columns:
        df_simple_todos['Done'] = df_simple_todos['Done'].astype(str).str.lower() == 'true'

    return df, df_p, df_scrims, df_availability, df_todos, df_messages, df_team_pb, df_legacy_pb, df_pb_strats, df_theory, df_res, df_cal, df_simple_todos

# ==============================================================================
# 🚀 APP START & DATEN LADEN
# ==============================================================================

# HIER WERDEN DIE DATEN GELADEN UND DIE VARIABLEN GLOBAL GESETZT
df, df_players, df_scrims, df_availability, df_todos, df_messages, df_team_pb, df_legacy_pb, df_pb_strats, df_theory, df_res, df_cal, df_simple_todos = load_data()

# Handle navigation triggers
if "trigger_navigation" in st.session_state:
    st.session_state["navigation_radio"] = st.session_state["trigger_navigation"]
    del st.session_state["trigger_navigation"]

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
    st.title("NEXUS")
    
    # --- NAVIGATION LOGIK ---
    all_pages = ["🏠 DASHBOARD", "👥 COACHING", "⚽ SCRIMS", "📝 MATCH ENTRY", "🗺️ MAP ANALYZER", "📘 STRATEGY BOARD", "📚 RESOURCES", "📅 CALENDAR", "📊 PLAYERS", "💾 DATABASE"]
    
    # Hole die erlaubten Seiten aus dem Session State (gesetzt beim Login)
    # Fallback auf alle Seiten, falls Session State leer ist
    allowed_pages = st.session_state.get('allowed_pages', all_pages)
    
    # Navigation erstellen
    page = st.radio("NAVIGATION", allowed_pages, label_visibility="collapsed", key="navigation_radio")
    
    st.markdown("---")
    
    # --- RELOAD BUTTON (MIT CACHE CLEAR) ---
    if st.button("🔄 Reload Data (if you created/deleted something)"): 
        st.cache_data.clear()
        st.rerun()
    
    # --- USER INFO & LOGOUT ---
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**User:** {st.session_state.get('username', 'Unknown')}")
    with col2:
        if st.button("🚪 Logout"):
            logout()

# ==============================================================================
# 1. DASHBOARD
# ==============================================================================
if page == "🏠 DASHBOARD":
    # Get current user info
    current_user = st.session_state.get('username', '')
    user_role = st.session_state.get('role', '')

    # --- Data for "What's Next" widget ---
    incomplete_todos = 0
    unread_messages = 0
    next_event_str = "No upcoming events."
    next_event_nav = None

    # Player-specific data
    if user_role == 'player' and current_user:
        player_todos = df_todos[(df_todos['Player'] == current_user) & (df_todos['Completed'] == False)]
        incomplete_todos = len(player_todos)
        player_messages = df_messages[(df_messages['ToUser'] == current_user) & (df_messages['Read'] == False)]
        unread_messages = len(player_messages)
    # Upcoming events (Scrims and Calendar)
    now = pd.Timestamp.now()
    upcoming_events = []
    if not df_scrims.empty and 'DateTimeObj' in df_scrims.columns:
        upcoming_scrims = df_scrims[df_scrims['DateTimeObj'] >= now].copy()
        if not upcoming_scrims.empty:
            upcoming_scrims['Type'] = 'Scrim'
            upcoming_scrims['Title'] = upcoming_scrims['Title']
            upcoming_scrims['DateTime'] = upcoming_scrims['DateTimeObj']
            upcoming_events.append(upcoming_scrims[['DateTime', 'Title', 'Type']])

    if not df_cal.empty and 'Date' in df_cal.columns and 'Time' in df_cal.columns:
        df_cal_copy = df_cal.copy()
        df_cal_copy['DateTime'] = pd.to_datetime(df_cal_copy['Date'] + ' ' + df_cal_copy['Time'], format="%d.%m.%Y %H:%M", errors='coerce')
        upcoming_cal = df_cal_copy[df_cal_copy['DateTime'] >= now]
        if not upcoming_cal.empty:
            upcoming_cal = upcoming_cal.rename(columns={'Event': 'Title'})
            upcoming_events.append(upcoming_cal[['DateTime', 'Title', 'Type']])

    if upcoming_events:
        all_upcoming = pd.concat(upcoming_events).sort_values('DateTime').iloc[0]
        event_time = all_upcoming['DateTime']
        time_delta = event_time - now
        
        if time_delta.days < 1:
            hours, rem = divmod(time_delta.seconds, 3600)
            minutes, _ = divmod(rem, 60)
            if hours > 0:
                next_event_str = f"**{all_upcoming['Title']}** in {hours}h {minutes}m"
            else:
                next_event_str = f"**{all_upcoming['Title']}** in {minutes}m"
        else:
            next_event_str = f"**{all_upcoming['Title']}** in {time_delta.days} day(s)"
        
        next_event_nav = "⚽ SCRIMS" if all_upcoming['Type'] == 'Scrim' else "📅 CALENDAR"

    st.title("PERFORMANCE DASHBOARD")

    # --- Page Layout ---
    main_col, side_col = st.columns([3.5, 1])

    with side_col:
        st.markdown("##### 🔔 WHAT'S NEXT")
        with st.container(border=True):
            if next_event_nav and st.button(f"🗓️ {next_event_str}", use_container_width=True, key="dash_nav_event"):
                st.session_state['trigger_navigation'] = next_event_nav; st.rerun()
            if incomplete_todos > 0 and st.button(f"📝 **{incomplete_todos}** pending task(s)", use_container_width=True, key="dash_nav_todo"):
                st.session_state['trigger_navigation'] = "👥 COACHING"; st.rerun()
            if unread_messages > 0 and st.button(f"💬 **{unread_messages}** unread message(s)", use_container_width=True, key="dash_nav_msg"):
                st.session_state['trigger_navigation'] = "👥 COACHING"; st.rerun()
            if not next_event_nav and incomplete_todos == 0 and unread_messages == 0:
                st.caption("All clear! ✨")

    with main_col:
        # --- Statistiken und Charts ---
        if not df.empty:
            min_date = df['DateObj'].min() if pd.notna(df['DateObj'].min()) else datetime(2024,1,1)
            c1, c2 = st.columns([1,3])
            with c1: start_d = st.date_input("Stats ab:", min_date)
            df_filt = df[df['DateObj'] >= pd.Timestamp(start_d)].copy()
            
            if not df_filt.empty:
                # --- CONFIDENCE SCALE ---
                st.divider(); st.markdown("### 📊 MAP CONFIDENCE")
                all_maps = sorted(df_filt['Map'].unique())
                sel_maps = st.multiselect("Wähle Maps:", all_maps, default=all_maps)
                conf_list = []
                for m in (sel_maps if sel_maps else all_maps):
                    md = df_filt[df_filt['Map']==m]
                    if md.empty: continue
                    g=len(md); w=len(md[md['Result']=='W']); delta=md['Delta'].sum()
                    wr=w/g*100; score=(wr*1.0)+(g*2.0)+(delta*0.5)
                    # DASHBOARD: nutzt 'list' (Banner)
                    img_p = get_map_img(m, type='list'); 
                    b64 = img_to_b64(img_p)
                    col = "#00ff80" if score>=60 else "#ffeb3b" if score>=40 else "#ff1493"
                    conf_list.append({'M':m, 'S':score, 'WR':wr, 'I':b64, 'C':col})
                
                conf_list.sort(key=lambda x: x['S'], reverse=True)
                html = "<div class='conf-scroll-wrapper'>"
                for c in conf_list:
                    img_tag = f"<img src='data:image/png;base64,{c['I']}'>" if c['I'] else ""
                    html += f"<div class='conf-card' style='border-bottom: 4px solid {c['C']}'><div class='conf-img-container'>{img_tag}</div><div class='conf-body'><div style='font-weight:bold; color:white'>{c['M']}</div><div class='conf-val' style='color:{c['C']}'>{c['S']:.1f}</div><div class='conf-sub'>{c['WR']:.0f}% WR</div></div></div>"
                st.markdown(html+"</div>", unsafe_allow_html=True)
                
                # --- TABLE ---
                # --- POWER RANKING (CUSTOM UI) ---
                st.divider()
                st.markdown("### 🏆 POWER RANKING")
                
                # Daten vorbereiten (wie vorher)
                rank_df = pd.DataFrame(conf_list).rename(columns={'M':'Map','S':'Score','WR':'Winrate'})
                
                if not rank_df.empty:
                    # Max Score finden für die Berechnung der Balkenlänge (100% Breite)
                    max_score = rank_df['Score'].max() if rank_df['Score'].max() > 0 else 1
                    
                    # Header (Optional, aber schön für Übersicht)
                    # st.caption("MAP PERFORMANCE BREAKDOWN")

                    for idx, row in rank_df.iterrows():
                        # 1. Daten holen
                        map_name = row['Map']
                        score = row['Score']
                        winrate = row['Winrate']
                        
                        # 2. Bild holen (als Base64)
                        # Wir nutzen hier 'list' (breit) oder 'icon' (quadratisch) - was du lieber magst
                        img_path = get_map_img(map_name, 'list') 
                        b64_img = img_to_b64(img_path)
                        img_html = f"<img src='data:image/png;base64,{b64_img}' class='rank-img'>" if b64_img else ""
                        
                        # 3. Balkenbreiten berechnen (in %)
                        # Score relativ zum besten Score
                        score_width = min(int((score / max_score) * 100), 100)
                        # Winrate ist einfach der Prozentwert
                        winrate_width = int(winrate)
                        
                        # 4. Farben für Balken definieren
                        # Score: Cyan (#00BFFF)
                        # Winrate: Pink (#FF1493) oder dynamisch (Grün/Rot)
                        wr_color = "#00ff80" if winrate >= 50 else "#ff4655" # Grün wenn >50%, sonst Rot
                        
                        # 5. HTML zusammenbauen
                        html_rank = f"""
                        <div class="rank-row">
                            <div class="rank-img-box">
                                {img_html}
                            </div>
                            
                            <div class="rank-name">{map_name}</div>
                            
                            <div class="rank-stats">
                                <div class="stat-line">
                                    <div class="stat-label">RATING</div>
                                    <div class="prog-bg">
                                        <div class="prog-fill" style="width: {score_width}%; background-color: #00BFFF; box-shadow: 0 0 10px rgba(0, 191, 255, 0.4);"></div>
                                    </div>
                                    <div class="stat-val" style="color: #00BFFF;">{score:.1f}</div>
                                </div>
                                
                                <div class="stat-line">
                                    <div class="stat-label">WIN %</div>
                                    <div class="prog-bg">
                                        <div class="prog-fill" style="width: {winrate_width}%; background-color: {wr_color};"></div>
                                    </div>
                                    <div class="stat-val" style="color: {wr_color};">{winrate:.0f}%</div>
                                </div>
                            </div>
                        </div>
                        """
                        
                        # Rendern ohne Zeilenumbrüche
                        st.markdown(html_rank.replace("\n", " "), unsafe_allow_html=True)

                else:
                    st.info("Noch keine Daten für das Ranking verfügbar.")
                
                # --- RECENT ---
                st.divider()
                st.markdown("### 📜 RECENT MATCHES")
                matches_to_show = df_filt.sort_values('DateObj', ascending=False).head(5)
                
                for idx, row in matches_to_show.iterrows():
                    
                    # 1. DATEN VORBEREITEN
                    res = row['Result']
                    score_us = int(row['Score_Us'])
                    score_en = int(row['Score_Enemy'])
                    
                    # Farben setzen
                    if res == 'W':
                        main_color = "#00ff80" 
                    elif res == 'L':
                        main_color = "#ff4655"
                    else:
                        main_color = "#aaaaaa"

                    # Map Bild laden
                    map_img_path = get_map_img(row['Map'], 'list')
                    b64_map = img_to_b64(map_img_path)
                    map_bg_style = f"background-image: linear-gradient(to right, rgba(0,0,0,0) 0%, rgba(18,18,18,1) 100%), url('data:image/png;base64,{b64_map}');" if b64_map else "background-color: #222;"

                    # 2. STATS EXTRAHIEREN
                    atk_w = int(row.get('Atk_R_W', 0)) if pd.notna(row.get('Atk_R_W')) else 0
                    atk_l = int(row.get('Atk_R_L', 0)) if pd.notna(row.get('Atk_R_L')) else 0
                    def_w = int(row.get('Def_R_W', 0)) if pd.notna(row.get('Def_R_W')) else 0
                    def_l = int(row.get('Def_R_L', 0)) if pd.notna(row.get('Def_R_L')) else 0
                    date_str = row['Date']

                    # 3. AGENTEN ICONS GENERIEREN
                    def get_agent_row_html(comp_prefix):
                        html = ""
                        for i in range(1, 6):
                            an = row.get(f'{comp_prefix}_{i}')
                            if pd.notna(an) and str(an) != "":
                                b64 = img_to_b64(get_agent_img(an))
                                if b64:
                                    html += f"<img src='data:image/png;base64,{b64}' class='val-agent-img' title='{an}'>"
                                else:
                                    html += f"<div class='val-agent-img' style='background:#333' title='?'></div>"
                            else:
                                 html += f"<div class='val-agent-img' style='background:transparent; border:1px dashed #333'></div>"
                        return html

                    my_agents = get_agent_row_html('MyComp')
                    en_agents = get_agent_row_html('EnComp')

                    # 4. VOD LINK
                    vod_link = row.get('VOD_Link')
                    vod_html = ""
                    if pd.notna(vod_link) and str(vod_link).startswith("http"):
                        vod_html = f'<a href="{vod_link}" target="_blank" class="val-vod-link" style="color: {main_color};">WATCH VOD ↗</a>'

                    # 5. HTML ZUSAMMENBAUEN
                    html_card = f"""
                    <div class="val-card">
                        <div class="val-bar" style="background-color: {main_color};"></div>
                        <div class="val-map-section">
                            <div class="val-map-bg" style="{map_bg_style}"></div>
                            <div class="val-map-text">
                                <div class="val-map-name">{row['Map']}</div>
                            </div>
                        </div>
                        <div class="val-comps-section">
                            <div class="val-agent-row">
                                <div class="val-team-label" style="color:#00ff80">US</div>
                                {my_agents}
                            </div>
                            <div class="val-agent-row">
                                <div class="val-team-label" style="color:#ff4655">EN</div>
                                {en_agents}
                            </div>
                        </div>
                        <div class="val-stats-section">
                            <div class="stat-group">
                                <div class="stat-label">ATTACK</div>
                                <div class="stat-value" style="color:#ff99aa">{atk_w} - {atk_l}</div>
                            </div>
                            <div class="stat-group">
                                <div class="stat-label">DEFENSE</div>
                                <div class="stat-value" style="color:#99ffcc">{def_w} - {def_l}</div>
                            </div>
                            <div class="stat-group">
                                <div class="stat-label">DATE</div>
                                <div class="stat-date">{date_str}</div>
                            </div>
                        </div>
                        <div class="val-score-section">
                            <div class="val-score" style="color: {main_color};">{score_us} : {score_en}</div>
                            {vod_html}
                        </div>
                    </div>
                    """
                    
                    st.markdown(html_card.replace("\n", " "), unsafe_allow_html=True)

            else:
                st.info("No matches found for the selected date range.")
        else:
            st.info("No match data available. Please import matches in the 'Match Entry' tab.")

# ==============================================================================
# 👥 COACHING
# ==============================================================================
elif page == "👥 COACHING":
    st.title("👥 PLAYER COACHING")

    # Get current user info
    current_user = st.session_state.get('username', '')
    user_role = st.session_state.get('role', '')
    
    # Testing role context switcher
    if user_role == 'testing':
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Switch to Coach View", type="primary"):
                st.session_state.testing_context = 'coach'
                st.rerun()
        with col2:
            if st.button("🔄 Switch to Player View", type="secondary"):
                st.session_state.testing_context = 'player'
                st.rerun()
        
        # Show current context
        current_context = st.session_state.get('testing_context', 'coach')
        st.info(f"🧪 **Testing Mode**: Currently viewing as **{current_context.upper()}**")
        user_role = current_context  # Override role for the rest of the page
        st.markdown("---")
    
    if user_role == 'coach':
        # Coach view - manage all players
        tab1, tab2, tab3 = st.tabs(["📝 Assign Todos", "💬 Send Messages", "📊 Player Overview"])
        
        with tab1:
            st.markdown("### 📝 Assign Tasks to Players")
            
            with st.form("assign_todo"):
                col1, col2 = st.columns(2)
                
                with col1:
                    player = st.selectbox("Select Player", 
                                            ["Luggi","Benni","Andrei","Luca","Sofi","Remus"],
                                            format_func=lambda x: f"🎮 {x}")
                    title = st.text_input("Task Title", placeholder="e.g., Review Ascent Defense")
                
                with col2:
                    # Playbook selection
                    all_playbooks = []
                    if not df_legacy_pb.empty:
                        legacy_pbs = [f"Legacy: {pb}" for pb in df_legacy_pb.get('Name', [])]
                        all_playbooks.extend(legacy_pbs)
                    if not df_team_pb.empty:
                        team_pbs = [f"Team: {pb}" for pb in df_team_pb.get('Name', [])]
                        all_playbooks.extend(team_pbs)
                    
                    playbook_link = st.selectbox("Link Playbook (optional)", 
                                                ["None"] + all_playbooks,
                                                help="Select a playbook to link to this task")
                    
                    youtube_link = st.text_input("YouTube Link (optional)", 
                                                placeholder="https://youtube.com/watch?v=...")
                
                description = st.text_area("Task Description", 
                                            placeholder="Detailed instructions for the player...")
                
                submitted = st.form_submit_button("📤 Assign Task")
                
                if submitted:
                    if not title or not description:
                        st.error("Please fill in title and description.")
                    else:
                        # Create todo
                        todo_id = str(uuid.uuid4())[:8]
                        
                        # Process playbook link
                        final_pb_link = ""
                        if playbook_link != "None":
                            if playbook_link.startswith("Legacy: "):
                                pb_name = playbook_link.replace("Legacy: ", "")
                                final_pb_link = f"Legacy Playbook: {pb_name}"
                            elif playbook_link.startswith("Team: "):
                                pb_name = playbook_link.replace("Team: ", "")
                                final_pb_link = f"Team Playbook: {pb_name}"
                        
                        new_todo = {
                            'ID': todo_id,
                            'Player': player,
                            'Title': title,
                            'Description': description,
                            'PlaybookLink': final_pb_link,
                            'YoutubeLink': youtube_link if youtube_link else "",
                            'AssignedBy': current_user,
                            'AssignedAt': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'Completed': False,
                            'CompletedAt': ""
                        }
                        
                        # Save to GSheets
                        updated_todos = pd.concat([df_todos, pd.DataFrame([new_todo])], ignore_index=True)
                        save_player_todos(updated_todos)
                        
                        st.success(f"Task '{title}' assigned to {player}!")
                        st.rerun()
        
        with tab2:
            st.markdown("### 💬 Chat with Players")
            
            # Select player to chat with
            chat_player = st.selectbox("Chat with", 
                                     ["Luggi","Benni","Andrei","Luca","Sofi","Remus"],
                                    format_func=lambda x: f"🎮 {x}",
                                    key="chat_player_select")
            
            if chat_player:
                st.markdown(f"### 💬 Chat with {chat_player}")
                
                # Display chat history
                chat_messages = df_messages[
                    ((df_messages['FromUser'] == current_user) & (df_messages['ToUser'] == chat_player)) |
                    ((df_messages['FromUser'] == chat_player) & (df_messages['ToUser'] == current_user))
                ].sort_values('SentAt') if not df_messages.empty else pd.DataFrame()
                
                # Chat container
                chat_container = st.container(height=400)
                
                with chat_container:
                    if chat_messages.empty:
                        st.info(f"No messages with {chat_player} yet. Start the conversation!")
                    else:
                        for _, msg in chat_messages.iterrows():
                            is_from_coach = msg['FromUser'] == current_user
                            
                            col1, col2, col3 = st.columns([1, 3, 1])
                            
                            with col1 if is_from_coach else col3:
                                sender = "You" if is_from_coach else msg['FromUser']
                                st.caption(f"**{sender}**")
                            
                            with col2:
                                # Message bubble styling
                                bubble_style = "background-color: #007bff; color: white; padding: 10px; border-radius: 15px; margin: 5px 0;" if is_from_coach else "background-color: #f1f1f1; color: black; padding: 10px; border-radius: 15px; margin: 5px 0;"
                                st.markdown(f"<div style='{bubble_style}'>{msg['Message']}</div>", unsafe_allow_html=True)
                            
                            with col3 if is_from_coach else col1:
                                st.caption(msg['SentAt'])
                
                # Message input
                message_key = f"chat_input_{chat_player}"
                if message_key not in st.session_state:
                    st.session_state[message_key] = ""
                
                # Clear input if just submitted
                if st.session_state.get('just_submitted', False):
                    st.session_state[message_key] = ""
                    st.session_state['just_submitted'] = False
                
                with st.form(key=f"chat_form_{chat_player}"):
                    message = st.text_input("Type your message...", 
                                            value=st.session_state[message_key], 
                                            key=message_key)
                    submitted = st.form_submit_button("📤 Send")
                    
                    if submitted and message.strip():
                        st.session_state['just_submitted'] = True
                        
                        message_id = str(uuid.uuid4())[:8]
                        
                        new_message = {
                            'ID': message_id,
                            'FromUser': current_user,
                            'ToUser': chat_player,
                            'Message': message.strip(),
                            'SentAt': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'Read': False
                        }
                        
                        updated_messages = pd.concat([df_messages, pd.DataFrame([new_message])], ignore_index=True)
                        save_player_messages(updated_messages)
                        
                        st.success("Message sent!")
                        st.rerun()
        
        with tab3:
            st.markdown("### 📊 Player Overview")
            
            players =  ["Luggi","Benni","Andrei","Luca","Sofi","Remus"]
            
            for player in players:
                with st.expander(f"🎮 {player}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    # Task stats
                    player_todos = df_todos[df_todos['Player'] == player]
                    completed_tasks = len(player_todos[player_todos['Completed'] == True])
                    total_tasks = len(player_todos)
                    
                    with col1:
                        st.metric("Tasks Completed", f"{completed_tasks}/{total_tasks}")
                        if total_tasks > 0:
                            completion_rate = int((completed_tasks / total_tasks) * 100)
                            st.progress(completion_rate / 100)
                            st.caption(f"{completion_rate}% completion rate")
                    
                    # Message stats
                    player_messages = df_messages[df_messages['ToUser'] == player]
                    unread_messages = len(player_messages[player_messages['Read'] == False])
                    
                    with col2:
                        st.metric("Unread Messages", unread_messages)
                        if unread_messages > 0:
                            st.warning(f"{unread_messages} unread message(s)")
                        else:
                            st.success("All messages read")
                    
                    # Scrim availability
                    player_availability = df_availability[df_availability['Player'] == player]
                    available_count = len(player_availability[player_availability['Available'] == 'Yes'])
                    total_scrims = len(df_scrims) if not df_scrims.empty else 0
                    
                    with col3:
                        if total_scrims > 0:
                            availability_rate = int((available_count / total_scrims) * 100)
                            st.metric("Scrim Availability", f"{availability_rate}%")
                            st.progress(availability_rate / 100)
                        else:
                            st.metric("Scrim Availability", "N/A")
    
    elif user_role == 'player':
        # Player view - see their own tasks and messages
        
        # Check for notifications
        player_todos = df_todos[(df_todos['Player'] == current_user) & (df_todos['Completed'] == False)]
        incomplete_todos = len(player_todos)
        player_messages = df_messages[(df_messages['ToUser'] == current_user) & (df_messages['Read'] == False)]
        unread_messages = len(player_messages)
        
        # Load playbooks for linking
        try:
            df_legacy_pb = pd.read_csv(PLAYBOOKS_FILE, encoding='utf-8')
        except:
            df_legacy_pb = pd.DataFrame()
        
        try:
            df_team_pb = pd.read_csv(TEAM_PLAYBOOKS_FILE, encoding='utf-8')
        except:
            df_team_pb = pd.DataFrame()
        
        tab1, tab2 = st.tabs(["📋 My Tasks", "💬 My Messages"])
        
        with tab1:
            st.markdown("### 📋 My Assigned Tasks")
            
            if df_todos.empty:
                st.info("No tasks assigned yet.")
            else:
                player_todos = df_todos[df_todos['Player'] == current_user]
                
                if player_todos.empty:
                    st.info("No tasks assigned to you yet.")
                else:
                    for _, todo in player_todos.iterrows():
                        completed = todo['Completed']
                        status_icon = "✅" if completed else "⏳"
                        
                        with st.expander(f"{status_icon} {todo['Title']}", expanded=not completed):
                            st.markdown(f"**Assigned by:** {todo['AssignedBy']}")
                            st.markdown(f"**Assigned:** {todo['AssignedAt']}")
                            st.markdown(f"**Description:** {todo['Description']}")
                            
                            if todo['PlaybookLink']:
                                if todo['PlaybookLink'].startswith("Team Playbook: "):
                                    pb_name = todo['PlaybookLink'].replace("Team Playbook: ", "")
                                    if not df_team_pb.empty:
                                        matching_pb = df_team_pb[df_team_pb['Name'] == pb_name]
                                        if not matching_pb.empty:
                                            pb_id = matching_pb.iloc[0]['ID']
                                            if st.button(f"📖 Open Playbook: {pb_name}", key=f"open_pb_{todo['ID']}"):
                                                st.session_state["trigger_navigation"] = "📘 STRATEGY BOARD"
                                                st.session_state['sel_pb_id'] = pb_id
                                                st.rerun()
                                        else:
                                            st.markdown(f"**📖 Playbook:** {todo['PlaybookLink']} (not found)")
                                    else:
                                        st.markdown(f"**📖 Playbook:** {todo['PlaybookLink']}")
                                elif todo['PlaybookLink'].startswith("Legacy Playbook: "):
                                    pb_name = todo['PlaybookLink'].replace("Legacy Playbook: ", "")
                                    if not df_legacy_pb.empty:
                                        matching_pb = df_legacy_pb[df_legacy_pb['Name'] == pb_name]
                                        if not matching_pb.empty:
                                            pb_link = matching_pb.iloc[0].get('Link', '')
                                            if pb_link:
                                                st.markdown(f"**📖 Playbook:** [{pb_name}]({pb_link})")
                                            else:
                                                st.markdown(f"**📖 Playbook:** {pb_name}")
                                        else:
                                            st.markdown(f"**📖 Playbook:** {todo['PlaybookLink']} (not found)")
                                    else:
                                        st.markdown(f"**📖 Playbook:** {todo['PlaybookLink']}")
                                else:
                                    st.markdown(f"**📖 Playbook:** {todo['PlaybookLink']}")
                            
                            if todo['YoutubeLink']:
                                st.markdown(f"**📺 YouTube:** [{todo['YoutubeLink']}]({todo['YoutubeLink']})")
                            
                            if not completed:
                                if st.button("✅ Mark as Completed", key=f"complete_{todo['ID']}"):
                                    # Mark as completed
                                    df_todos.loc[df_todos['ID'] == todo['ID'], 'Completed'] = True
                                    df_todos.loc[df_todos['ID'] == todo['ID'], 'CompletedAt'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    save_player_todos(df_todos)
                                    st.success("Task marked as completed!")
                                    st.rerun()
                            else:
                                st.success(f"✅ Completed on {todo['CompletedAt']}")
        
        with tab2:
            st.markdown("### 💬 Chat with Coaches")
            
            # Get unique coaches who have messaged this player
            coach_conversations = df_messages[
                (df_messages['ToUser'] == current_user) | (df_messages['FromUser'] == current_user)
            ]['FromUser'].unique() if not df_messages.empty else []
            
            coach_conversations = [c for c in coach_conversations if c != current_user]
            
            if not coach_conversations:
                st.info("No conversations yet. Coaches will reach out to you here!")
            else:
                # Select coach to chat with
                selected_coach = st.selectbox("Chat with", 
                                                coach_conversations,
                                                format_func=lambda x: f"👨‍🏫 {x}",
                                                key="player_chat_select")
                
                if selected_coach:
                    st.markdown(f"### 💬 Chat with {selected_coach}")
                    
                    # Display chat history
                    chat_messages = df_messages[
                        ((df_messages['FromUser'] == current_user) & (df_messages['ToUser'] == selected_coach)) |
                        ((df_messages['FromUser'] == selected_coach) & (df_messages['ToUser'] == current_user))
                    ].sort_values('SentAt')
                    
                    # Chat container
                    chat_container = st.container(height=400)
                    
                    with chat_container:
                        if chat_messages.empty:
                            st.info(f"No messages with {selected_coach} yet.")
                        else:
                            for _, msg in chat_messages.iterrows():
                                is_from_player = msg['FromUser'] == current_user
                                
                                col1, col2, col3 = st.columns([1, 3, 1])
                                
                                with col1 if is_from_player else col3:
                                    sender = "You" if is_from_player else msg['FromUser']
                                    st.caption(f"**{sender}**")
                                
                                with col2:
                                    # Message bubble styling
                                    bubble_style = "background-color: #28a745; color: white; padding: 10px; border-radius: 15px; margin: 5px 0;" if is_from_player else "background-color: #f1f1f1; color: black; padding: 10px; border-radius: 15px; margin: 5px 0;"
                                    st.markdown(f"<div style='{bubble_style}'>{msg['Message']}</div>", unsafe_allow_html=True)
                                
                                with col3 if is_from_player else col1:
                                    st.caption(msg['SentAt'])
                    
                    # Mark messages as read
                    unread_messages = chat_messages[
                        (chat_messages['ToUser'] == current_user) & (chat_messages['Read'] == False)
                    ]
                    
                    if not unread_messages.empty:
                        if st.button(f"Mark {len(unread_messages)} messages as read", key=f"mark_read_{selected_coach}"):
                            for msg_id in unread_messages['ID']:
                                df_messages.loc[df_messages['ID'] == msg_id, 'Read'] = True
                            save_player_messages(df_messages)
                            st.success("Messages marked as read!")
                            st.rerun()

# ==============================================================================
# ⚽ SCRIMS
# ==============================================================================
elif page == "⚽ SCRIMS":
    st.title("⚽ SCRIM SCHEDULER")
    
    current_user = st.session_state.get('username', '')
    user_role = st.session_state.get('role', '')
    
    tabs = ["📅 View Scrims"]
    if user_role == 'coach':
        tabs.append("➕ Create Scrim")
    
    tab1, *other_tabs = st.tabs(tabs)
    
    with tab1:
        st.markdown("### 📅 Upcoming Scrims")
        if df_scrims.empty:
            st.info("No scrims scheduled yet.")
        else:
            df_scrims_sorted = df_scrims[df_scrims['DateTimeObj'] >= pd.Timestamp.now()].sort_values('DateTimeObj', ascending=True)
            if df_scrims_sorted.empty:
                st.info("No upcoming scrims. Check the 'Create Scrim' tab to schedule one.")
            
            for _, scrim in df_scrims_sorted.iterrows():
                scrim_id = scrim['ID']
                with st.container(border=True):
                    c1, c2 = st.columns([1, 2.5])
                    with c1:
                        map_img = get_map_img(scrim.get('Map'), 'list')
                        if map_img: st.image(map_img)
                        else: st.markdown(f"**🗺️ {scrim.get('Map', 'N/A')}**")
                    
                    with c2:
                        st.markdown(f"#### {scrim['Title']}")
                        st.caption(f"🗓️ {scrim['Date']} at {scrim['Time']} | Created by {scrim['CreatedBy']}")
                        if pd.notna(scrim.get('Description')) and scrim['Description']:
                            st.markdown(f"> _{scrim['Description']}_")
                        
                        # Links
                        l1, l2 = st.columns(2)
                        pb_link = scrim.get('PlaybookLink')
                        if pd.notna(pb_link) and pb_link and pb_link != "None":
                            if st.button(f"📖 Open Playbook", key=f"pb_{scrim_id}", use_container_width=True):
                                if pb_link.startswith("Team: "):
                                    pb_name = pb_link.replace("Team: ", "")
                                    pb_id = df_team_pb[df_team_pb['Name'] == pb_name].iloc[0]['ID']
                                    st.session_state['sel_pb_id'] = pb_id
                                    st.session_state['trigger_navigation'] = "📘 STRATEGY BOARD"
                                    st.rerun()
                        
                        vid_link = scrim.get('VideoLink')
                        if pd.notna(vid_link) and vid_link:
                            l2.link_button("📺 Watch Video", vid_link, use_container_width=True)

                        st.markdown("---")
                        
                        # Availability
                        avail_data = df_availability[df_availability['ScrimID'] == scrim_id]
                        available_players = avail_data[avail_data['Available'] == 'Yes']['Player'].tolist()
                        
                        st.markdown(f"**Availability ({len(available_players)}/{len(OUR_TEAM)})**")
                        st.progress(len(available_players) / len(OUR_TEAM) if OUR_TEAM else 0, text=f"{', '.join(available_players) if available_players else 'None'}")

                        # Player actions
                        if user_role != 'coach':
                            st.caption("Your Status:")
                            b1, b2, b3 = st.columns(3)
                            if b1.button("✅ Yes", key=f"yes_{scrim_id}", use_container_width=True): update_availability(scrim_id, current_user, "Yes"); st.rerun()
                            if b2.button("🤔 Maybe", key=f"maybe_{scrim_id}", use_container_width=True): update_availability(scrim_id, current_user, "Maybe"); st.rerun()
                            if b3.button("❌ No", key=f"no_{scrim_id}", use_container_width=True): update_availability(scrim_id, current_user, "No"); st.rerun()
                        
                        # Coach actions
                        if user_role == 'coach':
                            if st.button("🗑️ Delete Scrim", key=f"del_{scrim_id}", use_container_width=True):
                                delete_scrim(scrim_id); st.rerun()

    if user_role == 'coach':
        with other_tabs[0]:
            st.markdown("### ➕ Create New Scrim")
            with st.form("create_scrim"):
                c1, c2 = st.columns(2)
                with c1:
                    title = st.text_input("Scrim Title", placeholder="e.g., Weekly Scrim vs Team X")
                    date = st.date_input("Date", min_value=datetime.today().date())
                    time = st.time_input("Time")
                with c2:
                    map_name = st.selectbox("Map", sorted(df['Map'].unique()) if not df.empty else ["Ascent"])
                    description = st.text_area("Description", placeholder="e.g., Focus on B-Site retakes")
                
                st.markdown("---")
                st.markdown("##### Optional Links")
                c3, c4 = st.columns(2)
                with c3:
                    all_playbooks = ["None"]
                    if not df_team_pb.empty: all_playbooks.extend([f"Team: {pb}" for pb in df_team_pb.get('Name', [])])
                    if not df_legacy_pb.empty: all_playbooks.extend([f"Legacy: {pb}" for pb in df_legacy_pb.get('Name', [])])
                    playbook_link = st.selectbox("Link Playbook", all_playbooks)
                with c4:
                    video_link = st.text_input("Video Link (VOD, YouTube, etc.)")

                if st.form_submit_button("Create Scrim", type="primary", use_container_width=True):
                    if not title: st.error("Please enter a scrim title.")
                    else:
                        scrim_id = str(uuid.uuid4())[:8]
                        new_scrim = {
                            'ID': scrim_id, 'Title': title, 'Date': date.strftime("%Y-%m-%d"),
                            'Time': time.strftime("%H:%M"), 'Map': map_name, 'Description': description,
                            'CreatedBy': current_user, 'CreatedAt': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'PlaybookLink': playbook_link if playbook_link != "None" else "",
                            'VideoLink': video_link
                        }
                        updated = pd.concat([df_scrims, pd.DataFrame([new_scrim])], ignore_index=True)
                        save_scrims(updated)
                        st.success(f"Scrim '{title}' created!"); st.rerun()

# ==============================================================================
# 2. MATCH ENTRY (AUTO PLAYER STATS)
# ==============================================================================
elif page == "📝 MATCH ENTRY":
    st.header("Match Import")
    if 'fd' not in st.session_state: st.session_state['fd'] = {'d':datetime.today(), 'm':'Ascent', 'r':'W', 'us':13, 'en':8, 'mid':'', 'vod':'', 'my':[""]*5, 'en':[""]*5, 'hm':None, 'p_stats':[]}

    with st.expander("📂 JSON Import (Auto-Stats)", expanded=True):
        up = st.file_uploader("Tracker JSON", type=['json'], key="json")
        if up:
            try:
                data = json.load(up); meta = data['data']['metadata']; segs = data['data']['segments']
                mid = meta.get('matchId', f"J_{int(datetime.now().timestamp())}")
                mid = meta.get('matchId') or data['data'].get('attributes', {}).get('id') or f"J_{int(datetime.now().timestamp())}"
                
                my_tid = None
                # Team ID
                for s in segs:
                    if s['type']=='player-summary' and any(t.lower() in s['attributes']['platformUserIdentifier'].lower() for t in OUR_TEAM):
                        my_tid = s['metadata']['teamId']; break
                
                if my_tid:
                    rw=0; rl=0; my_c=[]; en_c=[]; heatmap=[]; p_stats=[]
                    
                    for s in segs:
                        if s['type']=='round-summary':
                            w = s.get('attributes',{}).get('winningTeamId') or s.get('metadata',{}).get('winningTeamId')
                            if w: (rw:=rw+1) if w==my_tid else (rl:=rl+1)
                            w = s.get('attributes',{}).get('winningTeamId') or \
                                s.get('metadata',{}).get('winningTeamId') or \
                                s.get('stats',{}).get('winningTeam',{}).get('value')
                            if w: 
                                if w==my_tid: rw+=1 
                                else: rl+=1
                        
                        if s['type']=='player-summary':
                            ag = s['metadata']['agentName']; name = s['attributes']['platformUserIdentifier']
                            if s['metadata']['teamId']==my_tid: my_c.append(ag)
                            else: en_c.append(ag)
                            
                            # EXTRACT STATS
                            if any(t.lower() in name.lower() for t in OUR_TEAM):
                                sts = s['stats']
                                rounds = rw + rl if (rw+rl) > 0 else 1
                                p_stats.append({
                                    'MatchID': mid, 'Date': datetime.today().strftime("%d.%m.%Y"),
                                    'Map': meta.get('mapName'), 'Player': name.split('#')[0], 'Agent': ag,
                                    'Kills': sts.get('kills', {}).get('value', 0),
                                    'Deaths': sts.get('deaths', {}).get('value', 0),
                                    'Assists': sts.get('assists', {}).get('value', 0),
                                    'Score': sts.get('score', {}).get('value', 0), 'Rounds': rounds,
                                    'HS': sts.get('hsAccuracy', {}).get('value', 0)
                                })

                        if s['type']=='player-round-kills':
                            v=s['attributes']['opponentPlatformUserIdentifier']; k=s['attributes']['platformUserIdentifier']
                            w=s['metadata']['weaponName']; r=s['attributes'].get('round',0)
                            if any(t.lower() in v.lower() for t in OUR_TEAM) and 'opponentLocation' in s['metadata']:
                                heatmap.append({'X':s['metadata']['opponentLocation']['x'], 'Y':s['metadata']['opponentLocation']['y'], 'Player':v, 'Type':'Death', 'Weapon':w, 'Round':r})
                            if any(t.lower() in k.lower() for t in OUR_TEAM) and 'location' in s['metadata']:
                                heatmap.append({'X':s['metadata']['location']['x'], 'Y':s['metadata']['location']['y'], 'Player':k, 'Type':'Kill', 'Weapon':w, 'Round':r})

                    st.session_state['fd'].update({'m':meta.get('mapName','Ascent'), 'us':int(rw), 'en':int(rl), 'r':'W' if rw>rl else 'L' if rl>rw else 'D', 'mid':mid, 'hm':heatmap, 'p_stats':p_stats})
                    while len(my_c)<5: my_c.append(""); 
                    while len(en_c)<5: en_c.append("")
                    st.session_state['fd']['my']=my_c[:5]; st.session_state['fd']['en']=en_c[:5]
                    st.success(f"✅ Loaded! Stats for {len(p_stats)} players ready.")
                else: st.error("Team not found")
            except Exception as e: st.error(str(e))

    d = st.session_state['fd']
    with st.form("e"):
        c1,c2=st.columns(2)
        with c1:
            maps=sorted(["Ascent","Bind","Haven","Split","Lotus","Sunset","Abyss","Pearl","Fracture","Icebox","Breeze","Corrode"])
            try: mx=maps.index(d['m'])
            except: mx=0
            dt=st.date_input("D",d['d']); mp=st.selectbox("M",maps,index=mx)
            ags = sorted([os.path.basename(x).replace(".png","").capitalize() for x in glob.glob(os.path.join(ASSET_DIR, "agents", "*.png"))])
            ac=st.columns(5); my_final=[]
            for i in range(5):
                pr=d['my'][i]; idx=0
                if pr: 
                    try: idx=ags.index(pr.capitalize())+1
                    except: pass
                my_final.append(ac[i].selectbox(f"A{i}",[""]+ags,index=idx))
        with c2:
            ro=["W","L","D"]; ri=ro.index(d['r'])
            re=st.radio("R",ro,index=ri,horizontal=True)
            su=int(d['us']) if isinstance(d['us'],(int,float)) else 0
            se=int(d['en']) if isinstance(d['en'],(int,float)) else 0
            us=st.number_input("U",0,25,su); en=st.number_input("E",0,25,se)
            mi=st.text_input("ID",d['mid']); vo=st.text_input("VOD",d['vod'])
            en_f=d['en']

        with st.expander("Details"):
            rc1,rc2=st.columns(2)
            aw=rc1.number_input("AW",0); al=rc1.number_input("AL",0)
            dw=rc2.number_input("DW",0); dl=rc2.number_input("DL",0)

        if st.form_submit_button("SAVE"):
            if d['hm']: pd.DataFrame(d['hm']).to_csv(os.path.join(BASE_DIR,"data",f"Locs_{mi}.csv"),index=False)
            row={'Date':dt.strftime("%d.%m.%Y"),'Map':mp,'Result':re,'Score_Us':us,'Score_Enemy':en,'MatchID':mi,'Source':'Tracker' if d['hm'] else 'Manual','VOD_Link':vo,'Atk_R_W':aw,'Atk_R_L':al,'Def_R_W':dw,'Def_R_L':dl}
            for i in range(5): row[f'MyComp_{i+1}']=my_final[i]; row[f'EnComp_{i+1}']=en_f[i] if i<len(en_f) else ""
            
            # Save Matches to GSheets
            old = df # Loaded from GSheets
            updated_matches = pd.concat([old,pd.DataFrame([row])],ignore_index=True)
            save_matches(updated_matches)
            
            # Save Player Stats to GSheets
            if d['p_stats']:
                ps_old = df_players # Loaded from GSheets
                updated_stats = pd.concat([ps_old, pd.DataFrame(d['p_stats'])], ignore_index=True)
                save_player_stats(updated_stats)
                
            st.success("Saved!"); st.cache_data.clear(); st.rerun()

# ==============================================================================
# 3. MAP ANALYZER
# ==============================================================================
elif page == "🗺️ MAP ANALYZER":
    st.title("TACTICAL BOARD")
    if not df.empty:
        # --- VISUAL MAP SELECTOR ---
        if 'ana_map' not in st.session_state: 
            st.session_state.ana_map = sorted(df['Map'].unique())[0] if not df.empty else "Ascent"
        
        with st.expander("🗺️ SELECT MAP", expanded=True):
            render_visual_selection(sorted(df['Map'].unique()), 'map', 'ana_sel', multi=False, key_state='ana_map')
        
        sel_map = st.session_state.ana_map
        m_df = df[df['Map'] == sel_map]
        head = get_map_img(sel_map, 'list'); 
        if head: st.image(head, use_container_width=True)
        
        wins = len(m_df[m_df['Result']=='W']); g = len(m_df)
        aw = m_df['Atk_R_W'].sum(); al = m_df['Atk_R_L'].sum()
        dw = m_df['Def_R_W'].sum(); dl = m_df['Def_R_L'].sum()
        wr = wins/g*100 if g>0 else 0
        awr = aw/(aw+al)*100 if (aw+al)>0 else 0
        dwr = dw/(dw+dl)*100 if (dw+dl)>0 else 0
        
        def get_col(v):
            if v >= 55: return "rgba(0, 255, 128, 0.15)", "#00ff80"
            elif v >= 45: return "rgba(255, 235, 59, 0.15)", "#ffeb3b"
            else: return "rgba(255, 20, 147, 0.15)", "#ff1493"

        c1, c2, c3 = st.columns(3)
        bg,bo=get_col(wr); c1.markdown(f"<div class='stat-box' style='background:{bg};border-color:{bo}'><div class='stat-val'>{wr:.1f}%</div><div class='stat-lbl'>WINRATE</div></div>", unsafe_allow_html=True)
        bg,bo=get_col(awr); c2.markdown(f"<div class='stat-box' style='background:{bg};border-color:{bo}'><div class='stat-val'>{awr:.1f}%</div><div class='stat-lbl'>ATK WIN%</div></div>", unsafe_allow_html=True)
        bg,bo=get_col(dwr); c3.markdown(f"<div class='stat-box' style='background:{bg};border-color:{bo}'><div class='stat-val'>{dwr:.1f}%</div><div class='stat-lbl'>DEF WIN%</div></div>", unsafe_allow_html=True)
        
        st.divider(); st.subheader("📍 HEATMAP ANALYSIS")
        
        match_lookup = {}
        for idx, row in m_df.iterrows():
            mid = str(row['MatchID'])
            if os.path.exists(os.path.join(BASE_DIR, "data", f"Locs_{mid}.csv")):
                match_lookup[f"{row['Date']} ({row['Result']})"] = mid
        
        if match_lookup:
            c_sel, c_opt, c_side = st.columns([2, 1, 1])
            with c_sel: sels = st.multiselect("Matches:", list(match_lookup.keys()), default=list(match_lookup.keys())[:1])
            with c_opt: metric = st.radio("Metric:", ["Deaths", "Kills"], horizontal=True)
            with c_side: side_filter = st.selectbox("Side:", ["All", "First Half", "Second Half"])
            
            if sels:
                dfs = []
                for l in sels:
                    try: dfs.append(pd.read_csv(os.path.join(BASE_DIR,"data",f"Locs_{match_lookup[l]}.csv")))
                    except: pass
                if dfs:
                    dfh = pd.concat(dfs, ignore_index=True)
                    if 'Type' not in dfh.columns: dfh['Type'] = 'Death'
                    target = 'Kill' if "Kills" in metric else 'Death'
                    dfh = dfh[dfh['Type'] == target]
                    if 'Round' in dfh.columns:
                        if side_filter == "First Half": dfh = dfh[dfh['Round'] <= 12]
                        elif side_filter == "Second Half": dfh = dfh[dfh['Round'] > 12]
                    
                    col_p = 'Player' if 'Player' in dfh.columns else 'Victim'
                    players = sorted(dfh[col_p].astype(str).unique())
                    sel_p = st.multiselect("Filter Player:", players)
                    if sel_p: dfh = dfh[dfh[col_p].isin(sel_p)]
                    else:
                        pat = '|'.join([p.lower() for p in OUR_TEAM])
                        dfh = dfh[dfh[col_p].str.lower().str.contains(pat, na=False)]

                    if not dfh.empty:
                        try:
                            try:
                                r = requests.get("https://valorant-api.com/v1/maps", timeout=3)
                                if r.status_code == 200:
                                    mapi = next((m for m in r.json()['data'] if m['displayName'].lower() == sel_map.lower()), None)
                                else: mapi = None
                            except: mapi = None

                            if mapi:
                                S = 1024
                                dfh['PX'] = (dfh['Y'] * mapi['xMultiplier'] + mapi['xScalarToAdd']) * S
                                dfh['PY'] = (dfh['X'] * mapi['yMultiplier'] + mapi['yScalarToAdd']) * S
                                fig = px.scatter(dfh, x='PX', y='PY', color=col_p, symbol='Weapon', width=700, height=700)
                                icon = get_map_img(sel_map, 'icon')
                                if icon:
                                    img = Image.open(icon)
                                    fig.add_layout_image(dict(source=img, xref="x", yref="y", x=0, y=0, sizex=S, sizey=S, sizing="stretch", layer="below"))
                                fig.update_layout(xaxis=dict(visible=False, range=[0,S]), yaxis=dict(visible=False, range=[S,0], scaleanchor="x"), margin=dict(l=0,r=0,t=0,b=0))
                                st.plotly_chart(fig)
                        except Exception as e: st.error(f"Map Error: {e}")
        else: st.info("No Heatmaps.")
        
        st.divider(); st.subheader("History")
        for idx, row in m_df.sort_values('DateObj', ascending=False).iterrows():
            with st.expander(f"{'✅' if row['Result']=='W' else '❌'} {row['Date']} | {int(row['Score_Us'])}-{int(row['Score_Enemy'])}"):
                c1,c2,c3=st.columns([2,2,1])
                with c1:
                    st.caption("NEXUS"); cols=st.columns(5)
                    for i in range(1,6):
                        ag=row.get(f'MyComp_{i}')
                        if pd.notna(ag): 
                            p=get_agent_img(ag); 
                            if p: cols[i-1].image(p, width=35)
                with c2:
                    st.caption("ENEMY"); cols=st.columns(5)
                    for i in range(1,6):
                        ag=row.get(f'EnComp_{i}')
                        if pd.notna(ag) and str(ag).strip()!="":
                            p=get_agent_img(ag); 
                            if p: cols[i-1].image(p, width=35)
                with c3:
                    st.write(f"ATK: {int(row.get('Atk_R_W',0))}/{int(row.get('Atk_R_L',0))}")
                    st.write(f"DEF: {int(row.get('Def_R_W',0))}/{int(row.get('Def_R_L',0))}")
                    if pd.notna(row.get('VOD_Link')): st.link_button("📺", row['VOD_Link'])

# ==============================================================================
# 4. STRATEGY BOARD
# ==============================================================================
elif page == "📘 STRATEGY BOARD":
    st.title("COMMAND CENTER")
    
    if 'sel_pb_id' not in st.session_state: st.session_state['sel_pb_id'] = None

    # Load Data (Variables are already loaded globally: df_team_pb, df_pb_strats, df_theory)
    
    # TABS (INTEGRATION OF WHITEBOARD)
    tab_playbooks, tab_whiteboard, tab_theory, tab_links = st.tabs(["🧠 TACTICAL PLAYBOOKS", "🎨 TACTICAL BOARD", "📜 MAP THEORY", "🔗 EXTERNAL LINKS"])

    # --------------------------------------------------------------------------
    # TAB 1: TACTICAL PLAYBOOKS
    # --------------------------------------------------------------------------
    with tab_playbooks:
        if st.session_state['sel_pb_id'] is None:
            c1, c2 = st.columns([3, 1])
            with c1: st.subheader("Active Playbooks")
            with c2: 
                with st.popover("➕ New Playbook"):
                    with st.form("create_pb"):
                        pm = st.selectbox("Map", sorted(df['Map'].unique()) if not df.empty else ["Ascent"])
                        pn = st.text_input("Playbook Name (e.g. 'Standard Default')")
                        st.caption("Select Composition:")
                        ac = st.columns(5)
                        ags = sorted([os.path.basename(x).replace(".png","").capitalize() for x in glob.glob(os.path.join(ASSET_DIR, "agents", "*.png"))])
                        sel_ags = [ac[i].selectbox(f"P{i+1}", [""]+ags, key=f"n_pb_{i}") for i in range(5)]
                        
                        if st.form_submit_button("Create System"):
                            new_id = str(uuid.uuid4())
                            new_row = {'ID': new_id, 'Map': pm, 'Name': pn}
                            for i in range(5): new_row[f'Agent_{i+1}'] = sel_ags[i]
                            
                            updated = pd.concat([df_team_pb, pd.DataFrame([new_row])], ignore_index=True)
                            save_team_playbooks(updated)
                            st.rerun()

            if not df_team_pb.empty:
                for idx, row in df_team_pb.iterrows():
                    map_img = get_map_img(row['Map'], 'list')
                    b64_map = img_to_b64(map_img)
                    ag_html = ""
                    for i in range(1, 6):
                        a = row.get(f'Agent_{i}')
                        if a and pd.notna(a):
                            ab64 = img_to_b64(get_agent_img(a))
                            if ab64: ag_html += f"<img src='data:image/png;base64,{ab64}' style='width:35px; height:35px; border-radius:50%; border:2px solid #111; margin-right:-10px; z-index:{i}'>"
                    
                    st.markdown(f"""<div class='pb-card'><div style="display:flex;align-items:center;gap:20px;"><div style="width:80px;height:50px;border-radius:5px;background-image:url('data:image/png;base64,{b64_map}');background-size:contain;background-position:center;border:1px solid #444;"></div><div><div style="color:#00BFFF;font-weight:bold;font-size:1.1em;text-transform:uppercase;">{row['Name']}</div><div style="color:#666;font-size:0.8em;">{row['Map']}</div></div><div style="margin-left:auto;padding-right:10px;">{ag_html}</div></div></div>""", unsafe_allow_html=True)
                    if st.button(f"OPEN TACTICS >>", key=f"btn_{row['ID']}"):
                        st.session_state['sel_pb_id'] = row['ID']; st.rerun()
            else:
                st.info("No Playbooks defined yet.")

        else:
            # Single Playbook
            pb = df_team_pb[df_team_pb['ID'] == st.session_state['sel_pb_id']].iloc[0]
            st.button("⬅ BACK TO LOBBY", on_click=lambda: st.session_state.update({'sel_pb_id': None}))
            
            header_col1, header_col2 = st.columns([1, 4])
            with header_col1: st.image(get_map_img(pb['Map'], 'list'), width='stretch')
            with header_col2:
                st.markdown(f"<h1 style='margin:0'>{pb['Name']} <span style='font-size:0.5em; color:#666'>//{pb['Map']}</span></h1>", unsafe_allow_html=True)
                cols = st.columns(10)
                for i in range(1,6):
                    ag = pb.get(f'Agent_{i}'); 
                    if ag: cols[i-1].image(get_agent_img(ag), width=50)

            st.divider(); my_strats = df_pb_strats[df_pb_strats['PB_ID'] == pb['ID']]
            
            with st.expander("➕ ADD NEW STRATEGY / SET PLAY (IMAGE UPLOAD)"):
                with st.form("add_pb_strat"):
                    sn = st.text_input("Strategy Name")
                    si = st.file_uploader("Sketch", type=['png', 'jpg'])
                    if st.form_submit_button("Add"):
                        if sn and si:
                            fname = f"PB_{pb['ID'][:8]}_{sn}_{int(datetime.now().timestamp())}.png".replace(" ", "_")
                            with open(os.path.join(STRAT_IMG_DIR, fname), "wb") as f: f.write(si.getbuffer())
                            new_strat = {'PB_ID': pb['ID'], 'Strat_ID': str(uuid.uuid4()), 'Name': sn, 'Image': fname, 'Protocols': '[]'}
                            
                            updated = pd.concat([df_pb_strats, pd.DataFrame([new_strat])], ignore_index=True)
                            save_pb_strats(updated)
                            st.rerun()

            if not my_strats.empty:
                for idx, strat in my_strats.iterrows():
                    with st.container():
                        c_img, c_proto = st.columns([1.5, 1])
                        with c_img:
                            st.subheader(f"📍 {strat['Name']}")
                            spath = os.path.join(STRAT_IMG_DIR, strat['Image'])
                            if os.path.exists(spath): st.image(spath, use_container_width=True)
                        with c_proto:
                            st.markdown("### ⚡ PROTOCOLS")
                            try: protos = json.loads(strat['Protocols'])
                            except: protos = []
                            if protos:
                                for p in protos: st.markdown(f"""<div class="proto-box"><div class="proto-if">IF: {p['trigger']}</div><div class="proto-then">👉 {p['reaction']}</div></div>""", unsafe_allow_html=True)
                            else: st.caption("No protocols defined.")
                            
                            with st.popover(f"Edit Protocols"):
                                with st.form(f"pf_{strat['Strat_ID']}"):
                                    trig = st.text_input("IF (Trigger)"); react = st.text_input("THEN (Reaction)")
                                    if st.form_submit_button("Add"):
                                        protos.append({'trigger': trig, 'reaction': react})
                                        df_pb_strats.loc[df_pb_strats['Strat_ID'] == strat['Strat_ID'], 'Protocols'] = json.dumps(protos)
                                        save_pb_strats(df_pb_strats)
                                        st.rerun()
                                if st.button("Clear Protocols", key=f"clr_{strat['Strat_ID']}"):
                                    df_pb_strats.loc[df_pb_strats['Strat_ID'] == strat['Strat_ID'], 'Protocols'] = '[]'
                                    save_pb_strats(df_pb_strats)
                                    st.rerun()
                        st.divider()

    # --------------------------------------------------------------------------
    # TAB 2: TACTICAL WHITEBOARD (100% CORRECTED)
    # --------------------------------------------------------------------------
    with tab_whiteboard:
        st.subheader("TACTICAL BOARD")
        
        # --- VISUAL MAP SELECTOR ---
        if 'wb_map_sel' not in st.session_state: st.session_state.wb_map_sel = "Ascent"
        with st.expander("🗺️ MAP SELECTION", expanded=False):
            render_visual_selection(sorted(df['Map'].unique()) if not df.empty else ["Ascent"], 'map', 'wb_m', multi=False, key_state='wb_map_sel')
        wb_map = st.session_state.wb_map_sel

        # --- VISUAL AGENT SELECTOR ---
        agent_files = glob.glob(os.path.join(ASSET_DIR, "agents", "*.png"))
        agent_options = [os.path.basename(x).replace('.png', '') for x in agent_files] if agent_files else []
        
        if 'wb_agent_sel' not in st.session_state: st.session_state.wb_agent_sel = agent_options[0] if agent_options else None
        with st.expander("♟️ AGENT ICON (for placement)", expanded=False):
             render_visual_selection(agent_options, 'agent', 'wb_a', multi=False, key_state='wb_agent_sel')
        selected_agent = st.session_state.wb_agent_sel
        
        st.divider()
        
        st.markdown("#### 2. WERKZEUG")
        # --- FIX: NUR GÜLTIGE WERKZEUGE (KEIN ARROW/TEXT!) ---
        tool_map = {
            "Linie (Laufweg/Wall)": "line",
            "Rechteck (Area)": "rect",
            "Kreis (Smoke/Zone)": "circle",
            "Agent (Platzierung)": "agent",
            "Stift (Freihand)": "freedraw",
            "Maus (Bewegen)": "transform"
        }
        tool_select = st.radio("Tool wählen:", list(tool_map.keys()), index=0)
        mode = tool_map[tool_select]
        
        # Toggle für gerade Linien
        force_straight = st.checkbox("Gerade Linien erzwingen", key="force_straight")
        if force_straight and mode == "freedraw":
            mode = "line"
        
        st.divider()
        
        st.markdown("#### 3. TAKTIK-FARBEN")
        color_presets = {
            "🟥 ATTACK / T (#FF4655)": "#FF4655",
            "🟦 DEFENSE / CT (#00FFFF)": "#00FFFF",
            "⬜ INFO / TEXT (#FFFFFF)": "#FFFFFF",
            "☁️ SMOKE (#DDDDDD)": "#DDDDDD",
            "🟩 VIPER / TOXIC (#00FF00)": "#00FF00",
            "🟨 KJ / FLASH (#FFD700)": "#FFD700",
            "⬛ SHADOW / DARK (#000000)": "#000000"
        }
        c_name = st.selectbox("Farbe:", list(color_presets.keys()))
        stroke_color = color_presets[c_name]
        
        stroke_width = st.slider("Linienstärke", 1, 8, 3)
        
        st.divider()
        
        st.markdown("#### 4. SPEICHERN")
        strat_name = st.text_input("Name der Taktik", placeholder="z.B. B Rush Pistol")
        
        map_pbs = df_team_pb[df_team_pb['Map'] == wb_map]
        assign_pb = st.selectbox("Zu Playbook hinzufügen:", ["Keins"] + list(map_pbs['Name'].unique()) if not map_pbs.empty else ["Keins"])

        # Persist canvas drawing across tool changes
        if 'canvas_drawing' not in st.session_state:
            st.session_state.canvas_drawing = {}
        initial_drawing = st.session_state.canvas_drawing
        
        # BILD VORBEREITUNG
        bg_image_path = get_map_img(wb_map, 'icon')
        pil_image = None
        bg_url = None
        
        if bg_image_path and os.path.exists(bg_image_path):
            try:
                loaded = Image.open(bg_image_path)
                pil_image = loaded.convert("RGBA")
                pil_image = pil_image.resize((700, 700))
            except Exception as e:
                st.error(f"Fehler beim Laden des Bildes: {e}")

            st.markdown("""
            <style>
            [data-testid="stCanvas"] {
                border: 2px solid #333;
                border-radius: 5px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            }
            </style>
            """, unsafe_allow_html=True)

            canvas_result = st_canvas(
                fill_color=stroke_color + "44",  
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                background_color=None, 
                background_image=pil_image, 
                update_streamlit=True,
                height=700,
                width=700, 
                drawing_mode="circle" if mode == "agent" else mode,
                point_display_radius=0,
                display_toolbar=True,
                initial_drawing=initial_drawing
            )
            
            # Update session state with current drawing
            st.session_state.canvas_drawing = canvas_result.json_data if canvas_result.json_data else {}
            
            if st.button("💾 SAVE STRATEGY", type="primary"):
                if canvas_result.image_data is not None and strat_name:
                    img_data = canvas_result.image_data.astype("uint8")
                    im = Image.fromarray(img_data)
                    
                    # Overlay agent images on circles if agent selected
                    if selected_agent and canvas_result.json_data:
                        agent_path = os.path.join(ASSET_DIR, "agents", selected_agent + ".png")
                        if os.path.exists(agent_path):
                            agent_img = Image.open(agent_path)
                            for obj in canvas_result.json_data['objects']:
                                if obj['type'] == 'circle':
                                    x = obj['left'] + obj['width'] / 2
                                    y = obj['top'] + obj['height'] / 2
                                    radius = obj['width'] / 2
                                    size = int(radius * 2)
                                    if size > 0:
                                        resized_agent = agent_img.resize((size, size))
                                        im.paste(resized_agent, (int(x - radius), int(y - radius)), resized_agent if resized_agent.mode == 'RGBA' else None)
                    
                    fname = f"STRAT_{wb_map}_{strat_name}_{int(datetime.now().timestamp())}.png".replace(" ", "_")
                    im.save(os.path.join(STRAT_IMG_DIR, fname))
                    
                    if assign_pb != "Keins":
                        pb_id = df_team_pb[df_team_pb['Name']==assign_pb].iloc[0]['ID']
                        new_entry = {
                            'PB_ID': pb_id, 
                            'Strat_ID': str(uuid.uuid4()), 
                            'Name': strat_name, 
                            'Image': fname, 
                            'Protocols': '[]'
                        }
                        updated = pd.concat([df_pb_strats, pd.DataFrame([new_entry])], ignore_index=True)
                        save_pb_strats(updated)
                        st.success(f"Gespeichert in Playbook: {assign_pb}")
                    else:
                        st.success(f"Bild gespeichert als {fname}")
                else:
                    st.error("Bitte gib der Taktik einen Namen!")
        else:
            st.error(f"⚠️ Kein Map-Bild gefunden für {wb_map}.")
            st.info(f"Suche nach: assets/maps/{str(wb_map).lower()}_icon.png")

    # --------------------------------------------------------------------------
    # TAB 3: MAP THEORY
    # --------------------------------------------------------------------------
    with tab_theory:
        st.subheader("CONCEPTUAL FRAMEWORK")
        theory_map = st.selectbox("Select Map:", sorted(df['Map'].unique()) if not df.empty else ["Ascent"], key="theory_map_sel")
        if 'Image' not in df_theory.columns: df_theory['Image'] = None

        def get_theory_data(m, s):
            row = df_theory[(df_theory['Map'] == m) & (df_theory['Section'] == s)]
            if not row.empty: return row.iloc[0]['Content'], row.iloc[0]['Image']
            return "", None

        def save_theory_data_gsheet(m, s, text, new_img_obj, old_img_name):
            img_name = old_img_name
            if new_img_obj:
                img_name = f"THEORY_{m}_{s}_{int(datetime.now().timestamp())}.png".replace(" ", "_")
                with open(os.path.join(STRAT_IMG_DIR, img_name), "wb") as f: f.write(new_img_obj.getbuffer())
            
            # Remove old entry for this section
            new_df = df_theory[~((df_theory['Map'] == m) & (df_theory['Section'] == s))]
            # Add new entry
            new_entry = pd.DataFrame([{'Map': m, 'Section': s, 'Content': text, 'Image': img_name}])
            updated = pd.concat([new_df, new_entry], ignore_index=True)
            
            save_map_theory(updated)
            return img_name

        t_gen, t_atk, t_def = st.tabs(["🌐 GENERAL", "⚔️ ATTACK", "🛡️ DEFENSE"])
        sections = [("General", t_gen), ("Attack", t_atk), ("Defense", t_def)]
        
        for sec_name, sec_tab in sections:
            with sec_tab:
                c_txt, c_upl = st.columns([2, 1])
                curr_txt, curr_img = get_theory_data(theory_map, sec_name)
                with c_txt: new_txt = st.text_area(f"{sec_name} Notes", value=curr_txt, height=400)
                with c_upl:
                    if curr_img:
                        p = os.path.join(STRAT_IMG_DIR, curr_img)
                        if os.path.exists(p): st.image(p, caption="Current Reference", use_container_width=True)
                    new_img = st.file_uploader(f"Upload {sec_name} Image", type=['png', 'jpg'], key=f"up_{theory_map}_{sec_name}")
                if st.button(f"Save {sec_name}", key=f"sv_{theory_map}_{sec_name}"):
                    save_theory_data_gsheet(theory_map, sec_name, new_txt, new_img, curr_img)
                    st.success("Saved"); st.rerun()

    # --------------------------------------------------------------------------
    # TAB 4: EXTERNAL LINKS
    # --------------------------------------------------------------------------
    with tab_links:
        # Use Legacy Playbooks for external links if that's the intent or df_legacy_pb
        # Based on previous code, pb_df seemed to load PLAYBOOKS_FILE which is now df_legacy_pb
        pb_df = df_legacy_pb 
        
        with st.expander("➕ New External Link"):
            with st.form("pb_link"):
                c1, c2 = st.columns(2)
                pm = c1.selectbox("Map", sorted(df['Map'].unique()) if not df.empty else ["Ascent"], key="lm")
                pn = c1.text_input("Name", key="ln"); pl = c2.text_input("Link", key="ll")
                ags = sorted([os.path.basename(x).replace(".png","").capitalize() for x in glob.glob(os.path.join(ASSET_DIR, "agents", "*.png"))])
                cols = st.columns(5)
                mas = [cols[i].selectbox(f"P{i}", [""]+ags, key=f"la{i}") for i in range(5)]
                if st.form_submit_button("Save"): 
                    nr = {'Map': pm, 'Name': pn, 'Link': pl}
                    for i in range(5): nr[f'Agent_{i+1}'] = mas[i]
                    
                    updated = pd.concat([pb_df, pd.DataFrame([nr])], ignore_index=True)
                    save_legacy_playbooks(updated)
                    st.rerun()

        if not pb_df.empty:
            f_pb = st.selectbox("Links Map:", ["All"]+sorted(pb_df['Map'].unique()), key="fl_map")
            v_pb = pb_df if f_pb == "All" else pb_df[pb_df['Map'] == f_pb]
            for idx, row in v_pb.iterrows():
                map_img = get_map_img(row['Map'], 'list')
                b64_map = img_to_b64(map_img)
                ag_html = ""
                for i in range(1, 6):
                    a = row.get(f'Agent_{i}')
                    if a and pd.notna(a):
                        ab64 = img_to_b64(get_agent_img(a))
                        if ab64: ag_html += f"<img src='data:image/png;base64,{ab64}' style='width:35px; height:35px; border-radius:50%; border:2px solid #111; margin-right:-10px; z-index:{i}'>"
                
                st.markdown(f"""<div class='pb-card'><div style="display:flex;align-items:center;gap:20px;"><div style="width:160px;height:90px;border-radius:5px;background-image:url('data:image/png;base64,{b64_map}');background-size:contain;background-position:center;background-repeat:no-repeat;border:1px solid #444;"></div><div><div style="color:#00BFFF;font-weight:bold;font-size:1.1em;text-transform:uppercase;">{row['Name']}</div><div style="color:#666;font-size:0.8em;">{row['Map']}</div></div><div style="margin-left:auto;padding-right:10px;">{ag_html}</div></div></div>""", unsafe_allow_html=True)
                st.markdown(f'<a href="{row["Link"]}" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(90deg, #00BFFF, #FF1493); color: white; padding: 8px 15px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer;">OPEN LINK >></button></a>', unsafe_allow_html=True)

# ==============================================================================
# 5. RESOURCES
# ==============================================================================
elif page == "📚 RESOURCES":
    st.title("KNOWLEDGE BASE")
    # df_res loaded globally
    
    with st.expander("➕ Add"):
        with st.form("ra"):
            rt = st.text_input("Title"); rl = st.text_input("Link"); rc = st.selectbox("Cat", ["Theory", "Lineups", "Setup", "Playbook Theory"]); rn = st.text_area("Note")
            if st.form_submit_button("Save"):
                updated = pd.concat([df_res, pd.DataFrame([{'Title': rt, 'Link': rl, 'Category': rc, 'Note': rn}])], ignore_index=True)
                save_resources(updated)
                st.rerun()
    
    if not df_res.empty:
        cats = st.multiselect("Filter:", df_res['Category'].unique(), default=df_res['Category'].unique())
        view = df_res[df_res['Category'].isin(cats)]
        cols = st.columns(4)
        for i, (idx, row) in enumerate(view.iterrows()):
            with cols[i%4]:
                thumb = get_yt_thumbnail(row['Link'])
                img = f"<img src='{thumb}' class='res-thumb'>" if thumb else "<div style='height:140px; background:#222; display:flex; align-items:center; justify-content:center'>📄</div>"
                st.markdown(f"""<div class="res-tile">{img}<div class="res-info"><div style="color:#00BFFF; font-size:0.8em">{row['Category']}</div><div style="font-weight:bold">{row['Title']}</div><a href="{row['Link']}" target="_blank" style="color:#aaa; font-size:0.8em">OPEN</a></div></div>""", unsafe_allow_html=True)
    
    with st.expander("✏️ Edit"):
        ed = st.data_editor(df_res, num_rows="dynamic")
        if st.button("Save Changes"): 
            save_resources(ed)
            st.success("Saved"); st.rerun()

# ==============================================================================
# 6. CALENDAR
# ==============================================================================
elif page == "📅 CALENDAR":
    st.title("SCHEDULE")
    if 'cy' not in st.session_state: st.session_state['cy'] = datetime.now().year
    if 'cm' not in st.session_state: st.session_state['cm'] = datetime.now().month
    
    c1, c2 = st.columns([2, 1])
    # df_cal and df_simple_todos loaded globally
    
    with c1:
        cp, cc, cn = st.columns([1,2,1])
        if cp.button("<"): st.session_state['cm']-=1
        if cn.button(">"): st.session_state['cm']+=1
        if st.session_state['cm']==0: st.session_state['cm']=12; st.session_state['cy']-=1
        if st.session_state['cm']==13: st.session_state['cm']=1; st.session_state['cy']+=1
        
        curr = datetime(st.session_state['cy'], st.session_state['cm'], 1)
        cc.markdown(f"<h3 style='text-align:center'>{curr.strftime('%B %Y')}</h3>", unsafe_allow_html=True)
        
        cal = calendar.monthcalendar(curr.year, curr.month)
        cols = st.columns(7)
        for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]: cols[["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].index(d)].write(f"**{d}**")
        
        for w in cal:
            cols = st.columns(7)
            for i, d in enumerate(w):
                with cols[i]:
                    if d!=0:
                        d_s = f"{d:02d}.{curr.month:02d}.{curr.year}"
                        evs = df_cal[df_cal['Date']==d_s]
                        bg = "#1a1a40; border:1px solid #00BFFF" if date(curr.year, curr.month, d)==date.today() else "#222"
                        h = f"<div class='cal-day-box' style='background:{bg}'><b>{d}</b>"
                        for _, e in evs.iterrows():
                            c = "#FF1493" if e.get('Type')=="Match" else "#00BFFF"
                            h+=f"<div class='cal-event-pill' style='background:{c}40; border-left:2px solid {c}'>{e['Time']} {e['Event']}</div>"
                        st.markdown(h+"</div>", unsafe_allow_html=True)
        
        with st.expander("Add Event"):
            with st.form("ca"):
                cd=st.date_input("D"); ct=st.time_input("T"); ce=st.text_input("E"); cm=st.text_input("M"); cty=st.selectbox("T",["Match","Scrim","Other"])
                if st.form_submit_button("Add"):
                    updated = pd.concat([df_cal, pd.DataFrame([{'Date':cd.strftime("%d.%m.%Y"),'Time':ct.strftime("%H:%M"),'Event':ce,'Map':cm,'Type':cty}])], ignore_index=True)
                    save_calendar(updated)
                    st.rerun()

    with c2:
        st.subheader("TODO")
        with st.form("td"):
            t = st.text_input("Task")
            if st.form_submit_button("Add"):
                updated = pd.concat([df_simple_todos, pd.DataFrame([{'Task':t, 'Done':False}])], ignore_index=True)
                save_simple_todos(updated)
                st.rerun()
        if not df_simple_todos.empty:
            ed = st.data_editor(df_simple_todos, num_rows="dynamic")
            if st.button("Save Todo"): 
                save_simple_todos(ed)
                st.success("Saved")

# ==============================================================================
# 7. PLAYERS (KOMPLETT NEU MIT DEEP DIVE)
# ==============================================================================
elif page == "📊 PLAYERS":
    st.title("PLAYER PERFORMANCE")

    # Styling Functions for Conditional Formatting (moved here to be available for all tabs)
    def style_good_bad(v, good_thresh, bad_thresh, inverse=False):
        if pd.isna(v): return ""
        # Colors: Dark Green / Dark Yellow / Dark Red backgrounds with light text
        c_good = 'background-color: #113321; color: #aaffaa'
        c_avg = 'background-color: #443311; color: #ffffaa'
        c_bad = 'background-color: #441111; color: #ffaaaa'
        
        if inverse: # Lower is better (e.g. Deaths)
            if v <= good_thresh: return c_good
            elif v <= bad_thresh: return c_avg
            else: return c_bad
        else: # Higher is better
            if v >= good_thresh: return c_good
            elif v >= bad_thresh: return c_avg
            else: return c_bad

    # TABS ERSTELLEN
    tab_overview, tab_deep = st.tabs(["📊 TEAM OVERVIEW", "🧬 DEEP DIVE ANALYZER"])
    
    # --------------------------------------------------------------------------
    # TAB 1: TEAM OVERVIEW (Der alte Code)
    # --------------------------------------------------------------------------
    with tab_overview:
        if df_players.empty:
            st.info("No player stats yet. Import JSON matches to see data.")
        else:
            # --- 1. FILTER SECTION ---
            st.markdown("### 🔎 FILTER")
            
            # Get unique values for filters
            available_maps = sorted(df_players['Map'].unique())
            available_agents = sorted(df_players['Agent'].unique())
            available_players = sorted(df_players['Player'].unique())
            
            # Determine default players
            default_players = [p for p in available_players if any(t.lower() in p.lower() for t in OUR_TEAM)]
            if not default_players: default_players = available_players

            # --- VISUAL FILTERS ---
            with st.expander("🗺️ MAPS & ♟️ AGENTS FILTER", expanded=False):
                st.caption("Select Maps:")
                sel_maps = render_visual_selection(available_maps, 'map', 'p_map_flt', default=available_maps, multi=True)
                st.divider()
                st.caption("Select Agents:")
                sel_agents = render_visual_selection(available_agents, 'agent', 'p_ag_flt', default=available_agents, multi=True)

            # Player filter
            sel_players = st.multiselect("Select Players:", available_players, default=default_players)

            # --- 2. DATA PROCESSING ---
            df_filtered = df_players.copy()
            
            if sel_maps:
                df_filtered = df_filtered[df_filtered['Map'].isin(sel_maps)]
            if sel_agents:
                df_filtered = df_filtered[df_filtered['Agent'].isin(sel_agents)]
            if sel_players:
                df_filtered = df_filtered[df_filtered['Player'].isin(sel_players)]
                
            if df_filtered.empty:
                st.warning("No data matches your filters.")
            else:
                # Aggregate Data
                p_agg = df_filtered.groupby('Player').agg({
                    'MatchID': 'nunique', 
                    'Kills': 'sum', 
                    'Deaths': 'sum', 
                    'Assists': 'sum', 
                    'Score': 'sum', 
                    'Rounds': 'sum',
                    'HS': 'mean' 
                }).reset_index()
                
                # Calculate Metrics
                p_agg['SafeDeaths'] = p_agg['Deaths'].replace(0, 1)
                p_agg['KD'] = p_agg['Kills'] / p_agg['SafeDeaths']
                p_agg['ACS'] = p_agg['Score'] / p_agg['Rounds'].replace(0, 1)
                p_agg['KPR'] = p_agg['Kills'] / p_agg['Rounds'].replace(0, 1)
                p_agg['APR'] = p_agg['Assists'] / p_agg['Rounds'].replace(0, 1)
                p_agg['DPR'] = p_agg['Deaths'] / p_agg['Rounds'].replace(0, 1)
                
                p_display = p_agg.rename(columns={'MatchID': 'Matches'})
                
                # --- 3. TABLE VIEW ---
                st.divider()
                st.markdown("### 📋 STATS OVERVIEW")
                
                # Styling Functions
                def style_good_bad(v, good_thresh, bad_thresh, inverse=False):
                    if pd.isna(v): return ""
                    c_good = 'background-color: #113321; color: #aaffaa'
                    c_avg = 'background-color: #443311; color: #ffffaa'
                    c_bad = 'background-color: #441111; color: #ffaaaa'
                    
                    if inverse: 
                        if v <= good_thresh: return c_good
                        elif v <= bad_thresh: return c_avg
                        else: return c_bad
                    else: 
                        if v >= good_thresh: return c_good
                        elif v >= bad_thresh: return c_avg
                        else: return c_bad

                # Apply Pandas Styling
                styler = p_display[['Player', 'Matches', 'KD', 'ACS', 'HS', 'KPR', 'APR', 'DPR']].style\
                    .format({"KD": "{:.2f}", "ACS": "{:.0f}", "HS": "{:.1f}%", "KPR": "{:.2f}", "APR": "{:.2f}", "DPR": "{:.2f}"})\
                    .map(lambda v: style_good_bad(v, 1.2, 0.9), subset=['KD'])\
                    .map(lambda v: style_good_bad(v, 230, 180), subset=['ACS'])\
                    .map(lambda v: style_good_bad(v, 25, 15), subset=['HS'])\
                    .map(lambda v: style_good_bad(v, 0.8, 0.6), subset=['KPR'])\
                    .map(lambda v: style_good_bad(v, 0.65, 0.80, inverse=True), subset=['DPR'])

                st.dataframe(
                    styler,
                    column_config={
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                        "Matches": st.column_config.NumberColumn("Matches", format="%d"),
                        "KD": st.column_config.NumberColumn("K/D"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # --- 4. SPIDER CHART ---
                st.divider()
                st.markdown("### 🕸️ TRAIT ANALYSIS")
                
                c_chart, c_metrics = st.columns([1.5, 1])
                player_list = p_agg['Player'].tolist()
                
                with c_metrics:
                    st.markdown("#### Compare Players")
                    p1_name = st.selectbox("Player 1 (Blue)", player_list, index=0 if len(player_list)>0 else None)
                    p2_name = st.selectbox("Player 2 (Pink)", ["None"] + player_list, index=1 if len(player_list)>1 else 0)
                    
                    if p1_name:
                        row1 = p_agg[p_agg['Player'] == p1_name].iloc[0]
                        
                        def show_metric_comp(label, val1, val2=None, fmt="{:.2f}"):
                            delta = None
                            if val2 is not None: delta = val1 - val2
                            st.metric(label, fmt.format(val1), f"{delta:.2f}" if delta is not None else None)

                        if p2_name and p2_name != "None":
                            row2 = p_agg[p_agg['Player'] == p2_name].iloc[0]
                            st.markdown("---")
                            c_m1, c_m2 = st.columns(2)
                            with c_m1: show_metric_comp("K/D", row1['KD'], row2['KD'])
                            with c_m2: show_metric_comp("ACS", row1['ACS'], row2['ACS'], "{:.0f}")
                            c_m3, c_m4 = st.columns(2)
                            with c_m3: show_metric_comp("KPR", row1['KPR'], row2['KPR'])
                            with c_m4: show_metric_comp("HS%", row1['HS'], row2['HS'], "{:.1f}%")
                        else:
                            st.markdown("---")
                            c_m1, c_m2 = st.columns(2)
                            with c_m1: st.metric("K/D", f"{row1['KD']:.2f}")
                            with c_m2: st.metric("ACS", f"{row1['ACS']:.0f}")
                            c_m3, c_m4 = st.columns(2)
                            with c_m3: st.metric("KPR", f"{row1['KPR']:.2f}")
                            with c_m4: st.metric("HS%", f"{row1['HS']:.1f}%")

                with c_chart:
                    if p1_name:
                        categories = ['K/D', 'ACS', 'HS%', 'KPR', 'APR']
                        max_values = {'K/D': 2.0, 'ACS': 300, 'HS%': 40, 'KPR': 1.0, 'APR': 0.5}
                        radar_data = []
                        
                        def add_player_data(p_row, p_label):
                            vals = {'K/D': p_row['KD'], 'ACS': p_row['ACS'], 'HS%': p_row['HS'], 'KPR': p_row['KPR'], 'APR': p_row['APR']}
                            for cat in categories:
                                norm = min(vals[cat] / max_values[cat], 1.0)
                                radar_data.append({'Player': p_label, 'Metric': cat, 'Value': norm, 'Display': vals[cat]})
                        
                        add_player_data(row1, p1_name)
                        if p2_name and p2_name != "None": add_player_data(row2, p2_name)
                        
                        fig = px.line_polar(pd.DataFrame(radar_data), r='Value', theta='Metric', color='Player', line_close=True,
                                            color_discrete_sequence=['#00BFFF', '#FF1493'], hover_data={'Value': False, 'Display': True})
                        fig.update_traces(fill='toself')
                        fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 1]), bgcolor='rgba(255,255,255,0.05)'),
                                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                                          margin=dict(t=20, b=20, l=20, r=20), legend=dict(orientation="h", y=1.02))
                        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
    # TAB 2: DEEP DIVE (MIT DIAGRAMMEN)
    # --------------------------------------------------------------------------
    with tab_deep:
        # --- ABILITY MAPPING DATABASE ---
        AGENT_ABILITIES = {
            "Astra": {"C": "Gravity Well", "Q": "Nova Pulse", "E": "Nebula", "X": "Astral Form"},
            "Breach": {"C": "Aftershock", "Q": "Flashpoint", "E": "Fault Line", "X": "Rolling Thunder"},
            "Brimstone": {"C": "Stim Beacon", "Q": "Incendiary", "E": "Sky Smoke", "X": "Orbital Strike"},
            "Chamber": {"C": "Trademark", "Q": "Headhunter", "E": "Rendezvous", "X": "Tour De Force"},
            "Clove": {"C": "Pick-me-up", "Q": "Meddle", "E": "Ruse", "X": "Not Dead Yet"},
            "Cypher": {"C": "Trapwire", "Q": "Cyber Cage", "E": "Spycam", "X": "Neural Theft"},
            "Deadlock": {"C": "GravNet", "Q": "Sonic Sensor", "E": "Barrier Mesh", "X": "Annihilation"},
            "Fade": {"C": "Prowler", "Q": "Seize", "E": "Haunt", "X": "Nightfall"},
            "Gekko": {"C": "Mosh Pit", "Q": "Wingman", "E": "Dizzy", "X": "Thrash"},
            "Harbor": {"C": "Cascade", "Q": "Cove", "E": "High Tide", "X": "Reckoning"},
            "Iso": {"C": "Contingency", "Q": "Undercut", "E": "Double Tap", "X": "Kill Contract"},
            "Jett": {"C": "Cloudburst", "Q": "Updraft", "E": "Tailwind", "X": "Blade Storm"},
            "KAY/O": {"C": "FRAG/ment", "Q": "FLASH/drive", "E": "ZERO/point", "X": "NULL/cmd"},
            "Killjoy": {"C": "Nanoswarm", "Q": "Alarmbot", "E": "Turret", "X": "Lockdown"},
            "Neon": {"C": "Fast Lane", "Q": "Relay Bolt", "E": "High Gear", "X": "Overdrive"},
            "Omen": {"C": "Shrouded Step", "Q": "Paranoia", "E": "Dark Cover", "X": "From the Shadows"},
            "Phoenix": {"C": "Blaze", "Q": "Curveball", "E": "Hot Hands", "X": "Run it Back"},
            "Raze": {"C": "Boom Bot", "Q": "Blast Pack", "E": "Paint Shells", "X": "Showstopper"},
            "Reyna": {"C": "Leer", "Q": "Devour", "E": "Dismiss", "X": "Empress"},
            "Sage": {"C": "Barrier Orb", "Q": "Slow Orb", "E": "Healing Orb", "X": "Resurrection"},
            "Skye": {"C": "Regrowth", "Q": "Trailblazer", "E": "Guiding Light", "X": "Seekers"},
            "Sova": {"C": "Owl Drone", "Q": "Shock Bolt", "E": "Recon Bolt", "X": "Hunter's Fury"},
            "Viper": {"C": "Snake Bite", "Q": "Poison Cloud", "E": "Toxic Screen", "X": "Viper's Pit"},
            "Vyse": {"C": "Razorvine", "Q": "Shear", "E": "Arc Rose", "X": "Steel Garden"},
            "Yoru": {"C": "Fakeout", "Q": "Blindside", "E": "Gatecrash", "X": "Dimensional Drift"},
        }

        st.markdown("### 🧬 INDIVIDUAL PLAYER DEEP DIVE")
        deep_player = st.selectbox("Select Player", ["Andrei", "Benni", "Luca", "Luggi", "Remus", "Sofi"])
        
        # Pfad laden
        file_path = os.path.join(BASE_DIR, "data", "players", f"{deep_player.lower()}_data.json")
        df_deep = pd.DataFrame()
        
        if os.path.exists(file_path):
            st.success(f"📂 Analysing local data for **{deep_player}**")
            df_deep = parse_tracker_json(file_path)
        else:
            up = st.file_uploader("Upload JSON", type=['json'])
            if up: df_deep = parse_tracker_json(up)

        # --- HIER BEGINNT DIE ANALYSE ---
        if not df_deep.empty:
            
            if df_deep.empty:
                st.warning(f"⚠️ Datei geladen, aber keine Daten für Spieler **{deep_player}** gefunden.")
                st.stop()

            # SICHERHEITS-CHECK: Sind die neuen Daten da?
            if 'Cast_Ult' not in df_deep.columns:
                st.error("⚠️ FEHLER: Dein Parser ist veraltet. Bitte führe SCHRITT 1 aus meiner Nachricht aus (Funktion parse_tracker_json aktualisieren).")
                st.stop()

            # 1. TOP STATS ROW
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("K/D RATIO", f"{df_deep['KD'].mean():.2f}")
            k2.metric("HEADSHOT %", f"{df_deep['HS%'].mean():.1f}%")
            k3.metric("ADR", f"{df_deep['ADR'].mean():.0f}")
            k4.metric("UTIL PER MATCH", f"{df_deep['Total_Util'].mean():.1f}")
            
            st.divider()

            # 2. AGENT BREAKDOWN (VLR.gg Style Table)
            st.subheader("♟️ AGENT PERFORMANCE")
            
            # Daten aggregieren
            ag_stats = df_deep.groupby('Agent').agg({
                'MatchesPlayed': 'sum', 
                'Kills': 'sum', 'Deaths': 'sum', 
                'Wins': 'sum',
                'HS%': 'mean',
                'Cast_Grenade':'mean', 'Cast_Abil1':'mean', 'Cast_Abil2':'mean', 'Cast_Ult':'mean'
            }).reset_index()
            ag_stats['Win%'] = ag_stats['Wins'] / ag_stats['MatchesPlayed'] * 100
            ag_stats['KD'] = ag_stats['Kills'] / ag_stats['Deaths'].replace(0,1)
            
            # Sortieren nach meisten Matches
            ag_stats = ag_stats.sort_values('MatchesPlayed', ascending=False)
            
            # Tabelle vorbereiten
            table_data = []
            for _, row in ag_stats.iterrows():
                agent_name = row['Agent']
                # Bild laden und zu Base64 konvertieren für die Tabelle
                img_path = get_agent_img(agent_name)
                img_b64 = f"data:image/png;base64,{img_to_b64(img_path)}" if img_path else ""
                
                table_data.append({
                    "Icon": img_b64,
                    "Agent": agent_name,
                    "Matches": int(row['MatchesPlayed']),
                    "Win%": row['Win%'],
                    "K/D": row['KD'],
                    "HS%": row['HS%'],
                    "C": row['Cast_Grenade'],
                    "Q": row['Cast_Abil1'],
                    "E": row['Cast_Abil2'],
                    "X": row['Cast_Ult'],
                })
            
            df_table = pd.DataFrame(table_data)
            
            # Apply Styling
            styler = df_table.style\
                .format({
                    "Win%": "{:.0f}%", "K/D": "{:.2f}", "HS%": "{:.1f}%",
                    "C": "{:.1f}", "Q": "{:.1f}", "E": "{:.1f}", "X": "{:.1f}"
                })\
                .map(lambda v: style_good_bad(v, 60, 45), subset=['Win%'])\
                .map(lambda v: style_good_bad(v, 1.2, 0.9), subset=['K/D'])\
                .map(lambda v: style_good_bad(v, 25, 15), subset=['HS%'])\
                .background_gradient(cmap='Purples', subset=['C', 'Q', 'E', 'X'])

            st.dataframe(
                styler,
                column_config={
                    "Icon": st.column_config.ImageColumn("Icon", width="small"),
                    "Agent": st.column_config.TextColumn("Agent", width="small"),
                    "Matches": st.column_config.NumberColumn("#", format="%d", width="small"),
                    "Win%": st.column_config.TextColumn("Win%"),
                    "K/D": st.column_config.TextColumn("K/D"),
                    "HS%": st.column_config.TextColumn("HS%"),
                    "C": st.column_config.NumberColumn("C", help="Avg Casts per Match"),
                    "Q": st.column_config.NumberColumn("Q", help="Avg Casts per Match"),
                    "E": st.column_config.NumberColumn("E", help="Avg Casts per Match"),
                    "X": st.column_config.NumberColumn("X", help="Avg Casts per Match"),
                },
                use_container_width=True,
                hide_index=True,
                height=400
            )

            with st.expander("Ability Key"):
                for agent in df_table['Agent']:
                    abils = AGENT_ABILITIES.get(agent, {})
                    if abils:
                        st.markdown(f"**{agent}:** C: *{abils.get('C')}*, Q: *{abils.get('Q')}*, E: *{abils.get('E')}*, X: *{abils.get('X')}*")

            st.divider()

            # 3. MAP UTILITY ANALYSIS
            st.subheader("🗺️ MAP UTILITY DEEP DIVE")
            
            # Initialize session state for this selector
            if 'deep_agent' not in st.session_state:
                st.session_state.deep_agent = ag_stats['Agent'].unique()[0] if not ag_stats.empty else None

            with st.expander("♟️ SELECT AGENT", expanded=True):
                render_visual_selection(ag_stats['Agent'].unique(), 'agent', 'deep_a_sel', multi=False, key_state='deep_agent')
            
            sel_agent = st.session_state.deep_agent
            
            if sel_agent:
                # Filter auf Agent
                df_ag = df_deep[df_deep['Agent'] == sel_agent]
                # Durchschnittliche Nutzung pro Map berechnen
                map_util = df_ag.groupby('Map')[['Cast_Grenade', 'Cast_Abil1', 'Cast_Abil2', 'Cast_Ult']].mean().reset_index()
                
                # Umformen für Stacked Bar Chart
                map_melt = map_util.melt(id_vars='Map', var_name='Ability', value_name='Avg Casts')
                
                fig2 = px.bar(map_melt, x='Map', y='Avg Casts', color='Ability',
                              title=f"Average Utility Usage for {sel_agent} per Map",
                              color_discrete_map={
                                  'Cast_Ult': '#FF1493', 
                                  'Cast_Grenade': '#88FFFF',
                                  'Cast_Abil1': '#00BFFF',
                                  'Cast_Abil2': '#0055AA'
                              })
                fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,0.05)', font=dict(color='white'))
                st.plotly_chart(fig2, use_container_width=True)
        
        else:
            st.info("👆 Bitte lade eine JSON-Datei hoch (Tracker.gg Match-Export oder Profil-Export), um die Analyse zu starten.")

# ==============================================================================
# 8. DATABASE
# ==============================================================================
elif page == "💾 DATABASE":
    st.header("Database")
    ed = st.data_editor(df, num_rows="dynamic")
    if st.button("Save"): 
        save_matches(ed)
        st.success("Saved to Google Sheets")