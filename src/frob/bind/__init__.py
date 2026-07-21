from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from frob.excludes import iter_files


# frob:doc docs/modules/bind.md#public-api
@dataclass
class BindingDecl:
    file: str
    line: int
    signature: str
    kind: str  # "pybind11" | "pyo3"


# frob:doc docs/modules/bind.md#public-api
@dataclass
class SourceDecl:
    file: str
    line: int
    signature: str
    kind: str  # "cpp_header" | "cpp_impl" | "rust"


# frob:doc docs/modules/bind.md#public-api
@dataclass
class Mismatch:
    binding: BindingDecl
    issue: str


# frob:doc docs/modules/bind.md#public-api
def scan_bindings(root: Path) -> list[BindingDecl]:
    """Scan a project root for // BIND: comments in .cpp and .rs files."""
    results = []
    for path in iter_files(root, suffix=".cpp"):
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            m = re.search(r"//\s*BIND:\s*(.+)", line)
            if m:
                results.append(
                    BindingDecl(str(path), i, m.group(1).strip(), "pybind11")
                )
    for path in iter_files(root, suffix=".rs"):
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            m = re.search(r"//\s*BIND:\s*(.+)", line)
            if m:
                results.append(BindingDecl(str(path), i, m.group(1).strip(), "pyo3"))
    return results


# frob:doc docs/modules/bind.md#public-api
def scan_sources(root: Path) -> list[SourceDecl]:
    """Scan .h and .cpp files for declared functions, and .rs for #[pyfunction]."""
    results = []
    fn_re = re.compile(r"^\s*(?:[\w:*&<> ]+)\s+(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?;")
    for path in iter_files(root, suffix=".h"):
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            m = fn_re.match(line)
            if m:
                results.append(
                    SourceDecl(str(path), i, line.strip().rstrip(";"), "cpp_header")
                )
    for path in iter_files(root, suffix=".rs"):
        lines = path.read_text(errors="replace").splitlines()
        for i, line in enumerate(lines, 1):
            if "#[pyfunction]" in line and i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith("fn "):
                    results.append(
                        SourceDecl(str(path), i + 1, next_line.rstrip(" {"), "rust")
                    )
    return results


def _normalize(sig: str) -> str:
    """Remove type annotations, whitespace differences for loose comparison."""
    sig = re.sub(r"\s+", " ", sig).strip().lower()
    sig = re.sub(r"\s*->\s*\w+", "", sig)
    sig = re.sub(r":\s*\w+", "", sig)
    sig = re.sub(r"[&*]", "", sig)
    return sig


# frob:doc docs/modules/bind.md#public-api
# frob:invariant INV-007
def check(root: Path) -> list[Mismatch]:
    """Return mismatches: bindings that have no matching source declaration."""
    bindings = scan_bindings(root)
    sources = scan_sources(root)
    source_sigs = [_normalize(s.signature) for s in sources]
    mismatches = []
    for b in bindings:
        norm = _normalize(b.signature)
        name_m = re.match(r"(\w+)\s*\(", norm)
        fn_name = name_m.group(1) if name_m else norm
        found = any(fn_name in s for s in source_sigs)
        if not found:
            mismatches.append(
                Mismatch(b, f"no source declaration found for '{b.signature}'")
            )
    return mismatches
