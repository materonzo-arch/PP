"""
Script per scaricare automaticamente i valori NAV del Fondo FONCHIM Crescita
usando Selenium per gestire contenuto JavaScript dinamico.

Uso:
  python scrape_fonchim.py

Output:
  - fonchim_crescita.json (per Portfolio Performance)
  - fonchim_crescita.csv (alternativa CSV)
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import re
from datetime import datetime
import sys
import time

def scrape_fonchim_crescita():
    """Scarica i valori NAV dal sito FONCHIM usando Selenium"""
    
    print("=" * 60)
    print("FONCHIM CRESCITA - Scraper automatico")
    print("=" * 60)
    
    url = "https://www.fonchim.it/site/funziona-fondo/rendimenti-quote"
    print(f"\n📥 Download da: {url}")
    
    # Configurazione Chrome headless
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Prova diversi percorsi di Chrome
    chrome_paths = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        None
    ]
    
    driver = None
    for chrome_path in chrome_paths:
        try:
            if chrome_path:
                chrome_options.binary_location = chrome_path
                print(f"🔍 Provo Chrome: {chrome_path}")
            else:
                print("🔍 Provo Chrome di default")
            
            driver = webdriver.Chrome(options=chrome_options)
            print(f"✅ Chrome avviato!")
            break
        except Exception as e:
            if chrome_path:
                print(f"❌ {chrome_path} non funziona")
            continue
    
    if not driver:
        print("❌ Impossibile avviare Chrome!")
        sys.exit(1)
    
    try:
        driver.set_page_load_timeout(30)
        driver.get(url)
        
        print("⏳ Attendo caricamento pagina...")
        time.sleep(8)  # Aspetta caricamento JavaScript
        
        # Prova a trovare tabelle o elementi con i dati
        page_text = driver.find_element(By.TAG_NAME, "body").text
        page_html = driver.page_source
        
        print(f"✅ Contenuto caricato: {len(page_text)} caratteri")
        
        # Cerca tabelle
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"📊 Trovate {len(tables)} tabelle")
        
        # Cerca anche altri elementi comuni
        divs_with_data = driver.find_elements(By.XPATH, "//*[contains(text(), 'Crescita') or contains(text(), 'crescita')]")
        print(f"📋 Trovati {len(divs_with_data)} elementi con 'Crescita'")
        
    except Exception as e:
        print(f"❌ Errore caricamento: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        sys.exit(1)
    
    # Parsing dei dati
    nav_data = []
    
    print("🔍 Estrazione dati...")
    
    # Strategia 1: Cerca pattern data + valore nel testo
    # Pattern tipici: "01/2024 15,234" o "Gennaio 2024 15,234"
    lines = page_text.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Pattern: data formato DD/MM/YYYY o MM/YYYY + valore
        match_date_value = re.search(r'(\d{2}/\d{2}/\d{4}|\d{2}/\d{4})\s+([\d,\.]+)', line)
        if match_date_value:
            date_str = match_date_value.group(1)
            value_str = match_date_value.group(2)
            
            try:
                # Converti data
                if '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:  # DD/MM/YYYY
                        date_formatted = f"{parts[2]}-{parts[1]}-{parts[0]}"
                    elif len(parts) == 2:  # MM/YYYY
                        date_formatted = f"{parts[1]}-{parts[0]}-01"
                    else:
                        continue
                else:
                    continue
                
                # Converti valore
                value = float(value_str.replace(",", "."))
                
                nav_data.append({
                    "date": date_formatted,
                    "value": value
                })
            except (ValueError, IndexError):
                continue
    
    # Strategia 2: Se non trova dati, analizza le tabelle HTML
    if not nav_data and tables:
        print("🔍 Analizzo tabelle HTML...")
        
        for table_idx, table in enumerate(tables):
            try:
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                # Cerca la colonna "Crescita"
                headers = []
                crescita_col_idx = -1
                date_col_idx = 0  # La data è sempre la prima colonna
                
                if rows:
                    header_row = rows[0]
                    header_cells = header_row.find_elements(By.TAG_NAME, "th")
                    if not header_cells:
                        header_cells = header_row.find_elements(By.TAG_NAME, "td")
                    
                    for idx, cell in enumerate(header_cells):
                        cell_text = cell.text.strip().lower()
                        headers.append(cell_text)
                        if 'crescita' in cell_text:
                            crescita_col_idx = idx
                            print(f"✅ Trovata colonna Crescita all'indice {idx}")
                        if 'data' in cell_text or 'periodo' in cell_text or 'mese' in cell_text:
                            date_col_idx = idx
                            print(f"✅ Trovata colonna Data all'indice {idx}")
                
                if crescita_col_idx >= 0:
                    print(f"🔍 Estraggo dati: Data=colonna {date_col_idx}, Crescita=colonna {crescita_col_idx}")
                    # Estrai i dati dalle righe
                    for row_idx, row in enumerate(rows[1:], 1):  # Salta header
                        cells = row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cells) <= crescita_col_idx:
                            continue
                        
                        try:
                            date_text = cells[date_col_idx].text.strip()
                            value_text = cells[crescita_col_idx].text.strip()
                            
                            # Debug prime 3 righe
                            if row_idx <= 3:
                                print(f"  Riga {row_idx}: [{len(cells)} celle] data='{date_text}' crescita='{value_text}'")
                            
                            # Rimuovi €, spazi e converti virgola in punto
                            value_clean = value_text.replace("€", "").replace(" ", "").replace(",", ".").replace("\u00a0", "").strip()
                            
                            if not value_clean or not date_text:
                                continue
                            
                            value = float(value_clean)
                            
                            # Parsea la data formato DD/MM/YYYY
                            if '/' in date_text:
                                parts = date_text.split('/')
                                if len(parts) == 3:
                                    day, month, year = parts
                                    date_formatted = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                    
                                    nav_data.append({
                                        "date": date_formatted,
                                        "value": value
                                    })
                                elif len(parts) == 2:
                                    month, year = parts
                                    date_formatted = f"{year}-{month.zfill(2)}-01"
                                    
                                    nav_data.append({
                                        "date": date_formatted,
                                        "value": value
                                    })
                        except (ValueError, IndexError) as e:
                            if row_idx <= 3:
                                print(f"  ⚠️  Errore riga {row_idx}: {e}")
                            continue
                    
                    print(f"✅ Estratte {len(nav_data)} righe dalla tabella")
            except Exception as e:
                continue
    
    try:
        driver.quit()
        print("🔒 Browser chiuso")
    except:
        pass
    
    if not nav_data:
        print("❌ ERRORE: Nessun dato estratto!")
        print("\n📄 Contenuto pagina (primi 3000 caratteri):")
        print(page_text[:3000])
        print("\n📄 Headers trovati:", headers if 'headers' in locals() else "Nessuna tabella")
        sys.exit(1)
    
    # Rimuovi duplicati e ordina
    seen = set()
    unique_data = []
    for item in nav_data:
        if item["date"] not in seen:
            seen.add(item["date"])
            unique_data.append(item)
    
    nav_data = sorted(unique_data, key=lambda x: x["date"])
    
    # Crea JSON per Portfolio Performance
    output = {
        "name": "FONCHIM Crescita",
        "isin": "N/A",
        "currency": "EUR",
        "feed": "custom",
        "source": "https://www.fonchim.it",
        "last_updated": datetime.now().isoformat(),
        "total_entries": len(nav_data),
        "prices": nav_data
    }
    
    # Salva JSON
    with open("fonchim_crescita.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Salva CSV
    csv_content = "Date;Value;Currency\n"
    for entry in nav_data:
        csv_content += f"{entry['date']};{entry['value']:.4f};EUR\n"
    
    with open("fonchim_crescita.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    # Statistiche
    print(f"\n✅ Scraping completato con successo!")
    print(f"\n📊 Statistiche:")
    print(f"   • Totale valori estratti: {len(nav_data)}")
    print(f"   • Periodo: {nav_data[0]['date']} → {nav_data[-1]['date']}")
    print(f"   • Primo valore: €{nav_data[0]['value']:.4f}")
    print(f"   • Ultimo valore: €{nav_data[-1]['value']:.4f}")
    
    if len(nav_data) >= 2:
        first_value = nav_data[0]['value']
        last_value = nav_data[-1]['value']
        total_return = ((last_value - first_value) / first_value) * 100
        print(f"   • Rendimento totale: {total_return:+.2f}%")
    
    print(f"\n📁 File generati:")
    print(f"   • fonchim_crescita.json")
    print(f"   • fonchim_crescita.csv")
    print("\n" + "=" * 60)
    
    return output

if __name__ == "__main__":
    try:
        scrape_fonchim_crescita()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operazione interrotta dall'utente")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
