"""T-0701: strata mode-conformance enforcement -- prove each node's code
OBEYS its declared T-0700 `access` mode (`read`/`append`/`alpha`/`write`/
`exclusive`), the code-level half of the resource-contention mandate
`_access.py`'s module docstring explicitly defers ("whether the arbiter is
actually RESPECTED by the node's code is T-0701's separate, code-level
conformance proof, not this function's job"). SYS204 (`_access.py`) proves
the MODEL-level declaration is internally consistent; SYS205 (this module)
proves the node's OWN bound code actually behaves the way its declaration
claims -- the catalogued-is-not-enforced trap (T-0343 doctrine) this
mandate exists to close.

USER MANDATE (2026-07-22): join the T-0700 access declaration against the
code's OBSERVED effects. This module implements a v0, PYTHON-ONLY textual
join (disclosed cut, matching `_lock_ordering.py`'s own "same-module only"
precedent for the class of check this resembles): a `.py` file is scanned
line-by-line for a small, curated set of write-capable operation shapes
(`_classify_line`) -- `open()` calls with an explicit write/append/
exclusive-creation mode, `os.remove`/`os.rename`/`os.unlink`, `shutil.
rmtree`/`move`, `pathlib` `write_text`/`write_bytes`/`.unlink(`, a socket
`.send`/`.sendall`/`sendto`, and a SQL DML keyword (`INSERT`/`UPDATE`/
`DELETE`/`DROP`/`TRUNCATE`) on a line that also calls `.execute(`.
Non-python bound files are skipped entirely for THIS check (disclosed cut,
`_classify_line`'s own docstring) -- `check_capability_conformance`'s
existing multi-language `fs.write` join still covers them for the coarser
undeclared-capability obligation, just not this mode-precision one.

There is no path-level identity between a declared resource id and a
specific file/call site (same v0 scope cut `_effects.py`'s own module
docstring already discloses for capability conformance: "a node with any
`may` atom of kind X is allowed any X-effect anywhere in its bound code" --
finer, target-scoped joins need a first-class capability grammar this
kernel does not have yet). `check_mode_conformance` therefore joins at
NODE granularity: every write-capable line found anywhere in a node's
`code=`-bound python files is checked against EVERY resource that node
declares `access` to, exactly mirroring `check_capability_conformance`'s
own node-wide join shape.

MODE SEMANTICS (mandate, `_access.py::AccessMode`):

- READ: zero write-capable operations anywhere in the node's bound code.
  Fail-closed -- any classified write-capable line is a violation,
  regardless of which specific resource it happens to touch (the same
  node-granularity cut as above).
- APPEND: write-capable operations are allowed ONLY when classified
  `"append_open"` (an `open(path, "a"...)`-shaped call); every other
  write-capable category (`"write_open"`, `"fs_write"`, `"send"`,
  `"sql_dml"`) is a violation.
- WRITE: unrestricted in v0 -- the mandate's "only on declared paths"
  clause needs the same path-level identity this module's docstring
  above discloses as out of scope; `bind_code`'s own file->node
  ownership partition is the only "declared path" enforcement this pass
  can make, and it already gates which files are even scanned. Disclosed
  cut, follow-up ticket filed at close (see Done report).
- ALPHA / EXCLUSIVE: both require a CODE-CHECKABLE arbiter -- v0 only
  supports the `lock "NAME"` form of `_ast.py::ResourceDecl` (an
  `arbitrated_by NODE` arbiter has no code-level identity this module can
  resolve without cross-node call-graph analysis, a disclosed follow-up
  cut, same class of limit `_lock_ordering.py`'s own module docstring
  accepts for "a lock passed as a function PARAMETER"). A resource with
  no `lock` declared (bare, or `arbitrated_by`-only) fails closed for
  BOTH modes -- "no code-checkable context to be inside" is itself a
  violation, not a silent pass. When a `lock` IS declared, every
  write-capable line must sit lexically inside a `with` block whose
  header text mentions the lock name (`_enclosing_with_headers`, a
  cheap indentation-based block scan, not a full parse -- v0 scope,
  same textual-convention precedent `_access.py`/`_starvation.py`'s own
  resource-id string matching already uses) -- a write-capable line
  found OUTSIDE every such block is the "unguarded path" the acceptance
  criteria names. EXCLUSIVE additionally inherits WRITE's baseline (which
  is unrestricted in v0, so EXCLUSIVE's own obligation IS the lock-context
  join, not an additional restriction beyond it in this pass).

DISCLOSED CUT, not silently dropped: the mandate's ALPHA "upgrade-deadlock
ANTI-PATTERN" (a node acquiring a write while ALSO holding a plain `read`
lock context on the SAME resource, the shape `alpha` exists to prevent) is
NOT detected in this pass -- doing so soundly needs per-lock-variable
identity across nested `with` blocks (which lock guards which resource),
the same "lock IDENTITY" modeling problem `_lock_ordering.py`'s own
T-0694 `_collect_module_locks` solves for `frob.arch`'s cyclic-order
check, out of this ticket's textual-join scope. Filed as a follow-up
ticket at close (see Done report) rather than approximated unreliably.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's 'only'/ \
# 'never' hits are source-level design-rationale/scope-cut prose (the module \
# docstring's mode-semantics description and disclosed cuts) rather than a separate \
# cross-module contract needing its own tracked invariant, the same disposition \
# _access.py/_effects.py's own module docstrings already carry for this file family"

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger
from frob.vet._capability import is_self_pattern_path, language_for

from ._access import AccessMode, node_access_declarations
from ._ast import Module, ResourceDecl
from ._code_binding import FOREIGN, CodeBinding
from ._models import KernelModel, Node

_log = get_logger(__name__)

#: `frob sys audit` rule id for SYS205 mode nonconformance: a node's own
#: bound code exhibits an effect its declared `access ... mode MODE`
#: clause forbids (module docstring's per-mode semantics).
# frob:doc docs/strata/host.md#resource-access-modes-t-0700
SYS_MODE_NONCONFORMANCE = "SYS205"

#: `open(PATH, "MODE"...)` -- captures the quoted mode string so
#: `_classify_line` can tell append (`"a"`) from write/create/update
#: (`"w"`/`"x"`/`"+"`) from an explicit read mode (`"r"`/`"rb"`, no
#: violation) without a full parse. Deliberately narrow: an `open()` call
#: with no explicit mode argument (bare `open(path)`) defaults to read and
#: is correctly left unclassified (the regex requires a comma-separated
#: second argument to match at all).
_OPEN_MODE_RE = re.compile(r"""open\(\s*[^,)]*,\s*["']([a-zA-Z+]{1,4})["']""")

#: Write-capable filesystem operations with no mode string to inspect --
#: the call ITSELF is inherently destructive/mutating (mirrors the
#: `fs-write` needle rows in `frob.vet._capability_registry` for the same
#: python stdlib surface, kept as a small local table here rather than
#: importing the registry directly since this module needs a narrower
#: WRITE-vs-APPEND classification the registry's `fs-write`/`fs-read` kind
#: split does not carry).
_FS_WRITE_NEEDLES: tuple[str, ...] = (
    "os.remove(",
    "os.rename(",
    "os.unlink(",
    "shutil.rmtree(",
    "shutil.move(",
    "write_text(",
    "write_bytes(",
    ".unlink(",
)

#: Socket-send needles (mandate: "sends on the port").
_SEND_NEEDLES: tuple[str, ...] = (".send(", ".sendall(", "sendto(")

#: SQL DML keyword, checked only on a line that ALSO calls `.execute(` --
#: a bare DML keyword alone is far too common in prose/tests to use as a
#: standalone needle (mirrors `_capability.py`'s own T-0151 "avoid a needle
#: wrong by construction" lesson).
_DML_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE)\b", re.IGNORECASE)

#: The four write-capable classification categories `_classify_line` can
#: return; `"append_open"` is the only one APPEND mode discharges.
_APPEND_OPEN = "append_open"
_WRITE_OPEN = "write_open"
_FS_WRITE = "fs_write"
_SEND = "send"
_SQL_DML = "sql_dml"
_WRITE_CAPABLE_CATEGORIES = frozenset(
    {_APPEND_OPEN, _WRITE_OPEN, _FS_WRITE, _SEND, _SQL_DML}
)


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
class ModeObservation(BaseModel):
    """One write-capable operation observed at `file`:`line`, classified
    into one of `_classify_line`'s categories (`category`)."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    category: str
    text: str


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
class ModeConformanceViolation(BaseModel):
    """One SYS205 finding: the node, its declared resource + mode, the
    observed operation that broke conformance, and a human-readable
    detail naming the offending site (acceptance criteria: "a fail-closed
    error names the write site" / "names the unguarded path")."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    resource: str
    mode: AccessMode
    file: str
    line: int
    category: str
    detail: str


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
class ModeConformanceReport(BaseModel):
    """Every SYS205 finding across a model."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ModeConformanceViolation, ...] = ()


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
def _classify_line(line: str) -> str | None:
    """The write-capable category `line` exhibits, or `None` if it
    matches none of this module's curated write-capable shapes (module
    docstring's category list) -- the classification join every mode
    check (`_node_mode_observations`) is built on."""
    match = _OPEN_MODE_RE.search(line)
    if match:
        mode = match.group(1).lower()
        if "a" in mode:
            return _APPEND_OPEN
        if "w" in mode or "x" in mode or "+" in mode:
            return _WRITE_OPEN
        return None
    for needle in _FS_WRITE_NEEDLES:
        if needle in line:
            return _FS_WRITE
    for needle in _SEND_NEEDLES:
        if needle in line:
            return _SEND
    if "execute(" in line and _DML_RE.search(line):
        return _SQL_DML
    return None


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
def _file_mode_observations(path: Path, root: Path) -> list[ModeObservation]:
    """Every write-capable line in `path` (python only, module docstring's
    disclosed cut) -- `is_self_pattern_path`-excluded exactly like
    `_effects.py::_line_effects` so this module's own needle table cannot
    self-match."""
    if is_self_pattern_path(path, root):
        return []
    if language_for(path) != "python":
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning("strata mode-conformance: could not read %s: %s", path, exc)
        return []
    rel = path.relative_to(root).as_posix()
    found: list[ModeObservation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        category = _classify_line(line)
        if category is not None:
            found.append(
                ModeObservation(file=rel, line=lineno, category=category, text=line)
            )
    return found


def _sorted_owned_files(binding: CodeBinding, owner: str) -> list[str]:
    """Every non-`FOREIGN` bound file path owned by `owner`, deterministic
    (sorted) order -- mirrors `_effects.py::_sorted_owned_files` scoped to
    one node instead of every non-`FOREIGN` file."""
    return sorted(rel for rel, o in binding.owner.items() if o == owner)


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
def _node_mode_observations(
    node: Node, binding: CodeBinding, root: Path
) -> list[ModeObservation]:
    """Every write-capable operation observed anywhere in `node`'s own
    `code=`-bound python files, file-then-line order -- the per-node
    observation set every mode check below joins against."""
    if node.id == FOREIGN:
        return []
    observations: list[ModeObservation] = []
    for rel in _sorted_owned_files(binding, node.id):
        observations.extend(_file_mode_observations(root / rel, root))
    return observations


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
def _enclosing_with_headers(lines: list[str], line_no: int) -> list[str]:
    """Every `with` statement header lexically enclosing 1-indexed
    `line_no` in `lines`, found by climbing to each strictly-lower-
    indented ancestor line in turn (a cheap indentation-based block scan,
    module docstring -- not a full parse, so a line continuation or a
    single-line `with x: body` collapses this heuristic; acceptable for
    v0's curated litmus-fixture shape)."""
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        return []
    headers: list[str] = []
    target_indent = len(lines[idx]) - len(lines[idx].lstrip())
    i = idx - 1
    while i >= 0 and target_indent > 0:
        line = lines[i]
        stripped = line.strip()
        if stripped:
            indent = len(line) - len(line.lstrip())
            if indent < target_indent:
                if stripped.startswith("with "):
                    headers.append(stripped)
                target_indent = indent
        i -= 1
    return headers


def _lock_name_for(resource: ResourceDecl | None) -> str | None:
    """The code-checkable arbiter name for `resource` (module docstring:
    v0 only supports `lock`, never `arbitrated_by`) -- `None` when
    `resource` is absent or declares no `lock`, the "no code-checkable
    context" fail-closed case both ALPHA and EXCLUSIVE share."""
    if resource is None:
        return None
    return resource.lock


def _observation_guarded_by_lock(
    observation: ModeObservation, root: Path, lock_name: str
) -> bool:
    """Whether `observation`'s site sits inside a `with` block naming
    `lock_name` (`_enclosing_with_headers`) -- re-reads the file's lines
    once per call rather than threading a cache through, matching this
    module's other read-through-`Path` calls; call sites are bounded by
    the number of write-capable observations, not file size."""
    path = root / observation.file
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    return any(
        lock_name in header
        for header in _enclosing_with_headers(lines, observation.line)
    )


def _read_violation(
    node: Node, resource: str, mode: AccessMode, observation: ModeObservation
) -> ModeConformanceViolation:
    """One READ-mode violation: any write-capable observation at all."""
    return ModeConformanceViolation(
        rule=SYS_MODE_NONCONFORMANCE,
        node=node.id,
        resource=resource,
        mode=mode,
        file=observation.file,
        line=observation.line,
        category=observation.category,
        detail=(
            f"node {node.id!r} declares mode=read on resource {resource!r} "
            f"but {observation.file}:{observation.line} is a write-capable "
            f"operation ({observation.category})"
        ),
    )


def _append_violation(
    node: Node, resource: str, mode: AccessMode, observation: ModeObservation
) -> ModeConformanceViolation:
    """One APPEND-mode violation: a write-capable observation that is not
    itself an append-mode open."""
    return ModeConformanceViolation(
        rule=SYS_MODE_NONCONFORMANCE,
        node=node.id,
        resource=resource,
        mode=mode,
        file=observation.file,
        line=observation.line,
        category=observation.category,
        detail=(
            f"node {node.id!r} declares mode=append on resource {resource!r} "
            f"but {observation.file}:{observation.line} is a non-append "
            f"write operation ({observation.category})"
        ),
    )


def _no_arbiter_violation(
    node: Node, resource: str, mode: AccessMode
) -> ModeConformanceViolation:
    """One ALPHA/EXCLUSIVE violation: the resource has no code-checkable
    `lock` arbiter at all (module docstring: `arbitrated_by`-only or bare
    resources fail closed for these two modes)."""
    return ModeConformanceViolation(
        rule=SYS_MODE_NONCONFORMANCE,
        node=node.id,
        resource=resource,
        mode=mode,
        file="",
        line=0,
        category="no_arbiter",
        detail=(
            f"node {node.id!r} declares mode={mode.value} on resource "
            f"{resource!r} but no code-checkable `lock` arbiter is declared "
            f"for it (a bare resource or `arbitrated_by`-only arbiter is "
            f"unresolvable at the code level in this v0 pass)"
        ),
    )


def _unguarded_violation(
    node: Node,
    resource: str,
    mode: AccessMode,
    observation: ModeObservation,
    lock_name: str,
) -> ModeConformanceViolation:
    """One ALPHA/EXCLUSIVE violation: a write-capable observation outside
    every `with <lock_name>:`-shaped enclosing block."""
    return ModeConformanceViolation(
        rule=SYS_MODE_NONCONFORMANCE,
        node=node.id,
        resource=resource,
        mode=mode,
        file=observation.file,
        line=observation.line,
        category=observation.category,
        detail=(
            f"node {node.id!r} declares mode={mode.value} on resource "
            f"{resource!r} (lock {lock_name!r}) but "
            f"{observation.file}:{observation.line} ({observation.category}) "
            f"is outside every `with` block naming that lock"
        ),
    )


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
# frob:enforces CHK-GATE-SYS205
# frob:tests tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_read_mode_fails_on_a_write_open  # noqa: E501
def check_mode_conformance(
    model: KernelModel, module: Module, binding: CodeBinding, root: Path
) -> ModeConformanceReport:
    """The SYS205 mode-conformance entrypoint (T-0701): for every node
    declaring `access "RESOURCE" mode MODE` (`node_access_declarations`),
    join the declared MODE against `node`'s own observed write-capable
    operations (`_node_mode_observations`) per the module docstring's
    per-mode semantics. `module` supplies `Module.resources` (the `lock`
    arbiter lookup ALPHA/EXCLUSIVE need) the same way `_access.py::
    resource_contention_violations` already takes it in, for the same
    reason (`KernelModel` has no reconstructible `resource` block)."""
    resources: dict[str, ResourceDecl] = {r.id: r for r in module.resources}
    violations: list[ModeConformanceViolation] = []
    for node in model.nodes:
        declarations = node_access_declarations(node)
        if not declarations:
            continue
        observations = _node_mode_observations(node, binding, root)
        write_capable = [
            o for o in observations if o.category in _WRITE_CAPABLE_CATEGORIES
        ]
        for declaration in declarations:
            resource_id = declaration.resource
            mode = declaration.mode
            if mode is AccessMode.READ:
                for observation in write_capable:
                    violations.append(
                        _read_violation(node, resource_id, mode, observation)
                    )
            elif mode is AccessMode.APPEND:
                for observation in write_capable:
                    if observation.category == _APPEND_OPEN:
                        continue
                    violations.append(
                        _append_violation(node, resource_id, mode, observation)
                    )
            elif mode in (AccessMode.ALPHA, AccessMode.EXCLUSIVE):
                lock_name = _lock_name_for(resources.get(resource_id))
                if lock_name is None:
                    violations.append(_no_arbiter_violation(node, resource_id, mode))
                    continue
                for observation in write_capable:
                    if _observation_guarded_by_lock(observation, root, lock_name):
                        continue
                    violations.append(
                        _unguarded_violation(
                            node, resource_id, mode, observation, lock_name
                        )
                    )
            # AccessMode.WRITE: unrestricted in v0, module docstring's
            # disclosed cut -- no violation possible from this join.
    _log.info(
        "strata mode-conformance: %d SYS205 violation(s) across %d node(s)",
        len(violations),
        len(model.nodes),
    )
    return ModeConformanceReport(violations=tuple(violations))


__all__ = [
    "SYS_MODE_NONCONFORMANCE",
    "ModeConformanceReport",
    "ModeConformanceViolation",
    "ModeObservation",
    "check_mode_conformance",
]
