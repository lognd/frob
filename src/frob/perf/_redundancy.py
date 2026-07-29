"""PERF007: cross-stage redundant recomputation (T-0413, the PERF META-GAP).

PERF001-004 are per-FUNCTION lexical smells; PERF005/006 (T-0290) are
per-function recursion termination/depth proofs. All six are structurally
blind to the class of waste that actually dominated a real `frob check`
run: the SAME expensive computation (`frob.lang._parse`, in T-0413's own
incident) invoked repeatedly, from DIFFERENT top-level functions, on the
same kind of input, with no shared cache -- ~168s of redundant CPU that
none of PERF001-006 could ever have caught, because each only looks
inside one function body at a time.

Config-driven, generic, project-agnostic (same posture as
`frob.gates._docblocks`'s `[[docblocks.commands]]`, never a hardcoded
per-project list): `frob.toml`'s `[[perf.heavy]]` array names each
computation this project considers expensive enough to deduplicate:

```toml
[[perf.heavy]]
name = "parse_file"
cached_by = ["memoize_per_run", "lru_cache", "cache"]
```

`name` is the bare call-target identifier (as it appears in a call
expression's token stream -- `frob.lang._models`'s `RawSymbol.body_tokens`
carries no import-resolution, so this is a name match, not a fully
qualified one, matching every other PERF rule's token-level posture).
`cached_by` (optional, defaults to the built-in `_DEFAULT_CACHE_MARKERS`)
lists decorator names that, found immediately above `name`'s own `def` in
the project's tracked sources, mean a shared cache already exists and a
second call is a cheap hit rather than a genuine recompute -- exactly
`frob.check._memo.memoize_per_run`'s own shape (T-0423), plus the stdlib
`functools.lru_cache`/`functools.cache` any project might reach for
instead.

DETECTION (pure, over the already-parsed token stream, no re-parsing):
for every top-level `FUNCTION`/`METHOD` symbol in every `ParsedFile`, scan
`body_tokens` for a `<heavy-name> (` call-site pattern. Group every hit by
heavy name; if a name is called from 2+ DISTINCT top-level symbols (a
real cross-stage/cross-call-site repeat, not two calls inside the same
function which is simply that function's own business) and its own
definition (searched across every git-tracked source file) carries none
of `cached_by`'s decorator names immediately above its `def`, every call
site beyond the first is PERF007 (error) -- "this computation runs N times
across N call sites with nothing memoizing it". A `frob.toml` with no
`[[perf.heavy]]` entries means zero PERF007 checking -- fail-open, same
posture as every DOC004 namespace/command source.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.lang._models import ParsedFile, SymbolKind
from frob.logging import get_logger
from frob.tomlio import read_toml_lenient

_log = get_logger(__name__)

__all__ = ["redundant_computation_violations"]

_FUNCTION_KINDS = frozenset({SymbolKind.FUNCTION, SymbolKind.METHOD})

_DEFAULT_CACHE_MARKERS = ("memoize_per_run", "lru_cache", "cache")


@dataclass(frozen=True)
class _HeavyComputation:
    """One `[[perf.heavy]]` entry: the watched call-target name plus the
    decorator names that count as "already shares a cache" for it."""

    name: str
    cached_by: tuple[str, ...]


def _read_toml(path: Path) -> dict | None:
    """Best-effort TOML load: `None` on any missing/unreadable/malformed
    file -- a missing/absent `[[perf.heavy]]` table just means no PERF007
    checking, never a gate crash (fail-open). Thin wrapper over
    `frob.tomlio.read_toml_lenient` (extracted T-0861) that fixes this
    module's own `log_prefix`."""
    return read_toml_lenient(path, log_prefix="perf007")


def _heavy_computations(root: Path) -> tuple[_HeavyComputation, ...]:
    """Every `[[perf.heavy]]` entry declared in this project's `frob.toml`,
    or `()` if the table is absent/malformed."""
    data = _read_toml(root / "frob.toml")
    if data is None:
        return ()
    entries = data.get("perf", {}).get("heavy", [])
    if not isinstance(entries, list):
        return ()
    heavy: list[_HeavyComputation] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not (isinstance(name, str) and name):
            continue
        cached_by = entry.get("cached_by", _DEFAULT_CACHE_MARKERS)
        if not (
            isinstance(cached_by, list) and all(isinstance(c, str) for c in cached_by)
        ):
            cached_by = _DEFAULT_CACHE_MARKERS
        heavy.append(_HeavyComputation(name=name, cached_by=tuple(cached_by)))
    return tuple(heavy)


def _call_sites(tokens: tuple[str, ...], name: str) -> int:
    """How many times `<name> (` appears as a call-site pattern in `tokens`."""
    count = 0
    n = len(tokens)
    for i in range(n - 1):
        if tokens[i] == name and tokens[i + 1] == "(":
            count += 1
    return count


def _tracked_source_files(root: Path) -> tuple[str, ...]:
    """Every git-tracked source file this project's own definitions could
    live in -- used only to search for `name`'s own `def` + decorators,
    never re-parsed."""
    spawned = run_argv(
        ("git", "-C", str(root), "ls-files", "*.py", "*.rs", "*.ts", "*.tsx")
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return ()
    return tuple(line for line in spawned.danger_ok.stdout.splitlines() if line)


_DEF_RE_TMPL = r"^\s*(?:async\s+)?(?:def|fn)\s+{name}\b"
_DECORATOR_LOOKBEHIND = 5


def _is_already_cached(root: Path, name: str, cached_by: tuple[str, ...]) -> bool:
    """Whether `name`'s own definition (searched across every tracked
    source file) carries one of `cached_by`'s decorator names on one of the
    up-to-`_DECORATOR_LOOKBEHIND` lines immediately above its `def`/`fn` --
    a textual, conservative check (same posture as `_docblocks._rust_item_
    defined`), never a full symbol-table resolution."""
    def_pattern = re.compile(_DEF_RE_TMPL.format(name=re.escape(name)))
    for rel in _tracked_source_files(root):
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if def_pattern.match(line) is None:
                continue
            window = lines[max(0, i - _DECORATOR_LOOKBEHIND) : i]
            if any(marker in wline for wline in window for marker in cached_by):
                return True
    return False


# frob:doc \
# docs/modules/perf.md#cross-stage-redundant-recomputation-perf007-t-0413----the-perf-m\
# eta-gap
# frob:tests \
# tests/test_perf.py::TestPerf007RedundantComputation.test_two_stages_calling_the_same_\
# uncached_parse_is_flagged
# frob:tests \
# tests/test_perf.py::TestPerf007RedundantComputation.test_single_shared_call_site_is_n\
# ot_flagged
# frob:tests \
# tests/test_perf.py::TestPerf007RedundantComputation.test_cached_definition_suppresses\
# _the_warning
# frob:tests \
# tests/test_perf.py::TestPerf007RedundantComputation.test_no_config_means_no_perf007_c\
# hecking
# frob:ticket T-0413
def redundant_computation_violations(
    root: Path, files: Sequence[ParsedFile]
) -> tuple[Violation, ...]:
    """PERF007: a `[[perf.heavy]]`-configured call target invoked from 2+
    distinct top-level symbols across `files` with no shared-cache
    decorator on its own definition -- see this module's docstring for the
    full heuristic. `()` (no violations, no work at all) when `frob.toml`
    declares no `[[perf.heavy]]` entries."""
    heavy_computations = _heavy_computations(root)
    if not heavy_computations:
        return ()

    call_sites = _perf007_call_sites(files, heavy_computations)

    violations: list[Violation] = []
    for heavy in heavy_computations:
        sites = call_sites.get(heavy.name, [])
        if len(sites) < 2:
            continue
        if _is_already_cached(root, heavy.name, heavy.cached_by):
            _log.debug(
                "perf007: %s called from %d call sites but already cached (%s)",
                heavy.name,
                len(sites),
                heavy.cached_by,
            )
            continue
        first_file, first_qualname, first_line = sites[0]
        for file_path, qualname, line in sites[1:]:
            violations.append(
                Violation(
                    rule="PERF007",
                    severity=Severity.ERROR,
                    file=file_path,
                    line=line,
                    message=(
                        f"PERF007: {qualname} in {file_path}:{line} calls "
                        f"{heavy.name}(...) which is ALSO called from "
                        f"{first_qualname} in {first_file}:{first_line} -- "
                        f"the same expensive computation runs at least "
                        f"twice across separate call sites/stages with no "
                        f"shared cache; wrap {heavy.name} in one of "
                        f"{heavy.cached_by} (or route both call sites "
                        f"through a single shared call) so the second "
                        f"invocation is a cache hit, not a recompute"
                    ),
                )
            )
    _log.info(
        "perf007: %d heavy computation(s) configured, %d violation(s)",
        len(heavy_computations),
        len(violations),
    )
    return tuple(violations)


# frob:ticket T-0598
def _perf007_call_sites(
    files: Sequence[ParsedFile], heavy_computations: tuple[_HeavyComputation, ...]
) -> dict[str, list[tuple[str, str, int]]]:
    """`{heavy_name: [(file_path, qualname, span_start), ...]}` -- one entry
    per DISTINCT top-level symbol that calls it (a symbol calling it twice
    in its own body is that function's own business, not a cross-call-site
    repeat). `redundant_computation_violations`'s collection phase, split
    out for ARCH001 -- T-0598."""
    call_sites: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for file in files:
        for symbol in file.symbols:
            if symbol.kind not in _FUNCTION_KINDS:
                continue
            for heavy in heavy_computations:
                if _call_sites(symbol.body_tokens, heavy.name) > 0:
                    call_sites[heavy.name].append(
                        (file.path, symbol.qualname, symbol.span[0])
                    )
    return call_sites
