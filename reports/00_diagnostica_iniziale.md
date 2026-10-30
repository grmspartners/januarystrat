# 00 — Rapporto diagnostico iniziale (Fase 0)

| | |
|---|---|
| Progetto | GRMS Partners — ricerca quantitativa indipendente sulla strategia January Buy |
| Repository | `grmspartners/januarystrat`, branch `claude/peaceful-cray-bkvt73` |
| Stato analizzato | commit `20b2ef1` (unico commit; `source_original/` identico al commit) |
| Data | 30-10-2026 (analisi in sola lettura); salvato in questo file durante la Fase 1.0 |
| Autore | Claude (assistente di ricerca), su incarico di GRMS Partners |
| Registro delle verifiche | [`logs/registro_verifiche.md`](../logs/registro_verifiche.md); i codici `V-nnn` rimandano alle sue voci |

**Perimetro.** Questo rapporto descrive lo stato del progetto prima di qualsiasi intervento. Durante la Fase 0 non sono stati modificati o creati file nel repository, non sono stati scaricati dati e non sono stati eseguiti backtest. Il rapporto non contiene conclusioni sulla performance della strategia.

**Legenda.** Ogni affermazione rilevante porta una di queste etichette.

| Etichetta | Significato |
|---|---|
| **[VERIFICATO]** | Controllato con una procedura riproducibile descritta nel registro (`V-nnn`). Per il codice, "verificato" significa che il codice fa ciò che è descritto, non che il risultato sia corretto. |
| **[RIPORTATO]** | Affermato dai documenti o prodotto dal codice originale; non ancora verificato in modo indipendente. |
| **[STIMA]** | Valore approssimato o calcolato sotto ipotesi esplicite. |
| **[IPOTESI]** | Interpretazione o ipotesi di lavoro, da sottoporre a test. |
| **[DA CONFERMARE]** | Richiede una fonte o una verifica non ancora disponibile. |

La sezione 9 elenca ciò che è cambiato o è stato chiarito durante la Fase 1.0, inclusa una correzione a questo rapporto.

---

## 1. Struttura del progetto e stato Git

- **[VERIFICATO V-001]** Un solo commit (`20b2ef1`), working tree pulito, branch di lavoro allineato a `master`.
- **[VERIFICATO V-001]** 166 file tracciati: 6 nella radice (`CLAUDE.md`, `PROJECT_STRUCTURE.md`, i tre file sorgente, `.gitignore`) e 160 in `source_original/` (204 MB su disco). Il pacchetto Git occupa 195 MB perché i dati grezzi sono stati committati nel commit iniziale.
- **[VERIFICATO V-002]** Il `.xlsx` e il `.docx` della radice sono identici byte per byte alle copie in `source_original/` (SHA-256 `1a3bb4c6…` e `e7d3c486…`). Il `.md` della radice è una nota di sintesi; il report completo in Markdown è `source_original/GRMS_Report_January_Buy_Annuale.md`.
- **[VERIFICATO V-001]** Al momento della diagnosi non esistevano le cartelle suggerite da `PROJECT_STRUCTURE.md`, né test, né un file con le versioni delle dipendenze.

### Immutabilità di `source_original/`

- **[VERIFICATO V-017]** `source_original/` era identico al commit iniziale; ne è stata registrata l'impronta SHA-256 (160 file).
- **[VERIFICATO V-007] Problema critico.** Il codice originale ricava tutti i percorsi dalla propria posizione (`config.ROOT = parents[1]`). Eseguito sul posto scriverebbe dentro `source_original/`:
  - `fetch_data.py` → `data/raw/jb_prices.parquet` (166 MB; il `.gitignore` originale lo esclude proprio per questo);
  - `parse_yahoo.py`, `data_layer.py` → `data/processed/`;
  - tutti gli script di analisi → `out/`; `make_report.py` crea `out/charts` già all'import.
- **[VERIFICATO V-017]** I file di `source_original/` non sono protetti in scrittura a livello di file system.

## 2. File e dataset disponibili

| Dataset | Stato |
|---|---|
| `jb_prices.parquet` (7 parti, 166.227.925 byte; Johnbrick123/sp500-data, copia del 12-10-2026 **[RIPORTATO]**) | **[VERIFICATO V-003]** il file ricomposto ha l'impronta dichiarata in `MANIFEST.json` (`c8217576…`) |
| `jb_membership_intervals.parquet`, `jb_renames.csv` | **[VERIFICATO V-003]** impronte coincidenti; le due copie della membership sono identiche |
| `GRMS_YAHOO_batch1.ndjson.gz` | **[VERIFICATO V-004]** 227 simboli, scaricato il 2026-10-12T12:17:13Z, **81** simboli non trovati (corretto: vedi sezione 9); `^SP500TR` e `^GSPC` dal 4-1-1988 al 9-10-2026; SPY con 136 dividendi. Nessuna impronta nel manifesto. |
| `GRMS_FRED_v1.json` | **[VERIFICATO V-005]** 12 serie (DTB3, DTB6, DTB1YR, DGS1, DGS2, DEXUSEU, VIXCLS, FEDFUNDS, CPIAUCSL, EXGEUS, EXITUS, AAA); nessuna impronta né data di download |
| 5 file zip di Kenneth French | Presenti; nessuna impronta; non usati dalla catena annuale **[VERIFICATO V-008]** |
| Liste Wikipedia, `no_data_tickers.txt` (38), `recycled_tickers.csv` (5), file Nasdaq-100 | Presenti; i file Nasdaq-100 non servono allo studio annuale sull'S&P 500 |
| `results/`: CSV/JSON storici, 4 workbook, 24 grafici | **[RIPORTATO]** risultati storici, non ancora riprodotti |

- **[VERIFICATO V-004]** Ultimo dato di prezzo: 9-10-2026. La diagnosi è del 30-10-2026.

**Manca, ma serve all'audit:**
- `data/processed/*` e i file intermedi `out/*.pkl` (rigenerabili dai dati grezzi). Ricostruiti nella Fase 1.0, sezione 9.
- **[DA CONFERMARE]** I documenti primari dietro le 9 serie ricostruite (proxy DEF 14A e 10-K alla SEC, lista S&P DJI, articoli CNN e Forbes). Sono citati in `patches.py`, ma i valori sono scritti a mano e i documenti non sono archiviati.
- Dati da fornitori a pagamento per una verifica indipendente (CRSP, Norgate): non disponibili; lo studio usa solo dati gratuiti.
- Prezzi storici delle opzioni, documentazione dell'AMC, fonti fiscali ufficiali.
- **[DA CONFERMARE]** Licenza del dataset Johnbrick123 e condizioni d'uso di Yahoo Finance.

## 3. Ambiente e dipendenze (situazione in Fase 0)

- **[VERIFICATO V-006]** Presenti nel sistema: Python 3.13.17, pandas 3.0.5, numpy 2.5.3, openpyxl 3.1.5, PyYAML, python-docx, Node 22 con il pacchetto `docx`, LibreOffice.
- **[VERIFICATO V-006]** Mancanti: **pyarrow** (bloccante: lettura dei parquet), **scipy** (bloccante: `leaps.py`, `metrics.py`), **matplotlib** (grafici), statsmodels (solo `extra_analyses.py`), pytest.
- **[VERIFICATO V-006]** PyPI raggiungibile; GitHub risponde 403 dal proxy, quindi `fetch_data.py --latest` non funzionerebbe (e non va usato). Risorse: 4 CPU, 15 GB di RAM, 30 GB di disco liberi.
- **[VERIFICATO V-008]** Catena minima per lo studio annuale: `fetch_data` → `parse_yahoo` → `data_layer` → `annual_study`, poi `build_excel_annuale` → `charts_annuale` → `report_annuale_tables` → `build_report_annuale`.

Situazione risolta nella Fase 1.0: sezione 9.

## 4. Ricostruzione della strategia dal codice

**[VERIFICATO V-008, lettura di `annual_study.py`, `signals.py`, `panel.py`, `patches.py`, `benchmarks.py`]** Il codice implementa:

- **Universo:** i membri dell'S&P 500 all'ultima seduta dell'anno T0, con un prezzo in quella data e ancora quotati dopo.
- **Classifica:** rendimento totale dell'anno solare T0 (dividendi inclusi). IPO e spin-off con almeno 126 sedute sono classificati sul rendimento dalla prima quotazione. È successo tre volte: Carrier 2020, Constellation 2022, Sandisk 2025 **[VERIFICATO V-011]**.
- **Acquisto e vendita:** acquisto all'apertura della prima seduta di T0+1, vendita alla chiusura dell'ultima (2026: al 9 ottobre).
- **Stop:** uscita al 65% del prezzo d'ingresso, controllando i minimi giornalieri su prezzi rettificati per i dividendi. Vendita al livello dello stop o, se il titolo apre già sotto, all'apertura. La liquidità rende zero.
- **Prime tre:** media semplice dei tre rendimenti, nessun ribilanciamento.
- **Benchmark:** `^SP500TR` da chiusura a chiusura; ETF UCITS = TR − 15% × rendimento da dividendi di SPY − TER 0,07%.
- **Interventi sui dati:**
  - riparazione automatica dei salti di rettifica superiori al 15%;
  - un titolo escluso perché la serie riguarda un'altra società (Sonat, `SNT-199910`);
  - buchi interni alle serie riempiti con il prezzo precedente; minimi e massimi mancanti sostituiti con la chiusura;
  - 9 serie sintetiche ricostruite da documenti, non da prezzi di mercato.
- **[VERIFICATO V-015]** Il registro storico delle riparazioni (foglio `Riparazioni_dati` del workbook principale) conta 30 celle su 24 titoli, nessuna negli anni di classifica o di detenzione delle posizioni della top-3.

**Coerenza tra le fonti (in sola lettura):**
- **[VERIFICATO V-009]** I CAGR 1997-2025 di tutte le strategie, nelle tre viste, coincidono in `AN_sintesi.csv`, nella nota Markdown, nel report Markdown e nella prima tabella del Word.
- **[VERIFICATO V-010]** I CAGR lordi ricalcolati da `AN_rendimenti_annui.csv` sono 9,94% / 17,75% / 30,34% / 19,40% / 19,06%, come riportato. È un controllo aritmetico sui risultati salvati, non una riproduzione del backtest.
- **[VERIFICATO V-012]** Il workbook ha 11 fogli e 1.257 formule, tutte con valori calcolati, senza nomi definiti. Nettista, LEAPS, rendimenti con stop e rendimenti dell'S&P 500 sono valori fissi: cambiare i parametri nel foglio `Parametri` non li ricalcola.
- **[VERIFICATO V-008]** Incongruenza minore: la docstring di `annual_study.py` descrive la detenzione da chiusura a chiusura, mentre il codice (e il report) usano l'apertura della prima seduta.

## 5. Problemi di riproducibilità

1. **Critico [VERIFICATO V-007]:** la pipeline scrive dentro `source_original/`.
2. **Bloccante [VERIFICATO V-006]:** mancavano pyarrow e scipy.
3. **[VERIFICATO V-006] / [IPOTESI]:** le versioni originali non sono registrate (il README indica `pip install` senza versioni). Con pandas 3 e numpy 2.5 sono possibili differenze numeriche rispetto all'ambiente originale.
4. **[VERIFICATO V-008] / [DA CONFERMARE]:** valori delle serie ricostruite scritti a mano, senza documenti archiviati. Due sono dichiarati `[DA VERIFICARE]` dagli autori: Reebok 2001 (stimato tra −8,6% e −1,4%) e Avaya 2004.
5. **[VERIFICATO V-004, V-005]:** Yahoo, FRED e French senza impronta: l'integrità si può verificare solo tramite Git.
6. **[VERIFICATO V-012]:** workbook solo in parte "vivo".
7. **[VERIFICATO V-001]:** circa 200 MB di dati grezzi già nel repository. Contrasta con la regola Git di `PROJECT_STRUCTURE.md` e forse con le condizioni d'uso di Yahoo **[DA CONFERMARE]**.
8. **[VERIFICATO]** Il `.gitignore` esclude `*.log`: i registri di audit vanno salvati come `.md` o `.txt`.

## 6. Rischi metodologici

Nessuno di questi punti è una conclusione sulla performance: sono rischi da sottoporre a test.

1. **[RIPORTATO] / [IPOTESI] Nessun vero test fuori campione.** Secondo il paper principale, il thread è circolato su X nel 2026 con dati fino al 2025. Se è così, tutto il 1997-2025 è interno al campione rispetto all'ipotesi, e il primo anno davvero indipendente è il 2027, a condizione di registrare la regola prima.
2. **[VERIFICATO V-010] Il vantaggio dello stop sul solo vincitore dipende da 4 anni.** Con e senza stop i rendimenti differiscono solo nel 2000, 2002, 2008 e 2011. Insieme, quei quattro anni moltiplicano la ricchezza finale per 19,0 volte, circa 10,7 punti annui sul CAGR. **[VERIFICATO V-011]** Sulle posizioni 2 e 3 lo stesso stop ha evitato una perdita maggiore 7 volte su 18.
3. **[IPOTESI] Qualità dei dati sui quattro stop decisivi.** Ogni stop dipende da un singolo minimo giornaliero in serie gratuite, cucite da più fonti. Qualcomm 2000 cade subito dopo un frazionamento 4:1 di fine 1999 **[DA CONFERMARE]** e va verificato con una fonte indipendente.
4. **[VERIFICATO V-011] Serie sintetiche.** Riguardano 3 vincitori su 29 (anni di detenzione 2001, 2003, 2004) e 9 posizioni su 87.
   - **[VERIFICATO V-008]** Il loro andamento dentro l'anno è liscio (interpolazione log-lineare).
   - Gli stop sono ricavati dai minimi trimestrali dei 10-K, con vendita esattamente al livello: ipotesi favorevole per Sprint PCS, Nextel e Dynegy 2001 **[IPOTESI]**.
5. **[RIPORTATO V-014] Universo incompleto prima del 2006.** I prezzi coprono il 49,1% dei membri nel 1996 e il 75,2% nel 2005. Il file di composizione non contiene Nortel nel 1999. Le liste esterne usate per il controllo misurano il rendimento di prezzo, mentre la classifica usa il rendimento totale.
6. **[VERIFICATO V-011] / [DA CONFERMARE] Classifica parziale degli spin-off.** La soglia di 126 sedute è un parametro discrezionale. Sandisk 2025 è classificata sul rendimento dalla prima quotazione (13-02-2025 nei dati); quella data potrebbe corrispondere a negoziazioni "when-issued", prima della separazione formale.
7. **[VERIFICATO V-008] / [IPOTESI] Informazioni successive alla decisione.** Il filtro "quotato dopo la data di decisione" è un piccolo uso di informazioni future. Il significato della data di fine nella composizione (inclusa o esclusa) va verificato.
8. **[VERIFICATO V-008] Benchmark non omogenei.**
   - L'indice è misurato da chiusura a chiusura, la strategia dall'apertura del giorno dopo.
   - Le versioni con stop hanno un'esposizione minore, ma non c'è un benchmark a parità di esposizione o di rischio.
   - Il calo massimo è misurato solo sui valori di fine anno, quindi è sottostimato.
   - Mancano volatilità, Sharpe, Sortino, Calmar e tempi di recupero.
9. **[IPOTESI] Esecuzione.**
   - 10 punti base per lato sono pochi per i singoli titoli del 1997-2001, quando i prezzi si muovevano a scatti di 1/8 o 1/16 di dollaro.
   - Lo stop è calcolato su prezzi rettificati per i dividendi, non sul prezzo di carico effettivo **[VERIFICATO V-008]**.
   - Non c'è un'analisi della capacità.
10. **[RIPORTATO] / [IPOTESI] Molti test e scelte a posteriori.**
    - Il progetto precedente ha eseguito più di 2.304 backtest.
    - Il Deflated Sharpe Ratio è calcolato su 48-84 prove, quindi probabilmente sopravvalutato **[IPOTESI]**.
    - Le osservazioni indipendenti sono circa 29 **[STIMA]**.
    - Gennaio è risultato il migliore dei 12 mesi di partenza **[RIPORTATO]**, con serie ricostruite interpolate per gli altri mesi.
11. **Fisco e struttura.**
    - **[DA CONFERMARE]** Trattamento fiscale dell'AMC, inclusa la ritenuta USA sui "dividend equivalent" dei certificati su azioni USA (sezione 871(m) del codice fiscale USA).
    - **[VERIFICATO V-008]** AMC testato solo allo 0,5%; `CLAUDE.md` chiede 0,5-0,9%.
    - **[VERIFICATO V-008]** Analisi in USD, mentre le plusvalenze imponibili si calcolano in EUR. Regole 2026 applicate a tutta la storia **[RIPORTATO]**.
    - **[VERIFICATO V-011]** Il nettista vende e ricompra anche quando il vincitore si ripete (Dell 1997-99, AMD 2019-20).
    - **[VERIFICATO V-008] La società di investimento non è modellata affatto.** Se l'investitore è una holding o un family office societario, il regime fiscale è diverso **[DA CONFERMARE]**.
12. **Moderna.**
    - **[RIPORTATO V-016]** Nei dati al 9-10-2026 è prima da inizio anno (+663%), davanti a Sandisk (+566%).
    - **[IPOTESI]** Diventa vincitrice solo alla chiusura di giovedì 31-12-2026, e solo se è ancora nell'S&P 500 a quella data.
    - **[DA CONFERMARE: calendario NYSE 2027]** Il primo prezzo eseguibile sarebbe l'apertura di lunedì 4-1-2027 (1-1-2027 è venerdì, festivo).
    - Oggi non è nulla più di un candidato.

## 7. Piano operativo per la Fase 1 (audit)

1. **F1.0 Preparazione** — autorizzata il 30-10-2026 ed eseguita: sezione 9.
2. **F1.1 Registro di audit** in `logs/`, che separi fatti verificati, affermazioni riportate, ipotesi, stime e domande aperte.
3. **F1.2 Ricostruzione e profilazione dei dati nella copia di lavoro** (`work/replica_originale/`, esclusa da Git, codice originale non modificato, nessun accesso alla rete):
   - controllo per anno della copertura, dei valori mancanti, dei buchi riempiti e delle riparazioni;
   - coerenza tra apertura, massimo, minimo e chiusura;
   - frazionamenti e dividendi sulle 87 posizioni della top-3.
4. **F1.3 Riproduzione del baseline:** eseguire `annual_study.py` senza modifiche e confrontare cella per cella con `source_original/results/AN_*.csv`; ricalcolare il workbook con LibreOffice; misurare l'effetto delle versioni di pandas (2.x contro 3.0).
5. **F1.4 Seconda implementazione indipendente** in `research/`, con test unitari su stop, zainetto, calcoli lordista e nettista e assenza di dati successivi alla decisione.
6. **F1.5 Verifiche mirate** sui dati esistenti: i 4 stop sul vincitore, sensibilità a Reebok e Avaya, soglia di 126 sedute, date di fine della composizione, allineamento dei benchmark.
7. **F1.6 Riconciliazione** delle 17 tabelle del Word, del Markdown e del workbook con i CSV.
8. **F1.7 Preregistrazione da approvare prima di qualsiasi nuovo test:** ipotesi, elenco chiuso di soglie di stop, metriche, test statistici (bootstrap a blocchi, permutazione delle posizioni, placebo), correzione per i test multipli, periodo di verifica dal 2027.

## 8. Decisioni che spettano al committente

1. ~~Autorizzazione a creare la struttura di cartelle e a committare sul branch di lavoro.~~ Concessa il 30-10-2026.
2. ~~Autorizzazione a installare i pacchetti Python.~~ Concessa il 30-10-2026.
3. ~~Approccio "copia di lavoro" per eseguire il codice originale.~~ Concesso il 30-10-2026.
4. **Profilo fiscale dell'investitore:** persona fisica in regime amministrato oppure società. Cambia l'intera analisi fiscale e di struttura.
5. **Fonti esterne:** accesso a dati di fornitori a pagamento (CRSP, Norgate, Bloomberg) e autorizzazione futura a scaricare i documenti della SEC per verificare le serie ricostruite.
6. Destino dei circa 200 MB di dati grezzi già nel repository, anche alla luce delle licenze.

---

## 9. Aggiornamento dopo la Fase 1.0 (30-10-2026)

Dettagli e comandi nel registro, voci `V-101`–`V-112`.

**Correzione a questo rapporto.**
- **C-001** Il numero di simboli non trovati nel batch Yahoo è **81**, non 82 come indicato nella prima versione del rapporto consegnata in chat. Il valore 82 era un conteggio a vista, non calcolato; 81 è `len(header["fail"])` ed è confermato dall'output di `parse_yahoo.py` **[VERIFICATO V-004, V-108]**.

**Punti risolti o chiariti.**
- **[VERIFICATO V-104, V-105]** `source_original/` è ora protetto da un manifesto SHA-256 (160 file, 212.809.099 byte) ancorato al commit `20b2ef1`, da 11 test automatici e da un hook pre-commit **[VERIFICATO V-106]**.
- **[VERIFICATO V-103]** Ambiente: `.venv` con Python 3.13.17 e versioni fissate in `requirements.txt`; tutte le versioni dirette hanno wheel per Python 3.13 su Linux e Windows **[VERIFICATO V-102]**. L'equivalenza con l'ambiente originale resta un'**[IPOTESI]**.
- **[VERIFICATO V-108]** La pipeline dei dati (`fetch_data` → `parse_yahoo` → `data_layer`) è stata ricostruita solo nella copia di lavoro, senza rete, senza errori né avvisi. `source_original/` è risultato intatto prima e dopo.
- **[VERIFICATO V-109]** Il pannello ricostruito ha 9.766 date (4-1-1988 → 9-10-2026) e 947 titoli. Riproduce esattamente le 30 riparazioni del registro storico (scarto massimo 4,4×10⁻¹⁶): è un indizio forte che il data layer coincide con quello originale **[IPOTESI** fino alla riproduzione del baseline in F1.3**]**.
- **[VERIFICATO V-109]** Schema di `jb_prices.parquet`, finora non ispezionabile: 6.163.332 righe, 1.022 ticker, date dal 2-1-1970 al 9-10-2026; righe per fonte: Yahoo 4,98 M, Tiingo 0,84 M, Quandl WIKI 0,31 M, Kaggle 0,03 M, più 48 righe di "patch".
- **[VERIFICATO V-109]** Anche nel dataset Johnbrick123, quello usato per la classifica, Sandisk (`SNDK`) parte dal 13-02-2025; le sue 416 righe hanno come fonte Yahoo. Se le prime sedute siano negoziazioni "when-issued" resta **[DA CONFERMARE]**.
- **[VERIFICATO V-108]** `data_layer.py` riempie con il valore precedente 11.231 celle mancanti all'interno della vita dei titoli. **[IPOTESI]** In quei giorni il minimo coincide con la chiusura precedente, quindi uno stop non può scattare e il rendimento è zero: l'effetto sulle posizioni della top-3 va misurato in F1.2.
- **[VERIFICATO V-110]** Tutti i moduli della catena annuale si importano nel nuovo ambiente; i percorsi di output puntano alla copia di lavoro.

**Non ancora fatto, per scelta.** Nessun backtest è stato eseguito: `annual_study.py` non è stato lanciato. La riproduzione del baseline (F1.3) attende l'autorizzazione.
