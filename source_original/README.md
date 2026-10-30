# GRMS Partners · January Buy

Studio quantitativo della regola "compra a gennaio il miglior titolo dell'anno precedente e ripeti ogni anno" (thread X) e delle varianti richieste: top-3, stop al 35%, LEAPS, orizzonti più brevi, fisco italiano, veicolo lordista. Include la risposta finale sulla strategia da applicare.

Dati aggiornati al **9 ottobre 2026**, con il 2026 incluso come anno in corso. Tutte le tabelle sono in `results/GRMS_JanuaryBuy_Risultati.xlsx`.

---

## 0. Nota di aggiornamento del 13 ottobre 2026 (versione semplificata)

Su richiesta del committente l'analisi è stata rifatta nella forma più semplice: solo S&P 500, solo regola di gennaio, nessuna quota in ETF.

- `GRMS_Report_January_Buy_Annuale.docx` / `.md`: il report.
- `results/GRMS_JanuaryBuy_Analisi_Annuale.xlsx`: tutti i dati, con formule.

Il report confronta:

- solo vincitore oppure prime tre a un terzo ciascuna;
- con e senza stop al 35% dal prezzo di acquisto;
- vincitore con 35% in LEAPS e 65% nell'azione;
- tre viste: lordo, lordista (AMC con costo annuo 0,5%, imposta alla fine) e nettista (imposta ogni anno con zainetto);
- confronto con l'S&P 500: indice Total Return per il lordo, ETF UCITS per il lordista e il nettista.

Importi in dollari.

| CAGR 1997-2025 | Lordo | Lordista (AMC) | Nettista |
|---|---|---|---|
| S&P 500 (indice / ETF) | 9,9% | 8,3% | 8,3% |
| Solo vincitore, senza stop | 17,7% | 15,4% | 11,2% |
| Solo vincitore, stop 35% | 30,3% | 27,7% | 23,0% |
| Prime tre, senza stop | 19,4% | 17,0% | 13,6% |
| Prime tre, stop 35% | 19,1% | 16,7% | 13,9% |
| Vincitore, 35% LEAPS + 65% azione | 13,6% | 11,4% | 6,8% |
| Vincitore, 35% LEAPS + 65% azione con stop | 25,7% | 23,3% | 18,2% |

Script: `annual_study.py` → `build_excel_annuale.py` → `charts_annuale.py` → `report_annuale_tables.py` → `build_report_annuale.py`. Il modello del testo è `paper/annuale.md`. Gli script sono inclusi in `run_all.py`.

---

## 1. Che cosa c'è nella cartella

```
januarybuy/
├── GRMS_Paper_January_Buy.docx    documento per il board (Word, identità GRMS)
├── GRMS_Paper_January_Buy.md      stesso documento in Markdown
├── README.md                      questo file
├── results/
│   ├── GRMS_JanuaryBuy_Strategia_Definitiva.xlsx   decisione, regole, calcolatore, piano di avvio,
│   │                                               segnali di oggi, registro esecuzioni, zainetto
│   ├── GRMS_JanuaryBuy_LEAPS.xlsx                  versione LEAPS: sintesi, trade log, scenari,
│   │                                               calcolatore Black-Scholes
│   ├── GRMS_JanuaryBuy_Risultati.xlsx              TUTTI i dati e TUTTI i test (oltre 35 fogli)
│   ├── charts/                                     figure fig01-fig16
│   └── *.csv                                       ogni tabella in formato CSV
├── code/                          pipeline Python (codice e commenti in inglese)
├── data/raw/                      input grezzi, inclusa la copia congelata del dataset S&P 500
└── tools/yahoo_browser_downloader.js
```

### Come rifare tutto sul PC dello Studio

```
pip install pandas numpy scipy pyarrow statsmodels matplotlib openpyxl pyyaml
cd code
python run_all.py          # 30-40 minuti; i risultati vanno in januarybuy/out/
```

Per generare di nuovo il Word serve Node.js con il pacchetto `docx`:

```
node md2docx.js ../out/GRMS_Paper_January_Buy.md ../out/GRMS_Paper_January_Buy.docx ../out
```

La pipeline lancia, nell'ordine, questi script:

| Script | Che cosa fa |
|---|---|
| `fetch_data.py` | Ricompone la copia congelata del dataset e ne controlla l'impronta SHA-256 |
| `parse_yahoo.py`, `data_layer.py` | Costruiscono il pannello dei prezzi |
| `parse_wiki_changes.py` | Registro storico delle variazioni dell'S&P 500 (nomi delle società uscite) |
| `build_top3.py` | Top-3 per anno |
| `spariti.py` | Analisi dei titoli spariti |
| `experiments.py`, `experiments2.py`, `rank_tests.py`, `extra_analyses.py` | Replica, dal lordo al netto, varianti, LEAPS, robustezza, protocolli, fattori |
| `final_selection.py` | 48 regole × 12 mesi di partenza × 4 periodi = 2.304 backtest |
| `final_decision.py` | Criterio di scelta, walk-forward, segnali di oggi |
| `rebalanced_mix.py` | ETF + satellite con ribilanciamento annuale |
| `make_report.py`, `build_excel_leaps.py`, `build_excel_definitiva.py` | Excel e figure |
| `paper_tables.py` | Tabelle del documento, generate dai dati senza ricopiature a mano |

I risultati di questa consegna sono in `results/`, una copia di `out/` senza i file intermedi `.pkl`.

---

## 2. Dati e titoli spariti

| Elemento | Fonte | Copertura |
|---|---|---|
| Composizione S&P 500 point-in-time | fja05680/sp500 + Johnbrick123/sp500-data | dal 2-1-1996 |
| Composizione Nasdaq-100 point-in-time | jmccarrell/n100tickers | dal 2007 |
| Prezzi giornalieri, inclusi i delistati | Johnbrick123/sp500-data (Yahoo, Tiingo, Quandl WIKI, Kaggle); Yahoo Finance | 49% dei membri nel 1996, 75% nel 2005, 95% dal 2010, 100% dal 2018 |
| Nomi e motivi di uscita delle società | Wikipedia, "Historical components of the S&P 500" (12-10-2026) | completo dal 2007, scarso prima |
| T-bill, EUR/USD | FRED; euro sintetico dal marco tedesco prima del 1999 | dal 1988 |
| Fattori | Kenneth French (FF3 + Momentum) | dal 1927 |

**Le cartelle dello Studio** (`MarketData`, `sp500`, `Stooq`) contengono serie di **indici**. Per sapere quali sono le 3 azioni migliori di ogni anno servono invece i prezzi di ogni singola azione dell'indice, comprese quelle che oggi non esistono più. Questi prezzi sono quelli sopra elencati.

**Titoli spariti** (fogli `Spariti_*`):

- **Vincitori assenti dai dati gratuiti.** Nove vincitori annuali mancavano. Sono stati reinseriti ricostruendoli dai documenti SEC (proxy DEF 14A, 10-K) e dalle liste S&P DJI, CNN e Forbes:

  | Anno | Società reinserite |
  |---|---|
  | 1999 | Sprint PCS, Nextel |
  | 2000 | Reebok, Dynegy |
  | 2002 | Providian |
  | 2003 | Avaya, Dynegy |
  | 2004 | TXU |
  | 2008 | UST |

- **Società della top-3 non più quotate.** Dei 78 titoli distinti entrati nella top-3 dell'S&P 500 dal 1996, 25 non sono più quotati oggi, quasi sempre per acquisizione.
- **Nessun vincitore è andato a zero** nell'anno successivo, quello in cui la regola lo detiene. L'unico uscito entro l'anno è UST, comprata in contanti da Altria a premio il 6-1-2009. Il peggior anno di detenzione è Nvidia 2002, a -82,8%.
- **Membri senza alcun prezzo.** Sono 336 ticker, elencati anno per anno con nome e motivo di uscita dove disponibili.
- **Valori ancora da verificare** (`[DA VERIFICARE]`): il rendimento esatto di Reebok 2001 e quello di Avaya 2004.

---

## 3. Risultati in breve

Tutti i valori sono al netto del fisco italiano, in EUR, dopo l'imposta finale, salvo dove indicato.

| Tema | Risultato |
|---|---|
| Replica del thread (lordo USD) | Dal 2012: 170.002 dollari contro 176.114 del thread. Dal 1997 con stop 35%: 1.406.346 contro 1.514.581. Dal 1997 senza stop: 73.886 contro 89.418, con drawdown del -97,9%. |
| Fisco | Nel campione lungo la ricchezza finale netta è il 15% di quella lorda. In un veicolo a imposizione differita sarebbe il 69%. Ruotare ogni anno l'ETF S&P 500 costa 2,6 punti annui. |
| Fortuna del calendario | Dal 2009 la regola del thread fa +40,4% annuo con partenza a gennaio e -10,1% con partenza ad aprile. Gennaio è il mese migliore dei 12. |
| Stop | Gli stop stretti (15-25%) e lo stop trailing peggiorano il risultato. |
| Orizzonti brevi | Classifica a 6 mesi e ribilanciamento mensile peggiorano il risultato. |
| LEAPS al 35% | Rendono meno delle azioni in ogni scenario. Con il 100% del capitale in premi azzerano il capitale. |
| Filtro di regime | Il filtro sulla media a 10 mesi protegge nel 2000-2008 ma rende meno dell'ETF dopo il 2009. |
| 12 tranche mensili | Tutte le regole con stop 35% battono l'ETF in tutti e 4 i periodi, ma con drawdown molto più profondi. |

**Decisione finale** (criterio dichiarato nel documento, sezioni 3.6 e 4.7). L'allocazione raccomandata è:

- **70%** ETF UCITS S&P 500 ad accumulazione;
- **30%** satellite "top-2, stop 35%, mantieni i titoli riconfermati, 12 tranche mensili";
- ribilanciamento annuale con banda di 5 punti;
- tetto massimo del satellite: 60%.

| Netto fisco IT, EUR | ETF S&P 500 | 70/30 ribilanciato |
|---|---|---|
| CAGR 2009 - 9/10/2026 | 13,8% | 16,6% |
| CAGR 1997 - 9/10/2026 | 8,2% | 12,0% |
| CAGR 2009-2025 | 13,3% | 14,9% |
| CAGR 1997-2025 | 7,7% | 10,4% |
| Max drawdown 2009-2026 | -33,6% | -30,8% |
| Max drawdown 1997-2026 | -65,4% | -58,0% |

**Condizioni da accettare:**

- nel 2009-2023 il vantaggio è stato nullo;
- c'è un rischio di concentrazione: oggi Sandisk compare in 11 tranche su 12;
- c'è un rischio di gap sotto lo stop;
- la probabilità che lo Sharpe del satellite superi quello dell'ETF è stimata al 74%.

---

## 4. Avvertenze

- Backtest storico, non garanzia di risultati futuri. Non è una raccomandazione personalizzata: serve la valutazione di adeguatezza MiFID II.
- Le aliquote fiscali vigenti nel 2026 sono applicate a tutta la storia.
- Le LEAPS sono prezzate con un modello, non con prezzi storici di mercato.
- Le serie ricostruite sono esatte per la regola di gennaio e interpolate per gli altri mesi di partenza.
