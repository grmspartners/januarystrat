"""
SHA-256 integrity check of source_original/ (immutable historical snapshot).

The manifest tests/fixtures/source_original.sha256 lists every file under
source_original/ with its SHA-256, in `sha256sum` format, with paths relative
to source_original/ (so the same manifest also checks a copy of the tree,
e.g. work/replica_originale). It was generated once from the tree of the
initial commit 20b2ef1 (see tests/fixtures/source_original_baseline.json).

Every file is scanned, including files that Git ignores (a reassembled
jb_prices.parquet, __pycache__, out/): a modified, deleted or added file is
reported as a difference.

Usage, from the repository root (standard library only, no venv needed):

    python3 -m research.integrity verify
    python3 -m research.integrity verify --root work/replica_originale
    python3 -m research.integrity generate --out FILE    # never overwrites FILE

Exit codes: 0 identical, 1 differences found, 2 usage error or missing manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROTECTED = REPO / "source_original"
MANIFEST = REPO / "tests" / "fixtures" / "source_original.sha256"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(root: Path) -> dict[str, str]:
    """{relative posix path: sha256} for every file under root, hidden files included.
    A symbolic link is recorded by its target, never followed."""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(root)
    out = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        names = filenames + [d for d in dirnames if os.path.islink(os.path.join(dirpath, d))]
        for name in names:
            p = Path(dirpath) / name
            rel = p.relative_to(root).as_posix()
            out[rel] = "symlink:" + os.readlink(p) if p.is_symlink() else sha256_file(p)
    return out


def read_manifest(path: Path) -> dict[str, str]:
    entries = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(" ", 1)
        rel = rel[1:] if rel[:1] in (" ", "*") else rel
        entries[rel] = digest
    return entries


def write_manifest(entries: dict[str, str], path: Path) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists: a manifest is never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for rel in sorted(entries):
            f.write(f"{entries[rel]}  {rel}\n")


@dataclass
class Diff:
    modified: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.modified or self.missing or self.added)

    def report(self) -> str:
        lines = []
        for label, items in (("MODIFIED", self.modified), ("MISSING", self.missing), ("ADDED", self.added)):
            lines += [f"{label:9s} {rel}" for rel in items]
        return "\n".join(lines)


def compare(expected: dict[str, str], actual: dict[str, str]) -> Diff:
    return Diff(modified=sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k]),
                missing=sorted(expected.keys() - actual.keys()),
                added=sorted(actual.keys() - expected.keys()))


def verify(root: Path = PROTECTED, manifest: Path = MANIFEST) -> Diff:
    return compare(read_manifest(manifest), scan(root))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m research.integrity", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="compare a tree with the manifest")
    v.add_argument("--root", type=Path, default=PROTECTED)
    v.add_argument("--manifest", type=Path, default=MANIFEST)
    v.add_argument("--quiet", action="store_true", help="print only the differences")
    g = sub.add_parser("generate", help="write a new manifest of a tree (refuses to overwrite)")
    g.add_argument("--root", type=Path, default=PROTECTED)
    g.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    if args.cmd == "generate":
        entries = scan(args.root)
        write_manifest(entries, args.out)
        print(f"{len(entries)} files -> {args.out}")
        return 0
    if not args.manifest.exists():
        print(f"manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    diff = verify(args.root, args.manifest)
    if diff.ok:
        if not args.quiet:
            print(f"OK: {args.root} is identical to {args.manifest} ({len(read_manifest(args.manifest))} files)")
        return 0
    print(f"INTEGRITY FAILURE: {args.root} differs from {args.manifest}", file=sys.stderr)
    print(diff.report(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
