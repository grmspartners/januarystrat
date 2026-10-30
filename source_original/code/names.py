"""Company names for ticker labels (Wikipedia S&P 500 list, Yahoo metadata, manual map for delisted names)."""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

import patches
from config import WIKI_SP500, YAHOO_META

MANUAL = {
    "DELL-201310": "Dell (1988-2013)", "FDO-201507": "Family Dollar Stores", "XL-201809": "XL Capital / XL Group",
    "ESRX-201812": "Express Scripts", "PMCS-201601": "PMC-Sierra", "EMC-201609": "EMC Corp.",
    "FWLT-201412": "Foster Wheeler", "SNDK-201605": "SanDisk (1995-2016)",
    "ATI": "ATI Inc. (Allegheny Technologies)", "NOV": "NOV Inc. (National Oilwell Varco)",
    "CTRA": "Coterra Energy (ex Cabot Oil & Gas)", "AABA": "Altaba (ex Yahoo!)", "ALTR-201512": "Altera",
    "RDC": "Rowan Companies", "NAV": "Navistar International", "ODP": "Office Depot (ODP Corp.)",
    "JCP": "J.C. Penney", "S-202004": "Sprint Nextel / Sprint Corp.", "ATVI": "Activision Blizzard",
    "ABMD": "Abiomed", "MRO": "Marathon Oil", "HES": "Hess Corporation", "CELG": "Celgene",
    "ALXN": "Alexion Pharmaceuticals", "TEX": "Terex", "HRB": "H&R Block", "THC": "Tenet Healthcare",
    "WHR": "Whirlpool", "ETSY": "Etsy", "BBWI": "Bath & Body Works (ex L Brands)",
    "AN-199812": "Amoco", "APOL-201702": "Apollo Group", "BEAM-201404": "Beam Inc. (ex Fortune Brands)",
    "CTXS": "Citrix Systems", "DISH": "DISH Network", "IAC": "IAC", "LLTC-201703": "Linear Technology",
    "BE": "Bloom Energy", "MDP": "Meredith Corp.", "PBY-201602": "Pep Boys", "PETM-201503": "PetSmart", "RAD": "Rite Aid",
}


@lru_cache(maxsize=1)
def name_map() -> dict:
    names = {}
    wiki = pd.read_csv(WIKI_SP500)
    names.update(dict(zip(wiki.Symbol.str.replace(".", "-", regex=False), wiki.Security)))
    ym = json.load(open(YAHOO_META))
    names.update({"Y_" + k: v.get("name") for k, v in ym.items()})
    names.update({k: v.get("name") for k, v in ym.items() if k not in names})
    names.update(MANUAL)
    names.update({pt["label"]: pt["name"] + " (serie ricostruita)" for pt in patches.PATCHES})
    return names


def company(label: str) -> str:
    n = name_map()
    if label in n and n[label]:
        return n[label]
    base = label.split("-")[0] if label[-7:-6] == "-" else label
    return n.get(base, "") or ""


def clean(label: str) -> str:
    return label.replace("Y_", "")
