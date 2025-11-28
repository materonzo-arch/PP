"""
Script per scaricare automaticamente i valori NAV del Fondo FONCHIM Crescita
usando Selenium e parsing del testo.

Uso:
  python scrape_fonchim.py

Output:
  - fonchim_crescita.json (per Portfolio Performance)
  - fonchim_crescita.csv (alternativa CSV)
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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
        time.sleep(8)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"✅ Contenuto caricato: {len(page_text)} caratteri")
        
    except Exception as e:
        print(f"❌ Errore caricamento: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        sys.exit(1)
    
    # Parsing dei dati dal testo
    nav_data = []
    
    print("🔍 Estrazione dati dal testo...")
    
    # La tabella ha questo formato nel testo:
    # Data Stabilità Crescita Garantito Moneta
    # 17/11/2025 € 26,042 € 34,509 € 12,849
    # 31/10/2025 € 26,184 € 34,831 € 12,873
    
    lines = page_text.split('\n')
    
    # Cerca pattern: data DD/MM/YYYY seguita da valori
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Pattern: DD/MM/YYYY all'inizio della riga
        date_match = re.match(r'^(\d{1,2}/\d{1,2}/\d{4})', line)
        
        if date_match:
            date_str = date_match.group(1)
            
            # Prendi il resto della riga dopo la data
            rest_of_line = line[len(date_str):].strip()
            
            # Trova tutti i valori € XX,XXX nella riga
            values = re.findall(r'€\s*([\d,]+)', rest_of_line)
            
            if len(values) >= 2:
                # values[0] = Stabilità
                # values[1] = Crescita ✅
                # values[2] = Garantito (se presente)
                # values[3] = Moneta (se presente)
                
                try:
                    crescita_value = values[1].replace(",", ".")
                    nav_value = float(crescita_value)
                    
                    # Converti data DD/MM/YYYY -> YYYY-MM-DD
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        day, month, year = parts
                        date_formatted = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        
                        nav_data.append({
                            "date": date_formatted,
                            "value": nav_value
                        })
                        
                        # Debug prime 3 righe
                        if len(nav_data) <= 3:
                            print(f"  ✓ {date_str} → Crescita: €{nav_value:.3f}")
                
                except (ValueError, IndexError) as e:
                    continue
    
    try:
        driver.quit()
        print("🔒 Browser chiuso")
    except:
        pass
    
    if not nav_data:
        print("❌ ERRORE: Nessun dato estratto!")
        print("\n📄 Ultime 50 righe del contenuto:")
        print('\n'.join(lines[-50:]))
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
