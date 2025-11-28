"""
Script per scaricare automaticamente i valori NAV del Fondo FONTE Dinamico
usando Selenium per gestire contenuto JavaScript dinamico.

Uso:
  python scrape_fonte.py

Output:
  - fonte_dinamico.json (per Portfolio Performance)
  - fonte_dinamico.csv (alternativa CSV)
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

def scrape_fonte_dinamico():
    """Scarica i valori NAV dal sito Fondo FONTE usando Selenium"""
    
    print("=" * 60)
    print("FONDO FONTE DINAMICO - Scraper automatico")
    print("=" * 60)
    
    url = "https://www.fondofonte.it/gestione-finanziaria/i-valori-quota-dei-comparti/comparto-dinamico/"
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
        None  # Usa quello di default
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
                print(f"❌ {chrome_path} non funziona: {str(e)[:100]}")
            continue
    
    if not driver:
        print("❌ Impossibile avviare Chrome!")
        sys.exit(1)
    
    try:
        driver.set_page_load_timeout(30)
        driver.get(url)
        
        print("⏳ Attendo caricamento pagina...")
        time.sleep(5)
        
        # Trova tutti gli elementi cliccabili degli anni (accordion)
        print("🔍 Cerco gli accordion degli anni...")
        
        # Cerca elementi con pattern [YYYY] o link javascript
        year_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'javascript')]")
        print(f"📋 Trovati {len(year_elements)} elementi cliccabili")
        
        # Clicca su tutti gli accordion per espanderli
        for element in year_elements[:20]:  # Limita a 20 per sicurezza
            try:
                driver.execute_script("arguments[0].click();", element)
                time.sleep(0.3)  # Piccola pausa tra i click
            except:
                pass
        
        print("⏳ Aspetto espansione contenuti...")
        time.sleep(3)
        
        # Prendi tutto il contenuto HTML
        page_source = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        print(f"✅ Contenuto caricato: {len(page_text)} caratteri")
        
        if len(page_text) < 1500:
            print("⚠️ Contenuto troppo breve - provo approccio alternativo...")
            
            # Prova a fare scroll per attivare lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            page_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"📄 Contenuto dopo scroll: {len(page_text)} caratteri")
        
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
    
    months_it = {
        "Gennaio": "01", "Febbraio": "02", "Marzo": "03", "Aprile": "04",
        "Maggio": "05", "Giugno": "06", "Luglio": "07", "Agosto": "08",
        "Settembre": "09", "Ottobre": "10", "Novembre": "11", "Dicembre": "12"
    }
    
    print("🔍 Estrazione dati dal contenuto...")
    
    # Cerca pattern anno nel testo
    lines = page_text.split('\n')
    current_year = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Cerca anno (linea con solo 4 cifre)
        if re.match(r'^\d{4}$', line):
            current_year = line
            print(f"📅 Anno trovato: {current_year}")
            continue
        
        # Se abbiamo un anno corrente, cerca mese + valore
        if current_year:
            # Pattern: Mese seguito da valore con virgola
            match = re.match(r'^(Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre)$', line)
            if match and i + 1 < len(lines):
                month_name = match.group(1)
                next_line = lines[i + 1].strip()
                
                # Il valore dovrebbe essere nella riga successiva
                if re.match(r'^[\d,]+$', next_line) and ',' in next_line:
                    month_num = months_it[month_name]
                    try:
                        nav = float(next_line.replace(",", "."))
                        date_str = f"{current_year}-{month_num}-01"
                        nav_data.append({
                            "date": date_str,
                            "value": nav
                        })
                    except ValueError:
                        continue
    
    try:
        driver.quit()
        print("🔒 Browser chiuso")
    except:
        pass
    
    if not nav_data:
        print("❌ ERRORE: Nessun dato estratto!")
        print("\n📄 Contenuto pagina (primi 2000 caratteri):")
        print(page_text[:2000])
        print("\n📄 Ultime 100 righe del contenuto:")
        print('\n'.join(lines[-100:]))
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
        "name": "FONTE Dinamico",
        "isin": "N/A",
        "currency": "EUR",
        "feed": "custom",
        "source": "https://www.fondofonte.it",
        "last_updated": datetime.now().isoformat(),
        "total_entries": len(nav_data),
        "prices": nav_data
    }
    
    # Salva JSON
    with open("fonte_dinamico.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Salva CSV
    csv_content = "Date;Value;Currency\n"
    for entry in nav_data:
        csv_content += f"{entry['date']};{entry['value']:.4f};EUR\n"
    
    with open("fonte_dinamico.csv", "w", encoding="utf-8") as f:
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
    print(f"   • fonte_dinamico.json")
    print(f"   • fonte_dinamico.csv")
    print("\n" + "=" * 60)
    
    return output

if __name__ == "__main__":
    try:
        scrape_fonte_dinamico()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operazione interrotta dall'utente")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
