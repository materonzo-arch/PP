import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def scrape_fonte_dinamico():
    print(">>> STO ESEGUENDO LO SCRAPER FONDO FONTE DINAMICO")
    url = "https://www.fondofonte.it/gestione-finanziaria/i-valori-quota-dei-comparti/comparto-dinamico/"
    print(f"Scarico da {url}")
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    content = soup.get_text()
    nav_data = []
    
    months_it = {
        "Gennaio": "01", "Febbraio": "02", "Marzo": "03", "Aprile": "04",
        "Maggio": "05", "Giugno": "06", "Luglio": "07", "Agosto": "08",
        "Settembre": "09", "Ottobre": "10", "Novembre": "11", "Dicembre": "12"
    }
    
    # Estrai blocchi anno per anno
    year_blocks = re.split(r'\[(\d{4})\]', content)
    
    current_year = None
    for i, block in enumerate(year_blocks):
        # Se è un anno (4 cifre)
        if re.match(r'^\d{4}$', block):
            current_year = block
            continue
        
        # Se abbiamo un anno corrente, cerca i mesi e i valori nel blocco successivo
        if current_year and i > 0:
            # Trova tutti i pattern Mese + Valore (con virgola come separatore decimale)
            patterns = re.findall(r'(Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre)\s+([\d,]+)', block)
            
            for month_name, nav_str in patterns:
                if month_name in months_it:
                    month_num = months_it[month_name]
                    try:
                        nav = float(nav_str.replace(",", "."))
                        date_str = f"{current_year}-{month_num}-01"
                        nav_data.append({"date": date_str, "nav": nav})
                    except ValueError:
                        print(f"Errore conversione valore: {nav_str}")
                        continue
    
    if not nav_data:
        print("ERRORE: Nessun dato NAV estratto!")
        print("Primi 1000 caratteri del contenuto:")
        print(content[:1000])
        raise ValueError("Nessun dato NAV trovato nella pagina")
    
    # Ordina per data
    nav_data = sorted(nav_data, key=lambda x: x["date"])
    
    output = {
        "fund_name": "FONTE DINAMICO - Comparto Dinamico",
        "currency": "EUR",
        "last_update": datetime.now().isoformat(),
        "total_points": len(nav_data),
        "nav_history": nav_data
    }
    
    # Salva JSON
    with open("fonte_dinamico.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Salva CSV per Portfolio Performance
    csv_content = "data;prezzo;valuta\n"
    for entry in nav_data:
        csv_content += f"{entry['date']};{entry['nav']:.3f};EUR\n"
    
    with open("fonte_dinamico_portfolio.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    print(f"\n✓ Estratti {len(nav_data)} NAV")
    print(f"  Periodo: {nav_data[0]['date']} → {nav_data[-1]['date']}")
    print(f"  Primo valore: {nav_data[0]['nav']:.3f} EUR")
    print(f"  Ultimo valore: {nav_data[-1]['nav']:.3f} EUR")
    print(f"\n✓ File salvati:")
    print(f"  - fonte_dinamico.json")
    print(f"  - fonte_dinamico_portfolio.csv")
    
    return output

if __name__ == "__main__":
    try:
        scrape_fonte_dinamico()
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        raise
