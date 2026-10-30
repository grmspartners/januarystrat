# 01 — Riproduzione del baseline originale (Fase 1.3)

| | |
|---|---|
| Progetto | GRMS Partners — ricerca quantitativa indipendente sulla strategia January Buy |
| Repository | `grmspartners/januarystrat`, branch `claude/peaceful-cray-bkvt73`, base `bfb6a93` |
| Data | 30-10-2026 (esecuzioni tra le 21:00 e le 21:20 UTC) |
| Autorizzazione | Fase 1.3, 30-10-2026: solo nella copia `work/replica_originale/`; nessun download; regole originali invariate; nessuna ottimizzazione né nuovo test di performance |
| Autore | Claude (assistente di ricerca), su incarico di GRMS Partners |
| Evidenze | `logs/fase_1_3/`, `outputs/tables/f13_*.csv`, `logs/registro_anomalie.md`, `logs/registro_verifiche.md` (V-201…V-216) |

**Legenda** (come in `00_diagnostica_iniziale.md`): **[VERIFICATO]** controllato con procedura riproducibile · **[RIPORTATO]** affermato dai materiali originali · **[STIMA]** valore approssimato · **[IPOTESI]** interpretazione da testare · **[DA CONFERMARE]** serve una fonte o verifica non disponibile.

**Perimetro.** Questa fase verifica se il codice e i dati originali producono di nuovo gli stessi risultati, e come il codice tratta alcuni casi delicati dei dati. Non valuta se la strategia abbia un vantaggio: nessuna affermazione di questo rapporto riguarda la performance attesa.

---

## Sintesi

1. **[VERIFICATO] Riproduzione bit-identica.** `annual_study.py` e `report_annuale_tables.py`, eseguiti invariati nella copia di lavoro, producono 12 file CSV/JSON con la stessa impronta SHA-256 degli originali. Confronto cella per cella: 6.127 celle o chiavi, 0 differenze, 0 differenze entro la tolleranza.
2. **[VERIFICATO] Nessuna discrepanza da riconciliare.** Né i dati, né le versioni delle dipendenze (Python 3.13.17, numpy 2.5.4, pandas 3.0.6), né gli arrotondamenti producono differenze sugli output.
3. **[VERIFICATO]** La riproducibilità non garantisce la correttezza. I controlli metodologici hanno trovato **9 anomalie** (A-001…A-009) e **8 osservazioni** (O-001…O-008), raccolte in `logs/registro_anomalie.md`. Nessuna cambia i titoli selezionati o i rendimenti riprodotti. Due toccano il confronto con il benchmark e la verificabilità del risultato principale:
   - **A-005:** il benchmark parte dalla chiusura del giorno di decisione, la strategia dall'apertura del giorno dopo; il movimento notturno di SPY vale in media +0,39%;
   - **A-009:** i minimi giornalieri dei 4 stop sul vincitore, che spiegano tutta la differenza tra vincitore con e senza stop, non si possono verificare con una fonte indipendente senza scaricare dati.
4. **[VERIFICATO]** Le aree sensibili controllate (giorni riempiti, frazionamenti, serie sintetiche, copertura, delisting, liquidità) non modificano la selezione dei titoli né i rendimenti riprodotti. Le eccezioni minori sono documentate.
5. **[VERIFICATO]** `source_original/` è rimasto identico al manifesto prima e dopo ogni esecuzione: 16 test superati a fine fase.

---

## 1. Procedura

### 1.1 Comando ed esecuzione

```
.venv/bin/python -m research.replica_originale run annual_study.py report_annuale_tables.py
```

Il comando `run` (in `research/replica_originale.py`) esegue, nell'ordine:

1. verifica `source_original/` contro il manifesto SHA-256 e blocca tutto se differisce;
2. controlla che `config.ROOT` e `config.OUT` della copia puntino dentro `work/replica_originale/`;
3. controlla che i file originali della copia siano tutti presenti e invariati (0 modificati, 0 mancanti);
4. accetta solo gli script autorizzati per questa fase (`annual_study.py`, `report_annuale_tables.py`); la prova con `experiments.py` è stata rifiutata;
5. lancia ogni script con `cwd = work/replica_originale/code` e i proxy HTTP(S) verso una porta chiusa, così ogni tentativo di download fallisce;
6. registra versioni, impronta dello script, costanti del modulo (lette senza eseguirlo), comando, durata, codice di uscita, file scritti con impronta, output completo;
7. ripete i controlli 1 e 3 alla fine.

| Script | Durata | Esito | File scritti |
|---|---|---|---|
| `annual_study.py` (sha256 `409e6de1…` = manifesto) | 28,8 s | exit 0, nessun avviso | 11 CSV/JSON + `AN_paths.pkl` |
| `report_annuale_tables.py` (sha256 `8babefd9…` = manifesto) | 1,6 s | exit 0 | `report_annuale_tables.json` |

`report_annuale_tables.py` è il passo successivo della stessa catena originale. Legge solo i file prodotti da `annual_study.py` ed è l'unico modo per rigenerare il JSON originale con i numeri citati nel report. Non sono stati eseguiti `build_excel_annuale.py`, `charts_annuale.py` e `build_report_annuale.py` (Excel, grafici, Word): non producono CSV o JSON.

### 1.2 Versioni, parametri, configurazione

- **Ambiente [VERIFICATO]:** Python 3.13.17; numpy 2.5.4; pandas 3.0.6; pyarrow 26.0.0; scipy 1.18.1; openpyxl 3.1.5; matplotlib 3.11.2 (`requirements.txt`).
- **Dati [VERIFICATO]:** quelli ricostruiti nella Fase 1.0, senza download: `jb_prices.parquet` con l'impronta del manifesto originale (`c8217576…`), pannello di 9.766 date (4-1-1988 → 9-10-2026) e 947 titoli.
- **Parametri di `annual_study.py` [VERIFICATO]**, letti dal sorgente senza eseguirlo e identici a `AN_parametri.json`:

  | Parametro | Valore |
  |---|---|
  | Costo per lato | 0,10% |
  | Bollo | 0,20% |
  | Imposta sulle plusvalenze | 26% |
  | Imposta sui dividendi (nettista) | 37,1% |
  | Ritenuta sui dividendi nell'AMC | 15% |
  | Costo dell'AMC | 0,5% |
  | Stop | 35% |
  | Premio LEAPS | 35% |
  | Peso LEAPS | 35% |
  | Anni di riporto delle minusvalenze | 4 |
  | Anni di classifica | 1996-2025 |
  | Sigma proxy per le serie sintetiche | 0,5264 |
  | Ultimo dato | 2026-10-09 |

- **Configurazione [VERIFICATO]:** `ROOT = work/replica_originale`, `OUT = work/replica_originale/out`. La cartella `out/` esisteva già nella copia: l'aveva creata l'import di `make_report.py` durante la Fase 1.0 (V-110). Vedi anomalia A-006.

## 2. Confronto con i risultati originali

### 2.1 File

| File originale | Righe | Celle o chiavi confrontate | Identiche | Diverse | Byte identici |
|---|---|---|---|---|---|
| `AN_top3_anno.csv` | 90 | 1.620 | 1.620 | 0 | sì |
| `AN_rendimenti_annui.csv` | 30 | 1.110 | 1.110 | 0 | sì |
| `AN_sintesi.csv` | 110 | 1.100 | 1.100 | 0 | sì |
| `AN_finestre_10anni.csv` | 20 | 280 | 280 | 0 | sì |
| `AN_zainetto_*.csv` (6 file) | 6 × 30 | 6 × 330 | 1.980 | 0 | sì (6/6) |
| `AN_parametri.json` | 11 chiavi | 11 | 11 | 0 | sì |
| `report_annuale_tables.json` | 26 chiavi | 26 | 26 | 0 | sì |
| **Totale** | | **6.127** | **6.127** | **0** | **12/12** |

Nessun file manca da una delle due parti, nessuna chiave compare da un solo lato, colonne nello stesso ordine. `AN_paths.pkl` non ha un originale (i `.pkl` non erano stati consegnati). Dettaglio per colonna: `outputs/tables/f13_confronto_colonne.csv`; per chiave JSON: `f13_confronto_json.csv`; elenco delle discrepanze: `f13_discrepanze.csv` (vuoto).

### 2.2 Le verifiche richieste

| Verifica | Dove | Celle | Esito |
|---|---|---|---|
| Rendimenti annuali di ogni strategia | `AN_rendimenti_annui.csv` (lordo); `report_annuale_tables.json` (`annui_lordista`, `annui_nettista`); `AN_finestre_10anni.csv` | 120 + 780 LEAPS + 2 chiavi + 280 | identiche |
| Rendimento cumulato e CAGR | `AN_sintesi.csv` (`valore_finale`, `cagr`), tre viste e cinque periodi | 220 | identiche |
| Titoli selezionati ogni anno | `AN_top3_anno.csv` (ticker, etichetta, società, rendimento T0, classifica parziale, serie ricostruita, anno di detenzione) | 630 | identiche |
| Prezzi di ingresso e uscita | `AN_top3_anno.csv` (`prezzo_ingresso_rett`, `prezzo_uscita_rett`) | 180 | identiche |
| Date e livelli di stop | `AN_top3_anno.csv` (`stop_toccato`, `data_stop`, `stop_in_gap`, `rend_T1_con_stop`); `AN_rendimenti_annui.csv` (`titoli_fermati_top3`). Il livello (65% dell'ingresso) è ricostruito in §4.1 e in `f13_identita.csv`. | 300 | identiche |
| Trattamento della liquidità | Identità aritmetiche sugli output riprodotti (§4.8) | 22 stop | verificato |
| Rendimenti delle tre posizioni | `AN_top3_anno.csv` (`rend_T1_senza_stop`, `rend_T1_con_stop`) | 180 | identiche |
| Costi e fiscalità | `AN_sintesi.csv`, righe lordista e nettista (valore finale, CAGR, metriche, imposte pagate, minusvalenze scadute); 6 registri dello zainetto | 750 + 1.980 | identiche |
| Metriche di rischio | `AN_sintesi.csv` (peggior anno, miglior anno, calo massimo di fine anno, anni negativi, anni sopra l'S&P 500) | 660 | identiche |

**[VERIFICATO]** Anche i dividendi (300 celle), i delisting (180) e i benchmark (60) sono identici.

## 3. Riconciliazione delle differenze

**[VERIFICATO]** Non ci sono differenze da riconciliare: nessun dato interessato, nessun punto del codice responsabile, nessun contributo di dati, dipendenze o arrotondamenti agli output.

**Che cosa questo dimostra e che cosa no.**
- **[VERIFICATO]** Dati congelati e codice consegnati sono sufficienti a rigenerare esattamente i risultati dello studio annuale, anche con le versioni del 2026. L'equivalenza delle versioni ipotizzata in Fase 1.0 non è più un rischio per questi output (osservazione O-007).
- **[IPOTESI → esclusa per questi output]** Che i risultati dipendessero da file intermedi non consegnati. Il pannello ricostruito basta.
- **Non dimostra** che dati e metodo siano corretti: lo stesso errore si riproduce identico. Per questo servono i controlli della sezione 4 e una verifica con fonti indipendenti.

## 4. Controlli metodologici

Script: `research/controlli_f13.py`. Usa i moduli originali dalla copia senza modificarli e scrive solo in `outputs/tables/` e `logs/fase_1_3/`. Nessun backtest alternativo.

### 4.1 I 4 stop che determinano il vantaggio del vincitore con stop

`f13_stop_vincitore_eventi.csv`; finestre giornaliere attorno all'ingresso e allo stop in `f13_stop_vincitore_finestre.csv`.

| Anno | Titolo | Ingresso (apertura) | Stop | Sedute | Apertura sotto il livello | Con stop | Senza stop | Minimo più vicino prima dello stop |
|---|---|---|---|---|---|---|---|---|
| 2000 | Qualcomm | 3-1-2000, 99,625 | 26-1-2000 | 16 | sì (64,50 contro 64,76) | −35,26% | −58,75% | +2,6% sopra il livello |
| 2002 | Nvidia | 2-1-2002 | 28-3-2002 | 59 | no | −35,00% | −82,87% | +2,4% |
| 2008 | NOV | 2-1-2008 | 16-9-2008 | 178 | sì | −35,92% | −67,08% | +2,4% |
| 2011 | Netflix | 3-1-2011 | 29-9-2011 | 187 | no | −35,00% | −60,41% | +9,9% |

*I prezzi di Qualcomm sono quelli della colonna `open`/`low` della fonte: rettificati per i frazionamenti successivi (2:1 del 16-8-2004, quindi 99,625 corrisponde a circa 199,25 negoziati), non per i dividendi (QCOM non ne pagava nel 2000). "Minimo più vicino prima dello stop": distanza minima dal livello prima del giorno dello stop.*

- **[VERIFICATO]** Data, livello, eventuale apertura sotto il livello e rendimento coincidono con il CSV per tutti e quattro.
- **[VERIFICATO]** Tutte e quattro le serie hanno fonte `jb:yahoo` in tutta la finestra, nessun giorno riempito, nessuna barra incompleta, nessuna riparazione automatica.
- **[VERIFICATO]** L'unico frazionamento in finestra è il 4:1 di Qualcomm del 31-12-1999 (giorno di decisione); la serie rettificata è continua.
- **[VERIFICATO] Sensibilità a piccole variazioni.** In tre casi su quattro, prima dello stop il minimo è arrivato entro il 2,4-2,6% dal livello. **[IPOTESI]** Una soglia o un prezzo d'ingresso leggermente diversi potrebbero anticipare lo stop. Il risultato non è stato misurato: sarebbe un nuovo test, non autorizzato.
- **[VERIFICATO] Qualcomm 2000 (O-001).** L'acquisto all'apertura avviene a +13,1% sulla chiusura precedente e vicino al massimo di giornata: il livello di stop è ancorato a quel picco d'apertura.
- **[DA CONFERMARE] (A-009)** Il batch Yahoo non contiene una seconda copia di questi titoli: i minimi decisivi vanno verificati con una fonte indipendente (CRSP o un altro fornitore), oggi non disponibile senza download.
- **[VERIFICATO] (O-002)** La regola parla di "prezzo di carico", il codice usa prezzi rettificati per i dividendi. Con una base senza dividendi la data dello stop è la stessa per tutte le 81 posizioni con dati reali.

### 4.2 Gli 11.231 giorni riempiti con il prezzo precedente

`f13_ffill_per_anno.csv`, `f13_ffill_per_fonte.csv`, `f13_ffill_classifica.csv`.

- **[VERIFICATO]** Ricostruendo le matrici di `data_layer.py` prima del riempimento si trovano esattamente 11.231 celle. Apertura, massimo, minimo e chiusura ricostruiti coincidono con il pannello.
- **[VERIFICATO]** Le celle sono concentrate nel 1995-1997 e nel 2010-2018 (1.606 nel 2017, su 23 titoli). Per fonte: 8.096 su serie `jb:yahoo`, 1.550 WIKI, 1.409 Tiingo, 138 Yahoo, 38 Kaggle.
- **[VERIFICATO]** In nessun giorno il prezzo rettificato manca mentre la chiusura è presente, e nessuna barra ha apertura, massimo o minimo mancanti.
- **[VERIFICATO]** Nessun giorno riempito cade nelle finestre di classifica o di detenzione delle 90 posizioni, né alle date di ingresso, uscita o classifica.
- **[VERIFICATO]** Nell'intero universo classificato, solo 4 membri-anno hanno un prezzo riempito alla data di classifica o almeno 20 giorni riempiti nell'anno: SW 2024 (97°), CRR 1996 (190°), LO 2008 (192°), AMCR 2019 (307°). Effetto nullo sulla top-3.

### 4.3 Frazionamenti azionari

`f13_frazionamenti_posizioni.csv` (33 eventi nelle finestre delle 90 posizioni).

- **[VERIFICATO] (A-002)** In 11 giorni di frazionamento la colonna `close` crolla del 45-54%: è il prezzo grezzo delle serie WIKI (Dell, EMC) e Tiingo (Express Scripts, Coterra), non il prezzo rettificato per frazionamenti dichiarato in `config.py`. La serie total return negli stessi giorni è continua (0 salti superiori al 40%).
- **[VERIFICATO]** Il codice originale non ne è influenzato: stop, prezzi d'ingresso e minimi usano il fattore `a/c` del giorno stesso. La regola di riparazione segnala queste serie e lascia invariato il rendimento del fornitore (A-003). Il rischio riguarda codice nuovo.
- **[VERIFICATO] (A-008)** Due "frazionamenti" Yahoo sono in realtà scorpori (BBWI 2021, WDC 2025) ed entrano nel rendimento di classifica di due posizioni non prime. **[DA CONFERMARE]** la correttezza del trattamento.
- **[VERIFICATO]** Nessun frazionamento cade su un giorno riparato automaticamente.

### 4.4 Le 9 serie sintetiche

`f13_serie_sintetiche.csv`.

- **[VERIFICATO]** Tutte e 9 entrano nella top-3 riprodotta: 3 prime (Reebok 2001, Providian 2003, Avaya 2004), 3 seconde, 3 terze.
- **[VERIFICATO]** In 6 serie i rendimenti di classifica e di detenzione coincidono con `patches.py`. Nelle 3 serie con stop (Sprint PCS, Nextel, Dynegy 2001) la costruzione moltiplica per 1,0001 anche il prezzo di fine anno di classifica (A-001):
  - rendimento di classifica più alto di 3,2-4,4×10⁻⁴;
  - rendimento di detenzione più basso di circa 4-5×10⁻⁵;
  - stop esattamente a −35%.

  L'ordine della classifica non cambia.
- **[VERIFICATO]** Per costruzione le serie sintetiche hanno andamento liscio, dividendi zero e apertura uguale alla chiusura precedente. Uno stop scatta quindi sempre al livello, senza rischio di apertura sotto il livello.
- **[RIPORTATO] / [DA CONFERMARE]** I valori di detenzione di Reebok 2001 (−3,1%) e Avaya 2004 (+33%), dichiarati da verificare dagli autori, e le date di stop ricavate dai minimi trimestrali dei 10-K restano da confrontare con i documenti SEC.

### 4.5 Copertura storica incompleta dell'S&P 500

`f13_copertura.csv`.

- **[VERIFICATO]** Il numero di classificati e quello dei membri pubblicati in `copertura_dati.csv` si riproducono in 31 anni su 31 con la definizione originale.
- **[VERIFICATO] (A-004)** La definizione originale conta due volte le società ricostruite: 1 a 4 membri in più negli anni 1999-2005 e 2008. La copertura pubblicata cambia al massimo di 0,5 punti; i valori del rapporto (49% nel 1996, 75% nel 2005, 95% nel 2010) non cambiano all'arrotondamento.
- **[VERIFICATO]** Sul file di composizione (498-505 membri), i membri con una serie di prezzi passano da 261 nel 1996 a 390 nel 2005 e a 505 dal 2016.
- **[RIPORTATO] [DA CONFERMARE]** Il rischio che un vero vincitore manchi dai dati negli anni a bassa copertura resta quello del rapporto diagnostico: la top-3 1996-2008 è stata confrontata dagli autori con liste esterne, non qui.

### 4.6 Titoli delistati

`f13_delisting_per_anno.csv`, `f13_esclusi_ultimo_giorno.csv`.

- **[VERIFICATO]** Il filtro "quotato dopo la data di decisione" esclude 10 membri-anno:
  - 8 sono serie sintetiche nell'anno di detenzione: l'esclusione è corretta, impedisce di classificarle sul rendimento di detenzione;
  - gli altri 2 sono acquisizioni chiuse a cavallo d'anno: Merrill Lynch 2008 (−77,3%) e SCANA 2018 (+23,0%).

  Nessuno sarebbe entrato nella top-3.
- **[VERIFICATO]** Un solo membro-anno (2017) ha una serie che termina prima di fine anno e quindi non è classificato.
- **[VERIFICATO]** Durante la detenzione esce dal listino una sola posizione: la serie sintetica UST 2009. L'incasso in contanti del 6-1-2009 vale rendimento zero; la liquidità resta a zero fino a fine anno, senza reinvestimento (O-004).

### 4.7 Allineamento temporale tra benchmark e strategia

`f13_allineamento_benchmark.csv`.

- **[VERIFICATO]** In tutti gli anni le date coincidono: decisione all'ultima seduta di T0, ingresso alla prima di T0+1, uscita all'ultima di T0+1. Per il 2026: dal 2-1-2026 al 9-10-2026.
- **[VERIFICATO] (A-005)** Il rendimento `SP500_TR` del CSV è esattamente il rendimento da chiusura a chiusura di `^SP500TR`. Il benchmark include quindi il movimento notturno tra la chiusura di T0 e l'apertura di T0+1, la strategia no. Su SPY, nei 30 anni, quel movimento vale:
  - media +0,39%;
  - mediana +0,51%;
  - minimo −1,66% (2016);
  - massimo +1,90% (2013).

  **[STIMA]** Nel campione il benchmark parte in media circa 0,4 punti più avanti in ogni anno. L'effetto sui CAGR non è stato calcolato.
- **[VERIFICATO]** Le aperture di `^GSPC` coincidono con la chiusura precedente in 12 anni su 30 (dati di apertura degli indici poco affidabili prima del 2007). Per questo la misura usa SPY.
- **[VERIFICATO] (A-007)** La durata del 2026 nel CAGR è fissata a 0,77 anni: oggi coincide con 194/252 sedute, non si aggiorna con nuovi dati.

### 4.8 Liquidità e identità aritmetiche

`f13_identita.csv`: 14 identità su 14 verificate sugli output riprodotti.

- **[VERIFICATO]** Vincitore = rendimento del 1° classificato; prime tre = media semplice dei tre rendimenti, senza ribilanciamento.
- **[VERIFICATO]** Stop senza apertura sotto il livello: uscita esattamente al 65% del prezzo d'ingresso rettificato (17 casi). Stop con apertura sotto il livello: uscita all'apertura, sotto il livello (5 casi).
- **[VERIFICATO] (O-006)** Dopo lo stop la posizione resta in liquidità a rendimento zero fino a fine anno: nessun interesse, nessun reinvestimento, dividendi successivi esclusi. Se scattano tutti e tre gli stop, tutto il portafoglio resta in liquidità.
- **[VERIFICATO]** Valore finale = 100 × prodotto dei (1 + rendimento annuo); CAGR = (valore finale / 100)^(1/29) − 1. Verificato per i 5 rendimenti lordi 1997-2025.
- **[VERIFICATO]** LEAPS 35/65 = 0,35 × opzione + 0,65 × azione. I prezzi delle opzioni sono di modello (Black-Scholes), non di mercato **[RIPORTATO]**.

## 5. Anomalie

Elenco completo, con quantificazione, punto del codice e origine: `logs/registro_anomalie.md`. Nessuna è stata corretta nel codice originale.

| ID | Sintesi | Origine | Impatto sui risultati riprodotti |
|---|---|---|---|
| A-001 | Fattore 1,0001 nelle 3 serie sintetiche con stop | metodologia | trascurabile |
| A-002 | `close` non rettificata per frazionamenti nelle serie WIKI e Tiingo | dati + documentazione | nullo (rischio per codice nuovo) |
| A-003 | Ricostruzione di 156 serie segnalate (1,6e-14) | arrotondamenti | nullo |
| A-004 | Doppio conteggio nella copertura pubblicata | metodologia | nullo sulla strategia |
| A-005 | Benchmark da chiusura, strategia da apertura | metodologia + documentazione | da misurare (≈0,4 punti l'anno **[STIMA]**) |
| A-006 | `annual_study.py` non crea `out/` | riproducibilità | nullo |
| A-007 | Durata 2026 fissata a 0,77 | metodologia | nullo alla data dei dati |
| A-008 | Scorpori registrati come frazionamenti (BBWI, WDC) | dati | da misurare; posizioni non prime |
| A-009 | Nessuna fonte indipendente per i minimi dei 4 stop decisivi | dati | il risultato principale non è verificabile senza fonte esterna |

## 6. Integrità di `source_original/`

- **[VERIFICATO]** Prima della fase: 11 test superati (`logs/fase_1_3/integrita_prima.txt`).
- **[VERIFICATO]** Durante: il runner ha verificato il manifesto prima e dopo l'esecuzione (`esecuzione_runner.txt`). La copia è rimasta con 0 file originali modificati o mancanti; i 38 file aggiunti sono output della pipeline (dati ricostruiti, file in `out/`) e cache Python (`__pycache__`).
- **[VERIFICATO]** Dopo la fase: 16 test superati, cioè gli 11 di integrità più i 5 dei nuovi strumenti (`logs/fase_1_3/integrita_dopo.txt`); nessun `__pycache__` in `source_original/`.

## 7. Limiti di questa fase

- **Fonti.** Nessuna fonte esterna è stata consultata. I punti segnati [DA CONFERMARE] richiedono dati o documenti non presenti nel repository: minimi giornalieri dei 4 stop, documenti SEC delle serie sintetiche, trattamento degli scorpori.
- **Impatto non misurato.** L'effetto di A-005 e A-008 sui risultati non è stato misurato: richiederebbe un nuovo calcolo dei rendimenti, escluso da questa fase.
- **Altri output.** Il workbook Excel, i grafici e il Word non sono stati rigenerati. Il confronto riguarda i CSV e i JSON.
- **Copertura dei controlli.** I controlli riguardano lo studio annuale (S&P 500, regola di gennaio), non il paper principale (12 tranche, Nasdaq-100, EUR).

## 8. Deliverable

| File | Contenuto |
|---|---|
| `reports/01_baseline_reproduction.md` | questo rapporto |
| `outputs/tables/f13_confronto_file.csv`, `f13_confronto_colonne.csv`, `f13_confronto_json.csv`, `f13_discrepanze.csv` | confronto con gli originali (per file, per colonna, per chiave JSON, discrepanze) |
| `outputs/tables/f13_stop_vincitore_eventi.csv`, `f13_stop_vincitore_finestre.csv` | i 4 stop sul vincitore |
| `outputs/tables/f13_posizioni_qualita_dati.csv`, `f13_frazionamenti_posizioni.csv`, `f13_movimenti_estremi_detenzione.csv` | qualità dei dati delle 90 posizioni |
| `outputs/tables/f13_ffill_per_anno.csv`, `f13_ffill_per_fonte.csv`, `f13_ffill_classifica.csv` | giorni riempiti |
| `outputs/tables/f13_serie_sintetiche.csv`, `f13_copertura.csv`, `f13_delisting_per_anno.csv`, `f13_esclusi_ultimo_giorno.csv`, `f13_allineamento_benchmark.csv`, `f13_identita.csv` | serie sintetiche, copertura, delisting, tempi, identità |
| `logs/registro_anomalie.md` | registro delle anomalie |
| `logs/fase_1_3/comandi.md` e gli altri file in `logs/fase_1_3/` | comandi eseguiti e output completi |
| `logs/registro_verifiche.md` (V-201…V-216) | registro cronologico delle verifiche |
| `research/replica_originale.py` (comando `run`), `research/confronto_baseline.py`, `research/controlli_f13.py`, `tests/test_strumenti_fase_1_3.py` | codice e test |

Gli output riprodotti restano in `work/replica_originale/out/`, esclusa da Git: sono identici agli originali già presenti in `source_original/results/`.

## 9. Passi successivi possibili (da autorizzare)

1. **Verifica esterna dei 4 stop e delle serie sintetiche.** Richiede l'autorizzazione a usare fonti esterne: dati giornalieri da un secondo fornitore, documenti SEC.
2. **Riconciliazione del workbook e del Word con i CSV** (F1.6), incluso il ricalcolo delle formule con LibreOffice.
3. **Seconda implementazione indipendente** (F1.4), che misuri anche l'effetto di A-005 (finestre omogenee) e A-008 (scorpori).
4. **Preregistrazione** delle ipotesi e dei test (F1.7) prima di qualsiasi nuovo test di performance.
