"""
Scraper COREPENSION AZIONARIO PLUS (Amundi Corepension)
Output: corepension_azionario_plus.json / .csv

Strategie (in ordine):
  1. Intercetta le risposte JSON di rete caricate dalla pagina
  2. Parsing del testo visibile (data + valore quota)
Stampa molta diagnostica per facilitare eventuali correzioni.
"""

import json
import re
import sys
import time
from datetime import datetime, timezone

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

URL = "https://www.corepension.it/product/view/QS0000061309"
OUT = "corepension_azionario_plus"
FUND_NAME = "COREPENSION Azionario Plus"


# ---------- utilità ----------
def norm_date(v):
    """Ritorna YYYY-MM-DD oppure None."""
    try:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if v > 1e11:
                d = datetime.fromtimestamp(v / 1000, tz=timezone.utc)
            elif v > 1e9:
                d = datetime.fromtimestamp(v, tz=timezone.utc)
            else:
                return None
            return d.strftime("%Y-%m-%d") if 1990 <= d.year <= 2100 else None
        if isinstance(v, str):
            v = v.strip()
            m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", v)
            if m:
                return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    except Exception:
        pass
    return None


def to_float(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.replace("€", "").replace("\u00a0", "").replace(" ", "").strip()
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None


PREFERRED = ("nav", "value", "price", "quota", "close", "y", "v")


def series_from_list(lst):
    """Prova a interpretare una lista come serie storica."""
    if len(lst) < 10:
        return None
    # caso [[data, valore], ...]
    if all(isinstance(e, (list, tuple)) and len(e) >= 2 for e in lst):
        pts = [(norm_date(e[0]), to_float(e[1])) for e in lst]
        pts = [(d, v) for d, v in pts if d and v is not None]
        return pts if len(pts) >= 0.9 * len(lst) else None
    # caso [{...}, ...]
    if all(isinstance(e, dict) for e in lst):
        keys = list(lst[0].keys())
        date_key = None
        for k in keys:
            ok = sum(1 for e in lst if norm_date(e.get(k)))
            if ok >= 0.9 * len(lst):
                date_key = k
                break
        if not date_key:
            return None
        cands = []
        for k in keys:
            if k == date_key:
                continue
            ok = sum(1 for e in lst if to_float(e.get(k)) is not None)
            if ok >= 0.9 * len(lst):
                cands.append(k)
        if not cands:
            return None
        val_key = next((k for k in cands if k.lower() in PREFERRED), cands[0])
        pts = []
        for e in lst:
            d, v = norm_date(e.get(date_key)), to_float(e.get(val_key))
            if d and v is not None:
                pts.append((d, v))
        print(f"   ↳ serie trovata: chiave data='{date_key}', valore='{val_key}', "
              f"altre numeriche={[c for c in cands if c != val_key]}")
        return pts
    return None


def find_series(obj, found):
    if isinstance(obj, list):
        s = series_from_list(obj)
        if s:
            found.append(s)
        for item in obj[:50]:
            find_series(item, found)
    elif isinstance(obj, dict):
        for v in obj.values():
            find_series(v, found)


# ---------- browser ----------
def start_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    for path in ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome", None]:
        try:
            if path:
                opts.binary_location = path
            driver = webdriver.Chrome(options=opts)
            print(f"✅ Chrome avviato ({path or 'default'})")
            return driver
        except Exception:
            continue
    print("❌ Impossibile avviare Chrome")
    sys.exit(1)


def click_by_text(driver, texts, max_clicks=4):
    clicked = 0
    for _ in range(max_clicks):
        did = False
        for t in texts:
            els = driver.find_elements(
                By.XPATH,
                f"//*[self::button or self::a or self::span or self::li or self::div]"
                f"[normalize-space(text())='{t}']")
            for el in els:
                try:
                    if el.is_displayed():
                        driver.execute_script("arguments[0].click();", el)
                        print(f"🖱️  Click su '{t}'")
                        clicked += 1
                        did = True
                        time.sleep(1.5)
                        break
                except Exception:
                    continue
            if did:
                break
        if not did:
            break
    return clicked


seen_ids = set()


def collect_json(driver):
    """Raccoglie le risposte JSON dai log di rete."""
    out = []
    try:
        logs = driver.get_log("performance")
    except Exception:
        return out
    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
            if msg.get("method") != "Network.responseReceived":
                continue
            p = msg["params"]
            rid = p["requestId"]
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            mime = p["response"].get("mimeType", "")
            url = p["response"].get("url", "")
            if "json" not in mime.lower():
                continue
            body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": rid})["body"]
            out.append((url, body))
        except Exception:
            continue
    return out


def parse_text(page_text):
    pts = []
    for d, v in re.findall(r"(\d{1,2}/\d{1,2}/\d{4})\s*€?\s*(\d{1,3}(?:\.\d{3})*,\d{2,4})", page_text):
        nd, nv = norm_date(d), to_float(v)
        if nd and nv is not None:
            pts.append((nd, nv))
    return pts


def main():
    print("=" * 60)
    print(f"{FUND_NAME} - Scraper")
    print("=" * 60)

    driver = start_driver()
    all_json = []
    page_text = ""
    try:
        driver.set_page_load_timeout(40)
        try:
            driver.execute_cdp_cmd("Network.enable", {})
        except Exception:
            pass
        driver.get(URL)
        time.sleep(5)

        # banner profilo + cookie
        click_by_text(driver, ["Accetto e continua"])
        time.sleep(5)
        all_json += collect_json(driver)

        # eventuali tab con storico quote
        click_by_text(driver, ["Storico", "Quote storiche", "Valori quota", "Performance", "Quote"], max_clicks=2)
        time.sleep(4)
        all_json += collect_json(driver)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        all_json += collect_json(driver)

        page_text = driver.find_element(By.TAG_NAME, "body").text
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print(f"\n📄 Testo pagina: {len(page_text)} caratteri")
    print(f"🌐 Risposte JSON intercettate: {len(all_json)}")
    for url, body in all_json:
        print(f"   - {url[:110]} ({len(body)} byte)")

    # Strategia 1: JSON di rete
    candidates = []
    for url, body in all_json:
        try:
            data = json.loads(body)
        except Exception:
            continue
        found = []
        find_series(data, found)
        for s in found:
            print(f"✅ Serie candidata da {url[:80]}: {len(s)} punti")
            candidates.append(s)

    nav_data = max(candidates, key=len) if candidates else []

    # Strategia 2: testo
    if not nav_data:
        print("ℹ️  Nessuna serie nel JSON, provo il parsing del testo...")
        nav_data = parse_text(page_text)

    if not nav_data:
        print("\n❌ Nessun dato estratto.")
        print("\n📄 Testo visibile (primi 4000 caratteri):")
        print(page_text[:4000])
        print("\n👉 Incolla questo log nella chat: ti sistemo il parser.")
        sys.exit(1)

    unique = {}
    for d, v in nav_data:
        unique[d] = v
    series = [{"date": d, "value": unique[d]} for d in sorted(unique)]

    output = {
        "name": FUND_NAME,
        "isin": "N/A",
        "currency": "EUR",
        "source": URL,
        "last_updated": datetime.now().isoformat(),
        "total_entries": len(series),
        "prices": series,
    }
    with open(f"{OUT}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    with open(f"{OUT}.csv", "w", encoding="utf-8") as f:
        f.write("Date;Value;Currency\n")
        for e in series:
            f.write(f"{e['date']};{e['value']:.4f};EUR\n")

    print(f"\n✅ Estratti {len(series)} valori: {series[0]['date']} → {series[-1]['date']}")
    print(f"   Primo: {series[0]['value']:.4f}  Ultimo: {series[-1]['value']:.4f}")
    print(f"📁 Creati: {OUT}.json, {OUT}.csv")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ ERRORE: {e}")
        sys.exit(1)
