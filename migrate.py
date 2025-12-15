import pandas as pd
import glob
import os

# CONFIG
OLD_FILES = "data/Premier*Gametracker.csv"
DB_FILE = "data/nexus_matches.csv"

def migrate():
    print("--- ROBUSTE MIGRATION (INDEX-BASIERT) ---")
    files = glob.glob(OLD_FILES)
    if not files: 
        print(f"❌ Keine Datei gefunden: {OLD_FILES}")
        # Versuch im Hauptordner
        files = glob.glob("Premier*Gametracker.csv")
        if not files: return

    file_path = files[0]
    print(f"Lade Datei: {file_path}")

    try:
        # Wir laden ohne Header-Logik, einfach Daten ab Zeile 3
        df = pd.read_csv(file_path, header=2)
    except Exception as e:
        print(f"Lesefehler: {e}")
        return
    
    # --- BEREINIGUNG ---
    # Wir nutzen iloc (Index Location) statt Namen
    # Map ist Index 4 (Spalte E)
    # Wir filtern Zeilen raus, wo Map leer ist
    df = df[df.iloc[:, 4].notna()]
    
    # Filtern der Header-Wiederholung ("Map" steht in Spalte "Map")
    df = df[df.iloc[:, 4] != 'Map']

    print(f"Gefundene Matches: {len(df)}")

    # --- DATEN ZUORDNEN ---
    new_df = pd.DataFrame()
    
    # Basis Infos
    new_df['Date'] = df.iloc[:, 2]        # Spalte C
    new_df['Map'] = df.iloc[:, 4]         # Spalte E
    new_df['Result'] = df.iloc[:, 14]     # Spalte O (W/L)
    new_df['Score_Us'] = df.iloc[:, 12]   # Spalte M
    new_df['Score_Enemy'] = df.iloc[:, 13]# Spalte N
    new_df['VOD_Link'] = df.iloc[:, 16]   # Spalte Q
    
    # MatchID ist die allerletzte Spalte
    new_df['MatchID'] = df.iloc[:, -1]

    # --- AGENTEN ---
    # Spalten R, S, T, U, V sind Index 17, 18, 19, 20, 21
    # Wir prüfen sicherheitshalber ob genug Spalten da sind
    if df.shape[1] >= 22:
        new_df['MyComp_1'] = df.iloc[:, 17]
        new_df['MyComp_2'] = df.iloc[:, 18]
        new_df['MyComp_3'] = df.iloc[:, 19]
        new_df['MyComp_4'] = df.iloc[:, 20]
        new_df['MyComp_5'] = df.iloc[:, 21]
    else:
        print("⚠️ Warnung: Keine Agenten-Spalten gefunden.")
        for i in range(1, 6): new_df[f'MyComp_{i}'] = None

    # --- ZAHLEN BEREINIGEN ---
    def clean(v):
        try: return float(str(v).replace(',', '.').replace('%', '').strip())
        except: return 0.0

    new_df['Pistol_Def_W'] = df.iloc[:, 5].apply(clean) # F
    new_df['Pistol_Atk_W'] = df.iloc[:, 6].apply(clean) # G
    new_df['Def_R_W'] = df.iloc[:, 7].apply(clean)      # H
    new_df['Def_R_L'] = df.iloc[:, 8].apply(clean)      # I
    new_df['Atk_R_W'] = df.iloc[:, 9].apply(clean)      # J
    new_df['Atk_R_L'] = df.iloc[:, 10].apply(clean)     # K
    
    new_df['Source'] = 'Legacy'

    # Speichern
    new_df.to_csv(DB_FILE, index=False)
    print(f"✅ ERFOLG! Datenbank erstellt: {DB_FILE}")

if __name__ == "__main__":
    migrate()