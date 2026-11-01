"""Tests of the phase 1.3-BIS helpers on cases taken from the data (values rounded as in f13b_riparazioni.csv)."""
from __future__ import annotations

import pytest

from research import indagine_anomalie as ia


def test_repair_choice_reproduces_the_rule_on_pll_1991():
    # registered split 3:2, raw close -28.15%, vendor +7.78%: the rule keeps the x4/3 correction, the smallest in absolute value
    val, how = ia.repair_choice(0.0778094251683068, -0.2815, 0.0)
    assert how == "prezzo corretto x4/3"
    assert val == pytest.approx((1 - 0.2815) * 4 / 3 - 1)


def test_repair_choice_keeps_price_return_on_phantom_adjustment():
    # USB 1997-01-16: close already split-adjusted (-0.70%), vendor adjusted series jumps x3 (+197.9%)
    val, how = ia.repair_choice(1.9791, -0.0070, 0.0)
    assert how == "prezzo + dividendo" and val == pytest.approx(-0.0070)


def test_repair_class_cases():
    assert ia.repair_class(1.9791, -0.0070, -0.0070, 0.0, 3.0)[0] == "riparazione coerente con il frazionamento registrato"
    cls, truth = ia.repair_class(0.0778, -0.0419, -0.2815, 0.0, 1.5)
    assert cls == "riparazione che sostituisce un rendimento coerente con il frazionamento registrato"
    assert truth == pytest.approx(0.0778, abs=1e-4)
    assert ia.repair_class(0.0090, 0.0080, -0.3293, 0.0020, 1.5)[0] == "variazione marginale (< 0,5 punti)"
    # TSS 1996: neither reading of the 2:1 split day is an ordinary move (+31% or -34.5%)
    assert ia.repair_class(0.3099, -0.0176, -0.3451, 0.0, 2.0)[0].startswith("non determinabile")


def test_day_category():
    assert ia.day_category(1.5, "jb:wiki", "jb:wiki", 0.0) == "frazionamento registrato"
    assert ia.day_category(0.0, "jb:tiingo", "jb:tiingo", 0.3474) == "dividendo anomalo (> 5% in un giorno)"
    assert ia.day_category(0.0, "jb:yahoo", "jb:tiingo", 0.0) == "cambio di fonte"
    assert ia.day_category(0.0, "jb:yahoo", "jb:yahoo", 0.0) == "altro"
