# 📈 PP – Feed prezzi fondi pensione per Portfolio Performance

Questo repository scarica automaticamente ogni giorno i valori quota di alcuni fondi pensione italiani e li pubblica in formato **JSON** e **CSV**, in modo da poterli usare come fonte di quotazioni in [Portfolio Performance](https://www.portfolio-performance.info/).

I fondi pensione non hanno un ISIN né compaiono sui provider di quotazioni classici, quindi i dati vengono letti direttamente dai siti ufficiali dei fondi.

---

## 📦 Fondi supportati

| Fondo | Comparto | Fonte | File JSON | Aggiornamento (UTC) |
|---|---|---|---|---|
| Fon.Te. | Dinamico | [fondofonte.it](https://www.fondofonte.it/gestione-finanziaria/i-valori-quota-dei-comparti/comparto-dinamico/) | `fonte_dinamico.json` | ogni giorno ore 8:00 |
| Fonchim | Crescita | [fonchim.it](https://www.fonchim.it/site/funziona-fondo/rendimenti-quote) | `fonchim_crescita.json` | ogni giorno ore 9:00 |
| Core Pension (Amundi) | Azionario Plus | [corepension.it](https://www.corepension.it/product/view/QS0000061309) | `corepension_azionario_plus.json` | ogni giorno ore 10:00 |

> ℹ️ Gli orari sono in UTC: in Italia corrispondono a +1 ora (inverno) o +2 ore (estate).

### Frequenza dei dati

I fondi non pubblicano un valore quota al giorno, quindi aggiornare ogni giorno serve solo a intercettare il nuovo valore appena esce.

- **Fon.Te.**: un valore al mese (nel JSON la data è impostata al giorno `01` del mese di riferimento).
- **Fonchim**: due valori al mese (circa il 15 e l'ultimo giorno del mese).
- **Core Pension**: due valori al mese (il 15 e l'ultimo giorno lavorativo).

---

## 🔗 URL per Portfolio Performance

```
https://raw.githubusercontent.com/materonzo-arch/PP/main/fonte_dinamico.json
https://raw.githubusercontent.com/materonzo-arch/PP/main/fonchim_crescita.json
https://raw.githubusercontent.com/materonzo-arch/PP/main/corepension_azionario_plus.json
```

Versioni CSV (alternativa):

```
https://raw.githubusercontent.com/materonzo-arch/PP/main/fonte_dinamico.csv
https://raw.githubusercontent.com/materonzo-arch/PP/main/fonchim_crescita.csv
https://raw.githubusercontent.com/materonzo-arch/PP/main/corepension_azionario_plus.csv
```

---

## 📊 Configurazione in Portfolio Performance

1. Apri (o crea) il titolo, ad esempio *Fon.Te. Dinamico*.
2. Vai nella scheda **Quotazioni storiche** → **Provider**.
3. Scegli **JSON**.
4. Compila i campi:

| Campo | Valore |
|---|---|
| URL feed | l'URL del JSON del fondo (vedi sopra) |
| Path to Date | `$.prices[*].date` |
| Path to Close | `$.prices[*].value` |
| Formato data | `yyyy-MM-dd` |

5. Premi **Test**, poi salva e aggiorna le quotazioni.

### Struttura del JSON

```json
{
  "name": "FONTE Dinamico",
  "currency": "EUR",
  "source": "https://...",
  "last_updated": "2026-11-14T08:00:00",
  "total_entries": 210,
  "prices": [
    { "date": "2008-05-01", "value": 10.0 },
    { "date": "2008-06-01", "value": 10.1 }
  ]
}
```

---

## 🗂️ Struttura del repository

```
PP/
├── .github/
│   └── workflows/
│       ├── update-fonte.yml
│       ├── update-fonchim.yml
│       └── update-corepension.yml
├── scrape_fonte.py
├── scrape_fonchim.py
├── scrape_corepension.py
├── fonte_dinamico.json / .csv                 (generato)
├── fonchim_crescita.json / .csv               (generato)
├── corepension_azionario_plus.json / .csv     (generato)
└── README.md
```

---

## ⚙️ Come funziona

- Ogni fondo ha il suo **script Python** (Selenium + Chromium in modalità headless), perché i siti caricano i dati con JavaScript.
- Ogni fondo ha il suo **workflow GitHub Actions**, che parte:
  - ogni giorno all'orario indicato in tabella;
  - manualmente dalla tab **Actions** → *Run workflow*;
  - quando viene modificato lo script o il workflow di quel fondo.
- Se i dati cambiano, il workflow fa **commit e push** dei file aggiornati (con `git pull --rebase` prima del push, per evitare conflitti tra workflow).
- Quando i file JSON/CSV cambiano nel repo, Portfolio Performance li legge dall'URL *raw*.

---

## 🚀 Setup iniziale (se riparti da zero)

1. Crea un repository (anche pubblico: gli URL *raw* funzionano subito senza token).
2. Aggiungi gli script `.py` e i workflow in `.github/workflows/`.
3. Abilita i permessi di scrittura:
   **Settings → Actions → General → Workflow permissions → Read and write permissions → Save**.
4. Vai in **Actions**, scegli un workflow e premi **Run workflow**.
5. Verifica che il file compaia nel repo. Se non c'è, scarica l'artifact dall'esecuzione e caricalo a mano una prima volta.

---

## 🛠️ Risoluzione dei problemi

| Problema | Cosa fare |
|---|---|
| `404 Not found` sull'URL raw | Il file non è ancora nel repo: controlla che il workflow sia verde e che abbia fatto il commit. |
| Il workflow è verde ma il file non si aggiorna | Probabilmente non ci sono nuovi dati sul sito: è normale. |
| `failed to push some refs` | Due workflow hanno fatto push insieme: assicurati che ci sia `git pull --rebase origin main` prima di `git push`. |
| `Nessun dato estratto` | Il sito ha cambiato struttura: apri il log del workflow e adatta il parser nello script. |
| Workflow che parte per file non correlati | Controlla il blocco `paths:` nel trigger `push` del workflow. |
| Core Pension non estrae dati | Il sito è il più complesso dei tre: copia il log del run e adatta lo script alla chiamata di rete che contiene le quote. |

---

## ⚠️ Note

- I dati appartengono ai rispettivi fondi pensione e vengono riportati a solo scopo di uso personale. Verifica sempre i valori sui siti ufficiali prima di prendere decisioni.
- Questo progetto non è affiliato né approvato da Fon.Te., Fonchim, Amundi o Portfolio Performance.
- Se i siti cambiano struttura, gli script potrebbero smettere di funzionare e vanno aggiornati.

---

## 📝 Changelog

<!-- Aggiungi qui le tue modifiche -->
- **2026-11**: aggiunto Core Pension Azionario Plus
- **2026-11**: aggiunto Fonchim Crescita
- **2026-11**: primo rilascio con Fon.Te. Dinamico
