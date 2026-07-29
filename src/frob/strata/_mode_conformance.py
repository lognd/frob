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

V1 (T-1060) closes all three v0 cuts named above, each as a NARROW,
TEXTUAL approximation in this module's own established idiom (cheap
indentation/string-based scanning, same posture as `_enclosing_with_
headers` -- deliberately NOT tree-sitter-based like `frob.arch.
_lock_ordering`'s own T-0694 lock-identity solution, since that is a
heavier, differently-scoped mechanism this ticket does not adopt):

1. ALPHA/EXCLUSIVE upgrade-deadlock ANTI-PATTERN (the mandate's "a node
   acquiring a write while ALSO holding a plain lock context on the SAME
   resource" shape): `_enclosing_with_headers` already returns every
   `with` header lexically enclosing a write-capable line, ancestor-chain
   order. `_lock_reacquired` fires when the SAME lock name appears MORE
   THAN ONCE in that chain -- i.e., a `with lock:` block nested inside
   ANOTHER `with lock:` block naming the identical lock is exactly the
   non-reentrant-lock self-deadlock shape `alpha`/`exclusive` exist to
   prevent, textually detectable without real lock-VARIABLE identity
   (T-0694's harder problem: telling two DIFFERENT lock objects with the
   same NAME apart is still out of this v1's scope, same as before -- this
   only catches literal name reuse, the shape the mandate's own example
   describes). New violation category `"alpha_reacquire_deadlock"`, fires
   ALONGSIDE (not instead of) the existing unguarded-write check -- a
   nested-reacquisition write IS lexically "inside a with-block naming the
   lock" (so the old check alone would call it conformant), but it is
   simultaneously the specific anti-pattern this new check exists to
   catch, so both may fire on the same site for different reasons.

2. `arbitrated_by NODE` code-checkable identity: `_arbiter_identity_for`
   now resolves BOTH `lock` (unchanged, matched against `with`-header
   text) and `arbitrated_by` (NEW) -- for a NODE arbiter, "code-checkable"
   means the write-capable line's own TEXT mentions the arbiter node's id
   as a dotted-call prefix (`"{node_id}."`), the same "cheap textual
   identifier match" convention `_access.py`/`_starvation.py`'s resource-id
   string matching and this module's own lock-name matching already use --
   NOT a real cross-node call-graph resolution (still out of scope,
   disclosed): a write genuinely routed through the arbiter via an
   indirection (a local alias, a returned callable, an injected
   dependency) is invisible to this textual join and will still fail
   closed as unguarded. This narrows, but does not eliminate, the
   `_no_arbiter_violation` fail-closed default: a resource with NEITHER
   `lock` NOR `arbitrated_by` still fails closed exactly as before.

3. WRITE mode path-scoping: `_declared_write_paths` reads a node's own
   `owns` (POSIX; `acl`'s Windows paths join the same list) claims off
   `_host.py::host_manifest_for` -- the SAME "declared path" fact SYS201
   (`_contention.py`) already uses for path-overlap contention, reused
   here as the "only on declared paths" identity WRITE's mandate needs.
   A node declaring NO `owns`/`acl` at all now fails closed for WRITE
   (`"no_declared_path"`, the SAME fail-closed-when-nothing-code-
   checkable posture ALPHA/EXCLUSIVE's `_no_arbiter_violation` already
   establishes) -- WRITE is no longer silently unrestricted just because
   nothing was declared to scope it. When paths ARE declared,
   `_extract_path_literal` pulls a literal string path argument out of
   the categories that carry one (`open()`/`os.remove`/`os.rename`/
   `os.unlink`/`shutil.rmtree`/`shutil.move` -- the ones with an explicit
   PATH argument; `.write_text(`/`.write_bytes(`/`.unlink(`/`.send(`/SQL
   DML have no path ARGUMENT to extract at all, module docstring's own
   category list, so this join is silent for them, same as v0) and
   checks directory-segment-prefix overlap (`_path_segments`/`_paths_
   overlap`, a small local port of `_contention.py`'s identical logic --
   duplicated rather than imported since that module is out of this
   ticket's scope and the join is genuinely tiny) against the node's
   declared claims; a literal path with NO overlap fires
   `"write_outside_declared_path"`. A write-capable line with NO
   extractable literal (a dynamic path, or a category with no path
   argument at all) cannot be judged by this v1 pass and stays silent --
   disclosed, not a silent false-negative dressed as a pass: real
   path-literal resolution (constant-folding a variable, following an
   f-string) is the same class of "needs real static analysis" cut this
   module's other two v1 joins above accept.
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
from ._host import host_manifest_for
from ._models import KernelModel, Node
from ._waive import apply_waivers

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

#: T-1060: literal string PATH argument extraction for the categories
#: that carry one -- `open(PATH, ...)` and the `os.*`/`shutil.*` calls
#: whose first argument IS the path (module docstring's WRITE
#: path-scoping section). `.write_text(`/`.write_bytes(`/`.unlink(`/
#: `.send(`/SQL DML have no path ARGUMENT to extract (the receiver is an
#: arbitrary expression, not a literal), so they are deliberately absent
#: here -- `_extract_path_literal` returns `None` for them, same as for
#: any dynamic (non-literal) path argument.
_PATH_LITERAL_RE = re.compile(
    r"""(?:open|os\.(?:remove|rename|unlink)|shutil\.(?:rmtree|move))\(\s*
        ["']([^"']+)["']""",
    re.VERBOSE,
)

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
    """Every UNWAIVED SYS205 finding, plus `waived` (T-1061: findings a
    matching `waive "SYS205:<resource>"` clause suppressed, kept here for
    report visibility, never silently dropped -- `_waive.py` module
    docstring's "waived, never silently dropped" posture every other SYS
    family already follows). Mirrors `_contention.py::
    ResourceContentionReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ModeConformanceViolation, ...] = ()
    waived: tuple[ModeConformanceViolation, ...] = ()


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


#: T-1060: an `_arbiter_identity_for` result -- `kind` is `"lock"` (match
#: against enclosing `with`-header text, the v0 mechanism unchanged) or
#: `"node"` (match against a dotted-call textual mention of the arbiter
#: node's id, module docstring's "arbitrated_by code-identity" section).
class _ArbiterIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str
    name: str


def _arbiter_identity_for(resource: ResourceDecl | None) -> _ArbiterIdentity | None:
    """The code-checkable arbiter identity for `resource` (T-1060: BOTH
    `lock` and `arbitrated_by` now resolve to something code-checkable,
    module docstring's "arbitrated_by code-identity" section) -- `None`
    when `resource` is absent or declares NEITHER, the "no code-checkable
    context" fail-closed case both ALPHA and EXCLUSIVE still share (a
    resource declaring neither is exactly as unresolvable as before)."""
    if resource is None:
        return None
    if resource.lock is not None:
        return _ArbiterIdentity(kind="lock", name=resource.lock)
    if resource.arbitrated_by is not None:
        return _ArbiterIdentity(kind="node", name=resource.arbitrated_by)
    return None


# frob:waive EXHAUST001 reason="T-1062: leaked Unknown traces to _enclosing_with_ \
# headers, a module-local generator walk over already-caught read_text() output the \
# resolver cannot see through; the one real raise path (file read) is caught below"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
def _observation_guarded_by_arbiter(
    observation: ModeObservation, root: Path, arbiter: _ArbiterIdentity
) -> bool:
    """Whether `observation`'s site is textually guarded by `arbiter`:
    for a `"lock"` identity, inside a `with` block naming it
    (`_enclosing_with_headers`, unchanged v0 mechanism); for a `"node"`
    identity (T-1060), the observation's OWN line textually calls through
    the arbiter node's id (`"{node_id}."` dotted-call prefix -- module
    docstring's disclosed textual-match limitation, not real call-graph
    resolution). Re-reads the file's lines once per call rather than
    threading a cache through, matching this module's other
    read-through-`Path` calls; call sites are bounded by the number of
    write-capable observations, not file size."""
    if arbiter.kind == "node":
        return f"{arbiter.name}." in observation.text
    path = root / observation.file
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    return any(
        arbiter.name in header
        for header in _enclosing_with_headers(lines, observation.line)
    )


# frob:waive EXHAUST001 reason="T-1062: leaked Unknown traces to _enclosing_with_ \
# headers, a module-local generator walk over already-caught read_text() output the \
# resolver cannot see through; the one real raise path (file read) is caught below"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
def _lock_reacquired(observation: ModeObservation, root: Path, lock_name: str) -> bool:
    """T-1060: whether `lock_name` appears MORE THAN ONCE in
    `observation`'s enclosing `with`-header ancestor chain -- a `with
    lock_name:` block nested inside ANOTHER `with lock_name:` block naming
    the identical lock, the textually-detectable shape of the mandate's
    ALPHA/EXCLUSIVE "upgrade-deadlock ANTI-PATTERN" (module docstring's
    point 1). Only applicable to a `"lock"` arbiter identity -- a `"node"`
    arbiter has no `with`-block context to nest at all (module docstring's
    point 2 uses a different textual convention entirely)."""
    path = root / observation.file
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    headers = _enclosing_with_headers(lines, observation.line)
    return sum(1 for header in headers if lock_name in header) > 1


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
    arbiter at all (T-1060: neither `lock` nor `arbitrated_by` -- a bare
    resource is unresolvable at the code level for either mode)."""
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
            f"{resource!r} but the resource declares neither `lock` nor "
            f"`arbitrated_by` -- no code-checkable arbiter identity exists "
            f"for it"
        ),
    )


def _unguarded_violation(
    node: Node,
    resource: str,
    mode: AccessMode,
    observation: ModeObservation,
    arbiter: _ArbiterIdentity,
) -> ModeConformanceViolation:
    """One ALPHA/EXCLUSIVE violation: a write-capable observation not
    textually guarded by `arbiter` (`_observation_guarded_by_arbiter`) --
    outside every `with <lock>:` block naming it (lock identity) or never
    calling through it (node identity, T-1060)."""
    where = (
        f"outside every `with` block naming lock {arbiter.name!r}"
        if arbiter.kind == "lock"
        else f"never textually calls through arbiter node {arbiter.name!r}"
    )
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
            f"{resource!r} but {observation.file}:{observation.line} "
            f"({observation.category}) is {where}"
        ),
    )


def _alpha_reacquire_violation(
    node: Node,
    resource: str,
    mode: AccessMode,
    observation: ModeObservation,
    lock_name: str,
) -> ModeConformanceViolation:
    """T-1060: one ALPHA/EXCLUSIVE "upgrade-deadlock anti-pattern"
    violation -- `observation` sits inside a `with lock_name:` block
    that is ITSELF nested inside another `with lock_name:` block naming
    the SAME lock (`_lock_reacquired`), the non-reentrant-lock
    self-deadlock shape the mandate's ALPHA mode exists to prevent."""
    return ModeConformanceViolation(
        rule=SYS_MODE_NONCONFORMANCE,
        node=node.id,
        resource=resource,
        mode=mode,
        file=observation.file,
        line=observation.line,
        category="alpha_reacquire_deadlock",
        detail=(
            f"node {node.id!r} declares mode={mode.value} on resource "
            f"{resource!r} but {observation.file}:{observation.line} "
            f"({observation.category}) sits inside a nested `with "
            f"{lock_name}:` block already holding the SAME lock -- the "
            f"upgrade-deadlock anti-pattern {mode.value} exists to prevent"
        ),
    )


#: T-1060 WRITE path-scoping: split a POSIX/Windows PATH into non-empty
#: segments for directory-prefix comparison -- a small local port of
#: `_contention.py::_path_segments`'s identical logic (that module is out
#: of this ticket's scope; the join here is small enough that duplicating
#: it is cheaper and more honest than reaching across module boundaries
#: for a private helper).
_PATH_SEP_RE = re.compile(r"[\\/]+")


def _path_segments(path: str) -> tuple[str, ...]:
    """Split `path` into non-empty POSIX/Windows segments (module
    docstring's WRITE path-scoping section)."""
    return tuple(segment for segment in _PATH_SEP_RE.split(path) if segment)


def _path_within_declared(candidate: str, declared_paths: tuple[str, ...]) -> bool:
    """Whether `candidate`'s segments are a prefix-or-equal match of ANY
    of `declared_paths`' segments (or vice versa) -- the same directory-
    subtree-overlap semantics `_contention.py::_paths_overlap` uses for
    SYS201, reused (duplicated, see `_path_segments`) here for WRITE mode's
    "only on declared paths" join."""
    candidate_segments = _path_segments(candidate)
    if not candidate_segments:
        return False
    for declared in declared_paths:
        declared_segments = _path_segments(declared)
        if not declared_segments:
            continue
        shorter, longer = (
            (candidate_segments, declared_segments)
            if len(candidate_segments) <= len(declared_segments)
            else (declared_segments, candidate_segments)
        )
        if longer[: len(shorter)] == shorter:
            return True
    return False


def _extract_path_literal(line: str) -> str | None:
    """The literal string PATH argument `line` passes to one of the
    path-carrying write-capable call shapes (`_PATH_LITERAL_RE`), or
    `None` if the line matches none of them or the argument is not a
    plain string literal (module docstring's WRITE path-scoping
    section)."""
    match = _PATH_LITERAL_RE.search(line)
    return match.group(1) if match else None


def _declared_write_paths(node: Node) -> tuple[str, ...]:
    """Every `owns` (POSIX) and `acl` (Windows) path `node` declares, via
    `_host.py::host_manifest_for` -- the SAME per-node "declared path"
    fact `_contention.py`'s SYS201 already reads, reused here as WRITE
    mode's path-scoping identity (module docstring). Empty when `node`
    has no host manifest at all, or declares no owns/acl paths -- the
    "nothing declared to scope WRITE against" fail-closed case."""
    manifest = host_manifest_for(node)
    if manifest is None:
        return ()
    return tuple(owns.path for owns in manifest.owns) + tuple(
        acl.path for acl in manifest.acl
    )


def _no_declared_path_violation(
    node: Node, resource: str, mode: AccessMode
) -> ModeConformanceViolation:
    """T-1060: one WRITE-mode violation: `node` declares NO `owns`/`acl`
    path claim at all, so WRITE's "only on declared paths" mandate has
    nothing to scope against -- fails closed, the same posture ALPHA/
    EXCLUSIVE's `_no_arbiter_violation` already establishes for "nothing
    code-checkable was declared"."""
    return ModeConformanceViolation(
        rule=SYS_MODE_NONCONFORMANCE,
        node=node.id,
        resource=resource,
        mode=mode,
        file="",
        line=0,
        category="no_declared_path",
        detail=(
            f"node {node.id!r} declares mode={mode.value} on resource "
            f"{resource!r} but declares no `owns`/`acl` path claim at all "
            f"-- WRITE has no declared path to scope its writes against"
        ),
    )


def _write_outside_path_violation(
    node: Node,
    resource: str,
    mode: AccessMode,
    observation: ModeObservation,
    literal_path: str,
) -> ModeConformanceViolation:
    """T-1060: one WRITE-mode violation: `observation`'s extracted literal
    path (`_extract_path_literal`) does not overlap ANY of `node`'s
    declared `owns`/`acl` paths (`_path_within_declared`)."""
    return ModeConformanceViolation(
        rule=SYS_MODE_NONCONFORMANCE,
        node=node.id,
        resource=resource,
        mode=mode,
        file=observation.file,
        line=observation.line,
        category="write_outside_declared_path",
        detail=(
            f"node {node.id!r} declares mode={mode.value} on resource "
            f"{resource!r} but {observation.file}:{observation.line} "
            f"writes to {literal_path!r}, outside every path {node.id!r} "
            f"declares via `owns`/`acl`"
        ),
    )


def _read_append_violations(
    node: Node,
    resource_id: str,
    mode: AccessMode,
    write_capable: list[ModeObservation],
) -> list[ModeConformanceViolation]:
    """READ/APPEND's join (module docstring's per-mode semantics): every
    write-capable observation fires for READ; every non-append-open
    write-capable observation fires for APPEND. Split out of `check_mode_
    conformance` purely to keep it under ARCH001's line threshold."""
    if mode is AccessMode.READ:
        return [
            _read_violation(node, resource_id, mode, observation)
            for observation in write_capable
        ]
    return [
        _append_violation(node, resource_id, mode, observation)
        for observation in write_capable
        if observation.category != _APPEND_OPEN
    ]


def _alpha_exclusive_violations(
    node: Node,
    resource_id: str,
    mode: AccessMode,
    write_capable: list[ModeObservation],
    resource: ResourceDecl | None,
    root: Path,
) -> list[ModeConformanceViolation]:
    """ALPHA/EXCLUSIVE's join (module docstring's per-mode semantics,
    T-1060's arbiter-identity + reacquire-deadlock widening). Split out
    of `check_mode_conformance` purely to keep it under ARCH001's line
    threshold."""
    arbiter = _arbiter_identity_for(resource)
    if arbiter is None:
        return [_no_arbiter_violation(node, resource_id, mode)]
    violations: list[ModeConformanceViolation] = []
    for observation in write_capable:
        if _observation_guarded_by_arbiter(observation, root, arbiter):
            if arbiter.kind == "lock" and _lock_reacquired(
                observation, root, arbiter.name
            ):
                violations.append(
                    _alpha_reacquire_violation(
                        node, resource_id, mode, observation, arbiter.name
                    )
                )
            continue
        violations.append(
            _unguarded_violation(node, resource_id, mode, observation, arbiter)
        )
    return violations


def _write_violations(
    node: Node,
    resource_id: str,
    mode: AccessMode,
    write_capable: list[ModeObservation],
) -> list[ModeConformanceViolation]:
    """WRITE's join (T-1060 path-scoping, module docstring's WRITE
    path-scoping section). Split out of `check_mode_conformance` purely
    to keep it under ARCH001's line threshold."""
    declared_paths = _declared_write_paths(node)
    if not declared_paths:
        return [_no_declared_path_violation(node, resource_id, mode)]
    violations: list[ModeConformanceViolation] = []
    for observation in write_capable:
        literal_path = _extract_path_literal(observation.text)
        if literal_path is None:
            continue  # no extractable literal, disclosed cut
        if _path_within_declared(literal_path, declared_paths):
            continue
        violations.append(
            _write_outside_path_violation(
                node, resource_id, mode, observation, literal_path
            )
        )
    return violations


def _apply_mode_conformance_waivers(
    model: KernelModel, violations: list[ModeConformanceViolation]
):  # noqa: ANN201
    """T-1061: apply every node's `waive` clause to `violations`, exactly
    `_contention.py::_apply_contention_waivers`'s pattern reused for
    SYS205 -- `sub_target_of` returns `ModeConformanceViolation.resource`
    (SYS205 is now registered in `_waive.py::MULTI_INSTANCE_WAIVER_
    FAMILIES`, so a `waive` clause naming it must carry a
    `RULE:SUBTARGET`). `in_scope` restricts staleness judgment to SYS205
    alone, matching `apply_waivers`'s own `in_scope` docstring."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.resource,
        in_scope=lambda rule: rule == SYS_MODE_NONCONFORMANCE,
    )


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
# frob:enforces CHK-GATE-SYS205
# frob:tests tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_read_mode_fails_on_a_write_open  # noqa: E501
def check_mode_conformance(
    model: KernelModel, module: Module, binding: CodeBinding, root: Path
) -> ModeConformanceReport:
    """The SYS205 mode-conformance entrypoint (T-0701, v1 T-1060): for
    every node declaring `access "RESOURCE" mode MODE`
    (`node_access_declarations`), join the declared MODE against `node`'s
    own observed write-capable operations (`_node_mode_observations`) per
    the module docstring's per-mode semantics (`_read_append_violations`/
    `_alpha_exclusive_violations`/`_write_violations`). `module` supplies
    `Module.resources` (the `lock`/`arbitrated_by` arbiter lookup
    ALPHA/EXCLUSIVE need, T-1060 widened from `lock`-only) the same way
    `_access.py::resource_contention_violations` already takes it in, for
    the same reason (`KernelModel` has no reconstructible `resource`
    block)."""
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
            if mode in (AccessMode.READ, AccessMode.APPEND):
                violations.extend(
                    _read_append_violations(node, resource_id, mode, write_capable)
                )
            elif mode in (AccessMode.ALPHA, AccessMode.EXCLUSIVE):
                violations.extend(
                    _alpha_exclusive_violations(
                        node,
                        resource_id,
                        mode,
                        write_capable,
                        resources.get(resource_id),
                        root,
                    )
                )
            elif mode is AccessMode.WRITE:
                violations.extend(
                    _write_violations(node, resource_id, mode, write_capable)
                )
    applied = _apply_mode_conformance_waivers(model, violations)
    kept = tuple(applied.kept)
    waived = tuple(wf.finding for wf in applied.waived)
    _log.info(
        "strata mode-conformance: %d SYS205 violation(s), %d waived, across %d node(s)",
        len(kept),
        len(waived),
        len(model.nodes),
    )
    return ModeConformanceReport(violations=kept, waived=waived)


__all__ = [
    "SYS_MODE_NONCONFORMANCE",
    "ModeConformanceReport",
    "ModeConformanceViolation",
    "ModeObservation",
    "check_mode_conformance",
]
