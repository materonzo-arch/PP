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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Su GitHub Actions usa chromium-chromedriver
    chrome_options.binary_location = "/usr/bin/chromium-browser"
    
    driver = None
    try:
        print("🌐 Avvio browser headless...")
        
        # Usa ChromeDriver di sistema
        from selenium.webdriver.chrome.service import Service
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.set_page_load_timeout(30)
        driver.get(url)
        
        print("⏳ Attendo caricamento contenuto...")
        time.sleep(8)  # Aspetta il caricamento JavaScript
        
        # Prendi tutto il testo
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        print(f"✅ Pagina caricata: {len(page_text)} caratteri")
        
        if len(page_text) < 500:
            print("⚠️ Contenuto troppo breve!")
            print("Contenuto:")
            print(page_text[:500])
            raise ValueError("Pagina non caricata correttamente")
        
    except Exception as e:
        print(f"❌ Errore durante il caricamento: {e}")
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
    
    print("🔍 Estrazione dati...")
    
    # Cerca pattern anno
    year_blocks = re.split(r'(\d{4})\s*(?:javascript|Periodo)', page_text)
    
    current_year = None
    for i, block in enumerate(year_blocks):
        if re.match(r'^\d{4}$', block.strip()):
            current_year = block.strip()
            continue
        
        if current_year and i > 0:
            patterns = re.findall(
                r'(Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre)\s+([\d,]+)',
                block
            )
            
            for month_name, nav_str in patterns:
                if month_name in months_it and ',' in nav_str:
                    month_num = months_it[month_name]
                    try:
                        nav = float(nav_str.replace(",", "."))
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
        print("❌ ERRORE: Nessun dato estratto dalla pagina!")
        print("\n📄 Contenuto (primi 2000 caratteri):")
        print(page_text[:2000])
        print("\n💡 Suggerimento: Il sito potrebbe aver cambiato struttura")
        sys.exit(1)
    
    # Rimuovi duplicati
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
