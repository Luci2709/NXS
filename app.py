import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import glob
import requests
import uuid
import base64
import calendar
import io
import numpy as np
from datetime import datetime, date, timedelta
from PIL import Image

# ==============================================================================
# 🔧 ROBUST MONKEY PATCH (Fix für Component Error & Streamlit 1.40+)
# Dieser Block MUSS VOR dem Import von st_canvas stehen.
# ==============================================================================
import streamlit.elements.image as st_image
import io
import base64
from PIL import Image

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

# ⬇️ HIER WAR DER FEHLER: Das '#' am Anfang dieser Zeile muss weg!
st_image.image_to_url = custom_image_to_url

# ⚠️ JETZT ERST DIE CANVAS LIBRARY IMPORTIEREN
from streamlit_drawable_canvas import st_canvas


# --- CONFIG & THEME ---
st.set_page_config(page_title="NXS Dashboard", layout="wide", page_icon="💠")

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
</style>
""", unsafe_allow_html=True)

# --- PFADE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR_JSON = os.path.join(BASE_DIR, "data", "matches")
DATA_FILE_CSV = os.path.join(BASE_DIR, "data", "nexus_matches.csv")
PLAYER_STATS_CSV = os.path.join(BASE_DIR, "data", "nexus_player_performances.csv")
PLAYBOOKS_FILE = os.path.join(BASE_DIR, "data", "playbooks.csv") # Legacy
RESOURCES_FILE = os.path.join(BASE_DIR, "data", "resources.csv")
CALENDAR_FILE = os.path.join(BASE_DIR, "data", "calendar.csv")
TEAM_PLAYBOOKS_FILE = os.path.join(BASE_DIR, "data", "nexus_playbooks.csv")
PB_STRATS_FILE = os.path.join(BASE_DIR, "data", "nexus_pb_strats.csv")
MAP_THEORY_FILE = os.path.join(BASE_DIR, "data", "nexus_map_theory.csv")
TODO_FILE = os.path.join(BASE_DIR, "data", "todo.csv")
ASSET_DIR = os.path.join(BASE_DIR, "assets")
STRAT_IMG_DIR = os.path.join(ASSET_DIR, "strats")

# Verzeichnisse erstellen
for d in [DATA_DIR_JSON, os.path.join(BASE_DIR, "data"), STRAT_IMG_DIR, os.path.join(ASSET_DIR, "maps"), os.path.join(ASSET_DIR, "agents")]:
    if not os.path.exists(d): os.makedirs(d)

OUR_TEAM = ["Trashies", "Luggi", "Umbra", "Noctis", "n0thing", "Gengar", "Tejo", "Kawii", "Saizsu"]

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

# --- DATA LOADER ---
@st.cache_data(ttl=60)
def load_data():
    # Matches
    df = pd.read_csv(DATA_FILE_CSV) if os.path.exists(DATA_FILE_CSV) else pd.DataFrame()
    if not df.empty:
        for c in ['Score_Us', 'Score_Enemy', 'Atk_R_W', 'Def_R_W', 'Atk_R_L', 'Def_R_L']:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Delta'] = df['Score_Us'] - df['Score_Enemy']
        df['DateObj'] = pd.to_datetime(df['Date'], format="%d.%m.%Y", errors='coerce')
    
    # Player Stats
    df_p = pd.read_csv(PLAYER_STATS_CSV) if os.path.exists(PLAYER_STATS_CSV) else pd.DataFrame()
    
    return df, df_p

# --- UI START ---
df, df_players = load_data()

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
    st.title("NEXUS")
    page = st.radio("NAVIGATION", ["🏠 DASHBOARD", "📝 MATCH ENTRY", "🗺️ MAP ANALYZER", "📘 STRATEGY BOARD", "📚 RESOURCES", "📅 CALENDAR", "📊 PLAYERS", "💾 DATABASE"], label_visibility="collapsed")
    st.markdown("---")
    if st.button("🔄 RELOAD DATA"): st.cache_data.clear(); st.rerun()

# ==============================================================================
# 1. DASHBOARD
# ==============================================================================
if page == "🏠 DASHBOARD":
    st.title("PERFORMANCE DASHBOARD")
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
            st.divider(); st.markdown("### 🏆 POWER RANKING")
            rank_df = pd.DataFrame(conf_list).rename(columns={'M':'Map','S':'Score','WR':'Winrate'})
            rank_df['MapImg'] = rank_df['Map'].apply(lambda x: f"data:image/png;base64,{img_to_b64(get_map_img(x, 'list'))}")
            st.dataframe(rank_df[['MapImg','Map','Score','Winrate']], column_config={"MapImg":st.column_config.ImageColumn("Map",width="small"), "Score":st.column_config.ProgressColumn("Rating",format="%.1f",min_value=0,max_value=max(rank_df['Score'])+10), "Winrate":st.column_config.ProgressColumn("Win%",format="%.0f%%",min_value=0,max_value=100)}, use_container_width=True, hide_index=True)
            
            # --- RECENT ---
            st.divider(); st.markdown("### RECENT ACTIVITY")
            limit = st.slider("Matches:", 3, 20, 5)
            for idx, row in df_filt.sort_values('DateObj', ascending=False).head(limit).iterrows():
                res=row['Result']; b="#00ff80" if res=='W' else "#ff1493" if res=='L' else "#ffeb3b";
                with st.container():
                    st.markdown(f"<div class='rec-card' style='border-left-color:{b}'>", unsafe_allow_html=True)
                    c1,c2,c3,c4 = st.columns([1.2,1.5,4,1.5])
                    with c1: 
                        img=get_map_img(row['Map'], 'list'); 
                        if img: st.image(img, use_container_width=True)
                    with c2: st.markdown(f"**{row['Map']}**"); st.caption(f"{row['Date']}")
                    with c3:
                        mh=""; eh=""
                        for i in range(1,6):
                            if pd.notna(row.get(f'MyComp_{i}')): 
                                b64=img_to_b64(get_agent_img(row[f'MyComp_{i}'])); 
                                if b64: mh+=f"<img src='data:image/png;base64,{b64}' width='25' style='margin-right:3px'>"
                            if pd.notna(row.get(f'EnComp_{i}')): 
                                b64=img_to_b64(get_agent_img(row[f'EnComp_{i}'])); 
                                if b64: eh+=f"<img src='data:image/png;base64,{b64}' width='25' style='margin-right:3px'>"
                        if mh: st.markdown(f"<div class='comp-box-my'>{mh}</div>", unsafe_allow_html=True)
                        if eh: st.markdown(f"<div class='comp-box-en'>{eh}</div>", unsafe_allow_html=True)
                    with c4: st.markdown(f"<h3 style='color:{b}; margin:0; text-align:right'>{int(row['Score_Us'])}:{int(row['Score_Enemy'])}</h3>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

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
                                    'Kills': sts['kills']['value'], 'Deaths': sts['deaths']['value'],
                                    'Assists': sts['assists']['value'], 'Score': sts['score']['value'], 'Rounds': rounds,
                                    'HS': sts.get('headshotsPercentage', {}).get('value', 0)
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
            old=pd.read_csv(DATA_FILE_CSV) if os.path.exists(DATA_FILE_CSV) else pd.DataFrame()
            pd.concat([old,pd.DataFrame([row])],ignore_index=True).to_csv(DATA_FILE_CSV,index=False)
            
            # Save Player Stats
            if d['p_stats']:
                ps_old = pd.read_csv(PLAYER_STATS_CSV) if os.path.exists(PLAYER_STATS_CSV) else pd.DataFrame()
                pd.concat([ps_old, pd.DataFrame(d['p_stats'])], ignore_index=True).to_csv(PLAYER_STATS_CSV, index=False)
                
            st.success("Saved!"); st.cache_data.clear(); st.rerun()

# ==============================================================================
# 3. MAP ANALYZER
# ==============================================================================
elif page == "🗺️ MAP ANALYZER":
    st.title("TACTICAL BOARD")
    if not df.empty:
        sel_map = st.selectbox("MAP:", sorted(df['Map'].unique()))
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

    # Load Data
    df_pb = load_csv_generic(TEAM_PLAYBOOKS_FILE, ['ID', 'Map', 'Name', 'Agent_1', 'Agent_2', 'Agent_3', 'Agent_4', 'Agent_5'])
    df_pb_strats = load_csv_generic(PB_STRATS_FILE, ['PB_ID', 'Strat_ID', 'Name', 'Image', 'Protocols'])
    df_theory = load_csv_generic(MAP_THEORY_FILE, ['Map', 'Section', 'Content', 'Image']) 

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
                            pd.concat([df_pb, pd.DataFrame([new_row])], ignore_index=True).to_csv(TEAM_PLAYBOOKS_FILE, index=False)
                            st.rerun()

            if not df_pb.empty:
                for idx, row in df_pb.iterrows():
                    map_img = get_map_img(row['Map'], 'list')
                    b64_map = img_to_b64(map_img)
                    ag_html = ""
                    for i in range(1, 6):
                        a = row.get(f'Agent_{i}')
                        if a and pd.notna(a):
                            ab64 = img_to_b64(get_agent_img(a))
                            if ab64: ag_html += f"<img src='data:image/png;base64,{ab64}' style='width:35px; height:35px; border-radius:50%; border:2px solid #111; margin-right:-10px; z-index:{i}'>"
                    
                    st.markdown(f"""<div class='pb-card'><div style="display:flex;align-items:center;gap:20px;"><div style="width:80px;height:50px;border-radius:5px;background-image:url('data:image/png;base64,{b64_map}');background-size:cover;border:1px solid #444;"></div><div><div style="color:#00BFFF;font-weight:bold;font-size:1.1em;text-transform:uppercase;">{row['Name']}</div><div style="color:#666;font-size:0.8em;">{row['Map']}</div></div><div style="margin-left:auto;padding-right:10px;">{ag_html}</div></div></div>""", unsafe_allow_html=True)
                    if st.button(f"OPEN TACTICS >>", key=f"btn_{row['ID']}"):
                        st.session_state['sel_pb_id'] = row['ID']; st.rerun()
            else:
                st.info("No Playbooks defined yet.")

        else:
            # Single Playbook
            pb = df_pb[df_pb['ID'] == st.session_state['sel_pb_id']].iloc[0]
            st.button("⬅ BACK TO LOBBY", on_click=lambda: st.session_state.update({'sel_pb_id': None}))
            
            header_col1, header_col2 = st.columns([1, 4])
            with header_col1: st.image(get_map_img(pb['Map'], 'list'), use_container_width=True)
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
                            pd.concat([df_pb, pd.DataFrame([new_strat])], ignore_index=True).to_csv(PB_STRATS_FILE, index=False); st.rerun()

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
                                        df_pb_strats.to_csv(PB_STRATS_FILE, index=False); st.rerun()
                                if st.button("Clear Protocols", key=f"clr_{strat['Strat_ID']}"):
                                    df_pb_strats.loc[df_pb_strats['Strat_ID'] == strat['Strat_ID'], 'Protocols'] = '[]'
                                    df_pb_strats.to_csv(PB_STRATS_FILE, index=False); st.rerun()
                        st.divider()

    # --------------------------------------------------------------------------
    # TAB 2: TACTICAL WHITEBOARD (100% CORRECTED)
    # --------------------------------------------------------------------------
    with tab_whiteboard:
        st.subheader("TACTICAL BOARD")
        
        # Map selection
        wb_map = st.selectbox("Select Map", sorted(df['Map'].unique()) if not df.empty else ["Ascent"])
        
        # Agent Icons Referenz
        st.caption("Agent Referenz (für Kreise):")
        agent_files = glob.glob(os.path.join(ASSET_DIR, "agents", "*.png"))
        if agent_files:
            st.image([Image.open(x) for x in agent_files], width=20)
        
        # Agent Auswahl für Platzierung
        agent_options = [os.path.basename(x).replace('.png', '') for x in agent_files] if agent_files else []
        selected_agent = st.selectbox("Agent für Platzierung:", agent_options, key="selected_agent") if agent_options else None
        
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
        
        map_pbs = df_pb[df_pb['Map'] == wb_map]
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
            
            if st.button("💾 SAVE STRATEGY", type="primary", use_container_width=True):
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
                        pb_id = df_pb[df_pb['Name']==assign_pb].iloc[0]['ID']
                        new_entry = {
                            'PB_ID': pb_id, 
                            'Strat_ID': str(uuid.uuid4()), 
                            'Name': strat_name, 
                            'Image': fname, 
                            'Protocols': '[]'
                        }
                        pd.concat([df_pb_strats, pd.DataFrame([new_entry])], ignore_index=True).to_csv(PB_STRATS_FILE, index=False)
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

        def save_theory_data(m, s, text, new_img_obj, old_img_name):
            img_name = old_img_name
            if new_img_obj:
                img_name = f"THEORY_{m}_{s}_{int(datetime.now().timestamp())}.png".replace(" ", "_")
                with open(os.path.join(STRAT_IMG_DIR, img_name), "wb") as f: f.write(new_img_obj.getbuffer())
            new_df = df_theory[~((df_theory['Map'] == m) & (df_theory['Section'] == s))]
            new_entry = pd.DataFrame([{'Map': m, 'Section': s, 'Content': text, 'Image': img_name}])
            pd.concat([new_df, new_entry], ignore_index=True).to_csv(MAP_THEORY_FILE, index=False)
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
                    save_theory_data(theory_map, sec_name, new_txt, new_img, curr_img)
                    st.success("Saved"); st.rerun()

    # --------------------------------------------------------------------------
    # TAB 4: EXTERNAL LINKS
    # --------------------------------------------------------------------------
    with tab_links:
        pb_df = load_csv_generic(PLAYBOOKS_FILE, ['Map', 'Name', 'Link', 'Agent_1', 'Agent_2', 'Agent_3', 'Agent_4', 'Agent_5'])
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
                    pd.concat([pb_df, pd.DataFrame([nr])], ignore_index=True).to_csv(PLAYBOOKS_FILE, index=False)
                    st.rerun()

        if not pb_df.empty:
            f_pb = st.selectbox("Links Map:", ["All"]+sorted(pb_df['Map'].unique()), key="fl_map")
            v_pb = pb_df if f_pb == "All" else pb_df[pb_df['Map'] == f_pb]
            for idx, row in v_pb.iterrows():
                ags_html = ""
                for i in range(1,6):
                    ag = row.get(f'Agent_{i}')
                    if pd.notna(ag) and ag:
                        b64 = img_to_b64(get_agent_img(ag))
                        ags_html += f'<img src="data:image/png;base64,{b64}" style="width:30px; margin-right:3px;">'
                st.markdown(f"""
                <div class='pb-card' style='border-left: 4px solid #FF1493;'>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div><div style="font-weight:bold; font-size:1.1em">{row['Name']}</div><div style="color:#888">{row['Map']}</div><div style="margin-top:5px">{ags_html}</div></div>
                        <a href="{row['Link']}" target="_blank" style="background:linear-gradient(90deg, #00BFFF, #FF1493); color:white; padding:8px 15px; border-radius:5px; text-decoration:none; font-weight:bold;">OPEN LINK</a>
                    </div>
                </div>""", unsafe_allow_html=True)

# ==============================================================================
# 5. RESOURCES
# ==============================================================================
elif page == "📚 RESOURCES":
    st.title("KNOWLEDGE BASE")
    res_df = load_csv_generic(RESOURCES_FILE, ['Title', 'Link', 'Category', 'Note'])
    with st.expander("➕ Add"):
        with st.form("ra"):
            rt = st.text_input("Title"); rl = st.text_input("Link"); rc = st.selectbox("Cat", ["Theory", "Lineups", "Setup", "Playbook Theory"]); rn = st.text_area("Note")
            if st.form_submit_button("Save"):
                pd.concat([res_df, pd.DataFrame([{'Title': rt, 'Link': rl, 'Category': rc, 'Note': rn}])], ignore_index=True).to_csv(RESOURCES_FILE, index=False); st.rerun()
    
    if not res_df.empty:
        cats = st.multiselect("Filter:", res_df['Category'].unique(), default=res_df['Category'].unique())
        view = res_df[res_df['Category'].isin(cats)]
        cols = st.columns(4)
        for i, (idx, row) in enumerate(view.iterrows()):
            with cols[i%4]:
                thumb = get_yt_thumbnail(row['Link'])
                img = f"<img src='{thumb}' class='res-thumb'>" if thumb else "<div style='height:140px; background:#222; display:flex; align-items:center; justify-content:center'>📄</div>"
                st.markdown(f"""<div class="res-tile">{img}<div class="res-info"><div style="color:#00BFFF; font-size:0.8em">{row['Category']}</div><div style="font-weight:bold">{row['Title']}</div><a href="{row['Link']}" target="_blank" style="color:#aaa; font-size:0.8em">OPEN</a></div></div>""", unsafe_allow_html=True)
    
    with st.expander("✏️ Edit"):
        ed = st.data_editor(res_df, num_rows="dynamic")
        if st.button("Save Changes"): ed.to_csv(RESOURCES_FILE, index=False); st.rerun()

# ==============================================================================
# 6. CALENDAR
# ==============================================================================
elif page == "📅 CALENDAR":
    st.title("SCHEDULE")
    if 'cy' not in st.session_state: st.session_state['cy'] = datetime.now().year
    if 'cm' not in st.session_state: st.session_state['cm'] = datetime.now().month
    
    c1, c2 = st.columns([2, 1])
    cal_df = load_csv_generic(CALENDAR_FILE, ['Date', 'Time', 'Event', 'Map', 'Type'])
    todo_df = load_csv_generic(TODO_FILE, ['Task', 'Done'])
    if 'Done' not in todo_df.columns: todo_df['Done'] = False
    
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
                        evs = cal_df[cal_df['Date']==d_s]
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
                    pd.concat([cal_df, pd.DataFrame([{'Date':cd.strftime("%d.%m.%Y"),'Time':ct.strftime("%H:%M"),'Event':ce,'Map':cm,'Type':cty}])], ignore_index=True).to_csv(CALENDAR_FILE, index=False); st.rerun()

    with c2:
        st.subheader("TODO")
        with st.form("td"):
            t = st.text_input("Task")
            if st.form_submit_button("Add"):
                pd.concat([todo_df, pd.DataFrame([{'Task':t, 'Done':False}])], ignore_index=True).to_csv(TODO_FILE, index=False); st.rerun()
        if not todo_df.empty:
            ed = st.data_editor(todo_df, num_rows="dynamic")
            if st.button("Save Todo"): ed.to_csv(TODO_FILE, index=False); st.success("Saved")

# ==============================================================================
# 7. PLAYERS
# ==============================================================================
elif page == "📊 PLAYERS":
    st.title("PLAYER PERFORMANCE")
    if not df_players.empty:
        p_agg = df_players.groupby('Player').agg({
            'MatchID': 'count',
            'Kills': 'sum', 'Deaths': 'sum', 'Assists': 'sum', 'Score': 'sum', 'Rounds': 'sum',
            'HS': 'mean'
        }).reset_index()
        p_agg['SafeDeaths'] = p_agg['Deaths'].replace(0, 1)
        p_agg['KD'] = p_agg['Kills'] / p_agg['SafeDeaths']
        p_agg['ACS'] = p_agg['Score'] / p_agg['Roundss']
        p_agg = p_agg.rename(columns={'MatchID': 'Matches'})
        
        st.dataframe(
            p_agg[['Player', 'Matches', 'KD', 'ACS', 'HS', 'Kills']],
            column_config={
                "KD": st.column_config.ProgressColumn("K/D", format="%.2f", min_value=0, max_value=3),
                "ACS": st.column_config.NumberColumn("ACS", format="%.0f"),
                "HS": st.column_config.NumberColumn("HS%", format="%.1f%%")
            },
            use_container_width=True, hide_index=True
        )
        st.caption("Stats based on imported JSONs.")
    else: st.info("No player stats yet. Import JSON matches to see data.")

# ==============================================================================
# 8. DATABASE
# ==============================================================================
elif page == "💾 DATABASE":
    st.header("Database"); ed = st.data_editor(df, num_rows="dynamic")
    if st.button("Save"): ed.to_csv(DATA_FILE_CSV, index=False); st.success("Saved")