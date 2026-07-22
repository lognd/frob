"""Unified registry schema (T-0407): one typed model for every entry in
every `docs/design/registry/*.yaml` manifest, and a single disposition
grammar shared by all consumers instead of re-implemented per gate.

Root cause this closes: `frob.gates._registry_exhaustiveness` (T-0343) grew
its own regex-based disposition parser directly inline with the gate that
consumes it -- correct, but a second registry (T-0424's reflexive
check-coverage registry) would either duplicate that parser or import a
gate-internal module as if it were a library. This module is the one home:
`RegistryEntry`/`Disposition` are the typed shape, `parse_disposition` is
the one grammar, `load_registry_dir` is the one loader. `frob.gates.
_registry_exhaustiveness.registry_gate` now calls into this module rather
than parsing YAML/disposition strings itself.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict
from typani import Err, Ok, Result
from typani.error_set import ErrorSet

from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "Disposition",
    "DispositionKind",
    "RegistryAudit",
    "RegistryEntry",
    "RegistryFile",
    "RegistryLoadError",
    "audit_registry_file",
    "load_registry_dir",
    "parse_disposition",
]


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
class DispositionKind(StrEnum):
    """Every disposition a registry entry can carry under the one grammar
    every registry file shares. `UNDISPOSITIONED` is the catch-all for a
    missing/blank/`pending`/bare-`addressed`/unparseable string -- it is a
    real member of this enum (not `None`) so exhaustiveness checks over
    `DispositionKind` cannot silently forget the undispositioned case."""

    HANDLED_BY = "handled_by"
    DEFERRED = "deferred"
    DUPLICATE_OF = "duplicate_of"
    OUT_OF_SCOPE = "out_of_scope"
    UNDISPOSITIONED = "undispositioned"


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
class Disposition(BaseModel):
    """One parsed, typed disposition -- the unified replacement for the
    ad-hoc regex-match tuples the pre-T-0407 gate returned inline. `target`
    holds the rule id / ticket id / duplicate-target id / reason text
    depending on `kind`; it is `None` only for `UNDISPOSITIONED`."""

    model_config = ConfigDict(frozen=True)

    kind: DispositionKind
    target: str | None = None
    raw: str


_HANDLED_BY_RE = re.compile(r"^handled_by:(?P<rule>\S+)$")
_DEFERRED_RE = re.compile(r"^deferred:(?P<ticket>\S+)$")
_DUPLICATE_RE = re.compile(r"^duplicate[_-]of:(?P<target>\S+)$")
_OUT_OF_SCOPE_RE = re.compile(r"^out[_-]of[_-]scope[:(](?P<reason>.+?)[)]?$")


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
# frob:tests tests/test_registry_models.py::TestParseDisposition.test_handled_by
# frob:tests tests/test_registry_models.py::TestParseDisposition.test_undispositioned_pending  # noqa: E501
# frob:tests tests/test_registry_models.py::TestParseDisposition.test_undispositioned_bare_addressed  # noqa: E501
def parse_disposition(raw: str | None) -> Disposition:
    """Parse one entry's raw `disposition:` string into a typed
    `Disposition` under the ONE grammar every registry file shares
    (`handled_by:<rule>` / `deferred:<ticket>` / `duplicate_of:<id>` /
    `out_of_scope:<reason>`). Never raises: anything that does not parse
    -- missing, blank, the bare literal `pending`, a bare `addressed` with
    nothing backing it, or free text matching none of the four shapes --
    collapses to `DispositionKind.UNDISPOSITIONED` rather than erroring,
    so the caller (the exhaustiveness gate) can turn that into a loud
    `REG001` violation instead of a crash."""
    if raw is None or raw.strip() == "" or raw == "pending" or raw == "addressed":
        return Disposition(kind=DispositionKind.UNDISPOSITIONED, raw=raw or "")
    handled = _HANDLED_BY_RE.match(raw)
    if handled is not None:
        return Disposition(
            kind=DispositionKind.HANDLED_BY, target=handled.group("rule"), raw=raw
        )
    deferred = _DEFERRED_RE.match(raw)
    if deferred is not None:
        return Disposition(
            kind=DispositionKind.DEFERRED, target=deferred.group("ticket"), raw=raw
        )
    duplicate = _DUPLICATE_RE.match(raw)
    if duplicate is not None:
        return Disposition(
            kind=DispositionKind.DUPLICATE_OF, target=duplicate.group("target"), raw=raw
        )
    out_of_scope = _OUT_OF_SCOPE_RE.match(raw)
    if out_of_scope is not None:
        return Disposition(
            kind=DispositionKind.OUT_OF_SCOPE,
            target=out_of_scope.group("reason"),
            raw=raw,
        )
    return Disposition(kind=DispositionKind.UNDISPOSITIONED, raw=raw)


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
class RegistryEntry(BaseModel):
    """One typed entry from a registry manifest: the raw `id`/`cross_refs`
    the exhaustiveness gate's REG004 needs, plus the parsed `disposition`
    (never the raw string) so every consumer classifies off the same
    typed shape instead of re-parsing text."""

    model_config = ConfigDict(frozen=True)

    id: str
    disposition: Disposition
    cross_refs: tuple[str, ...] = ()
    source_file: str = ""


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
class RegistryFile(BaseModel):
    """One parsed `docs/design/registry/*.yaml` manifest: every entry list
    it declares (most files carry one `entries:` list; `weaknesses.yaml`
    splits into `cwe_entries`/`other_weakness_framework_entries`), each
    keyed by its YAML key, plus each key's declared `total`/`<prefix>
    _total` denominator if the file opted in to declaring one, and every
    structurally malformed entry (not a mapping, or missing a string
    `id`) that was skipped rather than silently dropped -- REG006's
    source."""

    model_config = ConfigDict(frozen=True)

    path: str
    entry_lists: dict[str, tuple[RegistryEntry, ...]] = {}
    declared_totals: dict[str, int] = {}
    malformed_count: int = 0


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
class RegistryAudit(BaseModel):
    """The `frob registry audit` per-file accounting: how many entries are
    `handled` (`handled_by`), `deferred`, `duplicate` (`duplicate_of`),
    `out_of_scope`, `unaccounted` (undispositioned -- REG001's target), or
    `malformed` (REG006's target) -- so "did we exhaust this registry" is
    a one-line honest answer read straight off `total`, never a vibe."""

    model_config = ConfigDict(frozen=True)

    path: str
    total: int
    handled: int = 0
    deferred: int = 0
    duplicate: int = 0
    out_of_scope: int = 0
    unaccounted: int = 0
    malformed: int = 0

    # frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
    @property
    def exhausted(self) -> bool:
        """True only when every entry (any `malformed` PLUS every real
        entry) is dispositioned as something other than `unaccounted` --
        the one-line pass/fail `frob registry audit` reports per file."""
        return self.unaccounted == 0 and self.malformed == 0


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
# frob:tests tests/test_registry_models.py::TestAuditRegistryFile.test_counts_each_kind
def audit_registry_file(registry_file: RegistryFile) -> RegistryAudit:
    """The per-file `RegistryAudit` for `registry_file`: one count per
    `DispositionKind` across every entry list it carries, plus
    `malformed` from the file's own `malformed_count`. This is the single
    accounting function `frob registry audit` and any future consumer
    (T-0424's reflexive check-coverage registry included) both call,
    rather than each re-deriving counts from raw entries."""
    counts: dict[DispositionKind, int] = dict.fromkeys(DispositionKind, 0)
    total_entries = 0
    for entries in registry_file.entry_lists.values():
        for entry in entries:
            counts[entry.disposition.kind] += 1
            total_entries += 1
    return RegistryAudit(
        path=registry_file.path,
        total=total_entries + registry_file.malformed_count,
        handled=counts[DispositionKind.HANDLED_BY],
        deferred=counts[DispositionKind.DEFERRED],
        duplicate=counts[DispositionKind.DUPLICATE_OF],
        out_of_scope=counts[DispositionKind.OUT_OF_SCOPE],
        unaccounted=counts[DispositionKind.UNDISPOSITIONED],
        malformed=registry_file.malformed_count,
    )


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
class RegistryLoadError(ErrorSet):
    """Failure values `load_registry_dir` can return for one manifest file."""

    Unreadable = "registry file could not be read from disk"
    MalformedYaml = "registry file is not valid YAML"
    NotAMapping = "registry file's top-level YAML node is not a mapping"


def _total_field_name(entries_key: str) -> str:
    """The `total:`-shaped field name paired with `entries_key` -- bare
    `entries` pairs with `total`; a split key like `cwe_entries` pairs
    with `cwe_total` (`weaknesses.yaml`'s own convention)."""
    if entries_key == "entries":
        return "total"
    return entries_key.removesuffix("_entries") + "_total"


def _parse_entry(rel_path: str, raw_entry: Any) -> RegistryEntry | None:
    """One list item into a typed `RegistryEntry`, or `None` if it is
    structurally malformed (not a mapping, or no string `id`) -- the
    caller counts `None`s into `malformed_count` (REG006) rather than
    silently skipping them the way the pre-T-0407 gate did."""
    if not isinstance(raw_entry, dict) or not isinstance(raw_entry.get("id"), str):
        return None
    cross_refs_raw = raw_entry.get("cross_refs")
    cross_refs = (
        tuple(str(c) for c in cross_refs_raw)
        if isinstance(cross_refs_raw, list)
        else ()
    )
    disposition_raw = raw_entry.get("disposition")
    disposition = parse_disposition(
        disposition_raw if isinstance(disposition_raw, str) else None
    )
    return RegistryEntry(
        id=raw_entry["id"],
        disposition=disposition,
        cross_refs=cross_refs,
        source_file=rel_path,
    )


def _entry_list_keys(data: dict[str, Any]) -> list[str]:
    """Every key in `data` that carries an entry list -- `entries` or any
    key ending in `_entries`, matching every registry file's own shape."""
    return [
        key
        for key, value in data.items()
        if isinstance(value, list) and (key == "entries" or key.endswith("_entries"))
    ]


def _parse_registry_file(rel_path: str, data: dict[str, Any]) -> RegistryFile:
    """One already-YAML-parsed manifest mapping into a typed `RegistryFile`."""
    entry_lists: dict[str, tuple[RegistryEntry, ...]] = {}
    declared_totals: dict[str, int] = {}
    malformed_count = 0
    for key in _entry_list_keys(data):
        parsed_entries: list[RegistryEntry] = []
        for raw_entry in data[key]:
            entry = _parse_entry(rel_path, raw_entry)
            if entry is None:
                malformed_count += 1
                continue
            parsed_entries.append(entry)
        entry_lists[key] = tuple(parsed_entries)
        total_field = _total_field_name(key)
        total_value = data.get(total_field)
        if isinstance(total_value, int):
            declared_totals[total_field] = total_value
    return RegistryFile(
        path=rel_path,
        entry_lists=entry_lists,
        declared_totals=declared_totals,
        malformed_count=malformed_count,
    )


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407
# frob:tests tests/test_registry_models.py::TestLoadRegistryDir.test_loads_typed_entries  # noqa: E501
# frob:tests tests/test_registry_models.py::TestLoadRegistryDir.test_malformed_yaml_is_err  # noqa: E501
def load_registry_dir(
    registry_dir: Path, filenames: tuple[str, ...]
) -> dict[str, Result[RegistryFile, RegistryLoadError]]:
    """Load every `filenames` entry under `registry_dir` into a typed
    `RegistryFile`, keyed by the file's basename. A file that does not
    exist under `registry_dir` is simply absent from the returned dict
    (the caller decides whether an expected-but-missing file is an
    error); a file that exists but is unreadable or not valid YAML/not a
    mapping is present as an `Err(RegistryLoadError)` rather than silently
    skipped -- this is the SINGLE loader every registry consumer (the
    T-0343 exhaustiveness gate, and any future registry instance such as
    T-0424's check-coverage registry) shares, so a loading bug gets fixed
    once, not once per consumer."""
    results: dict[str, Result[RegistryFile, RegistryLoadError]] = {}
    for filename in filenames:
        path = registry_dir / filename
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("load_registry_dir: %s unreadable: %s", path, exc)
            results[filename] = Err(RegistryLoadError.Unreadable)
            continue
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            _log.warning("load_registry_dir: %s malformed YAML: %s", path, exc)
            results[filename] = Err(RegistryLoadError.MalformedYaml)
            continue
        if not isinstance(data, dict):
            results[filename] = Err(RegistryLoadError.NotAMapping)
            continue
        results[filename] = Ok(_parse_registry_file(filename, data))
    return results
