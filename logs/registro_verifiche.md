# Registro delle verifiche

Registro cronologico di ogni controllo eseguito nella ricerca. Ogni voce indica oggetto, procedura, risultato ed evidenza. I file di evidenza sono in `logs/<fase>/` (formato `.txt` o `.md`: il `.gitignore` esclude `*.log`).

**Classificazione** (la stessa di `reports/00_diagnostica_iniziale.md`):
**[VERIFICATO]** controllato con procedura riproducibile · **[RIPORTATO]** affermato da documenti o codice originali, non verificato · **[STIMA]** valore approssimato · **[IPOTESI]** interpretazione da testare · **[DA CONFERMARE]** serve una fonte o verifica non ancora disponibile.

Orari in UTC. Esecutore: Claude (assistente di ricerca) per GRMS Partners. Repository `grmspartners/januarystrat`, branch `claude/peaceful-cray-bkvt73`.

---

## Fase 0 — Diagnosi in sola lettura (30-10-2026, prima delle 17:55)

Nessun file del repository modificato o creato, nessun dato scaricato, nessun backtest. Gli unici file prodotti erano fuori dal repository (scratchpad della sessione).

| ID | Oggetto | Procedura | Risultato | Stato |
|---|---|---|---|---|
| V-001 | Stato Git e struttura | `git status`, `git log --all`, `git ls-files`, `du` | Un commit `20b2ef1`, working tree pulito; 166 file tracciati (6 in radice, 160 in `source_original/`); `source_original/` 204 MB, pacchetto Git 195 MB; nessun test, nessun file delle dipendenze | VERIFICATO |
| V-002 | Copie in radice | `sha256sum` del `.xlsx` e del `.docx` in radice e in `source_original/` | Identici: `1a3bb4c64e55…` (xlsx), `e7d3c486a48e…` (docx) | VERIFICATO |
| V-003 | Dataset congelato | `cat jb_prices.parquet.part0* \| sha256sum`, confronto con `data/raw/MANIFEST.json` | `c82175764526…`, 166.227.925 byte = manifesto; membership `a8f3ebcedffb…` e renames `e571766f6f36…` = manifesto; le due copie della membership sono identiche | VERIFICATO |
| V-004 | Batch Yahoo | Lettura dell'intestazione e delle righe di `GRMS_YAHOO_batch1.ndjson.gz` | 227 simboli; `fetched` 2026-10-12T12:17:13.482Z; **81** simboli non trovati (`len(header["fail"])`; vedi C-001); `^SP500TR`, `^GSPC` 1988-01-04 → 2026-10-09; SPY 136 dividendi; SNDK da 2025-02-13; MRNA da 2018-12-07; nessuna impronta nel manifesto | VERIFICATO |
| V-005 | FRED | Chiavi di `GRMS_FRED_v1.json` | 12 serie (DTB3, DTB6, DTB1YR, DGS1, DGS2, DEXUSEU, VIXCLS, FEDFUNDS, CPIAUCSL, EXGEUS, EXITUS, AAA); nessuna impronta né data di download | VERIFICATO |
| V-006 | Ambiente di sistema | `importlib` dei pacchetti, `which`, stato HTTP di PyPI e GitHub, `nproc`, `free`, `df` | Python 3.13.17, pandas 3.0.5, numpy 2.5.3, openpyxl 3.1.5, PyYAML, python-docx presenti; pyarrow, scipy, matplotlib, statsmodels, pytest mancanti; Node 22 + `docx`, LibreOffice presenti; PyPI 200, GitHub 403; 4 CPU, 15 GB RAM, 30 GB liberi | VERIFICATO |
| V-007 | Dove scrive il codice originale | `grep` di `to_csv`, `to_parquet`, `savez`, `save`, `write_*`, `mkdir` in `code/*.py`; lettura di `config.py` | Tutti gli output sono relativi a `config.ROOT = parents[1]`: eseguito sul posto, scrive in `source_original/data/raw`, `data/processed`, `out/`; `make_report.py` crea `out/charts` all'import | VERIFICATO |
| V-008 | Regole implementate | Lettura integrale di `annual_study.py`, `signals.py`, `panel.py`, `data_layer.py`, `patches.py`, `benchmarks.py`, `leaps.py`, `config.py`, `fetch_data.py`, `run_all.py`, `build_report_annuale.py` | Regole come in `reports/00_diagnostica_iniziale.md` §4; calo massimo solo su valori di fine anno; AMC solo 0,5%; analisi in USD; nessuna struttura societaria; docstring di `annual_study.py` incoerente con il codice sull'ingresso (chiusura contro apertura) | VERIFICATO (lettura del codice) |
| V-009 | Coerenza dei CAGR 1997-2025 | Pivot di `AN_sintesi.csv`; confronto con la nota `.md` della radice, il report `.md` e la tabella 0 del `.docx` (python-docx) | Tutti i 7×3 valori coincidono | VERIFICATO |
| V-010 | Ricalcolo aritmetico dai rendimenti annui salvati | Prodotto di `1 + rendimento` 1997-2025 da `AN_rendimenti_annui.csv` | CAGR lordi 9,94 / 17,75 / 30,34 / 19,40 / 19,06%; solo vincitore con e senza stop differiscono solo nel 2000, 2002, 2008, 2011; rapporto cumulato 19,03, cioè 10,69 punti annui | VERIFICATO (sui risultati salvati, non è una riproduzione) |
| V-011 | Posizioni e stop | Lettura di `AN_top3_anno.csv` | 87 posizioni 1997-2025 + 3 nel 2026; 22 stop (posizione 1: 4; 2: 9; 3: 9), tutti nel 1997-2025; 11 utili, 11 dannosi; 5 in apertura sotto lo stop; 3 classifiche parziali (CARR, CEG, SNDK); 9 serie sintetiche (vincitori 2001, 2003, 2004) | VERIFICATO |
| V-012 | Workbook annuale | openpyxl, con e senza `data_only` | 11 fogli, 1.257 formule, tutte con valore calcolato; nessun nome definito; benchmark, LEAPS, stop e nettista sono valori fissi | VERIFICATO |
| V-013 | Report Word | python-docx | 227 paragrafi, 17 tabelle, 4 immagini; titoli identici al report `.md` | VERIFICATO |
| V-014 | Copertura dei dati | Lettura di `results/copertura_dati.csv` | 1996: 49,1% dei membri con prezzi; 2005: 75,2%; 2010: 95,4% (prodotto dal codice originale, non ricalcolato) | RIPORTATO |
| V-015 | Riparazioni storiche | Foglio `Riparazioni_dati` di `GRMS_JanuaryBuy_Risultati.xlsx`, incrociato con `AN_top3_anno.csv` | 30 celle su 24 titoli; nessuna negli anni di classifica o detenzione delle posizioni top-3 | VERIFICATO |
| V-016 | Classifica 2026 e calendario | `results/FD_classifica_2026YTD.csv`; giorni della settimana con Python | MRNA +663% (194 sedute), SNDK +566% al 9-10-2026; 31-12-2026 giovedì, 1-1-2027 venerdì, 4-1-2027 lunedì. Valori prodotti dal codice originale; calendario ufficiale NYSE 2027 da confermare | RIPORTATO / DA CONFERMARE |
| V-017 | Impronta di `source_original/` | `find source_original -type f \| sort \| xargs sha256sum` (scratchpad), ricontrollata a fine fase | 160 file; nessuna variazione durante la Fase 0; file scrivibili sul file system | VERIFICATO |

---

## Fase 1.0 — Preparazione (30-10-2026), autorizzata dal committente

Condizioni: cartelle e protezione di `source_original/`, ambiente virtuale con versioni fissate e solo pacchetti per l'audit, copia di lavoro esclusa da Git, nessun nuovo dataset, nessuna modifica al codice originale, solo il branch attuale, nessun merge su `master`, nessuna eliminazione di dati.

| ID | Ora | Oggetto | Procedura | Risultato | Evidenza | Stato |
|---|---|---|---|---|---|---|
| V-101 | 17:55 | Controllo preliminare | Branch, `git status`, `git diff --quiet 20b2ef1 -- source_original`, confronto con l'impronta di V-017 | Branch corretto, nessuna modifica, `source_original/` identico al commit e all'impronta | — | VERIFICATO |
| V-102 | 17:56 | Compatibilità con Python 3.13 | Metadati PyPI (`/pypi/<pkg>/<ver>/json`): data di pubblicazione, `requires_python`, wheel cp313 per Linux x86_64 e Windows amd64 | Tutte le versioni scelte hanno wheel cp313 per entrambe le piattaforme; criterio: ultima versione pubblicata entro il 12-10-2026 | `fase_1_0/compatibilita_py313.txt` | VERIFICATO |
| V-103 | 17:57 | Ambiente virtuale | `python3 -m venv .venv`; `pip install` di 8 pacchetti diretti fissati; `pip check`; `pip freeze`; `pip install --dry-run -r requirements.txt` | Python 3.13.17, pip 26.2.2; 8 diretti + 16 transitivi; nessun conflitto; `requirements.txt` coincide con `pip freeze`; non installati statsmodels e PyYAML (non servono alla catena annuale) | `requirements.txt`, `fase_1_0/pip_install_artifacts.txt` | VERIFICATO |
| V-104 | 17:58 | Manifesto SHA-256 | Verifica di V-101 ripetuta, poi `python3 -m research.integrity generate`; tre controlli incrociati | 160 file, 212.809.099 byte; identico all'impronta di V-017 (`sha256sum`, indipendente); `sha256sum -c` tutto OK; impronta del manifesto `0d709dfbce3a…` | `tests/fixtures/source_original.sha256`, `tests/fixtures/source_original_baseline.json` | VERIFICATO |
| V-105 | 17:59, 18:05 | Test automatici | `.venv/bin/python -m pytest -v` | 11 test superati: 4 sul manifesto e su file modificati, eliminati, aggiunti; 1 di ancoraggio ai blob Git del commit `20b2ef1`; 6 sul rilevatore (albero temporaneo: modifica, eliminazione, aggiunta di file ignorati da Git, round-trip del manifesto, codici di uscita) | `fase_1_0/pytest_fase_1_0.txt` | VERIFICATO |
| V-106 | 18:06 | Hook pre-commit | `.githooks/pre-commit`, attivato con `git config core.hooksPath .githooks` (configurazione locale del clone); collaudo in un clone usa e getta | Commit legittimo accettato; bloccati: modifica in stage, modifica non in stage, file aggiunto ignorato da Git; accettato dopo il ripristino; funziona con il `python3` di sistema | `fase_1_0/hook_precommit_test.txt` | VERIFICATO |
| V-107 | 18:00 | Copia di lavoro | `python -m research.replica_originale prepare` | `work/replica_originale/` identica al manifesto (160 file); `config.ROOT` della copia punta alla copia; `source_original/` intatto prima e dopo | `fase_1_0/replica_prepare.txt` | VERIFICATO |
| V-108 | 18:00–18:02 | Ricostruzione della pipeline dei dati, offline | `python -m research.replica_originale run-data`: `fetch_data.py`, `parse_yahoo.py`, `data_layer.py` nella copia, con proxy HTTP(S) verso una porta chiusa | Tutti con exit 0, senza avvisi. `fetch_data`: 3 file "= frozen copy" (nessun download). `parse_yahoo`: 1.365.261 righe, 227 simboli, 81 non trovati. `data_layer`: 9.766 date, 947 titoli, 11.231 celle riempite col valore precedente, Nasdaq-100 40 intervalli senza titolo su 324. `source_original/` intatto prima e dopo | `fase_1_0/replica_run_data.txt`, `replica_fetch_data.txt`, `replica_parse_yahoo.txt`, `replica_data_layer.txt` | VERIFICATO |
| V-109 | 18:02 | Controllo del pannello ricostruito (nessun backtest) | `python -m research.replica_originale check`; più la fonte delle righe SNDK (lettura del parquet con filtro) | Impronte del parquet ricomposto = manifesto. `jb_prices`: 6.163.332 righe, 1.022 ticker, 1970-01-02 → 2026-10-09, righe per fonte (Yahoo 4.982.664, Tiingo 841.674, WIKI 311.933, Kaggle 27.013, patch 48). SNDK 2025-02-13 → 2026-10-09 (416 righe, fonte Yahoo); SNDK-201605 1995-11-08 → 2016-05-11; MRNA da 2018-12-07. Pannello 1988-01-04 → 2026-10-09; 1.259 intervalli di composizione; 503 membri al 9-10-2026. **Riparazioni: 30/30 coincidono con il registro storico** (scarto massimo 4,4e-16). 9 serie sintetiche aggiunte; ultimo giorno 2026-10-09 = `AN_parametri.json` | `fase_1_0/replica_check.txt` | VERIFICATO |
| V-110 | 18:03 | Dipendenze della catena annuale | Import di 17 moduli nella copia (nessuna esecuzione) | Tutti importati dalla copia; `config.OUT` = `work/replica_originale/out` | `fase_1_0/replica_import_check.txt` | VERIFICATO |
| V-111 | 18:03 | Prova del rilevatore sulla copia reale | `python3 -m research.integrity verify --root work/replica_originale` | Exit 1, 25 file AGGIUNTI (output della pipeline, `jb_prices.parquet`, `__pycache__`), 0 modificati, 0 mancanti: il codice copiato non è stato alterato | `fase_1_0/integrity_demo_copia.txt` | VERIFICATO |
| V-112 | prima del commit | Integrità finale | `python3 -m research.integrity verify`; nessun `__pycache__` in `source_original/` | Identico al manifesto | — | VERIFICATO |

### Correzioni

- **C-001** (V-004). Nella prima versione del rapporto diagnostico, consegnata in chat, i simboli non trovati del batch Yahoo erano indicati come 82: era un conteggio a vista, non calcolato. Il valore corretto è **81** (`len(header["fail"])`, confermato da `parse_yahoo.py`). Corretto in `reports/00_diagnostica_iniziale.md`.

### Note di procedura

- **P-001** (V-103). Al primo tentativo il pip del venv è stato portato per errore da 26.2.2 (incluso con Python) a 26.0.1. Il venv è stato cancellato e ricreato da zero senza toccare pip prima di installare i pacchetti. Nessun effetto sui risultati.
- **P-002** (V-104). Nel file `source_original_baseline.json` l'ora di generazione era stata scritta a mano in modo errato (18:05); prima del commit è stata sostituita con l'ora reale del file del manifesto (17:58:36).
- **P-003** (V-111). Il rilevatore controlla i file, non le cartelle: una cartella vuota aggiunta (per esempio `out/charts`, creata da `make_report.py` all'import) non viene segnalata. Una cartella non vuota sì, attraverso i suoi file.
- **P-004** (V-106). L'attivazione dell'hook (`core.hooksPath`) è una configurazione locale e non viaggia con il repository: ogni nuovo clone deve eseguire `git config core.hooksPath .githooks`. I test pytest restano il controllo primario.
- **P-005**. Il criterio delle versioni (ultima release entro il 12-10-2026) approssima l'ambiente originale, che non è documentato: l'equivalenza è un'**IPOTESI** da misurare in F1.3. Le dipendenze transitive sono state risolte da pip il 30-10-2026.

### Punti aperti

- **[DA CONFERMARE]** Documenti primari delle 9 serie sintetiche; rendimenti di Reebok 2001 e Avaya 2004.
- **[DA CONFERMARE]** Prime sedute di SNDK (13-02-2025): negoziazioni "when-issued" o regolari.
- **[DA CONFERMARE]** Licenze di Johnbrick123/sp500-data e di Yahoo Finance.
- **[DA CONFERMARE]** Calendario ufficiale NYSE 2027.
- ~~**[IPOTESI]** Le 11.231 celle riempite col valore precedente possono nascondere stop e azzerare i rendimenti giornalieri: effetto sulla top-3 da misurare in F1.2.~~ Chiuso in Fase 1.3 (V-207): nessuna cella nelle finestre delle 90 posizioni.
- ~~In attesa di autorizzazione: F1.3, riproduzione del baseline.~~ Autorizzata ed eseguita il 30-10-2026 (sezione seguente).

---

## Fase 1.3 — Riproduzione del baseline (30-10-2026), autorizzata dal committente

Condizioni: solo nella copia `work/replica_originale/`; nessuno script con output verso `source_original/`; nessun download; regole originali invariate; nessuna ottimizzazione né nuovo test di performance. Rapporto: `reports/01_baseline_reproduction.md`. Anomalie: `logs/registro_anomalie.md`. Comandi: `logs/fase_1_3/comandi.md`.

| ID | Ora | Oggetto | Procedura | Risultato | Evidenza | Stato |
|---|---|---|---|---|---|---|
| V-201 | 21:00 | Integrità prima della fase | `pytest -v`; `research.integrity verify --root work/replica_originale` | 11 test superati; copia: 25 file aggiunti (Fase 1.0), 0 modificati, 0 mancanti | `fase_1_3/integrita_prima.txt` | VERIFICATO |
| V-202 | 21:02 | Blocco degli script non autorizzati | `research.replica_originale run experiments.py` | Rifiutato, exit 1; consentiti solo `annual_study.py` e `report_annuale_tables.py` | `fase_1_3/comandi.md` | VERIFICATO |
| V-203 | 21:03 | Riproduzione | `research.replica_originale run annual_study.py report_annuale_tables.py` (offline, nella copia) | `annual_study.py` exit 0 in 28,8 s, 12 file; `report_annuale_tables.py` exit 0 in 1,6 s, 1 file; `source_original/` intatto prima e dopo; codice della copia invariato prima e dopo | `fase_1_3/esecuzione_*.txt` | VERIFICATO |
| V-204 | 21:04 | Confronto byte per byte | `sha256sum` dei 12 CSV/JSON originali e riprodotti | 12/12 identici | `outputs/tables/f13_confronto_file.csv` | VERIFICATO |
| V-205 | 21:16 | Confronto cella per cella | `research.confronto_baseline` | 6.127 celle o chiavi, 0 diverse, 0 entro tolleranza; stesse colonne e chiavi | `f13_confronto_*.csv`, `f13_discrepanze.csv`, `fase_1_3/confronto_baseline.txt` | VERIFICATO |
| V-206 | 21:13 | I 4 stop sul vincitore | `research.controlli_f13` [C] | Date, livelli, aperture sotto il livello e rendimenti = CSV; fonte `jb:yahoo`; nessun giorno riempito o riparato; minimo prima dello stop entro 2,4-2,6% dal livello in 3 casi su 4; nessuna seconda copia Yahoo per una verifica incrociata | `f13_stop_vincitore_*.csv` | VERIFICATO (minimi: DA CONFERMARE) |
| V-207 | 21:13 | Giorni riempiti | [A] e controllo alle date di classifica | 11.231 celle ricostruite = valore di `data_layer.py`; apertura, massimo, minimo e chiusura identici al pannello; 0 nelle finestre delle 90 posizioni; 4 membri-anno classificati toccati, il migliore 97° | `f13_ffill_*.csv` | VERIFICATO |
| V-208 | 21:13 | Regola di riparazione | [A] | 156 serie segnalate, 24 con riparazione registrata, 132 ricostruite invariate (scarto ≤ 1,6e-14); tutte le altre colonne identiche | `fase_1_3/controlli_f13.txt` | VERIFICATO |
| V-209 | 21:13 | Frazionamenti | [B] | 33 eventi nelle finestre; 11 con `close` grezza (WIKI, Tiingo), 0 salti nella serie rettificata; 2 scorpori registrati come frazionamenti (BBWI, WDC) | `f13_frazionamenti_posizioni.csv` | VERIFICATO |
| V-210 | 21:13 | Base di prezzo dello stop | [B]: stop su prezzo senza dividendi (`price_index`) contro prezzo total return | Stessa data per tutte le 81 posizioni con dati reali; dividendi tra ingresso e stop o uscita al massimo 8,2% | `f13_posizioni_qualita_dati.csv` | VERIFICATO |
| V-211 | 21:13 | Serie sintetiche | [D] | 9 su 9 nella top-3 (3 prime); 6 identiche a `patches.py`; 3 diverse solo per il fattore 1,0001 (A-001) | `f13_serie_sintetiche.csv` | VERIFICATO |
| V-212 | 21:13 | Copertura | [E] con la definizione originale e con il file di composizione | Membri e classificati originali riprodotti 31/31; doppio conteggio di 1-4 membri nel 1999-2005 e 2008 (A-004) | `f13_copertura.csv` | VERIFICATO |
| V-213 | 21:13 | Delisting | [F] | 10 esclusioni al giorno di decisione (8 sintetiche, MER 2008, SCG 2018), nessuna da top-3; 1 serie terminata prima di fine anno (2017); in detenzione esce solo UST 2009 | `f13_delisting_per_anno.csv`, `f13_esclusi_ultimo_giorno.csv` | VERIFICATO |
| V-214 | 21:13 | Tempi di benchmark e strategia | [G] | Date coerenti; `SP500_TR` da chiusura a chiusura; movimento notturno di SPY: media +0,39% (da −1,66% a +1,90%); durata 2026 fissata a 0,77 = 194/252 | `f13_allineamento_benchmark.csv` | VERIFICATO |
| V-215 | 21:13 | Liquidità e identità | [H] | 14/14 identità; liquidità a zero dopo lo stop, senza interessi né reinvestimento | `f13_identita.csv` | VERIFICATO |
| V-216 | fine fase | Test e integrità finali | `pytest -v` (integrità + strumenti) | 16 test superati; nessun `__pycache__` in `source_original/` | `fase_1_3/integrita_dopo.txt` | VERIFICATO |

### Note di procedura

- **P-006** (V-206…V-211). Prima dell'esecuzione finale ho corretto quattro miei controlli; dettagli in `fase_1_3/comandi.md`. Nessun risultato errato è stato pubblicato.
  - stop su `close` assunta rettificata per frazionamenti: 4 false differenze;
  - indicatore unico per i salti nei giorni di frazionamento;
  - esclusione delle sole serie riparate nel confronto dei prezzi rettificati;
  - scarto delle serie sintetiche non spiegato.
- **P-007** (V-203). La cartella `out/` della copia esisteva già: l'aveva creata l'import di `make_report.py` nel controllo V-110. `annual_study.py` da solo non la crea (A-006); il runner l'avrebbe creata e lo avrebbe registrato.

### Punti aperti dopo la Fase 1.3

- **[DA CONFERMARE]** Minimi giornalieri dei 4 stop sul vincitore con una fonte indipendente (A-009).
- **[DA CONFERMARE]** Trattamento degli scorpori BBWI 2021 e WDC 2025 (A-008).
- Effetto sui risultati del diverso punto di partenza di benchmark e strategia (A-005): da misurare solo in una fase autorizzata a nuovi calcoli.
- Restano aperti i punti precedenti: documenti SEC delle serie sintetiche, SNDK "when-issued", licenze, calendario NYSE 2027.
