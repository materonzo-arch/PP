"""
Script per scaricare automaticamente i valori NAV del Fondo FONTE Dinamico
e generare un JSON compatibile con Portfolio Performance.

Uso:
  python scrape_fonte.py

Output:
  - fonte_dinamico.json (per Portfolio Performance)
  - fonte_dinamico.csv (alternativa CSV)
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import sys

def scrape_fonte_dinamico():
    """Scarica i valori NAV dal sito Fondo FONTE"""
    
    print("=" * 60)
    print("FONDO FONTE DINAMICO - Scraper automatico")
    print("=" * 60)
    
    url = "https://www.fondofonte.it/gestione-finanziaria/i-valori-quota-dei-comparti/comparto-dinamico/"
    print(f"\n📥 Download da: {url}")
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Errore durante il download: {e}")
        sys.exit(1)
    
    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.get_text()
    
    nav_data = []
    
    # Mappa mesi italiani -> numeri
    months_it = {
        "Gennaio": "01", "Febbraio": "02", "Marzo": "03", "Aprile": "04",
        "Maggio": "05", "Giugno": "06", "Luglio": "07", "Agosto": "08",
        "Settembre": "09", "Ottobre": "10", "Novembre": "11", "Dicembre": "12"
    }
    
    # Dividi il contenuto per anno usando il pattern [YYYY]
    year_blocks = re.split(r'\[(\d{4})\]', content)
    
    current_year = None
    for i, block in enumerate(year_blocks):
        # Identifica gli anni
        if re.match(r'^\d{4}$', block):
            current_year = block
            continue
        
        # Se abbiamo un anno, cerca mesi e valori nel blocco
        if current_year and i > 0:
            # Pattern: NomeMese seguito da numero con virgola
            patterns = re.findall(
                r'(Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre)\s+([\d,]+)',
                block
            )
            
            for month_name, nav_str in patterns:
                if month_name in months_it:
                    month_num = months_it[month_name]
                    try:
                        # Converti virgola in punto per il float
                        nav = float(nav_str.replace(",", "."))
                        date_str = f"{current_year}-{month_num}-01"
                        nav_data.append({
                            "date": date_str,
                            "value": nav
                        })
                    except ValueError:
                        print(f"⚠️  Valore non valido: {nav_str}")
                        continue
    
    if not nav_data:
        print("❌ ERRORE: Nessun dato estratto dalla pagina!")
        print("\nContenuto della pagina (primi 500 caratteri):")
        print(content[:500])
        sys.exit(1)
    
    # Ordina per data (dal più vecchio al più recente)
    nav_data = sorted(nav_data, key=lambda x: x["date"])
    
    # Crea struttura JSON per Portfolio Performance
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
    json_file = "fonte_dinamico.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Salva anche CSV come alternativa
    csv_file = "fonte_dinamico.csv"
    csv_content = "Date;Value;Currency\n"
    for entry in nav_data:
        csv_content += f"{entry['date']};{entry['value']:.4f};EUR\n"
    
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    # Statistiche
    print(f"\n✅ Scraping completato con successo!")
    print(f"\n📊 Statistiche:")
    print(f"   • Totale valori estratti: {len(nav_data)}")
    print(f"   • Periodo: {nav_data[0]['date']} → {nav_data[-1]['date']}")
    print(f"   • Primo valore: €{nav_data[0]['value']:.4f}")
    print(f"   • Ultimo valore: €{nav_data[-1]['value']:.4f}")
    
    # Calcola rendimento totale
    first_value = nav_data[0]['value']
    last_value = nav_data[-1]['value']
    total_return = ((last_value - first_value) / first_value) * 100
    print(f"   • Rendimento totale: {total_return:+.2f}%")
    
    print(f"\n📁 File generati:")
    print(f"   • {json_file} (per Portfolio Performance)")
    print(f"   • {csv_file} (formato CSV)")
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
