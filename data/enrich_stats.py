import pandas as pd
import requests
import time
import os
import glob

# --- KONFIGURATION ---
FILE_PATTERN = "Premier*Gametracker.csv"
OUTPUT_CSV = "Premier - Gametracker_ENRICHED.csv"
API_KEY = "HDEV-8aaa04d3-e0f5-4b20-9b54-31dd6d4a03ad"

def main():
    print("--- NEXUS STATS ENRICHER (Smart Column Fix) ---")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_path = os.path.join(script_dir, FILE_PATTERN)
    found_files = glob.glob(search_path)
    
    if not found_files:
        print(f"❌ Keine Datei gefunden.")
        return

    input_file_path = found_files[0]
    print(f"✅ Datei gefunden: {os.path.basename(input_file_path)}")

    try:
        # Wir lesen ab Zeile 3 (header=2)
        df = pd.read_csv(input_file_path, header=2)
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return

    # --- INTELLIGENTE SPALTEN SUCHE ---
    # Problem: Deine MatchID Spalte hat in Zeile 3 keinen Namen (ist leer ,,)
    # Lösung: Wir nehmen die allerletzte Spalte, da stehen deine IDs drin!
    
    match_id_col_name = df.columns[-1] # Die letzte Spalte
    print(f"ℹ️ Nutze letzte Spalte als ID-Quelle: '{match_id_col_name}'")
    
    # Umbenennen damit wir sauber arbeiten können
    df.rename(columns={match_id_col_name: 'MatchID_Internal'}, inplace=True)

    # Neue Spalten
    new_cols = ['Retake W', 'Retake L', 'Postplant W', 'Postplant L']
    for col in new_cols:
        if col not in df.columns:
            df[col] = 0

    print(f"Analysiere {len(df)} Zeilen...")

    for index, row in df.iterrows():
        # Wir holen die ID aus der letzten Spalte
        raw_id = str(row['MatchID_Internal']).strip()
        
        # Filter: Nur echte IDs (länger als 10 Zeichen, keine Kommas)
        if len(raw_id) < 10 or "http" in raw_id or "," in raw_id:
            continue
            
        print(f"Lade Daten für Match: {raw_id} ...")
        
        # API Abfrage
        url = f"https://api.henrikdev.xyz/valorant/v2/match/{raw_id}"
        try:
            r = requests.get(url, headers={"Authorization": API_KEY})
            if r.status_code == 200:
                data = r.json()
                match_data = data.get('data', {})
                rounds = match_data.get('rounds', [])
                
                if not rounds: continue

                # Team Color herausfinden (Wir suchen nach einem bekannten Spieler)
                my_team = "Red" # Default
                for p in match_data.get('players', {}).get('all_players', []):
                    # Passe "Luggi" an deinen Ingame Namen an falls nötig
                    if "Luggi" in p.get('name', ''): 
                        my_team = p.get('team')
                        break
                
                # Stats Zähler
                retake_w = 0; retake_l = 0
                post_w = 0; post_l = 0
                
                for rnd in rounds:
                    winner = rnd.get('winning_team')
                    we_won = (winner == my_team)
                    
                    plant = rnd.get('plant_events')
                    if plant and plant.get('plant_location'):
                        planter_team = plant.get('planted_by', {}).get('team')
                        
                        if planter_team == my_team:
                            # Wir haben geplantet -> Postplant
                            if we_won: post_w += 1
                            else: post_l += 1
                        else:
                            # Gegner hat geplantet -> Retake
                            if we_won: retake_w += 1
                            else: retake_l += 1
                
                # Schreiben
                df.at[index, 'Retake W'] = retake_w
                df.at[index, 'Retake L'] = retake_l
                df.at[index, 'Postplant W'] = post_w
                df.at[index, 'Postplant L'] = post_l
                
                print(f"   -> Retake: {retake_w}-{retake_l} | Post: {post_w}-{post_l}")
                time.sleep(1.2) # API Limit
            else:
                print(f"   ⚠️ API Fehler: {r.status_code}")
        except Exception as e:
            print(f"   ⚠️ Fehler: {e}")

    # Speichern
    output_path = os.path.join(script_dir, OUTPUT_CSV)
    df.to_csv(output_path, index=False)
    print(f"\n✅ Fertig! Datei gespeichert: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()