# 📈 Fondo FONTE Dinamico - Data Feed per Portfolio Performance

Questo repository aggiorna automaticamente i valori NAV del **Fondo FONTE Dinamico** per l'utilizzo in Portfolio Performance.

## 🔗 Link diretto al JSON

Usa questo URL in Portfolio Performance come feed JSON:

```
https://raw.githubusercontent.com/TUO-USERNAME/TUO-REPO/main/fonte_dinamico.json
```

Sostituisci `TUO-USERNAME` e `TUO-REPO` con i tuoi dati GitHub.

---

## 🚀 Setup Iniziale

### 1. Crea il repository su GitHub

1. Vai su GitHub e crea un nuovo repository (es. `fondo-fonte-data`)
2. Può essere pubblico o privato
3. Non inizializzare con README (lo faremo noi)

### 2. Clona e configura localmente

```bash
# Clona il repository
git clone https://github.com/TUO-USERNAME/fondo-fonte-data.git
cd fondo-fonte-data

# Crea la struttura delle cartelle
mkdir -p .github/workflows
```

### 3. Crea i file necessari

Crea questi file nella root del repository:

#### `scrape_fonte.py`
Lo script Python principale (vedi artifact separato)

#### `requirements.txt`
```txt
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
```

#### `.github/workflows/update-fonte.yml`
Il workflow di GitHub Actions (vedi artifact separato)

#### `.gitignore`
```txt
__pycache__/
*.pyc
.venv/
venv/
.env
*.log
```

### 4. Commit e push iniziale

```bash
git add .
git commit -m "🎉 Setup iniziale - Fondo FONTE scraper"
git push origin main
```

---

## ⚙️ Configurazione GitHub Actions

### Abilita i permessi di scrittura

1. Vai su **Settings** del tuo repository
2. Vai su **Actions** → **General**
3. Scorri fino a **Workflow permissions**
4. Seleziona **"Read and write permissions"**
5. Salva

### Verifica il workflow

1. Vai alla tab **Actions** del repository
2. Vedrai il workflow "Update Fondo FONTE Data"
3. Clicca su **Run workflow** per eseguirlo manualmente

---

## 📊 Come usare in Portfolio Performance

### Metodo 1: Feed JSON (Consigliato)

1. Apri Portfolio Performance
2. Vai su un titolo o creane uno nuovo
3. In **"Quotazioni storiche"** → **"Provider"**
4. Seleziona **"JSON"**
5. Inserisci l'URL:
   ```
   https://raw.githubusercontent.com/TUO-USERNAME/TUO-REPO/main/fonte_dinamico.json
   ```
6. Configura:
   - **Path to Date**: `$.prices[*].date`
   - **Path to Quote**: `$.prices[*].value`
   - **Date Format**: `yyyy-MM-dd`

### Metodo 2: Import CSV

1. Scarica `fonte_dinamico.csv` dal repository
2. In Portfolio Performance: **File** → **Import** → **CSV**
3. Configura le colonne:
   - Colonna 1: Data (formato: yyyy-MM-dd)
   - Colonna 2: Valore
   - Colonna 3: Valuta (EUR)

---

## 🔄 Automazione

Il workflow si esegue automaticamente:

- ⏰ **Ogni giorno alle 8:00 UTC** (9:00 CET)
- 🔘 **Manualmente** dal tab Actions
- 📝 **Ad ogni push** su main (per test)

### Modificare la frequenza

Modifica il cron in `.github/workflows/update-fonte.yml`:

```yaml
schedule:
  - cron: '0 8 * * *'  # Ogni giorno alle 8 UTC
  # - cron: '0 */6 * * *'  # Ogni 6 ore
  # - cron: '0 8 * * 1'  # Ogni lunedì alle 8 UTC
```

---

## 🧪 Test Locale

Per testare lo script localmente:

```bash
# Crea ambiente virtuale
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt

# Esegui lo scraper
python scrape_fonte.py
```

Se funziona, vedrai:
```
✅ Scraping completato con successo!

📊 Statistiche:
   • Totale valori estratti: XXX
   • Periodo: 2008-05-01 → 2025-XX-01
   ...
```

---

## 📁 Struttura del Repository

```
fondo-fonte-data/
├── .github/
│   └── workflows/
│       └── update-fonte.yml    # GitHub Actions workflow
├── scrape_fonte.py             # Script principale
├── requirements.txt            # Dipendenze Python
├── fonte_dinamico.json         # Output JSON (auto-generato)
├── fonte_dinamico.csv          # Output CSV (auto-generato)
├── .gitignore
└── README.md
```

---

## 🐛 Troubleshooting

### Il workflow fallisce

1. Controlla i log in **Actions** → seleziona il workflow fallito
2. Verifica che i permessi di scrittura siano abilitati
3. Controlla che `requirements.txt` sia presente

### I dati non si aggiornano

1. Verifica che il sito fonte sia raggiungibile
2. La struttura HTML potrebbe essere cambiata
3. Controlla i log del workflow per errori specifici

### Portfolio Performance non carica il JSON

1. Verifica che l'URL sia corretto (deve puntare a `raw.githubusercontent.com`)
2. Se il repo è privato, devi generare un token di accesso
3. Controlla la sintassi dei path JSON

---

## 📞 Supporto

- 🐛 **Bug**: Apri una Issue su GitHub
- 💡 **Suggerimenti**: Pull Request benvenute!
- 📖 **Documentazione Portfolio Performance**: [docs.portfolio-performance.info](https://docs.portfolio-performance.info)

---

## 📄 Licenza

Questo progetto è rilasciato sotto licenza MIT. I dati provengono da [fondofonte.it](https://www.fondofonte.it) e sono di proprietà del Fondo FONTE.

---

**Ultimo aggiornamento**: 2025-11-28
