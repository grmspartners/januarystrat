# Fase 1.3 — Comandi eseguiti (30-10-2026, UTC)

Tutti i comandi sono stati eseguiti dalla radice del repository (`/home/user/januarystrat`) con `.venv/bin/python` (Python 3.13.17, versioni in `requirements.txt`), salvo dove indicato. Nessun comando ha scritto in `source_original/`: l'integrità è verificata prima e dopo ogni esecuzione degli script originali e alla fine della fase.

Le ore con i secondi sono registrate dal sistema (file di evidenza o registro dei comandi). Quelle al minuto sono ricostruite dall'ordine di esecuzione e quindi approssimate.

## Esecuzioni che producono i deliverable

| Ora | Comando | Scopo | Evidenza |
|---|---|---|---|
| 21:00 | `.venv/bin/python -m pytest -v -p no:cacheprovider` | Integrità di `source_original/` prima della fase | `integrita_prima.txt` (11 test superati) |
| 21:02 | `python3 -m research.integrity verify --root work/replica_originale` | Stato della copia: 25 file aggiunti dalla Fase 1.0, 0 modificati, 0 mancanti | — |
| 21:02 | `.venv/bin/python -m research.replica_originale run experiments.py` | Prova del blocco: script non autorizzato rifiutato (exit 1) | — |
| 21:03:16 | `.venv/bin/python -m research.replica_originale run annual_study.py report_annuale_tables.py` | **Riproduzione**: esegue nella copia `annual_study.py` e poi `report_annuale_tables.py`, invariati, senza rete | `esecuzione_runner.txt`, `esecuzione_annual_study.txt`, `esecuzione_report_annuale_tables.txt` |
| 21:04 | `for f in …; sha256sum source_original/results/$f work/replica_originale/out/$f` | Confronto byte per byte dei 12 CSV/JSON | ripetuto e salvato in `outputs/tables/f13_confronto_file.csv` |
| 21:05:55 | `.venv/bin/python -m research.confronto_baseline` | Confronto cella per cella (prima esecuzione) | sostituito dall'esecuzione delle 21:16 |
| 21:08:55 | `.venv/bin/python -m research.controlli_f13` | Controlli metodologici (prima esecuzione) | sostituito |
| 21:12:21 | `.venv/bin/python -m research.controlli_f13` | Seconda esecuzione, dopo la correzione di tre miei controlli (sotto) | sostituito |
| 21:13:44 | `.venv/bin/python -m research.controlli_f13` | Esecuzione finale, con il controllo dei prezzi riempiti alle date di classifica | `controlli_f13.txt`, `outputs/tables/f13_*.csv` |
| 21:16:14 | `.venv/bin/python -m research.confronto_baseline` | Esecuzione finale, dopo la correzione di un'etichetta della colonna "tema" | `confronto_baseline.txt`, `outputs/tables/f13_confronto_*.csv`, `f13_discrepanze.csv` |
| 21:15 | `.venv/bin/python -m pytest -q tests/test_strumenti_fase_1_3.py` | Test dei nuovi strumenti | 5 test superati |
| fine fase | `.venv/bin/python -m pytest -v -p no:cacheprovider` | Integrità di `source_original/` dopo la fase | `integrita_dopo.txt` |

Gli script `controlli_f13.py` e `confronto_baseline.py` sono stati eseguiti con `HTTP_PROXY`/`HTTPS_PROXY` verso una porta chiusa (`http://127.0.0.1:9`), come gli script originali.

## Correzioni ai miei controlli durante la fase

Errori nei controlli, non nel codice originale; corretti prima dell'esecuzione finale.

1. **Prezzo "non rettificato" per lo stop.** La prima versione confrontava i minimi con la colonna `close`, assumendola rettificata per i frazionamenti come dichiara `config.py`. Per le serie WIKI e Tiingo non lo è (anomalia A-002). Risultato: 4 false differenze di data, tutte in giorni di frazionamento (Dell 1998 e 1999, EMC 1999, Coterra 2012). Il controllo ora usa `annual_study.price_index()`, coerente con i frazionamenti e senza dividendi: 0 differenze.
2. **Frazionamenti.** Il primo indicatore univa i salti della `close` e quelli della serie rettificata; ora sono due colonne separate (11 salti della `close`, 0 della serie rettificata).
3. **Confronto dei prezzi rettificati con il pannello.** La prima versione escludeva solo le 24 serie con riparazioni registrate e risultava "diverso". La regola di `panel.py` ricostruisce tutte le 156 serie segnalate (anomalia A-003); escluse quelle, il confronto è identico.
4. **Serie sintetiche.** La prima versione segnalava 3 serie "non coerenti con `patches.py`" senza spiegarne il motivo. Ora la tabella riporta lo scarto e verifica che sia interamente dovuto al fattore 1,0001 (anomalia A-001).

## Comandi esplorativi (sola lettura)

Servivano a capire i risultati intermedi. I numeri riportati nel rapporto vengono tutti dalle esecuzioni finali sopra.

| Ora | Comando | Scopo |
|---|---|---|
| 20:59 | `git status`, `git log`, `git fetch`, `ls .venv work/replica_originale` | Stato dell'ambiente all'avvio |
| 21:01 | `sed`/`grep` su `report_annuale_tables.py`, `paper_tables.py`, `make_report.py`, `spariti.py` (nella copia) | Input di `report_annuale_tables.py`; definizione originale della copertura |
| 21:10 | Script Python in linea: lettura di `f13_serie_sintetiche.csv` e `f13_frazionamenti_posizioni.csv` | Origine delle differenze delle serie sintetiche e dei salti nei giorni di frazionamento |
| 21:11 | Script Python in linea: ricostruzione delle matrici pre-riempimento con `research.controlli_f13.raw_matrices()` e confronto con `Panel.load()`; ricerca di `Y_QCOM`, `Y_NVDA`, `Y_NOV`, `Y_NFLX` | Origine della differenza dei prezzi rettificati (156 colonne segnalate, 1,6e-14); assenza di una seconda copia Yahoo |
| 21:13 | Script Python in linea: lettura di `f13_ffill_*`, `f13_movimenti_estremi_detenzione.csv`, `f13_stop_vincitore_finestre.csv`, `f13_copertura.csv`, `f13_esclusi_ultimo_giorno.csv` | Dettagli per il rapporto |
| 21:14 | Script Python in linea: lettura di `f13_stop_vincitore_eventi.csv`, `f13_allineamento_benchmark.csv` | Dettagli per il rapporto |
