// Yahoo Finance daily downloader - run in the browser console on a finance.yahoo.com page.
// Fetches daily OHLC, adjusted close, dividends and splits since 1988 for the symbols below,
// then saves one gzip NDJSON file (one JSON object per symbol) to the Downloads folder.
// Used once for this study (GRMS_YAHOO_batch1.ndjson.gz); kept for future refreshes.
(async () => {
  const syms = ["SPY", "QQQ", "^SP500TR", "^GSPC", "^NDX", "^VIX", "^IRX", "EURUSD=X" /* ...add symbols */];
  const p2 = Math.floor(Date.now() / 1000), out = [], fail = {};
  const queue = syms.slice();
  async function one(sym) {
    for (let attempt = 0; attempt < 4; attempt++) {
      const u = `https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?period1=567993600&period2=${p2}&interval=1d&events=div%7Csplit&includeAdjustedClose=true`;
      const r = await fetch(u, { credentials: "include" });
      if (r.status === 429) { await new Promise(s => setTimeout(s, 5000 * (attempt + 1))); continue; }
      const j = await r.json(), res = j?.chart?.result?.[0];
      if (!res || !res.timestamp) { fail[sym] = j?.chart?.error?.description || ("status " + r.status); return; }
      const q = res.indicators.quote[0], ac = res.indicators.adjclose?.[0]?.adjclose, ev = res.events || {};
      out.push(JSON.stringify({ s: sym, meta: { tz: res.meta.exchangeTimezoneName, cur: res.meta.currency, type: res.meta.instrumentType,
        name: res.meta.longName || res.meta.shortName, first: res.meta.firstTradeDate }, t: res.timestamp, o: q.open, h: q.high,
        l: q.low, c: q.close, v: q.volume, ac: ac, div: ev.dividends || {}, spl: ev.splits || {} }));
      return;
    }
  }
  async function worker() { while (queue.length) { await one(queue.shift()); await new Promise(r => setTimeout(r, 150)); } }
  await Promise.all([worker(), worker(), worker(), worker()]);
  const parts = [JSON.stringify({ tag: "GRMS_YAHOO", fail, fetched: new Date().toISOString() }), ...out].map(s => s + "\n");
  const gz = await new Response(new Blob(parts).stream().pipeThrough(new CompressionStream("gzip"))).blob();
  const a = document.createElement("a"); a.href = URL.createObjectURL(gz); a.download = "GRMS_YAHOO_batch.ndjson.gz"; a.click();
})();
