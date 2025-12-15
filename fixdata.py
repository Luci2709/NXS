import pandas as pd
import glob
import os

# CONFIG
SEARCH_PATTERN = "data/Premier*Gametracker.csv"
OUTPUT_FILE = "data/nexus_matches.csv"

def fix_db_final():
    print("--- FINALE DATENBANK REPARATUR ---")
    
    files = glob.glob(SEARCH_PATTERN)
    if not files:
        print("❌ Keine Gametracker Datei gefunden.")
        return

    filepath = files[0]
    print(f"Lade Rohdaten: {filepath}")

    try:
        # TRICK: Wir lesen OHNE Header (alles ist Daten)
        df = pd.read_csv(filepath, header=None)
    except Exception as e:
        print(f"Lesefehler: {e}")
        return

    # 1. Den echten Start finden
    # Wir suchen die Zeile, in der in Spalte 4 "Map" steht
    start_row_index = -1
    for i, row in df.iterrows():
        # Wir prüfen Spalte E (Index 4)
        val = str(row[4]).strip()
        if val == "Map":
            start_row_index = i
            break
            
    if start_row_index == -1:
        print("❌ Konnte Header-Zeile ('Map') nicht finden.")
        return
        
    print(f"Header gefunden in Zeile {start_row_index + 1}. Daten beginnen danach.")
    
    # 2. Daten ausschneiden (Alles NACH der Header-Zeile)
    data_df = df.iloc[start_row_index + 1:].copy()
    
    # Leere Maps filtern
    data_df = data_df[data_df[4].notna()]
    
    print(f"Anzahl Matches: {len(data_df)}")

    # 3. Neue saubere Datenbank aufbauen
    # Wir greifen HART auf die Spalten-Nummern zu (A=0, B=1, E=4...)
    new_df = pd.DataFrame()
    
    new_df['Date'] = data_df[2]       # C
    new_df['Map'] = data_df[4].astype(str).str.strip() # E
    new_df['Result'] = data_df[14]    # O (W/L)
    new_df['VOD_Link'] = data_df[16]  # Q
    
    # Scores (Spalte M=12, N=13)
    def clean_int(val):
        try: return int(float(str(val).replace(',', '.')))
        except: return 0
        
    new_df['Score_Us'] = data_df[12].apply(clean_int)
    new_df['Score_Enemy'] = data_df[13].apply(clean_int)
    
    # Match ID (Letzte Spalte - wir nehmen Index 25 oder -1)
    new_df['MatchID'] = data_df.iloc[:, -1]

    # AGENTEN (Spalte 20-24 / U-Y)
    # Check: Spalte 20 ist "COMP" im Header, also Daten darunter
    try:
        new_df['MyComp_1'] = data_df[20]
        new_df['MyComp_2'] = data_df[21]
        new_df['MyComp_3'] = data_df[22]
        new_df['MyComp_4'] = data_df[23]
        new_df['MyComp_5'] = data_df[24]
    except:
        print("⚠️ Warnung: Agenten-Spalten fehlen.")
        for i in range(1,6): new_df[f'MyComp_{i}'] = None

    # STATS (Runden W/L, Pistols)
    def clean_float(val):
        try: return float(str(val).replace(',', '.').replace('%', '').strip())
        except: return 0.0

    new_df['Pistol_Def_W'] = data_df[5].apply(clean_float) # F
    new_df['Pistol_Atk_W'] = data_df[6].apply(clean_float) # G
    new_df['Def_R_W'] = data_df[7].apply(clean_float)      # H
    new_df['Def_R_L'] = data_df[8].apply(clean_float)      # I
    new_df['Atk_R_W'] = data_df[9].apply(clean_float)      # J
    new_df['Atk_R_L'] = data_df[10].apply(clean_float)     # K
    
    new_df['Source'] = 'Legacy'

    # 4. Speichern
    new_df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Datenbank erfolgreich repariert: {OUTPUT_FILE}")
    print("Starte jetzt 'app.py'!")

if __name__ == "__main__":
    fix_db_final()