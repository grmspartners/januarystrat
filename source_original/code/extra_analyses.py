"""
Extra analyses used in the thesis:
  G5  rebalance-timing luck on both samples + 12-tranche staggered portfolios
  E9  factor regressions (CAPM and Fama-French 3 + Momentum, monthly, HAC errors)
  NDX buy & hold over the long sample (reference)
"""
from __future__ import annotations

import zipfile

import numpy as np
import pandas as pd
import statsmodels.api as sm

import patches
from config import FF_DIR, OUT
from experiments import B, END, GROSS, NET_IT, S
from experiments2 import PROTOCOLS
from metrics import summary
from panel import Panel

def ff_monthly(path, skip_marker):
    z=zipfile.ZipFile(path); name=z.namelist()[0]; txt=z.read(name).decode("latin1").splitlines()
    rows=[]; started=False
    for line in txt:
        parts=[x.strip() for x in line.split(",")]
        if len(parts)>1 and parts[0].isdigit() and len(parts[0])==6:
            rows.append(parts); started=True
        elif started and (not parts[0] or not parts[0].isdigit()): break
    return rows


def ff_factors() -> pd.DataFrame:
    """Kenneth French monthly factors: MKT_RF, SMB, HML, RF and UMD (momentum)."""
    f = ff_monthly(FF_DIR / "FF_Research_Factors_monthly.zip", None)
    ff = pd.DataFrame(f, columns=["ym", "MKT_RF", "SMB", "HML", "RF"]).set_index("ym").astype(float) / 100
    m = ff_monthly(FF_DIR / "FF_Momentum_Factor_monthly.zip", None)
    mom = pd.DataFrame(m, columns=["ym", "UMD"]).set_index("ym").astype(float) / 100
    F = ff.join(mom, how="inner")
    F.index = pd.PeriodIndex([f"{x[:4]}-{x[4:]}" for x in F.index], freq="M")
    return F


def main():
    pp = patches.apply(Panel.load())
    p = pp
    F = ff_factors()

    rows=[]; tr={}
    for sname,fy,P in [("core",2009,p),("long",1997,pp)]:
        b=B(p,"SPX",fy,"bh",currency="EUR",end=END); bs=summary(b["equity"],None,b["final_after_liq"],100)
        for name in ["P0 thread: top1 stop35 cash","P1 top1 no stop","P2 top3 no stop","P3 top3 stop35","P4 top3 regime","P5 top1 stop35 regime","P7 top3 keep-winners regime"]:
            kw=PROTOCOLS[name]; eqs=[]; afters=[]
            for m in range(1,13):
                r=S(P, universe="SPX", first_year=fy, first_month=m, currency="EUR", end=END, **NET_IT, **kw)
                s=summary(r["equity"],None,r["final_after_liq"],100)
                rows.append(dict(sample=sname, protocol=name, m=m, cagr=s["cagr_after_liq"], dd=s["max_dd"]))
                eqs.append(r["equity"]); afters.append(r["final_after_liq"])
            # tranche portfolio: 12 sleeves of 100/12 each; sleeves start investing at their first month (cash before -> T-bill ignored: count as flat)
            idx=sorted(set().union(*[e.index for e in eqs]))
            M=pd.DataFrame({i:e.reindex(idx) for i,e in enumerate(eqs)})
            M=M.bfill().ffill()   # before a sleeve starts, it holds its initial 100 (cash, no interest: conservative)
            port=M.mean(axis=1)
            s=summary(port,None,float(np.mean(afters)),100)
            tr[(sname,name)]=port
            rows.append(dict(sample=sname, protocol=name, m="12 tranches", cagr=s["cagr_after_liq"], dd=s["max_dd"], bench=bs["cagr_after_liq"], bench_dd=bs["max_dd"]))
    df=pd.DataFrame(rows); df.to_csv(OUT / "G5_timing_luck_tranches.csv",index=False)
    pd.to_pickle(tr,OUT / "G5_tranche_curves.pkl")
    x=df[df.m!="12 tranches"].groupby(["sample","protocol"]).agg(jan=("cagr",lambda v:v.iloc[0]),med=("cagr","median"),mn=("cagr","min"),mx=("cagr","max"),dd_med=("dd","median"))
    y=df[df.m=="12 tranches"].set_index(["sample","protocol"])[["cagr","dd","bench","bench_dd"]]
    print(x.join(y).round(3).to_string())
    
    out=[]
    for sname,fy,P in [("core 2009-2026YTD",2009,pp),("long 1997-2026YTD",1997,pp)]:
        for name in ["P0 thread: top1 stop35 cash","P1 top1 no stop","P2 top3 no stop","P4 top3 regime","P7 top3 keep-winners regime"]:
            r=S(P, universe="SPX", first_year=fy, currency="USD", end=END, **GROSS, **PROTOCOLS[name])
            eq=r["equity"]; mr=eq.resample("ME").last().pct_change().dropna(); mr.index=mr.index.to_period("M")
            df=pd.DataFrame({"r":mr}).join(F,how="inner")
            y=df.r-df.RF; X=sm.add_constant(df[["MKT_RF","SMB","HML","UMD"]])
            res=sm.OLS(y,X).fit(cov_type="HAC",cov_kwds={"maxlags":12})
            X1=sm.add_constant(df[["MKT_RF"]]); res1=sm.OLS(y,X1).fit(cov_type="HAC",cov_kwds={"maxlags":12})
            out.append(dict(sample=sname, protocol=name, months=len(df), capm_alpha_ann=res1.params["const"]*12, capm_t=res1.tvalues["const"], beta=res1.params["MKT_RF"],
                            ff4_alpha_ann=res.params["const"]*12, ff4_t=res.tvalues["const"], b_mkt=res.params["MKT_RF"], b_smb=res.params["SMB"], b_hml=res.params["HML"], b_umd=res.params["UMD"], r2=res.rsquared))
    o=pd.DataFrame(out); o.to_csv(OUT / "E_factor_regressions.csv",index=False); print(o.round(3).to_string())
    b=B(p,"NDX",1997,"bh",currency="EUR",end=END); print("NDX long bh", summary(b["equity"],None,b["final_after_liq"],100)["cagr_after_liq"], summary(b["equity"],None,b["final_after_liq"],100)["max_dd"], b["final_after_liq"])


if __name__ == "__main__":
    main()
