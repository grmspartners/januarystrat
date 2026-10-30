# January Buy — nota di aggiornamento "analisi annuale" (13 ottobre 2026)

Versione semplificata dello studio January Buy, chiesta da Francesco dopo il paper per il board: solo S&P 500, solo regola di gennaio, niente Nasdaq e niente quota in ETF.

## Regole

- **Classifica:** rendimento totale dell'anno solare T0, con la composizione storica dell'indice (inclusi i titoli spariti).
- **Operatività:** acquisto all'apertura del primo giorno di borsa di T0+1, vendita alla chiusura dell'ultimo giorno.
- **Strategie confrontate:**
  - solo vincitore;
  - prime tre a 1/3 ciascuna;
  - entrambe con e senza stop al 35% dal prezzo di carico. Lo stop chiude solo il titolo che scende; se scatta su tutti e tre, tutto il portafoglio passa in liquidità.
- **LEAPS:** 35% del capitale in premi e 65% nell'azione del vincitore.
  - Call a circa 1 anno, strike con premio pari al 35% del prezzo; Black-Scholes con IV = 1,1 volte la volatilità realizzata e spread del 3%.
  - Sensibilità testate: ottimista, prudente, LEAPS a 2 anni.
- **Viste fiscali:**
  - **lordo;**
  - **lordista:** strategia dentro un AMC con costo annuo dello 0,5% (scelta di Francesco), più costi dello 0,10% per lato, bollo 0,20%, ritenuta USA del 15%, 26% una sola volta alla fine;
  - **nettista:** 26% ogni anno con zainetto di 4 anni, dividendi USA al 37,1%.
- **Benchmark:**
  - lordo: S&P 500 Total Return;
  - lordista e nettista: ETF UCITS tenuto in portafoglio, senza AMC;
  - in più: ETF venduto e ricomprato ogni anno.
- **Valuta:** USD.

## Risultati (CAGR 1997-2025)

| | Lordo | Lordista (AMC) | Nettista |
|---|---|---|---|
| S&P 500 | 9,9% | 8,3% | 8,3% |
| Solo vincitore | 17,7% | 15,4% | 11,2% |
| Solo vincitore, stop 35% | 30,3% | 27,7% | 23,0% |
| Prime tre | 19,4% | 17,0% | 13,6% |
| Prime tre, stop 35% | 19,1% | 16,7% | 13,9% |
| LEAPS 35/65 | 13,6% | 11,4% | 6,8% |
| LEAPS 35/65, stop | 25,7% | 23,3% | 18,2% |

## Conclusioni del report

- **Senza stop:** tre titoli sono meglio di uno.
- **Con stop:** il solo vincitore rende circa 9 punti netti in più. Il vantaggio però poggia su 4 stop sul vincitore, tutti utili: sui 22 stop totali, 11 utili e 11 dannosi.
- **LEAPS:** no. Rendono meno dell'azione in tutti gli scenari salvo quello ottimista, dove pareggiano.
- **Fisco:** il nettista perde da 2,8 a 5,1 punti annui rispetto all'AMC lordista. Per l'ETF tenuto in portafoglio lordista e nettista coincidono.
- **Finestre di 10 anni:** le versioni con stop battono l'ETF al netto delle imposte in 10 finestre su 20. Delle finestre iniziate tra il 2000 e il 2009, il vincitore con stop ne perde 9 e le prime tre con stop tutte e 10.
- **Calendario:** gennaio è il mese di partenza più fortunato (dati del paper principale, in EUR e al netto).

## Ancora da verificare [DA VERIFICARE]

- Trattamento fiscale dello specifico AMC, suo costo effettivo e ritenuta USA applicata dentro il certificato.
- Esistenza di LEAPS quotate sui vincitori del periodo 1997-2003.
- Rendimenti di Reebok 2001 e Avaya 2004.

## File (Desktop\januarybuy)

- `GRMS_Report_January_Buy_Annuale.docx` / `.md`
- `results/GRMS_JanuaryBuy_Analisi_Annuale.xlsx`: formule live per Top3, Portafoglio, Lordo e Lordista, con costo AMC nel foglio Parametri
- `results/AN_*.csv`
- `code/annual_study.py` → `build_excel_annuale.py` → `charts_annuale.py` → `report_annuale_tables.py` → `build_report_annuale.py`
- Modello del testo: `paper/annuale.md`
