"""
source_original/ must stay byte-identical to the snapshot of the initial commit.

Any modified, deleted or added file under source_original/ fails these tests,
including files that Git ignores (a reassembled jb_prices.parquet, __pycache__,
out/). The detector itself is tested on a temporary tree, so a broken check
cannot pass silently.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess

import pytest

from research import integrity

BASELINE = json.loads((integrity.REPO / "tests" / "fixtures" / "source_original_baseline.json").read_text())


@pytest.fixture(scope="module")
def expected():
    return integrity.read_manifest(integrity.MANIFEST)


@pytest.fixture(scope="module")
def diff(expected):
    return integrity.compare(expected, integrity.scan(integrity.PROTECTED))


# --------------------------------------------------------------- the real tree
def test_manifest_is_the_recorded_one(expected):
    assert hashlib.sha256(integrity.MANIFEST.read_bytes()).hexdigest() == BASELINE["manifest_sha256"]
    assert len(expected) == BASELINE["n_files"]


def test_no_original_file_modified(diff):
    assert diff.modified == [], "modified in source_original/:\n" + "\n".join(diff.modified)


def test_no_original_file_deleted(diff):
    assert diff.missing == [], "deleted from source_original/:\n" + "\n".join(diff.missing)


def test_no_file_added(diff):
    assert diff.added == [], "added to source_original/:\n" + "\n".join(diff.added)


def _git(*args):
    return subprocess.run(["git", "-C", str(integrity.REPO), *args], capture_output=True, text=True)


def _git_blob_sha1(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def test_tree_matches_baseline_commit():
    """Anchors the manifest to Git: the files on disk have the same blobs as in the baseline commit."""
    if shutil.which("git") is None:
        pytest.skip("git not available")
    commit = BASELINE["baseline_commit"]
    if _git("cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
        pytest.skip(f"baseline commit {commit} not in this clone")
    ls = _git("ls-tree", "-r", commit, "--", "source_original")
    assert ls.returncode == 0, ls.stderr
    in_commit = {}
    for line in ls.stdout.splitlines():
        meta, path = line.split("\t", 1)
        in_commit[path.removeprefix("source_original/")] = meta.split()[2]
    on_disk = {rel: _git_blob_sha1(integrity.PROTECTED / rel) for rel in integrity.scan(integrity.PROTECTED)}
    assert on_disk == in_commit


# ------------------------------------------------------------ the detector
@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "orig"
    (root / "code").mkdir(parents=True)
    (root / "data.csv").write_text("anno,rend\n1997,0.1\n")
    (root / "code" / "x.py").write_text("print(1)\n")
    return root


def test_detector_passes_identical_tree(tree):
    assert integrity.compare(integrity.scan(tree), integrity.scan(tree)).ok


def test_detector_flags_modification(tree):
    before = integrity.scan(tree)
    (tree / "data.csv").write_text("anno,rend\n1997,0.2\n")
    d = integrity.compare(before, integrity.scan(tree))
    assert (d.modified, d.missing, d.added, d.ok) == (["data.csv"], [], [], False)


def test_detector_flags_deletion(tree):
    before = integrity.scan(tree)
    (tree / "code" / "x.py").unlink()
    d = integrity.compare(before, integrity.scan(tree))
    assert (d.modified, d.missing, d.added, d.ok) == ([], ["code/x.py"], [], False)


def test_detector_flags_additions_ignored_by_git(tree):
    before = integrity.scan(tree)
    (tree / "code" / "__pycache__").mkdir()
    (tree / "code" / "__pycache__" / "x.cpython-313.pyc").write_bytes(b"\0")
    (tree / ".hidden").write_text("x")
    d = integrity.compare(before, integrity.scan(tree))
    assert (d.added, d.ok) == ([".hidden", "code/__pycache__/x.cpython-313.pyc"], False)


def test_manifest_roundtrip_and_no_overwrite(tree, tmp_path):
    m = tmp_path / "m.sha256"
    integrity.write_manifest(integrity.scan(tree), m)
    assert integrity.read_manifest(m) == integrity.scan(tree)
    with pytest.raises(FileExistsError):
        integrity.write_manifest({}, m)


def test_cli_exit_codes(tree, tmp_path):
    m = tmp_path / "m.sha256"
    assert integrity.main(["generate", "--root", str(tree), "--out", str(m)]) == 0
    assert integrity.main(["verify", "--root", str(tree), "--manifest", str(m), "--quiet"]) == 0
    (tree / "new.txt").write_text("x")
    assert integrity.main(["verify", "--root", str(tree), "--manifest", str(m), "--quiet"]) == 1
    assert integrity.main(["verify", "--root", str(tree), "--manifest", str(tmp_path / "none")]) == 2
