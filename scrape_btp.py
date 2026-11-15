"""
Scraper BTP Valore Mz30 (IT0005583486) - Borsa Italiana

1) STORICO: apre il grafico interattivo con Chrome headless e intercetta le
   chiamate di rete che caricano la serie (prezzo di riferimento).
2) OGGI: legge "Prezzo di riferimento" + "Data di riferimento" dalla scheda.
I dati vengono uniti al JSON già presente (nessuna perdita di storico).

Output: btp_valore_mz30.json / btp_valore_mz30.csv
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

ISIN = "IT0005583486"
NAME = "BTP Valore Sc Mz30 Eur"
SCHEDA_URL = f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/{ISIN}-MOTX.html?lang=it"
CHART_URLS = [
    f"https://grafici.borsaitaliana.it/interactive-chart/{ISIN}-MOTX?lang=it",
    f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/grafico.html?isin={ISIN}&mic=MOTX&lang=it",
]
OUT = "btp_valore_mz30"
ROME = ZoneInfo("Europe/Rome")
MIN_DATE = "2024-03-05"  # inizio negoziazione
COOKIE_TEXTS = ["Accettare tutto", "Accetta tutto", "Accetta tutti", "Accetto"]
RANGE_TEXTS = ["MAX", "Max", "Tutto", "Tutti", "5A", "5 anni", "5Y", "ALL"]
PREFERRED = ("endpx", "closepx", "close", "c", "last", "chiusura", "riferimento", "reference",
             "prezzo", "price", "value", "nav", "quota", "y", "v")


# ---------- utilità ----------
def norm_date(v):
    try:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if v > 1e11:
                d = datetime.fromtimestamp(v / 1000, tz=ROME)
            elif v > 1e9:
                d = datetime.fromtimestamp(v, tz=ROME)
            else:
                return None
            return d.strftime("%Y-%m-%d") if 2000 <= d.year <= 2100 else None
        if isinstance(v, str):
            v = v.strip()
            m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", v)
            if m:
                return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
            # formato compatto Borsa Italiana: 20261113 oppure 20261113-09:00:00
            m = re.match(r"^(\d{4})(\d{2})(\d{2})(?:-|T|\s|$)", v)
            if m and 2000 <= int(m.group(1)) <= 2100:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
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


def pick_key(cands):
    for p in PREFERRED:
        for k in cands:
            if str(k).lower() == p:
                return k
    return cands[0]


def series_from_list(lst):
    if len(lst) < 10:
        return None
    # [[t, v], ...] oppure OHLC [[t, o, h, l, c, (vol)], ...]
    if all(isinstance(e, (list, tuple)) and len(e) >= 2 for e in lst):
        pts = []
        for e in lst:
            d = norm_date(e[0])
            v = to_float(e[4]) if len(e) >= 5 else to_float(e[1])
            if d and v is not None:
                pts.append((d, v))
        return pts if len(pts) >= 0.9 * len(lst) else None
    # [{...}, ...]
    if all(isinstance(e, dict) for e in lst):
        keys = list(lst[0].keys())
        date_key = next((k for k in keys
                         if sum(1 for e in lst if norm_date(e.get(k))) >= 0.9 * len(lst)), None)
        if not date_key:
            return None
        cands = [k for k in keys if k != date_key and
                 sum(1 for e in lst if to_float(e.get(k)) is not None) >= 0.9 * len(lst)]
        if not cands:
            return None
        vk = pick_key(cands)
        print(f"   ↳ lista di oggetti: data='{date_key}', valore='{vk}', numeriche={cands}")
        return [(norm_date(e.get(date_key)), to_float(e.get(vk))) for e in lst
                if norm_date(e.get(date_key)) and to_float(e.get(vk)) is not None]
    return None


def find_series(obj, found):
    if isinstance(obj, list):
        s = series_from_list(obj)
        if s:
            found.append(s)
        for item in obj[:50]:
            find_series(item, found)
    elif isinstance(obj, dict):
        # formato a colonne: {"t": [...], "c": [...]}
        cols = {k: v for k, v in obj.items() if isinstance(v, list) and len(v) >= 10}
        dk = next((k for k, v in cols.items()
                   if sum(1 for x in v if norm_date(x)) >= 0.9 * len(v)), None)
        if dk:
            nums = [k for k, v in cols.items() if k != dk and len(v) == len(cols[dk])
                    and sum(1 for x in v if to_float(x) is not None) >= 0.9 * len(v)]
            if nums:
                vk = pick_key(nums)
                print(f"   ↳ formato a colonne: data='{dk}', valore='{vk}'")
                found.append([(norm_date(d), to_float(v)) for d, v in zip(cols[dk], cols[vk])
                              if norm_date(d) and to_float(v) is not None])
        for v in obj.values():
            find_series(v, found)


# ---------- browser ----------
def start_driver():
    opts = Options()
    for a in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
              "--disable-gpu", "--window-size=1920,1080"]:
        opts.add_argument(a)
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    for path in ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome", None]:
        try:
            if path:
                opts.binary_location = path
            d = webdriver.Chrome(options=opts)
            print(f"✅ Chrome avviato ({path or 'default'})")
            return d
        except Exception:
            continue
    print("❌ Impossibile avviare Chrome")
    sys.exit(1)


DEEP_CLICK_JS = """
const target = arguments[0].toUpperCase();
function search(root) {
  for (const el of root.querySelectorAll('*')) {
    if (el.shadowRoot) { const r = search(el.shadowRoot); if (r) return r; }
    if (el.children.length === 0 && (el.textContent || '').trim().toUpperCase() === target) return el;
  }
  return null;
}
const el = search(document);
if (!el) return false;
for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
  el.dispatchEvent(new MouseEvent(type, {bubbles: true, composed: true, cancelable: true}));
}
return true;
"""

DEEP_LABELS_JS = """
const out = new Set();
function walk(root) {
  for (const el of root.querySelectorAll('*')) {
    if (el.shadowRoot) walk(el.shadowRoot);
    if (el.children.length === 0) {
      const t = (el.textContent || '').trim();
      if (t && t.length <= 12) out.add(t);
    }
  }
}
walk(document);
return Array.from(out).slice(0, 80);
"""

PROBE_JS = r"""
const done = arguments[arguments.length - 1];
const srcs = Array.from(document.querySelectorAll('script[src]'))
  .map(s => s.src).filter(s => s.includes('/assets/js/'));
Promise.all(srcs.map(u => fetch(u).then(r => r.text()).catch(() => '')))
  .then(a => done(a.join('\n')));
"""


def deep_click(driver, text):
    """Click su elementi anche dentro gli shadow DOM (web components)."""
    try:
        return bool(driver.execute_script(DEEP_CLICK_JS, text))
    except Exception:
        return False


def probe_bundle(driver):
    """Cerca nel JS del grafico gli endpoint API (diagnostica)."""
    print("\n🔎 Analisi del bundle JS del grafico (ricerca endpoint)...")
    try:
        driver.set_script_timeout(30)
        js = driver.execute_async_script(PROBE_JS) or ""
    except Exception as e:
        print(f"⚠️  Analisi fallita: {e}")
        return
    print(f"   bundle scaricato: {len(js)} caratteri")
    for label, pattern, flags in [
        ("/api/", r".{0,70}/api/.{0,120}", 0),
        ("resolution", r".{0,100}resolution.{0,100}", re.I),
        ("history|daily|eod", r".{0,80}(?:history|historical|daily|eod).{0,100}", re.I),
    ]:
        seen = []
        for m in re.finditer(pattern, js, flags):
            s = m.group(0)
            if s not in seen:
                seen.append(s)
            if len(seen) >= 12:
                break
        print(f"   [{label}] {len(seen)} occorrenze")
        for s in seen:
            print(f"     · {s}")
    print()


def click_first(driver, texts):
    for t in texts:
        if deep_click(driver, t):
            print(f"🖱️  Click (shadow DOM) su '{t}'")
            return True
        els = driver.find_elements(
            By.XPATH,
            f"//*[not(*)][translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', "
            f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='{t.upper()}']")
        for el in els:
            try:
                if el.is_displayed():
                    driver.execute_script("arguments[0].click();", el)
                    print(f"🖱️  Click su '{t}'")
                    return True
            except Exception:
                continue
    return False


seen_ids = set()
all_urls = []


def dump_labels(driver):
    """Etichette brevi (anche dentro gli shadow DOM)."""
    try:
        return driver.execute_script(DEEP_LABELS_JS)
    except Exception:
        pass
    labels = set()
    for el in driver.find_elements(By.XPATH, "//button|//a|//li|//span|//label"):
        try:
            t = el.text.strip()
            if t and len(t) <= 12 and el.is_displayed():
                labels.add(t)
        except Exception:
            continue
    return sorted(labels)[:60]


def collect(driver):
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
            mime = p["response"].get("mimeType", "").lower()
            all_urls.append((p.get("type"), mime, p["response"].get("url", "")))
            if p.get("type") not in ("XHR", "Fetch", "Other") and "json" not in mime:
                continue
            if mime.startswith(("image/", "font/", "text/css", "text/html")):
                continue
            body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": rid})["body"]
            out.append((p["response"].get("url", ""), body))
        except Exception:
            continue
    return out


def parse_body(body):
    """JSON oppure JSONP."""
    try:
        return json.loads(body)
    except Exception:
        m = re.search(r"\((\{.*\}|\[.*\])\)\s*;?\s*$", body, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return None


def get_history():
    print("\n--- STORICO dal grafico interattivo ---")
    best = []
    for url in CHART_URLS:
        print(f"🌐 Apro: {url}")
        driver = start_driver()
        responses, page_text = [], ""
        try:
            driver.set_page_load_timeout(40)
            try:
                driver.execute_cdp_cmd("Network.enable", {})
            except Exception:
                pass
            driver.get(url)
            time.sleep(8)
            responses += collect(driver)
            if "grafici.borsaitaliana.it" in url:
                probe_bundle(driver)
            click_first(driver, COOKIE_TEXTS)
            time.sleep(2)
            responses += collect(driver)
            print("🔘 Etichette cliccabili:", dump_labels(driver))
            for t in ["MAX", "Max", "Tutto", "ALL", "5A", "5Y", "3A", "3Y", "1A", "1Y",
                      "YTD", "6M", "3M", "1M"]:
                if click_first(driver, [t]):
                    time.sleep(5)
                    responses += collect(driver)
            page_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception as e:
            print(f"⚠️  Errore browser: {e}")
        finally:
            try:
                driver.quit()
            except Exception:
                pass

        print(f"📡 Risposte intercettate: {len(responses)}")
        print("🧾 Tutte le richieste di rete (tipo | mime | url):")
        for typ, mime, u in all_urls:
            if typ not in ("Image", "Font", "Stylesheet", "Media"):
                print(f"   · {typ} | {mime} | {u[:140]}")
        for u, body in responses:
            print(f"   - {u[:120]} ({len(body)} byte)")
            data = parse_body(body)
            found = []
            if data is not None:
                find_series(data, found)
            if found:
                for s in found:
                    ndates = len({d for d, _ in s})
                    if ndates < 20:
                        print(f"   ⏭️  serie scartata: solo {ndates} date distinte (probabile intraday)")
                        continue
                    print(f"   ✅ serie candidata: {len(s)} punti, {ndates} date")
                    if len(s) > len(best):
                        best = s
            else:
                print(f"     (nessuna serie) anteprima: {body[:150]!r}")
        if best:
            return best
        print(f"📄 Testo pagina (primi 800 car.): {page_text[:800]}")
    return best


# ---------- prezzo di oggi ----------
def get_reference_price():
    print("\n--- PREZZO DI RIFERIMENTO dalla scheda ---")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
               "Accept-Language": "it-IT,it;q=0.9"}
    try:
        r = requests.get(SCHEDA_URL, headers=headers, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️  Download scheda fallito: {e}")
        return None
    text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
    m = re.search(r"Prezzo di riferimento\s+([\d.]+,\d+)\s+Data di riferimento\s+"
                  r"(\d{2})/(\d{2})/(\d{4})", text)
    if not m:
        print("⚠️  Prezzo di riferimento non trovato nella scheda")
        return None
    d, p = f"{m.group(4)}-{m.group(3)}-{m.group(2)}", to_float(m.group(1))
    print(f"✅ {d}: {p}")
    return d, p


def valid(d, v):
    return d >= MIN_DATE and 50 <= v <= 150


def main():
    print("=" * 60)
    print(f"{NAME} - Scraper")
    print("=" * 60)

    prices = {}
    if os.path.exists(f"{OUT}.json"):
        with open(f"{OUT}.json", encoding="utf-8") as f:
            for p in json.load(f).get("prices", []):
                prices[p["date"]] = p["value"]
        print(f"📂 Storico esistente: {len(prices)} punti")

    hist = get_history()
    for d, v in hist:
        if valid(d, v):
            prices[d] = v  # in caso di più punti per data resta l'ultimo

    today = get_reference_price()
    if today and valid(*today):
        prices[today[0]] = today[1]

    if not prices:
        print("❌ Nessun dato disponibile")
        sys.exit(1)

    series = [{"date": d, "value": prices[d]} for d in sorted(prices)]
    output = {
        "name": NAME, "isin": ISIN, "currency": "EUR",
        "source": SCHEDA_URL,
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

    print(f"\n📁 Salvati {len(series)} punti: {series[0]['date']} → {series[-1]['date']}")

    if not hist and len(series) < 30:
        print("\n❌ STORICO NON OTTENUTO: incolla questo log nella chat per sistemare il parser.")
        sys.exit(1)


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
