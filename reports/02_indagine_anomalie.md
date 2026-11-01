# 02 — Indagine sulle anomalie (Fase 1.3-BIS)

| | |
|---|---|
| Progetto | GRMS Partners — ricerca quantitativa indipendente sulla strategia January Buy |
| Repository | `grmspartners/januarystrat`, branch `claude/peaceful-cray-bkvt73`, base `d40acfa` |
| Data | 31-10-2026 (esecuzioni tra le 13:38 e le 13:55 UTC) |
| Autorizzazione | Fase 1.3-BIS: indagine e risoluzione documentale di tre anomalie. Solo nella copia di lavoro; nessun download, nessun backtest, nessuna ottimizzazione, nessuna seconda implementazione, nessuna correzione del codice originale |
| Autore | Claude (assistente di ricerca), su incarico di GRMS Partners |
| Evidenze | `research/indagine_anomalie.py`; `outputs/tables/f13b_*.csv`; `logs/fase_1_3bis/` (comandi, output, hash dei file letti, integrità, revisione); `logs/registro_anomalie.md`; `logs/registro_verifiche.md` (V-301…V-319) |
| Revisione | 31-10-2026, revisione documentale: A-010 separato in baseline, controfattuale e ipotesi di plausibilità; conclusioni per ambito (§5); tracciabilità di ogni conclusione quantitativa (Appendice A, verificata da `logs/fase_1_3bis/revisione/verifica_tracciabilita.py`). Revisione finale pre-commit: script esplorativi esclusi dal commit, script di tracciabilità lasciato in `logs/` (§6) |

**Legenda delle affermazioni:** **[VERIFICATO]** controllato con procedura riproducibile · **[RIPORTATO]** affermato dai materiali originali · **[STIMA]** valore approssimato o calcolato sotto ipotesi · **[IPOTESI]** interpretazione da testare · **[DA CONFERMARE]** serve una fonte non disponibile.

**Classi delle anomalie** (definizioni adottate in questo rapporto):

| Classe | Significato |
|---|---|
| **VERIFICATA** | L'anomalia esiste ed è confermata da dati o codice, ma la causa non è ancora del tutto identificata |
| **SPIEGATA MA NON RISOLTA** | Causa identificata e documentata; l'anomalia resta nel codice o nei dati originali, che per mandato non vengono corretti |
| **RISOLTA** | Causa identificata e nulla da correggere: la discrepanza è un artefatto del controllo oppure un effetto numerico senza conseguenze |
| **NON DETERMINABILE** | Con i dati e i documenti del progetto non si possono stabilire la causa o la correttezza del valore |

**Perimetro.** Nessuna strategia è stata ricalcolata e nessun CAGR prodotto. Dove l'autorizzazione chiede l'impatto su rendimenti di posizioni o di anni, il calcolo è aritmetica su singole posizioni. Ogni valore alternativo è presentato a parte e non sostituisce quelli originali.

---

## Sintesi

| # | Anomalia indagata | Causa | Classe |
|---|---|---|---|
| 1 | Prezzi rettificati ricostruiti diversi dal pannello anche escludendo le riparazioni (132 serie) | `panel._repair_adjustments()` ricostruisce con un prodotto cumulato ogni serie che segnala, anche quando non cambia nessun giorno. Scarto massimo 1,6×10⁻¹⁴ relativo, sul prezzo rettificato e, per costruzione, sui prezzi rettificati derivati; apertura, massimo, minimo e chiusura identici. | **RISOLTA** |
| 2 | Confronto delle serie sintetiche con `patches.py` fallito (3 serie su 9) | Nelle serie con stop `patches.py` moltiplica per 1,0001 anche il prezzo di fine anno di classifica, che è il prezzo d'ingresso. La riga che dovrebbe portare il prezzo sotto il livello (×0,9999) viene sovrascritta. | **SPIEGATA MA NON RISOLTA** |
| 3 | Quattro posizioni con data di stop diversa tra il codice e il mio primo controllo | Il mio primo controllo confrontava minimi grezzi successivi a un frazionamento con un livello calcolato sul prezzo grezzo precedente. Con prezzi coerenti lo stop non scatta, come nel codice. | **RISOLTA** (artefatto del controllo) |

**Risultati nuovi, emersi dall'indagine** (dettagli nelle sezioni 1-2 e in `logs/registro_anomalie.md`):

- **[VERIFICATO] A-010.** La regola di riparazione sceglie sempre il candidato più piccolo in valore assoluto e ignora il rapporto di frazionamento registrato nei dati.
  1. **Classifica della baseline originale [VERIFICATO].** Le riparazioni fanno parte del codice originale e quindi della classifica riprodotta byte per byte. Solo 8 cadono nell'anno di classifica di un titolo classificato, e nessuno di questi è nella top-3: il migliore è 17°.
  2. **Controfattuale, non adottato [VERIFICATO l'aritmetica].** Rimettendo il valore del fornitore al posto di una riparazione (un caso alla volta), la top-3 cambierebbe in un solo caso. US Bancorp, nella classifica 1997 (che decide la detenzione 1998), passerebbe dal 43° posto con +66,4% al **1° posto con +399,2%**, davanti a Dell (+216,2%). Il controfattuale misura soltanto quanto la classifica dipende da quel dato: non prova né un errore né la correttezza della baseline.
  3. **Ipotesi adottata per stimare il valore plausibile [IPOTESI; classi = STIMA].** Di un giorno di frazionamento è plausibile la lettura con un movimento ordinario (sotto il 15%). Con questo criterio le 30 riparazioni si dividono così: 11 correggerebbero una rettifica errata del fornitore, tra cui quella di US Bancorp 1997; 9 sostituirebbero un rendimento del fornitore coerente con il frazionamento registrato; 4 sono marginali; 6 non determinabili. Le 9 riparazioni stimate sostitutive, rimesse al valore del fornitore, non cambierebbero nessuna top-3. Il criterio non è stato verificato su prezzi indipendenti.
- **[VERIFICATO] A-013.** Nella classifica del 2003 la serie sintetica di Dynegy (+262,6%, 3ª) precede PMC-Sierra (+261,5%) di appena lo 0,30%. Quel valore documentale decide la composizione della top-3 del 2004. **[STIMA]** Nello scenario di sensibilità il rendimento delle prime tre nel 2004 cambierebbe di −17,7 punti senza stop e di −14,3 punti con stop.
- **[RIPORTATO] A-012.** Il vincitore del 2001 dipende da una scelta tra fonti in conflitto documentata in `patches.py`: Dynegy +220,2% (TSR del proxy) contro +361% (S&P DJI). Reebok 2001 è "non toccato dallo stop" con un margine del 3,9% **[STIMA]**, calcolato sui valori documentali (minimo 18,50 contro un livello approssimato a ~17,8).

---

## 1. Prezzi rettificati e pannello

### 1.1 Trasformazioni applicate dalla pipeline

Ricostruite dal codice ed eseguite in sola lettura su dati identici al manifesto (`f13b_trasformazioni_pipeline.csv`):

| # | Passo (file, funzione) | Effetto misurato |
|---|---|---|
| 1 | `data_layer.load_jb()`, `load_yahoo()` | Righe dei titoli del pannello: 5.807.722 |
| 2 | Filtro sul calendario delle sedute di `^GSPC` (`build_panel`) | **[VERIFICATO]** 15.131 righe scartate: 14.917 anteriori al 4-1-1988 (inizio del pannello), 2 posteriori al 9-10-2026, 212 in giorni di borsa chiusa. 147 di queste righe hanno un dividendo, tutte anteriori al 1988: **0 dividendi persi nel periodo dello studio** |
| 3 | Eliminazione dei duplicati (titolo, data) | 0 righe |
| 4 | Matrici larghe; riempimento con il valore precedente dentro la vita di ogni titolo; apertura, massimo e minimo mancanti posti uguali alla chiusura | 11.231 celle riempite (Fase 1.3, V-207); nessuna barra incompleta |
| 5 | `Panel._derive()`: Sonat (`SNT-199910`) posta a NaN | 1 serie |
| 6 | `Panel._repair_adjustments()`: segnala i giorni con \|rend. rettificato − rend. chiusura − rend. dividendo\| > 15%, ne riscrive alcuni, **ricostruisce l'intera serie** con un prodotto cumulato ancorato all'ultimo prezzo | 357 giorni su 156 serie segnalati; 30 giorni riscritti su 24 serie |
| 7 | `Panel._derive()`: fattore `a/c`, apertura/massimo/minimo rettificati, rendimento da dividendo | Derivati dal prezzo rettificato del passo 6 |
| 8 | `patches.apply()` | 9 serie sintetiche aggiunte (sezione 2) |

### 1.2 Perché il confronto non coincideva, anche escludendo le riparazioni

`f13b_serie_segnalate.csv`, una riga per ognuna delle 156 serie.

- **[VERIFICATO]** Per le 132 serie segnalate e mai riscritte:
  - apertura, massimo, minimo e chiusura sono identici ai dati grezzi;
  - il prezzo rettificato differisce in 785.845 celle su 805.506, ma di pochissimo: scarto relativo massimo 1,6×10⁻¹⁴ (mediana tra le serie dello scarto massimo: 6,2×10⁻¹⁵), assoluto massimo 8,6×10⁻¹².
- **[VERIFICATO] Causa.** Nel ciclo finale di `_repair_adjustments()` (`for j in sorted({c for _, c in zip(ii, jj)})`) ogni colonna segnalata viene ricostruita come `cumprod(1 + r)` riscalato sull'ultimo prezzo valido, anche se nessun rendimento è cambiato. Moltiplicare migliaia di rendimenti e riscalarli introduce errori di arrotondamento in virgola mobile.
- **[VERIFICATO]** In questi scarti non c'è nessun effetto di dividendi, frazionamenti o fonti: i rendimenti giornalieri usati sono quelli del fornitore, invariati.
- **[VERIFICATO]** Gli output sono comunque identici agli originali byte per byte (Fase 1.3). **[IPOTESI, coerente con quell'identità]** Lo stesso arrotondamento era presente nell'esecuzione originale, che usa lo stesso `panel.py`.

Esempio, Dell il 9-3-1998 (frazionamento 2:1, fonte WIKI):

| Dato | Giorno prima | Giorno del frazionamento |
|---|---|---|
| Chiusura grezza | 138,50 | 63,13 (−54,4%) |
| Prezzo rettificato grezzo (fornitore) | 17,3125 | 15,7825 (−8,8%) |
| Prezzo rettificato nel pannello | 17,3125 | 15,7825 |

La regola segnala il giorno perché la chiusura crolla mentre il prezzo rettificato no. Il valore scelto coincide con quello del fornitore: nessuna riscrittura, solo la ricostruzione aritmetica.

**Classe: RISOLTA.** Causa identificata, nessun effetto sui risultati, nulla da correggere.

### 1.3 Che cosa fa scattare la regola

`f13b_giorni_segnalati.csv`: 357 righe con chiusura grezza, prezzo rettificato grezzo e del pannello nei due giorni, dividendo, frazionamento registrato, fonte, rendimenti, candidato scelto.

| Categoria | Giorni | Fonte |
|---|---|---|
| Frazionamento registrato nei dati grezzi | 356 | Tiingo 242, WIKI 111, Yahoo 3 |
| Dividendo anomalo: American Capital (ACAS), 10-8-2009, dividendo 1,07 su un prezzo di 3,08 (34,7%) | 1 | Tiingo |
| Cambio di fonte | 0 | — |

- **[VERIFICATO]** La regola scatta quasi solo nei giorni di frazionamento delle serie WIKI e Tiingo, dove la chiusura è il prezzo grezzo e non è rettificata per frazionamenti (anomalia A-002).
- **[VERIFICATO]** Il caso ACAS non è riscritto: il valore del fornitore è il più piccolo in valore assoluto. Il dividendo del 34,7% resta però nel campo dividendi. Nello studio annuale quel campo entra nei calcoli solo per i titoli detenuti (`annual_study.stock_year()`, dividendi tassati) e nel controllo della regola di riparazione; ACAS non entra mai nella top-3. **[DA CONFERMARE]** se si tratti di un dividendo in azioni registrato come contante.

### 1.4 Le 30 riparazioni registrate

`f13b_riparazioni.csv`.

- **[VERIFICATO]** La regola riproduce 30 riparazioni su 30 del registro storico.
- **Ipotesi di plausibilità [IPOTESI].** Un giorno di frazionamento si può leggere in due modi: chiusura non rettificata, con rendimento (1 + r_chiusura) × rapporto − 1 + dividendo, oppure chiusura già rettificata, con rendimento r_chiusura + dividendo. L'ipotesi adottata considera plausibile la lettura con un movimento ordinario (sotto il 15%), la più piccola se lo sono entrambe (`indagine_anomalie.repair_class()`). È un criterio, non una prova: non è stato verificato su prezzi indipendenti.
- **Classi che ne derivano [STIMA].**

| Classe stimata | N. | Esempi |
|---|---|---|
| Riparazione coerente con il frazionamento registrato (secondo l'ipotesi il fornitore avrebbe rettificato due volte o in modo incoerente) | 11 | US Bancorp 16-1-1997: fornitore +197,9%, chiusura −0,7%, frazionamento 3:1 → −0,7%. Lo stesso schema in XTO, Pepsi Bottling Group, Green Mountain, AMCC, Hanesbrands |
| Riparazione che sostituisce un rendimento del fornitore coerente con il frazionamento registrato | 9 | PLL 30-12-1991: frazionamento 3:2, chiusura −28,15%, fornitore +7,78% (= 0,7185 × 1,5 − 1) → la regola sceglie il rapporto 4:3, mai registrato: −4,19%. Lo stesso schema in Staples, Apollo, Chesapeake 1996, Citigroup 1996, Vitesse, BroadVision, YRC, DDR |
| Variazione marginale (meno di 0,5 punti) | 4 | Joy Global, People's United, Comcast, Envision |
| Non determinabile (nessuna lettura con un movimento ordinario) | 6 | Total System Services 1996, PMC-Sierra 1995, Dish 2000, Time Warner 2009 (raggruppamento 1:3), DXC 2015 (scorporo), Chesapeake 2020 (raggruppamento 1:200) |

- **[VERIFICATO]** Una riparazione cambia il livello di **tutta la storia precedente** della serie, perché la ricostruzione è ancorata all'ultimo prezzo. Per PLL il prezzo rettificato del 27-12-1991 passa da 15,016 (fornitore) a 16,893 (pannello): +12,5%.
- **[VERIFICATO] Dove cadono le 30 riparazioni.**
  - 3 sono anteriori agli anni di classifica 1996-2025 (PLL 1991, Staples 1995, PMC-Sierra 1995);
  - 19 cadono in un anno di classifica, ma su titoli che quell'anno non sono classificati (non membri dell'S&P 500 a fine anno, o senza prezzo alla data di decisione);
  - 8 cadono nell'anno di classifica di un membro classificato.

**Effetto sulle classifiche: baseline, controfattuale e ipotesi vanno tenuti separati.**

1. **Classifica della baseline originale [VERIFICATO].** Le riparazioni sono parte del codice originale: la classifica della baseline le include, ed è quella riprodotta byte per byte nella Fase 1.3. Nessuno degli 8 titoli classificati toccati da una riparazione è nella top-3; il migliore è 17° (Citigroup 1996). In questo senso nessuna riparazione riguarda un titolo selezionato dalla baseline (`f13b_riparazioni.csv`, colonna `posizione_con_riparazione`).
2. **Controfattuale, non adottato [VERIFICATO l'aritmetica].** Per ciascuno degli 8 casi, uno alla volta, il valore del fornitore è rimesso al posto della riparazione e il titolo è riclassificato (`f13b_riparazioni.csv`, colonne `posizione_con_valore_fornitore` e `rend_anno_con_valore_fornitore`). Il controfattuale dice solo quanto la classifica dipende da quel dato; da solo non indica quale dei due valori sia corretto.

  | Caso (classifica) | Classe stimata | Baseline | Controfattuale | La top-3 cambierebbe? |
  |---|---|---|---|---|
  | US Bancorp, 1997 | coerente con il frazionamento | 43° (+66,4%) | **1° (+399,2%)**, davanti a Dell (+216,2%) | **sì** |
  | Pepsi Bottling Group, 2001 | coerente | 80° (+19,2%) | 6° (+138,4%) | no |
  | US Bancorp, 1999 | coerente | 260° (−29,7%) | 23° (+111,0%) | no |
  | XTO Energy, 2004 | coerente | 125° (+25,0%) | 27° (+56,3%) | no |
  | Citigroup, 1996 | sostitutiva | 17° (+56,6%) | 14° (+67,1%) | no |
  | Hanesbrands, 2015 | coerente | 162° (+9,3%) | 110° (+16,8%) | no |
  | Time Warner, 2009 | non determinabile | 120° (+59,5%) | 383° (+6,4%) | no |
  | Envision, 2016 | marginale | 475° (−18,8%) | 475° (−18,6%) | no |

3. **Ipotesi adottata per stimare il valore plausibile [IPOTESI; lettura = STIMA].**
   - Secondo l'ipotesi di plausibilità descritta sopra, l'unico caso in cui la top-3 cambierebbe riguarda una riparazione stimata **corretta**: il valore del fornitore di US Bancorp (+197,9% in un giorno di frazionamento 3:1 con chiusura a −0,7%) sarebbe una doppia rettifica.
   - **Se l'ipotesi è corretta**, la regola evita un 1° posto dovuto a un errore del dato. Il controfattuale da solo non lo dimostra.
   - Le 9 riparazioni stimate **sostitutive**, cioè quelle che secondo l'ipotesi la regola sbaglierebbe, rimesse al valore del fornitore non cambierebbero nessuna top-3. L'unica in classifica è Citigroup 1996, che passerebbe dal 17° al 14° posto.
   - Senza prezzi da una fonte indipendente l'ipotesi resta tale **[DA CONFERMARE]**.

**Classe di A-010 (regola di riparazione): SPIEGATA MA NON RISOLTA.** La causa è identificata nel codice; la regola non è stata modificata. Nessun effetto sui titoli selezionati dalla baseline. Nel controfattuale la top-3 cambierebbe in un solo caso, relativo a una riparazione che l'ipotesi di plausibilità classifica come corretta. Per 6 riparazioni la correttezza è non determinabile senza una fonte esterna.

### 1.5 Differenze tra fonti

`f13b_cambi_di_fonte.csv`.

- **[VERIFICATO]** In 90 giorni una serie passa da una fonte all'altra (per esempio Tiingo → patch d'archivio, Yahoo → patch Nasdaq). In quei giorni lo scarto controllato dalla regola arriva al massimo al 4,72%, sotto la soglia del 15%, quindi nessun giorno viene segnalato.
- **[VERIFICATO]** Un solo giorno ha un movimento superiore al 10%: Vontier, 9-10-2020, −16,1%, con chiusura e prezzo rettificato concordi. È il periodo del suo scorporo da Fortive **[DA CONFERMARE]**.

---

## 2. `patches.py` e le serie sintetiche

### 2.1 Origine dei valori

`f13b_serie_sintetiche_dettaglio.csv`. Le colonne "documento" sono lette dalla tabella nella docstring di `patches.py` **[RIPORTATO]**.

| Serie | Pos. | Rend. classifica: documento → codice | Rend. detenzione: documento → codice | Stop: documento → codice | Fonti citate |
|---|---|---|---|---|---|
| Sprint PCS 2000 | 2ª | +343,2% → 3,432 | −60,1% → −0,601 | toccato T3-2000 (min. 27,81 contro ~33,3) → 15-9-2000 | DEF 14A 2001 (TSR); 10-K 2000 |
| Nextel 2000 | 3ª | +336,5% → 3,365 | −52,0% → −0,520 | toccato T4-2000 (min. 23,00 contro ~33,5) → 10-11-2000 | DEF 14A 2002; 10-K 2000 |
| Reebok 2001 | **1ª** | +234% (**prezzo**, S&P DJI) → 2,34 | ~−3% (in attesa di verifica secondo l'autore, intervallo −8,6%…−1,4%; **non verificato in modo indipendente**) → −0,031 | non toccato (min. 18,50 contro ~17,8) | S&P DJI; 10-K 2001/2002 |
| Dynegy 2001 | 2ª | +220,2% → 2,202 | −54,2% → −0,542 | toccato T3-2001 (min. 31,27 contro ~36,4) → 17-9-2001 | DEF 14A 2002/2005; 10-K 2001 |
| Providian 2003 | **1ª** | +82,8% → 0,828 | +79,4% → 0,794 | non toccato (min. 5,25 contro ~4,2) | DEF 14A 2004/2005; 10-K 2003 |
| Avaya 2004 | **1ª** | +428% (**prezzo**) → 4,28 | ~+33% (in attesa di verifica secondo l'autore; **non verificato in modo indipendente**) → 0,33 | non toccato (min. 11,95 contro ~8,4) | Forbes / S&P DJI; 10-K |
| Dynegy 2004 | 3ª | +262,6% → 2,626 | +7,9% → 0,079 | non toccato (**minimo di chiusura** 3,46 contro ~2,8) | DEF 14A 2005; 10-K 2004 |
| TXU 2005 | 3ª | +178% (**arrotondato**) → 1,78 | +59,9% (**arrotondato**) → 0,599 | non toccato (min. 30,22 contro ~21,0) | DEF 14A 2006; 10-K 2005 |
| UST 2009 | 2ª | +26,6% (**prezzo**) → 0,266 | ~0% (incasso del 6-1-2009 a 69,50 $) → 0,0 | n.d. | CNN; 8-K Altria |

- **[VERIFICATO]** I valori del codice coincidono con la tabella documentale, salvo gli arrotondamenti dichiarati e l'uso di −3,1% per il "~−3%" di Reebok.
- **[RIPORTATO]** Per Reebok 2001 e Avaya 2004 la docstring di `patches.py` (righe 27 e 30) contrassegna il rendimento di detenzione come ancora da verificare; per Reebok indica anche l'intervallo −8,6%…−1,4%, i cui estremi sono usati negli scenari del §2.6. Il codice usa −3,1% e +33%. **[DA CONFERMARE]** In questa fase nessuno dei due valori è stato verificato su una fonte indipendente.
- **[DA CONFERMARE]** I documenti citati non sono nel progetto. La correttezza dei valori non si può verificare senza scaricarli.
- **[VERIFICATO]** Le date di inizio della composizione (`member_from`) coincidono con il file di composizione per 8 serie su 9. Fa eccezione Dynegy 2004: 2-1-2002 contro 3-10-2000 nel file, senza effetto sulla classifica di fine 2003. Nessun ticker originale di queste società ha prezzi nei dati.

### 2.2 Metodo di ricostruzione (`patches.apply()`)

**[VERIFICATO]**, dal codice e dai valori nel pannello:

1. **Anno di classifica.** Andamento log-lineare da 1 all'ultima seduta dell'anno precedente fino a 1 + rendimento di classifica all'ultima seduta dell'anno.
2. **Anno di detenzione senza stop.** Andamento log-lineare fino a (1 + rendimento di classifica) × (1 + rendimento di detenzione) all'ultima seduta. Per UST, fino alla data d'uscita del 6-1-2009.
3. **Anno di detenzione con stop.**
   - discesa log-lineare fino al 65% del valore iniziale, moltiplicata per 1,0001;
   - una riga pone il giorno dello stop a ×0,9999, ma è sovrascritta (§2.3);
   - risalita log-lineare dal livello fino al valore finale documentato.
4. **Prezzi.** Massimo, minimo e chiusura uguali al prezzo rettificato; apertura uguale alla chiusura del giorno prima; dividendi zero; volume fisso a 1 milione.
5. **Composizione.** Intervallo da `member_from` al giorno dopo l'ultimo prezzo.

### 2.3 Perché il confronto falliva

- **[VERIFICATO] Il fattore 1,0001.** La riga `a[r1:sd + 1] = base * lvl ** (np.arange(k + 1) / k) * 1.0001` parte da `r1`, l'ultima seduta dell'anno di classifica. Moltiplica quindi per 1,0001 anche il valore di fine anno, che è il prezzo d'ingresso: nelle 3 serie con stop il rapporto con il valore documentato è 1,0001, nelle altre 6 è 1. Ne derivano:
  - un rendimento di classifica più alto di 3,2-4,4×10⁻⁴;
  - un rendimento di detenzione senza stop più basso di 4,0-4,8×10⁻⁵;
  - un rendimento con stop esattamente di −35%.
- **[VERIFICATO] La riga ×0,9999 non ha effetto.** `a[sd] = base * lvl * 0.9999` è sovrascritta dalla riga successiva, che inizia proprio da `sd`. Nel giorno dello stop il prezzo vale esattamente base × 0,65.

  Lo stop scatta perché il livello (65% del prezzo d'ingresso gonfiato) è più alto di 1×10⁻⁴: il prezzo del giorno è sotto il livello dello 0,01% in tutte e tre le serie. Senza il fattore 1,0001 scatterebbe solo per uguaglianza esatta in virgola mobile (`low <= livello`); oggi questo vale in tutti e tre i casi, ma è un meccanismo fragile e non documentato (anomalia A-011).

**Classe: SPIEGATA MA NON RISOLTA** (A-001, A-011). Codice non corretto. Effetto trascurabile sui rendimenti; nessun effetto sull'ordine delle classifiche e sugli stop.

### 2.4 Ipotesi non documentate o solo implicite

1. **[RIPORTATO]** Rendimenti di **prezzo** al posto del rendimento totale per Reebok 2000, Avaya 2003 e UST 2008, come indica la docstring, mentre la classifica usa rendimenti totali.
   - **[IPOTESI]** Per Reebok e Avaya l'effetto è nullo se non pagavano dividendi.
   - **[DA CONFERMARE]** UST pagava dividendi; il suo rendimento totale sarebbe più alto del 26,6%.
   - **[IPOTESI]** UST resterebbe 2ª salvo dividendi superiori a 12 punti (la 1ª, Family Dollar, è a +38,6%).
2. **[VERIFICATO]** **Dividendi zero** in tutte le serie. **[RIPORTATO]** Dove il valore documentale è un TSR del proxy (per esempio TXU 2005) il rendimento include i dividendi. **[STIMA]** Effetto solo sulla ripartizione fiscale (dividendi al 37,1% contro plusvalenze al 26%) di posizioni non prime; non misurato.
3. **[VERIFICATO]** **Nessuna oscillazione dentro l'anno** (massimo = minimo = chiusura): lo stop delle serie sintetiche non può avvenire con un'apertura sotto il livello. **[RIPORTATO]** Secondo la docstring, la data dello stop è scelta dentro il trimestre del minimo.
4. **[RIPORTATO]** Lo stop "non toccato" si basa su minimi trimestrali contro livelli approssimati ("~"). Margini tra minimo e livello **[STIMA]**, calcolati come minimo / livello − 1 sui valori della docstring:
   - Reebok **+3,9%** (18,50 / 17,8);
   - Dynegy 2004 +23,6% (3,46 / 2,8), misurato su un **minimo di chiusura**: il minimo intraday può essere più basso;
   - Providian +25,0% (5,25 / 4,2);
   - Avaya +42,3% (11,95 / 8,4);
   - TXU +43,9% (30,22 / 21,0).
5. **[VERIFICATO]** Per le opzioni (LEAPS) le serie sintetiche usano una volatilità proxy: 0,526 (`AN_parametri.json`), la mediana delle volatilità realizzate dei vincitori non sintetici (`annual_study.main()`). Vale per i vincitori del 2001, 2003 e 2004.
6. **[VERIFICATO]** UST 2009 ha rendimento zero per costruzione: ingresso e incasso allo stesso valore. Il prezzo d'apertura effettivo del 2-1-2009 non è nel progetto **[DA CONFERMARE]**.

### 2.5 Impatto potenziale sulle classifiche annuali

`f13b_sintetiche_classifiche.csv` (prime 6 posizioni di ogni anno con serie sintetiche) e margini in `f13b_serie_sintetiche_dettaglio.csv`. Margine = (1 + rend. della serie) / (1 + rend. del confinante) − 1.

| Anno di classifica | Serie | Posizione | Margine su chi segue | Cosa decide |
|---|---|---|---|---|
| 1999 | Sprint PCS | 2ª | +1,53% su Nextel | solo l'ordine tra 2ª e 3ª |
| 1999 | Nextel | 3ª | +12,0% su Oracle (4ª, +289,8%) | la composizione della top-3 |
| 2000 | Reebok | **1ª** | **+4,30% su Dynegy** | **l'identità del vincitore 2001** |
| 2000 | Dynegy | 2ª | +2,44% su EOG | solo l'ordine |
| 2002 | Providian | **1ª** | **+3,70% su Boston Scientific** | **l'identità del vincitore 2003** |
| 2003 | Avaya | 1ª | +44,3% | — |
| 2003 | Dynegy | 3ª | **+0,30% su PMC-Sierra (4ª, +261,5%)** | **la composizione della top-3 2004** |
| 2004 | TXU | 3ª | +40,7% su Valero | — |
| 2008 | UST | 2ª | +0,62% su H&R Block | solo l'ordine (la 4ª, Amgen, è a +24,4%) |

- **[VERIFICATO]** Senza il fattore 1,0001 l'ordine della classifica non cambierebbe in nessun anno.
- **[VERIFICATO]** Tre margini decidono vincitori o composizione e si basano su valori documentali non verificabili nel progetto: Reebok/Dynegy 2000 (4,3%), Providian/Boston Scientific 2002 (3,7%), Dynegy/PMC-Sierra 2003 (0,30%).

### 2.6 Impatto potenziale sui rendimenti e sugli stop

`f13b_sintetiche_scenari_documentali.csv`. **Nessuno di questi valori sostituisce quelli originali.** Ogni riga cambia un solo dato e mostra l'effetto sulla posizione e sul rendimento dell'anno, non sul CAGR.

| Tipo | Scenario | Vincitore, senza stop | Vincitore, con stop | Prime tre, senza stop | Prime tre, con stop |
|---|---|---|---|---|---|
| alternativa documentata | Dynegy 2000 = +361% (S&P DJI) invece di +220,2%: Dynegy 1ª nel 2001 al posto di Reebok | −51,1 punti (2001) | −31,9 punti | 0 (stessi tre titoli) | 0 |
| alternativa documentata | Reebok 2001 = −8,6% (estremo basso dell'intervallo dichiarato) | −5,5 punti | −5,5 punti | −1,83 punti | −1,83 punti |
| alternativa documentata | Reebok 2001 = −1,4% (estremo alto) | +1,7 punti | +1,7 punti | +0,57 punti | +0,57 punti |
| alternativa documentata | Reebok 2001 con stop toccato: basterebbe un'apertura del 2-1-2001 ≥ 18,50 / 0,65 = 28,46 | 0 | **−31,9 punti** | 0 | −10,6 punti |
| **stima di sensibilità (non documentale)** | PMC-Sierra 3ª nel 2003 al posto di Dynegy (margine 0,30%). Esito 2004 con `annual_study.stock_year()`: −45,1% senza stop, stop toccato il 29-4-2004 | 0 | 0 | **−17,7 punti** (2004) | **−14,3 punti** |

- **[RIPORTATO + scenario]** Reebok stop: nella baseline nessuno stop è scattato sul vincitore del 2001. Se l'apertura effettiva fosse stata sopra 28,46, il vincitore con stop avrebbe avuto uno stop **dannoso** in più (−35% invece di −3,1%), da aggiungere ai 4 stop sul vincitore, tutti utili, del periodo 1997-2025. L'apertura effettiva non è nel progetto **[DA CONFERMARE]**.
- **[VERIFICATO]** Gli stop delle 3 serie sintetiche toccate valgono esattamente −35%, indipendentemente dal fattore 1,0001 e dalla data scelta nel trimestre: sono posizioni 2ª e 3ª, senza LEAPS e senza dividendi.

**Classe dei valori documentali (A-012) e del margine Dynegy/PMC-Sierra (A-013): NON DETERMINABILE** senza i documenti SEC e i prezzi giornalieri delle società.

---

## 3. Le quattro posizioni con date di stop diverse

### 3.1 Origine della discrepanza

Nella prima versione dei controlli della Fase 1.3 avevo cercato lo stop confrontando i minimi grezzi (`low`) con il 65% dell'apertura grezza d'ingresso. Le quattro serie vengono da WIKI e Tiingo, dove la chiusura e i minimi grezzi **non sono rettificati per i frazionamenti** (A-002). Dopo un frazionamento 2:1 il prezzo grezzo si dimezza, e il confronto segnalava uno "stop" che non è mai avvenuto. Il codice originale confronta invece prezzi rettificati coerenti (`low × a / c`) con un livello rettificato. Il controllo corretto della Fase 1.3 (base senza dividendi, coerente con i frazionamenti) concorda con il codice.

Dati giornalieri completi di ogni posizione, dal giorno di decisione all'uscita, in `f13b_quattro_posizioni_giornaliero.csv`: prezzi grezzi e rettificati, dividendi, frazionamenti, fonte, livelli e rapporti. Sintesi in `f13b_quattro_posizioni.csv`.

### 3.2 Ricostruzione delle quattro posizioni

**Dell 1998, 1ª posizione (fonte WIKI)**

| Voce | Valore |
|---|---|
| Ingresso | 2-1-1998, apertura grezza 84,81; rettificata 10,6013 |
| Livello di stop | rettificato 6,8908; grezzo sulla base d'ingresso 55,1265 |
| Frazionamenti e dividendi | 2:1 il 9-3-1998 e 2:1 l'8-9-1998 (chiusura −54,4% e −45,3%); nessun dividendo |
| Data contestata | 10-9-1998 |
| Prezzi grezzi del giorno | apertura 54,88; massimo 55,75; minimo 53,00; chiusura 54,75 |
| Prezzi rettificati del giorno | apertura 27,44; massimo 27,875; minimo 26,50; chiusura 27,375 |
| Coerenza del confronto | minimo grezzo × fattore di frazionamento (4) = 212,0: **+284,6%** sul livello grezzo, esattamente come minimo rettificato contro livello rettificato |
| Distanza minima dal livello nell'anno | +44,0% (12-1-1998) |
| Uscita secondo il codice | 31-12-1998, prezzo rettificato 36,595, rendimento +245,20% |
| Uscita secondo il controllo corretto | 31-12-1998, 36,595, +245,20% |
| Primo controllo (artefatto) | 10-9-1998 "in apertura sotto il livello" a 54,88 grezzo: −35,29% |
| Differenza, controllo corretto − codice | posizione 0; vincitore 0; prime tre 0 |
| Differenza, artefatto − codice | posizione −280,5 punti; vincitore 1998 −280,5 punti; prime tre −93,5 punti |

**Dell 1999, 1ª posizione (fonte WIKI)**

| Voce | Valore |
|---|---|
| Ingresso | 4-1-1999, apertura grezza 74,87; rettificata 37,435 |
| Livello di stop | rettificato 24,3328; grezzo sulla base d'ingresso 48,6655 |
| Frazionamenti e dividendi | 2:1 l'8-3-1999 (chiusura −47,3%); nessun dividendo |
| Data contestata | 8-3-1999 (giorno del frazionamento) |
| Prezzi grezzi del giorno | apertura 44,00; massimo 45,50; minimo 43,03; chiusura 45,38 |
| Prezzi rettificati del giorno | uguali ai grezzi: dall'8-3-1999 a fine anno il fattore di rettifica vale 1 e nel 1999 non ci sono dividendi (`f13b_quattro_posizioni_giornaliero.csv`) |
| Coerenza del confronto | minimo × 2 = 86,06: **+76,8%** sul livello; uguale per i prezzi rettificati |
| Distanza minima dal livello nell'anno | +28,9% (2-6-1999) |
| Uscita secondo il codice | 31-12-1999, 51,00, +36,24% |
| Uscita secondo il controllo corretto | 31-12-1999, 51,00, +36,24% |
| Primo controllo (artefatto) | 8-3-1999 a 44,00 grezzo: −41,23% |
| Differenza, controllo corretto − codice | 0 |
| Differenza, artefatto − codice | posizione −77,5 punti; vincitore 1999 −77,5; prime tre −25,8 |

**EMC 1999, 3ª posizione (fonte WIKI)**

| Voce | Valore |
|---|---|
| Ingresso | 4-1-1999, apertura grezza 86,75; rettificata 20,1447 |
| Livello di stop | rettificato 13,0941; grezzo sulla base d'ingresso 56,3875 |
| Frazionamenti e dividendi | 2:1 l'1-6-1999 (chiusura −51,1%); nessun dividendo |
| Data contestata | 1-6-1999 (giorno del frazionamento) |
| Prezzi grezzi del giorno | apertura 50,94; massimo 50,94; minimo 49,00; chiusura 49,06 |
| Prezzi rettificati del giorno | apertura 23,658; massimo 23,658; minimo 22,757; chiusura 22,785 |
| Coerenza del confronto | minimo × 2 = 98,0: **+73,8%** sul livello; uguale per i prezzi rettificati |
| Distanza minima dal livello nell'anno | +49,0% (13-1-1999) |
| Uscita secondo il codice | 31-12-1999, 50,762, +151,99% |
| Uscita secondo il controllo corretto | 31-12-1999, 50,762, +151,99% |
| Primo controllo (artefatto) | 1-6-1999 a 50,94 grezzo: −41,28% |
| Differenza, controllo corretto − codice | 0 |
| Differenza, artefatto − codice | posizione −193,3 punti; vincitore 0 (3ª posizione); prime tre −64,4 |

**Coterra (Cabot Oil & Gas) 2012, 1ª posizione (fonte Tiingo)**

| Voce | Valore |
|---|---|
| Ingresso | 3-1-2012, apertura grezza 78,11; rettificata 14,2039 |
| Livello di stop | rettificato 9,2325; grezzo sulla base d'ingresso 50,7715 |
| Frazionamenti e dividendi | 2:1 il 26-1-2012 (chiusura −51,3%); 4 dividendi (0,17%) |
| Data contestata | 26-1-2012 (giorno del frazionamento) |
| Prezzi grezzi del giorno | apertura 33,35; massimo 33,95; minimo 31,76; chiusura 32,44 |
| Prezzi rettificati del giorno | apertura 12,133; massimo 12,351; minimo 11,554; chiusura 11,801 |
| Coerenza del confronto | minimo × 2 = 63,52: **+25,1%** sul livello (+25,15% con i prezzi rettificati; la differenza sono i dividendi) |
| Distanza minima dal livello nell'anno | +13,6% (16-4-2012) |
| Uscita secondo il codice | 31-12-2012, 18,121, +27,58% |
| Uscita secondo il controllo corretto | 31-12-2012, 18,121, +27,58% |
| Primo controllo (artefatto) | 26-1-2012 a 33,35 grezzo: −57,30% |
| Differenza, controllo corretto − codice | 0 |
| Differenza, artefatto − codice | posizione −84,9 punti; vincitore 2012 −84,9; prime tre −28,3 |

*Gli "artefatti" non sono esiti possibili: confrontano un prezzo successivo al frazionamento con un livello precedente. Sono riportati solo per misurare l'errore che il controllo sbagliato avrebbe introdotto.*

### 3.3 Coerenza del livello di stop con la convenzione di calcolo

- **[VERIFICATO]** In tutti e quattro i casi la discrepanza dipende da un frazionamento. Il minimo grezzo moltiplicato per il fattore di frazionamento cumulato dall'ingresso dà, rispetto al livello, esattamente la stessa distanza del minimo rettificato rispetto al livello rettificato del codice (Coterra: differenza di 0,04 punti dovuta ai dividendi).
- **[VERIFICATO]** Il codice originale confronta prezzi coerenti con la propria convenzione: tutti rettificati, con il fattore `a/c` del giorno stesso.
- **[VERIFICATO]** In nessuno dei quattro anni il prezzo si avvicina al livello: la distanza minima va dal 13,6% al 49,0%.
- **[VERIFICATO]** I 4 stop sul vincitore che determinano il vantaggio della versione con stop (Qualcomm 2000, Nvidia 2002, NOV 2008, Netflix 2011) hanno date identiche nel codice e nei controlli. Sono già ricostruiti in `f13_stop_vincitore_eventi.csv` (Fase 1.3).

**Classe: RISOLTA.** Artefatto del mio controllo; il codice originale è coerente; differenza zero su posizioni e strategie.

---

## 4. Classificazione di tutte le anomalie del registro

| ID | Oggetto | Classe | Motivo |
|---|---|---|---|
| A-001 | Fattore 1,0001 nelle 3 serie sintetiche con stop | SPIEGATA MA NON RISOLTA | causa nel codice (§2.3); effetto trascurabile |
| A-002 | Chiusura non rettificata per frazionamenti nelle serie WIKI e Tiingo | SPIEGATA MA NON RISOLTA | causa nei dati e nella documentazione di `config.py`; il codice originale la gestisce; rischio per codice nuovo |
| A-003 | Ricostruzione delle 156 serie segnalate | RISOLTA | effetto aritmetico (≤ 1,6×10⁻¹⁴), nulla da correggere |
| A-004 | Doppio conteggio nella copertura pubblicata | SPIEGATA MA NON RISOLTA | definizione in `spariti.py` |
| A-005 | Benchmark dalla chiusura, strategia dall'apertura | SPIEGATA MA NON RISOLTA | scelta di metodo documentata; effetto non misurato |
| A-006 | `annual_study.py` non crea `out/` | SPIEGATA MA NON RISOLTA | riproducibilità |
| A-007 | Durata del 2026 fissata a 0,77 | SPIEGATA MA NON RISOLTA | valore fisso |
| A-008 | Scorpori registrati come frazionamenti (BBWI, WDC; anche DXC 2015, riparazione non determinabile) | NON DETERMINABILE | serve l'informazione societaria sugli scorpori |
| A-009 | Nessuna fonte indipendente per i minimi dei 4 stop sul vincitore | NON DETERMINABILE | serve un secondo fornitore |
| A-010 | La regola di riparazione ignora il rapporto registrato (9 sostituzioni stimate, 6 casi indeterminati) | SPIEGATA MA NON RISOLTA | causa nel codice; baseline: nessun titolo selezionato toccato; controfattuale: top-3 cambiata solo per US Bancorp 1997, riparazione corretta secondo l'ipotesi di plausibilità; correttezza dei 6 casi non determinabile |
| A-011 | Riga ×0,9999 sovrascritta; stop sintetico che dipende dal fattore 1,0001 o dall'uguaglianza esatta | SPIEGATA MA NON RISOLTA | causa nel codice; oggi nessun effetto |
| A-012 | Valori documentali delle serie sintetiche (conflitto Dynegy 2000, intervallo Reebok, margine dello stop Reebok, rendimenti di prezzo, arrotondamenti) | NON DETERMINABILE | documenti SEC non disponibili; impatti potenziali in §2.6 |
| A-013 | Margine dello 0,30% tra Dynegy 2003 (sintetica) e PMC-Sierra per la 3ª posizione | NON DETERMINABILE | serve il rendimento totale di Dynegy dell'anno solare 2003 |
| A-014 | `member_from` di Dynegy 2004 diverso dal file di composizione | SPIEGATA MA NON RISOLTA | nessun effetto |

## 5. Conclusioni per ambito

Le conclusioni di questo rapporto riguardano cinque ambiti diversi. Un risultato in un ambito non implica nulla sugli altri.

### 5.1 Riproducibilità della pipeline originale

- **[VERIFICATO]** Con i dati congelati e il codice consegnati, la pipeline originale rigenera esattamente gli output dello studio annuale: 12 file su 12 identici byte per byte, 6.127 celle (Fase 1.3, `f13_confronto_file.csv`).
- **[VERIFICATO]** Le matrici ricostruite dai dati grezzi coincidono con il pannello. Apertura, massimo, minimo e chiusura sono identici; il prezzo rettificato differisce al massimo di 1,6×10⁻¹⁴ per la ricostruzione aritmetica (§1.2).
- **[VERIFICATO]** Gli output di questa indagine sono a loro volta riproducibili: rieseguendo `research/indagine_anomalie.py` in una cartella separata si ottengono gli stessi 10 CSV e lo stesso log, byte per byte (`logs/fase_1_3bis/revisione/riproducibilita.txt`).
- La riproducibilità **non dice** che i dati o il metodo siano corretti: lo stesso errore si riprodurrebbe identico.

### 5.2 Integrità dei dati

- **[VERIFICATO]** Il dataset congelato ha l'hash del manifesto originale. Nel periodo dello studio il filtro del calendario non scarta dividendi e non ci sono duplicati (§1.1). Gli 11.231 giorni riempiti non toccano nessuna delle 90 posizioni (Fase 1.3).
- **[VERIFICATO]** Nelle serie WIKI e Tiingo la chiusura è grezza, non rettificata per i frazionamenti (A-002). La regola di riparazione scatta in 356 giorni di frazionamento e riscrive 30 valori: 9 probabilmente in modo errato **[STIMA]**, 6 con esito non determinabile (A-010).
- **[DA CONFERMARE]** Il dividendo di ACAS del 2009 (34,7%); i valori delle 9 serie sintetiche, basati su documenti non presenti nel progetto (A-012, A-013); i minimi dei 4 stop sul vincitore, senza una seconda fonte (A-009).

### 5.3 Correttezza metodologica

- **[VERIFICATO]** Lo stop del codice originale confronta prezzi coerenti con la propria convenzione. Le quattro date di stop contestate erano un artefatto del mio controllo (§3, RISOLTA).
- **[VERIFICATO]** Restano nel codice e nei dati originali, spiegati ma non corretti per mandato:
  - la regola di riparazione che ignora il rapporto registrato (A-010);
  - la costruzione delle serie sintetiche, con il fattore 1,0001 e la riga ×0,9999 non attiva (A-001, A-011);
  - rendimenti di prezzo e dividendi zero nelle serie sintetiche (A-012);
  - la finestra diversa di benchmark e strategia (A-005);
  - la definizione della copertura (A-004).

### 5.4 Impatto potenziale sulle classifiche

- **Baseline [VERIFICATO].** La baseline è per definizione la classifica prodotta dal codice originale, comprese riparazioni e serie sintetiche. Nessuna delle verifiche di questa fase modifica i titoli selezionati riprodotti.
- **Potenziale [STIMA o RIPORTATO]**, cioè se un dato documentale o una riparazione fossero diversi:
  - il vincitore 2001 dipende dal conflitto tra fonti su Dynegy 2000 (+220,2% contro +361%; margine attuale di Reebok +4,30%);
  - il vincitore 2003 dipende dal valore documentale di Providian (margine +3,70% su Boston Scientific);
  - la composizione della top-3 2004 dipende da Dynegy 2003 (margine +0,30% su PMC-Sierra);
  - nel controfattuale senza la riparazione di US Bancorp 1997, la classifica 1997 avrebbe un altro 1° classificato. Il controfattuale non prova un errore della baseline; secondo l'ipotesi di plausibilità la riparazione è corretta (§1.4) **[IPOTESI]**;
  - le 9 riparazioni stimate sostitutive non cambiano nessuna top-3.

### 5.5 Impatto sul CAGR storico: non misurato

- **Nessun impatto sul CAGR è stato misurato in questa fase.** Gli effetti riportati (§2.6, §3) si fermano al rendimento di una posizione o di un anno.
- Trasformarli in un effetto sul CAGR 1997-2025 richiede di ricalcolare le strategie, cioè un nuovo backtest, non autorizzato. Nessuna cifra di questo rapporto va letta come stima dell'effetto sul CAGR.
- I CAGR della baseline restano quelli originali, riprodotti nella Fase 1.3.

## 6. Integrità ed evidenze

- **[VERIFICATO]** All'inizio della fase (13:38:55): `source_original/` identico al manifesto; copia con 0 file originali modificati.
- **[VERIFICATO]** Alla fine (`logs/fase_1_3bis/integrita.txt`): 20 test superati (11 di integrità, 5 strumenti della Fase 1.3, 4 di questa fase); nessun `__pycache__` in `source_original/`; copia con 38 file aggiunti, 0 modificati, 0 mancanti.
- **[VERIFICATO]** Hash dei 20 file letti in `logs/fase_1_3bis/hash_file_utilizzati.txt`. I moduli della copia hanno lo stesso hash degli originali.
- **[VERIFICATO]** Comandi in `logs/fase_1_3bis/comandi.md`; output completo in `logs/fase_1_3bis/indagine_anomalie.txt`.
- **Script esplorativi esclusi dal commit** (decisione del committente, revisione finale). Non sono riproducibili in modo autonomo: hanno percorsi anonimizzati ed `explore2.py` dipende da un file intermedio non conservato. Restano descritti, con i loro hash, in `comandi.md`; nessun deliverable ne dipende.
- **[VERIFICATO] Revisione documentale.**
  - Lo script dell'indagine, rieseguito in una cartella separata, produce gli stessi 10 CSV e lo stesso log (`logs/fase_1_3bis/revisione/riproducibilita.txt`).
  - Tutte le conclusioni quantitative dell'Appendice A sono state ricalcolate dalle evidenze (`logs/fase_1_3bis/revisione/verifica_tracciabilita.txt`).
  - Al termine, `source_original/` è identico al manifesto.
- **[VERIFICATO] Revisione finale pre-commit** (`logs/fase_1_3bis/revisione/revisione_finale.txt`): test, integrità di `source_original/`, determinismo dello script di tracciabilità e prova da una checkout pulita (vedi Appendice A).

## 7. Limiti

- **Fonti esterne.** I punti NON DETERMINABILE richiedono fonti non presenti nel progetto: documenti SEC, prezzi giornalieri di un secondo fornitore, informazioni sugli scorpori.
- **Classificazione delle riparazioni.** È una stima di plausibilità (soglia del 15% sul movimento giornaliero), non una verifica sui prezzi effettivi.
- **Scenari.** Gli scenari del §2.6 cambiano un solo valore alla volta e si fermano al rendimento dell'anno; non sono stati composti in un CAGR (sarebbe un nuovo backtest).
- **Codice originale.** Non è stato corretto in nessun punto.

## 8. Passi successivi possibili (da autorizzare)

1. **Fonti esterne.** Acquisire i documenti SEC delle serie sintetiche (in particolare Reebok 2000-2001, Dynegy 2000 e 2003, Providian 2002) e un secondo fornitore di prezzi giornalieri per i 4 stop sul vincitore e per i 6 casi di riparazione non determinabili.
2. **Analisi di sensibilità.** Decidere, in una fase autorizzata a nuovi calcoli, se e come misurare l'effetto complessivo di A-005, A-010, A-012 e A-013.
3. **Seconda implementazione.** In una seconda implementazione indipendente, usare i rapporti di frazionamento registrati invece della regola "valore più piccolo".

---

## Appendice A — Tracciabilità delle conclusioni quantitative

Ogni riga indica l'evidenza da cui la conclusione si ricava. I CSV citati senza percorso sono in `outputs/tables/`. `AN_top3_anno.csv` è `source_original/results/AN_top3_anno.csv`, identico byte per byte alla copia riprodotta `work/replica_originale/out/AN_top3_anno.csv` (stesso SHA-256 `516ea88b…` in `logs/fase_1_3bis/hash_file_utilizzati.txt`). Le etichette seguono la legenda iniziale.

**Verifica automatica e suoi limiti.**
- Lo script `logs/fase_1_3bis/revisione/verifica_tracciabilita.py` ricalcola ogni valore da queste evidenze e lo confronta con il testo; l'esito (232 affermazioni, 0 discordanze) è in `logs/fase_1_3bis/revisione/verifica_tracciabilita.txt`.
- Lo script è deterministico e non usa percorsi assoluti.
- **Non è eseguibile da una checkout pulita**: legge `AN_top3_anno.csv` dalla copia di lavoro `work/`, esclusa da Git (`revisione_finale.txt`). Per questo resta in `logs/` e non in `research/`.
- Segnala le discrepanze nel testo stampato, ma il codice di uscita è sempre 0.
- Nel file di evidenza i valori inferiori a 10⁻⁶ compaiono come `0.0` per la formattazione della stampa; il confronto è comunque numerico, con tolleranza.

| § | Conclusione | Valore | Evidenza (file, colonna, funzione o log) | Etichetta |
|---|---|---|---|---|
| 1.1 | Righe dei titoli del pannello; righe scartate dal calendario | 5.807.722; 15.131 (14.917 prima del 1988, 2 dopo l'ultimo giorno, 212 in giorni di borsa chiusa) | `f13b_trasformazioni_pipeline.csv`; ricostruzione di `data_layer.build_panel()` in `indagine_anomalie.pipeline_raw()` | VERIFICATO |
| 1.1 | Dividendi scartati; duplicati | 147, nessuno nel periodo dello studio; 0 | `f13b_trasformazioni_pipeline.csv` | VERIFICATO |
| 1.1 | Celle riempite col valore precedente | 11.231 | `f13_ffill_per_anno.csv`; `logs/fase_1_0/replica_data_layer.txt` | VERIFICATO |
| 1.1 | Giorni e serie segnalati; riparazioni | 357 su 156; 30 su 24 | `f13b_giorni_segnalati.csv`; `f13b_serie_segnalate.csv` | VERIFICATO |
| 1.2 | Serie senza riparazioni con OHLC identici | 132 | `f13b_serie_segnalate.csv` (`riparazioni_registrate` = 0, `open_high_low_close_identici`) | VERIFICATO |
| 1.2 | Celle del prezzo rettificato diverse; scarti | 785.845 su 805.506; massimo 1,6e-14, mediana 6,2e-15, assoluto 8,6e-12 | `f13b_serie_segnalate.csv` (`celle_adj_diverse`, `celle_adj_vita`, `max_diff_*`) | VERIFICATO |
| 1.2 | Causa: ricostruzione con prodotto cumulato | — | `panel._repair_adjustments()` (lettura del codice) | VERIFICATO (codice) |
| 1.2 | Stesso arrotondamento nell'esecuzione originale | — | coerente con l'identità dei byte (`f13_confronto_file.csv`) | IPOTESI |
| 1.2 | Esempio Dell 9-3-1998 | 138,50 → 63,13; 17,3125 → 15,7825 | `f13b_giorni_segnalati.csv` | VERIFICATO |
| 1.3 | Frazionamenti registrati per fonte | 356 = Tiingo 242 + WIKI 111 + Yahoo 3 | `f13b_giorni_segnalati.csv` (`categoria`, `fonte`) | VERIFICATO |
| 1.3 | Dividendo ACAS 10-8-2009 | 1,07 su 3,08 (34,7%); non riscritto; fuori dalla top-3 | `f13b_giorni_segnalati.csv`; `AN_top3_anno.csv` | VERIFICATO (natura del dividendo DA CONFERMARE) |
| 1.4 | Riparazioni riprodotte dalla regola | 30/30 | `f13b_riparazioni.csv` (`coincide_con_log_storico`); registro storico nel workbook originale | VERIFICATO |
| 1.4 | Criterio di plausibilità (movimento ordinario sotto il 15%) | — | `indagine_anomalie.repair_class()` (`PLAUSIBLE = 0.15`) | IPOTESI |
| 1.4 | Classi delle riparazioni | 11 coerenti, 9 sostitutive, 4 marginali, 6 non determinabili | `f13b_riparazioni.csv` (`classe_riparazione_stimata`); `indagine_anomalie.repair_class()` | STIMA |
| 1.4 | US Bancorp 16-1-1997; PLL 30-12-1991 | +197,9% / −0,7% / 3:1; +7,78% → −4,19% (×4/3) con frazionamento 3:2 | `f13b_riparazioni.csv` | VERIFICATO |
| 1.4 | Effetto di una riparazione sulla storia precedente (PLL) | +12,5% | `f13b_giorni_segnalati.csv` (`adj_grezzo_prima`, `adj_pannello_prima`) | VERIFICATO |
| 1.4 | Dove cadono le riparazioni | 3 prima del 1996, 19 su titoli non classificati, 8 su titoli classificati | `f13b_riparazioni.csv` (`anno_classifica`, `classificato`) | VERIFICATO |
| 1.4 | Baseline: nessun titolo della top-3 toccato | migliore 17° (Citigroup 1996) | `f13b_riparazioni.csv` (`posizione_con_riparazione`) | VERIFICATO |
| 1.4 | Controfattuale: le 8 riclassificazioni | US Bancorp 1997 43° → 1° (+66,4% → +399,2%); altri 7 casi fuori dalla top-3 | `f13b_riparazioni.csv` (`posizione_con_valore_fornitore`, `rend_anno_con_valore_fornitore`); Dell +216,2% da `AN_top3_anno.csv` | VERIFICATO (aritmetica) |
| 1.4 | Lettura del controfattuale (riparazione di US Bancorp corretta; 9 sostitutive senza effetto sulla top-3) | — | `f13b_riparazioni.csv` (`classe_riparazione_stimata`, `posizione_con_valore_fornitore`) | IPOTESI / STIMA |
| 1.5 | Cambi di fonte | 90 giorni; scarto massimo 4,72%; Vontier −16,1% | `f13b_cambi_di_fonte.csv` | VERIFICATO (scorporo di Vontier DA CONFERMARE) |
| 2.1 | Valori delle serie sintetiche: documento e codice | tabella §2.1 | docstring di `patches.py`; `f13b_serie_sintetiche_dettaglio.csv` (`doc_*`, `codice_*`) | RIPORTATO (documento); VERIFICATO (corrispondenza) |
| 2.1 | `member_from` uguale al file di composizione | 8/9 (eccezione Dynegy 2004) | `f13b_serie_sintetiche_dettaglio.csv` (`member_from_uguale_al_file`) | VERIFICATO |
| 2.3 | Fattore 1,0001 sul prezzo d'ingresso; scarti dei rendimenti; stop a −35% | 3 serie; +3,2…4,4e-4; −4,0…−4,8e-5 | `f13b_serie_sintetiche_dettaglio.csv`; `f13_serie_sintetiche.csv` (Fase 1.3); `AN_top3_anno.csv` | VERIFICATO |
| 2.3 | Riga ×0,9999 non attiva; prezzo nel giorno di stop | 0/3; base × 0,65, −1e-4 sul livello; stop anche per uguaglianza 3/3 | `f13b_serie_sintetiche_dettaglio.csv` (`riga_0_9999_attiva`, `a_giorno_stop_su_*`, `stop_scatterebbe_senza_fattore_1_0001`) | VERIFICATO |
| 2.4 | Dividendi zero; massimo = minimo = chiusura; apertura = chiusura precedente | 9/9 | `f13b_serie_sintetiche_dettaglio.csv` | VERIFICATO |
| 2.4 | Margini minimo/livello degli stop "non toccati" | 3,9%; 23,6%; 25,0%; 42,3%; 43,9% | docstring di `patches.py` (colonna `doc_stop`) + aritmetica | STIMA |
| 2.4 | Volatilità proxy delle serie sintetiche | 0,526 | `source_original/results/AN_parametri.json`; `annual_study.main()` | VERIFICATO |
| 2.4 | UST resterebbe 2ª con il rendimento totale | salvo dividendi > 12 punti | `f13b_sintetiche_classifiche.csv` (Family Dollar +38,6%) | IPOTESI |
| 2.5 | Margini e confinanti delle serie sintetiche | tabella §2.5 | `f13b_serie_sintetiche_dettaglio.csv` (`margine_*`, `quarto_classificato`); `f13b_sintetiche_classifiche.csv` | VERIFICATO |
| 2.5 | Ordine invariato senza 1,0001 | 9/9 | `f13b_serie_sintetiche_dettaglio.csv` (`ordine_invariato_senza_1_0001`) | VERIFICATO |
| 2.6 | Scenari su Dynegy 2000 e Reebok 2001 | tabella §2.6 | `f13b_sintetiche_scenari_documentali.csv` | RIPORTATO (valori alternativi); VERIFICATO (aritmetica) |
| 2.6 | Scenario PMC-Sierra 2004 | −45,1%; stop il 29-4-2004; −17,7 / −14,3 punti sulle prime tre | `f13b_sintetiche_scenari_documentali.csv`; `annual_study.stock_year()` | STIMA |
| 2.6 | Stop sul vincitore 1997-2025 | 4, tutti utili | `AN_top3_anno.csv` | VERIFICATO |
| 3 | Valori delle quattro posizioni (ingresso, livelli, prezzi del giorno contestato, uscite, differenze) | tabelle §3.2 | `f13b_quattro_posizioni.csv`; `f13b_quattro_posizioni_giornaliero.csv` | VERIFICATO |
| 3 | Stessa distanza dal livello con prezzi grezzi coerenti e rettificati | uguali; Coterra +0,04 punti (dividendi) | `f13b_quattro_posizioni.csv` (`low_coerente_su_livello`, `low_rett_su_livello_rett`) | VERIFICATO |
| 3 | Date identiche dei 4 stop sul vincitore | 4/4 | `f13_stop_vincitore_eventi.csv` (Fase 1.3) | VERIFICATO |
| 5.1 | Riproducibilità degli output di questa indagine | 10 CSV + log identici | `logs/fase_1_3bis/revisione/riproducibilita.txt` | VERIFICATO |
| 6 | Test superati; hash registrati | 20; 20 file | `logs/fase_1_3bis/integrita.txt`; `logs/fase_1_3bis/hash_file_utilizzati.txt` | VERIFICATO |
| 5.5 | Impatto sul CAGR storico | non misurato | — | — |
