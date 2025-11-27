import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def scrape_fonte_dinamico():
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
    
    years = re.findall(r"#####\s*(\d{4})", content)
    year_idx = 0
    
    patterns = re.findall(r"([A-Za-zàèìòù]+)\s+([\d,]+)", content)
    
    for month_name, nav_str in patterns:
        if month_name in months_it and "," in nav_str and year_idx < len(years):
            month_num = months_it[month_name]
            nav = float(nav_str.replace(",", "."))
            year = years[year_idx]
            
            date_str = f"{year}-{month_num}-01"
            nav_data.append({"date": date_str, "nav": nav})
            
            if month_name == "Dicembre":
                year_idx += 1
    
    nav_data = sorted(nav_data, key=lambda x: x["date"])
    
    output = {
        "fund_name": "FONTE DINAMICO - Comparto Dinamico",
        "currency": "EUR",
        "last_update": datetime.now().isoformat(),
        "total_points": len(nav_data),
        "nav_history": nav_data
    }
    
    with open("fonte_dinamico.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    csv_content = "data;prezzo;valuta\n"
    for entry in nav_
        csv_content += f"{entry['date']};{entry['nav']:.3f};EUR\n"
    
    with open("fonte_dinamico_portfolio.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    print(f"Estratti {len(nav_data)} NAV da {nav_data[0]['date']} a {nav_data[-1]['date']}")
    print("Salvati: fonte_dinamico.json + fonte_dinamico_portfolio.csv")
    
    return output

if __name__ == "__main__":
    scrape_fonte_dinamico()
