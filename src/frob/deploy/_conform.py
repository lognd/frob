"""DEPLOY002/DEPLOY003: bidirectional conformance between committed deploy
scripts' MUTATION SURFACE and the design model's `HostManifest` (T-0258,
deploy epic T-0254).

DEPLOY001 (`_drift.py`) catches a hand-edit by byte-diffing the WHOLE
script against a fresh regeneration. That is gameable in one specific
way: an operator (or an attacker with commit access) can regenerate a
clean script, then hand-append or hand-remove a step, and re-run `frob
deploy generate` never again -- the digest header in the tampered file
would no longer match `manifest_digest`, so DEPLOY001 still fires in that
case, but the FAILURE MESSAGE is only "does not match regeneration",
never "why". This module gives the structural "why": it parses each
committed script's actual MUTATION SURFACE -- the set of
(kind, target) system-mutating operations it performs (`useradd`/
`groupadd`/`userdel`/`groupdel`, `mkdir`/`install`/`cp`, `chown`/
`chmod`, `cat > ... <<EOF` unit-file writes, `rm -f`/`rm -rf`,
`systemctl enable`/`disable`/`start`/`stop`) -- and compares it
bidirectionally against the EXACT set `HostManifest` declares:

- **DEPLOY002** (extra): a mutation the script performs that the
  manifest does not declare -- a smuggled extra user, path, or unit.
  This is the red-team-relevant direction: it fires even when the rest
  of the script is byte-identical to a real regeneration, so bypassing
  `frob deploy generate` and hand-appending one rogue `useradd` still
  fails `frob check`.
- **DEPLOY003** (missing): a manifest entry the script implements no
  mutation for -- an incomplete install (a declared `owns` path never
  `mkdir`/`chown`/`chmod`'d) or incomplete uninstall (a declared
  `runs_as` user never `userdel`'d).

Extraction is GENUINE SHELL TOKENIZATION, not a quoting-shaped grep
(the round-1 regex mistake -- reviewer REJECT, see the fix note below).
Each physical line (after joining backslash-newline continuations) is
tokenized with `shlex` in POSIX mode with `punctuation_chars` enabled,
split into simple commands on `;`/`&&`/`||`/`|`/`&`/`(`/`)` and shell
keyword boundaries (`if`/`then`/`else`/`elif`/`fi`/`do`/`done`/`while`/
`until`/`case`/`esac`), and each simple command's real verb is resolved
by basename-of-argv[0] AFTER stripping leading environment-variable
assignments and known wrapper commands (`env`/`sudo`/`nice`/`nohup`/
`exec`/`command`/`time`); `eval "..."` is handled by re-tokenizing its
concatenated argument as a fresh command line. This means quoting style
(bare word, single-quoted, double-quoted), a full binary path
(`/usr/sbin/useradd`), a `;`-prefixed compound (`true; useradd ...`),
an `env`/`eval` wrapper, and a line-continued target ALL resolve to the
same `(kind, target)` regardless of surface form -- the round-1 version
required a literal command name at line start plus a double-quoted
target on the SAME line, which every one of those shapes evaded
silently. Heredoc BODY lines (unit-file content between `cat > ... <<
'EOF'` and the closing marker) are still walked per-line like any other
line -- they are inert (never executed, only ever written as literal
data), so this can only ever add a spurious extra match, never hide a
real mutation; the module docstring flags this as the one honestly
narrower-than-total scope cut left, and it is FAIL-CLOSED-shaped, not
fail-open. A line the tokenizer cannot parse at all (an unterminated
quote, e.g.) is NOT silently dropped -- it is recorded as one
`kind="parse-error"` mutation, which can never match a declared
manifest entry, so it always surfaces as a DEPLOY002 rather than
vanishing.

Reused for BOTH `install.sh` and `uninstall.sh` independently -- a
tamper that only touches one script (e.g. removing uninstall's
`userdel` while leaving install untouched) is caught at the script it
actually touched, not blurred into a single install+uninstall union.

Wired into `frob check` the same "extra stage, not `frob.gates`'s
pluggable job table" shape DEPLOY001 already uses (`src/frob/gates/**`
stays out of this ticket's `scope`) -- `frob.app.check_runner` calls
`deploy_conformance_violations` directly.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._drift import _load_current_model
from ._generate import ManifestEntry, _unit_name, sorted_manifest_entries

_log = get_logger(__name__)

#: Verbs that end a simple command's argument list and start a new one
#: -- `shlex`'s `punctuation_chars` mode returns each of these as its
#: own token (multi-char operators like `&&`/`||` stay grouped), so a
#: membership test is enough; no separate multi-char handling needed.
_COMMAND_SEPARATORS = frozenset({";", "&&", "||", "|", "&", "(", ")"})

#: Shell compound-statement keywords that also end a simple command
#: (the token itself is never a real command to resolve, only a
#: boundary) -- covers the `if ... ; then ...; fi` check-then-apply
#: shape `_generate.py` renders without requiring a full shell grammar.
_COMMAND_KEYWORDS = frozenset(
    {"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "case", "esac"}
)

#: Commands that merely forward to a REAL command named later in the
#: same simple command -- stripped (along with their own leading `-`
#: flags) before verb resolution, so `env useradd "x"` and
#: `sudo useradd "x"` resolve to the same `useradd` mutation a bare
#: `useradd "x"` would.
_WRAPPER_COMMANDS = frozenset(
    {"env", "sudo", "nice", "nohup", "exec", "command", "time"}
)

#: `NAME=value` leading assignment shape (`FOO=bar useradd ...`) --
#: skipped the same way a wrapper command is, since it never names the
#: command actually being run.
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

#: Verb -> `MutationTarget.kind` for the single-target-is-the-last-
#: positional-argument shape (`useradd NAME`, `mkdir -p PATH`, `chown
#: OWNER:OWNER PATH`, ...) -- covers every verb except `rm` (target
#: kind depends on the path, `_classify_path`), `systemctl` (target is
#: NOT the last arg when a unit name is followed by more flags), and
#: `cat` (target is the `>` redirect, not a positional argument).
_LAST_POSITIONAL_KIND: dict[str, str] = {
    "useradd": "user",
    "userdel": "user",
    "groupadd": "group",
    "groupdel": "group",
    "mkdir": "path",
    "install": "path",
    "cp": "path",
    "chown": "path",
    "chmod": "path",
}

#: `systemctl` subverbs this module treats as mutating (module
#: docstring's list) -- other subverbs (`daemon-reload`, `is-active`,
#: ...) are read-only/non-mutating and deliberately produce no target.
_SYSTEMCTL_MUTATING_SUBVERBS = frozenset({"enable", "disable", "start", "stop"})

#: The one sentinel `MutationTarget` a script line frob cannot tokenize
#: at all becomes -- deliberately matches NOTHING a `HostManifest` could
#: ever declare, so an unparseable script always surfaces as DEPLOY002
#: (fail-closed) instead of silently vanishing from the extracted set.
_PARSE_ERROR_TARGET = "unparseable script line(s) present"


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
class MutationTarget(BaseModel):
    """One system-mutating (kind, target) pair extracted from a script or
    declared by a `HostManifest` -- `kind` is `"user"`, `"group"`,
    `"unit"`, or `"path"`; `target` is the username, group name, systemd
    unit name, or filesystem path the mutation acts on. The single shape
    both `extract_mutation_surface` (script side) and
    `expected_mutation_surface` (manifest side) produce, so the two are
    directly set-comparable."""

    model_config = ConfigDict(frozen=True)

    kind: str
    target: str


def _classify_path(path: str) -> MutationTarget:
    """`rm -f`/`rm -rf` and `cat > ... <<EOF` both act on a bare path --
    this is the ONE place that path is classified as a systemd `"unit"`
    (under `/etc/systemd/system/`, `.service` suffix, matching
    `_generate.py::_unit_file_path`'s exact shape) vs. a plain `"path"`
    mutation, so `extract_mutation_surface`'s two callers of it can never
    classify the same shape two different ways."""
    if path.startswith("/etc/systemd/system/") and path.endswith(".service"):
        return MutationTarget(kind="unit", target=path.rsplit("/", 1)[-1])
    return MutationTarget(kind="path", target=path)


class _TokenizeError(Exception):
    """One physical script line failed to tokenize as shell (e.g. an
    unterminated quote) -- caught by `extract_mutation_surface` and
    turned into the fail-closed `_PARSE_ERROR_TARGET` sentinel, never
    silently swallowed."""


def _tokenize_line(line: str) -> list[str]:
    """Real shell-word tokenization of one physical line via `shlex`
    (POSIX mode, `punctuation_chars` enabled so `;`/`&&`/`||`/`|`/`&`/
    `(`/`)`/`>`/`<<` surface as their own tokens instead of being
    swallowed into adjacent words) -- the ONE place a line becomes
    tokens, so every extraction path below sees the same shell-word
    boundaries a real shell would, not a regex's idea of one. Raises
    `_TokenizeError` on malformed shell (unbalanced quote) rather than
    ever returning a silently-empty token list for it."""
    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError as exc:
        raise _TokenizeError(str(exc)) from exc


def _split_commands(tokens: list[str]) -> list[list[str]]:
    """Split one line's tokens into simple commands on `_COMMAND_
    SEPARATORS` (`;`/`&&`/`||`/`|`/`&`/`(`/`)`) and `_COMMAND_KEYWORDS`
    boundaries (`if`/`then`/`fi`/...) -- so `true; useradd "x"` and
    `if ...; then useradd "x"; fi` each yield a standalone `["useradd",
    "x"]` command, the same as a bare `useradd "x"` line would."""
    commands: list[list[str]] = []
    current: list[str] = []
    for tok in tokens:
        if tok in _COMMAND_SEPARATORS or tok in _COMMAND_KEYWORDS:
            if current:
                commands.append(current)
            current = []
            continue
        current.append(tok)
    if current:
        commands.append(current)
    return commands


def _is_redirect_op(tok: str) -> bool:
    """A token made ENTIRELY of `>`/`<`/`&` characters (`>`, `>>`, `<`,
    `<<`, `>&`, `&>`, ...) -- a shell redirection operator, never a real
    positional argument."""
    return bool(tok) and all(c in "><&" for c in tok)


def _clean_positional_args(tokens: list[str]) -> list[str]:
    """A command's real positional arguments: drop `-`-prefixed flags,
    drop redirection operators AND the target token immediately after
    one (`>/dev/null`, `2>&1`, ...), and drop a bare digit token that is
    itself immediately followed by a redirection operator (the `2` in
    `2>&1`, which `shlex` tokenizes as three separate tokens). Used for
    every verb whose real target is its LAST positional argument."""
    cleaned: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok.isdigit() and i + 1 < n and _is_redirect_op(tokens[i + 1]):
            i += 3 if i + 2 < n else 2
            continue
        if _is_redirect_op(tok):
            i += 2 if i + 1 < n else 1
            continue
        if tok.startswith("-") and tok != "-":
            i += 1
            continue
        cleaned.append(tok)
        i += 1
    return cleaned


def _resolve_command(tokens: list[str]) -> tuple[str, int] | None:
    """Resolve a simple command's REAL verb: skip leading `NAME=value`
    assignments and `_WRAPPER_COMMANDS` (plus their own `-` flags), then
    return `(basename-of-argv[0], index-of-argv[0])` -- basename so a
    full path (`/usr/sbin/useradd`) resolves the same as a bare
    `useradd`. `None` when the command list is empty or is entirely
    assignments/wrappers with no real command after them."""
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if _ASSIGN_RE.match(tok):
            i += 1
            continue
        base = tok.rsplit("/", 1)[-1]
        if base in _WRAPPER_COMMANDS:
            i += 1
            while i < n and tokens[i].startswith("-"):
                i += 1
            continue
        return base, i
    return None


def _mutation_for_command(tokens: list[str]) -> set[MutationTarget]:
    """The `MutationTarget` set (0 or 1 members, except `eval` which may
    recurse into several) one simple command's tokens produce, after
    verb resolution (`_resolve_command`). `eval` re-tokenizes its own
    concatenated argument as a fresh command line (bash's own eval
    semantics: all remaining arguments are joined with spaces and
    re-parsed) so `eval "useradd x"` and `eval useradd x` both resolve
    exactly like a bare `useradd x` would."""
    resolved = _resolve_command(tokens)
    if resolved is None:
        return set()
    base, start = resolved

    if base == "eval":
        remainder = tokens[start + 1 :]
        if not remainder:
            return set()
        joined = " ".join(remainder)
        try:
            sub_tokens = _tokenize_line(joined)
        except _TokenizeError:
            return {MutationTarget(kind="parse-error", target=_PARSE_ERROR_TARGET)}
        result: set[MutationTarget] = set()
        for sub_command in _split_commands(sub_tokens):
            result |= _mutation_for_command(sub_command)
        return result

    args = tokens[start + 1 :]

    if base in _LAST_POSITIONAL_KIND:
        cleaned = _clean_positional_args(args)
        if not cleaned:
            return set()
        return {MutationTarget(kind=_LAST_POSITIONAL_KIND[base], target=cleaned[-1])}

    if base == "rm":
        cleaned = _clean_positional_args(args)
        if not cleaned:
            return set()
        return {_classify_path(cleaned[-1])}

    if base == "systemctl":
        cleaned = _clean_positional_args(args)
        if len(cleaned) < 2 or cleaned[0] not in _SYSTEMCTL_MUTATING_SUBVERBS:
            return set()
        unit = cleaned[-1].rsplit("/", 1)[-1]
        return {MutationTarget(kind="unit", target=unit)}

    if base == "cat":
        for i, tok in enumerate(args):
            if tok == ">" and i + 1 < len(args):
                return {_classify_path(args[i + 1])}
        return set()

    return set()


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
# frob:tests tests/unit/deploy/test_conform.py::TestExtract.test_install kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestExtract.test_no_heredoc kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestEvasion.test_bare_word kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestEvasion.test_eval_wrap kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestEvasion.test_line_cont kind="unit"
def extract_mutation_surface(text: str) -> frozenset[MutationTarget]:
    """Parse one script's text into its full `MutationTarget` set via
    GENUINE shell tokenization (module docstring, `_tokenize_line`/
    `_split_commands`/`_resolve_command`/`_mutation_for_command`) --
    every `useradd`/`groupadd`/`userdel`/`groupdel`/`mkdir`/`install`/
    `cp`/`chown`/`chmod`/`rm -f`/`rm -rf`/`systemctl enable|disable|
    start|stop`/unit-file heredoc-write mutation resolves to its
    `(kind, target)` regardless of quoting style, full binary path,
    `;`-prefixed compound, `env`/`eval` wrapper, or line-continued
    target -- ordinary shell idioms an anchored-regex-with-quoting-
    requirement misses (the round-1 mistake this module was rewritten
    to fix)."""
    joined = text.replace("\\\n", " ")
    targets: set[MutationTarget] = set()
    for line in joined.splitlines():
        try:
            tokens = _tokenize_line(line)
        except _TokenizeError:
            targets.add(MutationTarget(kind="parse-error", target=_PARSE_ERROR_TARGET))
            continue
        for command in _split_commands(tokens):
            targets |= _mutation_for_command(command)
    return frozenset(targets)


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
# frob:tests tests/unit/deploy/test_conform.py::TestExpected.test_from_host kind="unit"
def expected_mutation_surface(
    entries: tuple[ManifestEntry, ...],
) -> frozenset[MutationTarget]:
    """The mutation surface a conformant install/uninstall script pair
    must exactly cover, derived straight from `HostManifest` facts: one
    `("user", <runs_as>)` per declared service user, one
    `("unit", <_unit_name(node_id)>)` per `is_unit`-marked entry (the
    SAME naming rule `_generate.py` renders scripts with -- never an
    independently re-derived name), and one `("path", <path>)` per
    declared `owns` entry."""
    targets: set[MutationTarget] = set()
    for entry in entries:
        if entry.manifest.runs_as is not None:
            targets.add(MutationTarget(kind="user", target=entry.manifest.runs_as))
        if entry.manifest.is_unit:
            targets.add(MutationTarget(kind="unit", target=_unit_name(entry.node_id)))
        for owns in entry.manifest.owns:
            targets.add(MutationTarget(kind="path", target=owns.path))
    return frozenset(targets)


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
class ConformanceViolation(BaseModel):
    """One DEPLOY002 (script mutation not declared in the manifest) or
    DEPLOY003 (manifest entry no script mutation implements) finding,
    reported with the exact file/kind/target so the fix is unambiguous:
    either add the missing manifest declaration / regenerate (DEPLOY003),
    or remove the unauthorized script mutation (DEPLOY002)."""

    model_config = ConfigDict(frozen=True)

    code: str
    file: str
    kind: str
    target: str
    message: str


def _script_conformance(
    filename: str, text: str, declared: frozenset[MutationTarget]
) -> list[ConformanceViolation]:
    """DEPLOY002 (extras) + DEPLOY003 (misses) for one script's
    `extract_mutation_surface` against the manifest's `declared` set --
    the one comparison both `install.sh` and `uninstall.sh` are run
    through independently by `deploy_conformance_violations`, so a tamper
    isolated to one script is reported against that script, not
    laundered through a combined install+uninstall union."""
    found = extract_mutation_surface(text)
    violations: list[ConformanceViolation] = []
    for mt in sorted(found - declared, key=lambda t: (t.kind, t.target)):
        _log.error(
            "deploy conformance: deploy/%s mutates %s %r, not declared in "
            "HostManifest (DEPLOY002)",
            filename,
            mt.kind,
            mt.target,
        )
        violations.append(
            ConformanceViolation(
                code="DEPLOY002",
                file=f"deploy/{filename}",
                kind=mt.kind,
                target=mt.target,
                message=(
                    f"deploy/{filename} mutates {mt.kind} {mt.target!r}, which "
                    "is not declared anywhere in the design model's "
                    "HostManifest -- unauthorized/smuggled mutation"
                ),
            )
        )
    for mt in sorted(declared - found, key=lambda t: (t.kind, t.target)):
        _log.error(
            "deploy conformance: HostManifest declares %s %r but deploy/%s "
            "implements no mutation for it (DEPLOY003)",
            mt.kind,
            mt.target,
            filename,
        )
        violations.append(
            ConformanceViolation(
                code="DEPLOY003",
                file=f"deploy/{filename}",
                kind=mt.kind,
                target=mt.target,
                message=(
                    f"HostManifest declares {mt.kind} {mt.target!r} but "
                    f"deploy/{filename} implements no mutation for it -- "
                    "incomplete install/uninstall"
                ),
            )
        )
    return violations


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
# frob:tests tests/unit/deploy/test_conform.py::TestConform.test_clean_pass kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestConform.test_no_dir kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestConform.test_extra_002 kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestConform.test_missing_003 kind="unit"
def deploy_conformance_violations(root: Path) -> tuple[ConformanceViolation, ...]:
    """DEPLOY002/DEPLOY003: every committed `deploy/install.sh` and
    `deploy/uninstall.sh` mutation checked bidirectionally against the
    CURRENT design model's `HostManifest` set (module docstring). Opt-in
    on `deploy/` existing, mirroring DEPLOY001's posture (`_drift.py`);
    returns `()` (clean) when the directory is absent, when no design
    model loads, or when every present script's mutation surface matches
    the manifest exactly in both directions."""
    deploy_dir = root / "deploy"
    if not deploy_dir.is_dir():
        _log.debug("deploy conformance: no deploy/ directory, skipping")
        return ()

    model = _load_current_model(root)
    if model is None:
        return ()

    entries = sorted_manifest_entries(model)
    declared = expected_mutation_surface(entries)

    violations: list[ConformanceViolation] = []
    for filename in ("install.sh", "uninstall.sh"):
        path = deploy_dir / filename
        if not path.exists():
            _log.debug("deploy conformance: %s not committed, skipping", filename)
            continue
        text = path.read_text(encoding="utf-8")
        violations.extend(_script_conformance(filename, text, declared))

    _log.info(
        "deploy conformance: checked %d declared mutation target(s), %d violation(s)",
        len(declared),
        len(violations),
    )
    return tuple(violations)


__all__ = [
    "ConformanceViolation",
    "MutationTarget",
    "deploy_conformance_violations",
    "expected_mutation_surface",
    "extract_mutation_surface",
]
