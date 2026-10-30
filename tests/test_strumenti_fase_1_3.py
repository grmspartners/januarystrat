"""Tests of the phase 1.3 tools that do not need the working copy."""
from __future__ import annotations

import pytest

from research import confronto_baseline as cb
from research import replica_originale as ro


def test_classify_identical_text():
    assert cb.classify("0.1", "0.1")[0] == "identico"
    assert cb.classify("", "")[0] == "identico"
    assert cb.classify("QCOM", "QCOM")[0] == "identico"


def test_classify_numeric_noise_and_real_difference():
    assert cb.classify("0.30000000000000004", "0.3")[0] == "entro_tolleranza"
    cls, d, r = cb.classify("0.3", "0.31")
    assert cls == "diverso" and d == pytest.approx(0.01) and r == pytest.approx(0.01 / 0.31)


def test_classify_text_difference():
    assert cb.classify("2000-01-26", "2000-01-27")[0] == "diverso"
    assert cb.classify("True", "False")[0] == "diverso"


def test_runner_refuses_scripts_not_authorised(capsys):
    with pytest.raises(SystemExit) as exc:
        ro.main(["run", "experiments.py"])
    assert "not authorised" in str(exc.value)
    assert ro.RUN_ALLOWED == ["annual_study.py", "report_annuale_tables.py"]


def test_module_constants_reads_without_executing(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("import sys\nSTOP = 0.35\nFIRST, LAST = 1996, 2025\nlower = 1\nsys.exit('executed')\n")
    assert ro.module_constants(f) == {"STOP": 0.35, "FIRST": 1996, "LAST": 2025}
