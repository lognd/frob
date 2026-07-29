"""T-0429: the corpus-emit mechanism an exhaustive-research pass uses to
write directly into the universe SSOT (`docs/design/registry/*.yaml`),
closing the research -> registry -> enforcement loop.

Root cause this closes: an exhaustive-research pass previously enumerated
its findings into an external store (a report, a vault note) with no
mechanical path into the registry the exhaustiveness gate
(`frob.gates._registry_exhaustiveness`) actually reads -- so a research
pass and the enforced corpus could silently diverge, or a research
finding could sit as untranscribed prose forever (the "orphaned docs"
failure mode T-0343/T-0424 already named for the registry itself, one
layer upstream).

Under the DERIVED-registry model (T-0428: `handled_by` is cross-checked
against code-declared `frob:enforces`, never authored by the researcher),
the researcher's job is narrow and mechanical: ENUMERATE completely,
append each entry with `disposition: pending` (dispositioning -- handled/
deferred/out-of-scope -- is a later, code-aware or reviewer act, not the
researcher's), and declare the denominator it enumerated so
`frob.gates._registry_exhaustiveness`'s REG005 total-drift check can
verify nothing was dropped between "what research found" and "what the
corpus now contains".

This module does NOT touch disposition semantics (`frob.registry._models`
owns that) -- it is purely the WRITE path: format one new entry as YAML
text matching the file's existing two-space list-item shape, locate that
entry list's own boundary inside the file via a plain top-level-key scan
(no full YAML round-trip, which would risk reformatting/losing the
hand-authored comments every registry file carries), and insert it there.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import re
from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger

_log = get_logger(__name__)

_ID_LINE_RE = re.compile(r'^\s*-\s*id:\s*"?([^"\n]+)"?\s*$')
_TOP_LEVEL_KEY_RE = re.compile(r"^\S")
_KEY_LINE_RE_TEMPLATE = r"^{key}:\s*$"
_TOTAL_LINE_RE_TEMPLATE = r"^({prefix}total):\s*(\d+)\s*$"


# frob:doc docs/guides/exhaustive-research.md#corpus-emit-mechanism-t-0429
class CorpusError(ErrorSet):
    """Failure values `append_entry` can return."""

    FileNotFound = "the target registry file does not exist"
    KeyNotFound = "the named entries key does not appear in the file"
    DuplicateId = "an entry with this id already exists in the file"


def _yaml_scalar(value: str) -> str:
    """Double-quote `value` for a YAML scalar, escaping embedded quotes --
    the same plain-scalar style every existing registry entry already
    uses for `id`/`name`/`source_doc`."""
    return '"' + value.replace('"', '\\"') + '"'


# frob:doc docs/guides/exhaustive-research.md#corpus-emit-mechanism-t-0429
# frob:ticket T-0429
# frob:tests tests/test_registry_corpus.py::TestFormatEntryBlock.test_pending_disposition_always kind="unit"  # noqa: E501
def format_entry_block(
    entry_id: str,
    name: str,
    *,
    source_doc: str = "",
    indent: str = "  ",
) -> str:
    """One new registry entry, formatted as YAML text matching the
    two-space list-item shape every `docs/design/registry/*.yaml` file
    already uses. Always `disposition: "pending"` -- per T-0429's
    DERIVED-registry posture, the researcher enumerates only; a real
    disposition (`handled_by`/`deferred`/`out_of_scope`) is a later,
    code-aware act (T-0428's `frob:enforces` cross-check, or a reviewer),
    never authored at emit time."""
    lines = [
        f"{indent}- id: {_yaml_scalar(entry_id)}",
        f"{indent}  name: {_yaml_scalar(name)}",
    ]
    if source_doc:
        lines.append(f"{indent}  source_doc: {_yaml_scalar(source_doc)}")
    lines.append(f'{indent}  disposition: "pending"')
    lines.append(f"{indent}  cross_refs: []")
    return "\n".join(lines) + "\n"


def _existing_ids(lines: list[str]) -> frozenset[str]:
    """Every `id:` value found on a `- id: "..."` list-item line, anywhere
    in the file -- used only for REG007-style pre-write duplicate
    rejection (the gate itself re-verifies this on the next `frob check`,
    this is a fail-fast courtesy at write time)."""
    ids: set[str] = set()
    for line in lines:
        match = _ID_LINE_RE.match(line)
        if match is not None:
            ids.add(match.group(1))
    return frozenset(ids)


def _key_block_bounds(lines: list[str], key: str) -> tuple[int, int] | None:
    """`(start, end)` line-index bounds of `key:`'s list block: `start` is
    the `key:` line itself, `end` is the index of the first line that
    dedents back to top level (or `len(lines)` at EOF) -- the insertion
    point for a new entry is `end` (append as the block's last item).
    `None` if `key:` never appears as a bare top-level key line."""
    key_re = re.compile(_KEY_LINE_RE_TEMPLATE.format(key=re.escape(key)))
    start = None
    for i, line in enumerate(lines):
        if key_re.match(line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.strip() == "":
            continue
        if _TOP_LEVEL_KEY_RE.match(line):
            end = i
            break
    return start, end


def _bump_total(lines: list[str], key: str) -> list[str]:
    """Increment a declared `total:` (or `<prefix>_total:` derived from
    `key`, e.g. `entries` -> `total`, `cwe_entries` -> `cwe_total`) by 1,
    in place -- REG005 (`frob.gates._registry_exhaustiveness`) fails a
    file whose declared total drifts from its actual entry count, so an
    append must keep both in lockstep. A file with no matching total line
    is left untouched (REG005 does not check files that never declared
    one)."""
    prefix = "" if key == "entries" else f"{key.removesuffix('_entries')}_"
    total_re = re.compile(_TOTAL_LINE_RE_TEMPLATE.format(prefix=re.escape(prefix)))
    for i, line in enumerate(lines):
        match = total_re.match(line)
        if match is not None:
            new_total = int(match.group(2)) + 1
            lines[i] = f"{match.group(1)}: {new_total}\n"
            _log.info(
                "append_entry: bumped %s %d -> %d",
                match.group(1),
                new_total - 1,
                new_total,
            )
            break
    return lines


# frob:doc docs/guides/exhaustive-research.md#corpus-emit-mechanism-t-0429
# frob:ticket T-0429
# frob:tests tests/test_registry_corpus.py::TestAppendEntry.test_append_adds_entry_and_bumps_total kind="unit"  # noqa: E501
def append_entry(
    registry_path: Path,
    key: str,
    entry_id: str,
    name: str,
    *,
    source_doc: str = "",
) -> Result[None, CorpusError]:
    """Append one new `disposition: pending` entry (id=`entry_id`,
    name=`name`) to `key`'s list in `registry_path`, bumping a declared
    total if present. Rejects a duplicate id before writing (REG007's
    concern, checked fail-fast here rather than only on the next `frob
    check`). This is the ONLY sanctioned write path into the universe
    corpus for an exhaustive-research pass -- it never assigns a real
    disposition (T-0428's derived-registry model: that is a later,
    code-aware or reviewer act)."""
    if not registry_path.is_file():
        _log.warning("append_entry: %s does not exist", registry_path)
        return Err(CorpusError.FileNotFound)

    text = registry_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    if entry_id in _existing_ids(lines):
        _log.warning("append_entry: %s already has id %r", registry_path, entry_id)
        return Err(CorpusError.DuplicateId)

    bounds = _key_block_bounds(lines, key)
    if bounds is None:
        _log.warning("append_entry: %s has no top-level key %r", registry_path, key)
        return Err(CorpusError.KeyNotFound)
    _, end = bounds

    block = format_entry_block(entry_id, name, source_doc=source_doc)
    lines[end:end] = [block]
    lines = _bump_total(lines, key)

    registry_path.write_text("".join(lines), encoding="utf-8")
    _log.info("append_entry: %s <- %s (%s)", registry_path, entry_id, key)
    return Ok(None)


__all__ = ["CorpusError", "append_entry", "format_entry_block"]
