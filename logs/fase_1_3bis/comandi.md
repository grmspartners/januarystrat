# Fase 1.3-BIS — Comandi eseguiti (31-10-2026, UTC)

Tutti i comandi partono dalla radice del repository con `.venv/bin/python` (Python 3.13.17, versioni in `requirements.txt`). Nessun download, nessun backtest, nessuna scrittura in `source_original/` o nella copia `work/replica_originale/`: gli script originali sono stati solo importati dalla copia, mai eseguiti come programmi. Le ore con i secondi sono registrate dal sistema; quelle al minuto sono ricostruite dall'ordine di esecuzione.

| Ora | Comando | Scopo | Evidenza |
|---|---|---|---|
| 13:38:55 | `git status`; `python3 -m research.integrity verify`; `… verify --root work/replica_originale` | Stato iniziale: `source_original/` identico al manifesto (160 file); copia con 38 file aggiunti, 0 modificati, 0 mancanti | `integrita.txt` (intestazione) |
| 13:39 | `.venv/bin/python <scratchpad>/explore1.py` | Esplorativo: classificazione dei 357 giorni segnalati dalla regola di riparazione (frazionamenti registrati, fonti, rapporto implicito) | `esplorativi/explore1.py` (non versionato) |
| 13:41 | `.venv/bin/python <scratchpad>/explore2.py` | Esplorativo: prima classificazione delle 30 riparazioni; meccanica degli stop sintetici (fattore 1,0001, riga 0,9999); confronto di `member_from` con il file di composizione | `esplorativi/explore2.py` (non versionato) |
| 13:45:59 | `HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 .venv/bin/python -m research.indagine_anomalie` | Prima esecuzione dello script dell'indagine | sostituita dall'esecuzione delle 13:48:25 |
| 13:47 | `.venv/bin/python <scratchpad>/explore3.py` | Esplorativo: righe e dividendi scartati dal filtro del calendario (date, fonti, finestre della top-3) | `esplorativi/explore3.py` (non versionato) |
| 13:48:25 | `HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 .venv/bin/python -m research.indagine_anomalie` | **Esecuzione finale**. Rispetto alla prima aggiunge la scomposizione delle righe scartate, i rendimenti nei giorni di cambio fonte e lo scenario di sensibilità PMC-Sierra 2004. | `indagine_anomalie.txt`, `hash_file_utilizzati.txt`, `outputs/tables/f13b_*.csv` |
| 13:49 | `.venv/bin/python -m pytest -q tests/test_indagine_anomalie.py` | Test delle funzioni di classificazione su casi reali | 4 test superati |
| 13:50 | Lettura in sola lettura delle tabelle `f13b_*.csv` (script Python in linea) | Esempi per il rapporto | — |
| fine fase | `.venv/bin/python -m pytest -v` più i controlli di `source_original/` e della copia | Integrità finale | `integrita.txt` (20 test superati) |

**Hash.**
- Gli hash SHA-256 dei 20 file letti dallo script sono in `hash_file_utilizzati.txt`: dati della copia, moduli originali, output riprodotti, workbook originale con il registro storico delle riparazioni, i due script di ricerca.
- I moduli originali della copia hanno lo stesso hash di `source_original/` (per esempio `patches.py` `ddd91133…`).
- Hash degli script esplorativi copiati in `esplorativi/` (percorsi resi anonimi con `<repo>` e `<scratchpad>`). Non sono versionati: restano solo sul disco della copia locale.
  - `explore1.py` `766ca1a2…`
  - `explore2.py` `da431619…`
  - `explore3.py` `af66abe5…`

**Calcoli su singole posizioni.** Lo scenario PMC-Sierra 2004 usa la funzione originale `annual_study.stock_year()` su un titolo che la strategia non ha detenuto. È un calcolo di sensibilità su una posizione, segnalato come stima nella tabella `f13b_sintetiche_scenari_documentali.csv` (colonna `tipo`). Non è un backtest: nessuna strategia è stata ricalcolata e nessun CAGR è stato prodotto.

**Riproducibilità degli script esplorativi: esclusi dal commit.** Nella revisione finale pre-commit il committente ha deciso di escluderli dal commit: sono stati rimossi dallo stage, non cancellati dal disco (non erano mai stati committati). I loro risultati sono superati dallo script finale. Motivi dell'esclusione:
- I percorsi sono resi anonimi (`<repo>`, `<scratchpad>`), quindi gli script non si eseguono senza sostituirli.
- `explore2.py` legge `flag_days.csv`, un file intermedio scritto da `explore1.py` nella scratchpad e non conservato nel repository.
- Nessun deliverable dipende da questi script.

## Revisione documentale (31-10-2026)

| Comando | Scopo | Evidenza |
|---|---|---|
| `git diff --cached --name-status`; `git diff --quiet`; `git ls-files --others --exclude-standard`; `python3 -m research.integrity verify` | Stato dello stage e di `source_original/` | risposta al committente |
| `HTTP(S)_PROXY=http://127.0.0.1:9 .venv/bin/python -c "import research.indagine_anomalie as m; m.TABLES=…; m.LOGS=…; m.main()"` (scritture nella scratchpad), poi `cmp` con i file in stage | Riproducibilità degli output | `revisione/riproducibilita.txt` |
| `.venv/bin/python logs/fase_1_3bis/revisione/verifica_tracciabilita.py` | Ricalcolo dalle evidenze di ogni valore citato nel rapporto 02 (3 esecuzioni; la finale ha 0 discordanze) | `revisione/verifica_tracciabilita.txt` |
| Lettura in sola lettura di `f13b_riparazioni.csv`, `f13b_sintetiche_classifiche.csv` e del pannello della copia (fattore di rettifica e dividendi di Dell) | Dettagli per il chiarimento di A-010 e per le precisazioni | — |

## Revisione finale pre-commit (31-10-2026)

| Comando | Scopo | Evidenza |
|---|---|---|
| `git restore --staged logs/fase_1_3bis/esplorativi/explore1.py logs/fase_1_3bis/esplorativi/explore2.py logs/fase_1_3bis/esplorativi/explore3.py` | Esclusione dal commit degli script esplorativi (restano sul disco, non tracciati) | `revisione/revisione_finale.txt` §4 |
| `grep` dei percorsi nello script di tracciabilità; `git checkout-index -a --prefix=<scratchpad>/checkout/` ed esecuzione dello script lì; due esecuzioni nel repository e `cmp` | Condizioni per spostare lo script in `research/` | `revisione/revisione_finale.txt` §3 |
| `.venv/bin/python -m pytest -v -p no:cacheprovider`; `python3 -m research.integrity verify`; `git diff --cached --quiet -- source_original` | Test e integrità finali | `revisione/revisione_finale.txt` §1-2 |
| `git diff --cached --name-only` con ricerca di file temporanei; `git ls-files -s` per i contenuti duplicati; `git ls-files --others --exclude-standard` | Controllo dello stage | `revisione/revisione_finale.txt` §4 |
| `git diff --cached > work/fase_1_3bis_diff_finale.patch`; `sha256sum` | Diff finale per la revisione del committente (in `work/`, escluso da Git) | risposta al committente |

## Revisione dei segnaposto (31-10-2026 23:57 – 01-11-2026, UTC)

| Comando | Scopo | Evidenza |
|---|---|---|
| `git write-tree` (albero dello stage prima della correzione: `24592e4d…`); copia del patch precedente in `work/fase_1_3bis_diff_finale_rev0_95f100d2.patch` | Riferimento per il diff incrementale (in `work/`, escluso da Git) | risposta al committente |
| `grep` sensibile alle maiuscole di TODO, FIXME, XXX, TBD, TBC, HACK; `grep -i` di "to verify", "placeholder", "da verificare", "da completare", `??`, `<…>`; ambito: file in stage e script esplorativi | Ricerca e classificazione dei segnaposto | `revisione/segnaposto.txt` §1 |
| Modifica del rapporto 02, §2.1: due celle della tabella e una nota | Correzione autorizzata (P-011) | rapporto 02 |
| `.venv/bin/python -m pytest -v -p no:cacheprovider`; `python3 -m research.integrity verify`; `git diff --cached --quiet -- source_original`; `git diff --quiet -- source_original` | Test e integrità | `revisione/segnaposto.txt` §2 |
| `HTTP(S)_PROXY=http://127.0.0.1:9 .venv/bin/python -c "import research.indagine_anomalie as m; m.TABLES=…; m.LOGS=…; m.main()"` (scritture nella scratchpad); `.venv/bin/python logs/fase_1_3bis/revisione/verifica_tracciabilita.py` (output nella scratchpad); `cmp` e `diff` con i file in stage | Riproducibilità | `revisione/segnaposto.txt` §3 |
| Script Python in linea, in sola lettura, su docstring di `patches.py`, CSV, rapporto e registro delle anomalie | Coerenza dei valori di Reebok 2001 e Avaya 2004 | `revisione/segnaposto.txt` §4 |
| `git add` dei 4 file interessati; `git diff --cached > work/fase_1_3bis_diff_finale.patch`; `git diff 24592e4d… <albero nuovo>` > `work/fase_1_3bis_diff_incrementale.patch`; `sha256sum` | Patch finale e patch incrementale per il committente | risposta al committente |
