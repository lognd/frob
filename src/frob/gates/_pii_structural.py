"""PII010/SEC110: structural PII/secrets detection over Python data
structures and env-var access sites (T-0207,
docs/modules/gates.md#structural-pii-secrets-detection-t-0207).

Scope decision (investigated first, T-0150 round-1 lesson): `frob.strata.
_pii` (T-0154, PII001-004) and `frob.gates._secrets` (T-0157, SEC001-003)
already own two adjacent concerns -- PII001-004 is a DECLARATION/join layer
over strata design models (`carries "<category>.<field>"` facts an author
writes by hand), and SEC001-003 is a VALUE-shape scanner over tracked-file
text (provider token regexes). Neither module observes a data structure's
actual field names/types or a real `os.environ`/`os.getenv` call site in
Python source -- `docs/design/secrets-pii-corpus.md`'s reconciliation
section says this explicitly ("neither module has ... scanning of actual
code/config content"). This module is that missing structural layer, drawn
directly from the corpus's field-name-detectable / schema-field-name-
detectable rows (Part B.2) and A.4's `KeywordDetector`-equivalent contextual
signal -- NOT a duplicate of either existing module:

- PII010: a class field (pydantic `BaseModel`, `@dataclass`, `TypedDict`,
  `attrs`/`attr.s`) whose NAME or TYPE ANNOTATION matches an entry in
  `FIELD_SIGNATURES` (the single-source keyword/type registry below) fires
  -- deny-by-default, exactly like PII001's "unknown category" default:
  a PII-shaped field with no accompanying `frob:waive PII010 reason="..."`
  is treated as an undeclared PII surface. Joining this to a T-0154
  `carries` tag on a strata `Node` (rather than a bare waiver) is the
  natural next step this module deliberately leaves to a follow-on ticket
  (see the Done report this ticket's evidence is recorded against) --
  today's discharge mechanism is the waiver alone, honestly documented as
  the boundary of this pass, not a silent gap.
- SEC110: an `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)` call
  site is a secret-SOURCE observation (corpus Part A intro: "env/secret
  sources ... must map to a declared strata secret node (T-0082 std.secrets)
  or be waived"). Same discharge boundary as PII010: waiver only, today.

DISCIPLINE (ticket-mandated, non-negotiable):
- Single-source registry (`FIELD_SIGNATURES`): every keyword/type entry
  lives in exactly one place; `_NAME_SIGNATURES`/`_TYPE_SIGNATURES` are
  derived views, never a second hand-maintained table.
- Self-match exclusion (T-0201 lesson: "the keyword table must not detect
  itself"): `_SELF_EXCLUDED_FILES` skips this module's own path outright,
  so `FIELD_SIGNATURES`'s own keyword STRING LITERALS (e.g. `"password"`)
  can never be misread as an `AnnAssign` field name by this scanner running
  over its own source.
- Per-entry drift-lock: `tests/test_pii_structural_gate.py::TestDriftLock`
  parametrizes over `FIELD_SIGNATURES` and asserts each entry's keyword
  fires PII010 against a synthetic fixture class -- a registry entry with
  no firing fixture fails the test (T-0182 style).

Deliberately NOT built this pass (disclosed, not silently dropped -- see
this ticket's Done report for the filed follow-on ticket ids):
family (2) database/DDL schema scanning (`CREATE TABLE`, alembic
migrations, sqlalchemy `Column(...)`), family (4) email-shape value
detection (structural `email.utils.parseaddr`-based, explicitly NOT regex
per the ticket body), family (5) keyword-only suggestion-severity sweep of
identifiers/comments, and non-Python languages (TS/Rust field-shape
equivalents). `PII010`/`SEC110` cover exactly families (1) and (3), scoped
to Python via `frob.lang`'s existing parse surface.
"""

# frob:ticket T-0207
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.strata._pii import PII_CATEGORIES

_log = get_logger(__name__)

#: This module's own path relative to a repo root -- excluded from scanning
#: outright (T-0201 self-match lesson, module docstring). Compared against
#: the git-relative path `_tracked_python_files` yields.
_SELF_EXCLUDED_FILES = frozenset({"src/frob/gates/_pii_structural.py"})


@dataclass(frozen=True)
# frob:doc docs/modules/gates.md#structural-pii-secrets-detection-t-0207
class _FieldSignature:
    """One field-name-or-type keyword entry: the single source both PII010's
    scanner and its per-entry drift-lock test read from (module docstring:
    "single-source registry")."""

    id: str
    keyword: str  # matched lowercase against a `_`-tokenized field name
    category: str  # one of frob.strata._pii.PII_CATEGORIES
    kind: str  # "name" | "type" -- which signal this entry matches on


def _sig(id: str, keyword: str, category: str, kind: str = "name") -> _FieldSignature:
    """Build one `_FieldSignature`, asserting `category` is a real PII_
    CATEGORIES member so the registry can never point at a category PII001
    would itself reject (deny-by-default consistency across both gates)."""
    if category not in PII_CATEGORIES:
        raise ValueError(f"_FieldSignature {id!r}: {category!r} not in PII_CATEGORIES")
    return _FieldSignature(id=id, keyword=keyword, category=category, kind=kind)


# frob:doc docs/modules/gates.md#structural-pii-secrets-detection-t-0207
#: The single-source field-name/type keyword table (corpus Part B.2 +
#: A.4's KeywordDetector-equivalent contextual signal), drawn from
#: docs/design/secrets-pii-corpus.md. Every entry needs a firing fixture in
#: `tests/test_pii_structural_gate.py::TestDriftLock` (module docstring).
FIELD_SIGNATURES: tuple[_FieldSignature, ...] = (
    _sig("email", "email", "contact"),
    _sig("phone", "phone", "contact"),
    _sig("address", "address", "contact"),
    _sig("ssn", "ssn", "identifier"),
    _sig("social_security", "social_security", "identifier"),
    _sig("dob", "dob", "identifier"),
    _sig("date_of_birth", "date_of_birth", "identifier"),
    _sig("ip_address", "ip_address", "identifier"),
    _sig("passport", "passport", "identifier"),
    _sig("password", "password", "credentials"),
    _sig("passwd", "passwd", "credentials"),
    _sig("api_key", "api_key", "credentials"),
    _sig("apikey", "apikey", "credentials"),
    _sig("secret", "secret", "credentials"),
    _sig("token", "token", "credentials"),
    _sig("salt", "salt", "credentials"),
    _sig("card_number", "card_number", "financial"),
    _sig("pan", "pan", "financial"),
    _sig("cvv", "cvv", "financial"),
    _sig("cvc", "cvc", "financial"),
    _sig("credit_card", "credit_card", "financial"),
    _sig("bank_account", "bank_account", "financial"),
    _sig("iban", "iban", "financial"),
    _sig("diagnosis", "diagnosis", "health"),
    _sig("medical_record", "medical_record", "health"),
    # T-0353: "fingerprint" alone was over-broad -- it matched far more
    # non-biometric fingerprints (CVE/CWE catalog ids, cache/content-hash
    # digests, git commit fingerprints) than actual biometric data in this
    # codebase's own corpus (`strata/_cve_fingerprint.py`'s `fingerprint_id`
    # false-fired on adoption). Narrowed to genuinely biometric field-name
    # shapes; a bare "fingerprint" field is no longer treated as PII-shaped
    # on that word alone.
    _sig("fingerprint_scan", "fingerprint_scan", "biometric"),
    _sig("fingerprint_template", "fingerprint_template", "biometric"),
    _sig("face_embedding", "face_embedding", "biometric"),
    # Type-based signals (corpus Part B.2: EmailStr/SecretStr and TS/Rust
    # equivalents named in the ticket body -- only the Python types are
    # scoped this pass, see module docstring).
    _sig("emailstr-type", "EmailStr", "contact", kind="type"),
    _sig("secretstr-type", "SecretStr", "credentials", kind="type"),
)

#: Derived index: `_`-tokenized single-word keywords matched by exact
#: token equality (avoids "tokenizer" matching "token"); multi-word
#: (already-underscored) keywords matched by substring on the full
#: underscored name. Both derived from `FIELD_SIGNATURES` -- never a
#: second hand-authored table (module docstring: no duplication).
_NAME_SIGNATURES = tuple(sig for sig in FIELD_SIGNATURES if sig.kind == "name")
_TYPE_SIGNATURES = tuple(sig for sig in FIELD_SIGNATURES if sig.kind == "type")


def _field_name_hit(field_name: str) -> _FieldSignature | None:
    """The first `FIELD_SIGNATURES` name-kind entry `field_name` matches, or
    `None`. Single-word keywords match a whole `_`-split token; multi-word
    (underscored) keywords match as a substring of the full lowered name."""
    lowered = field_name.lower()
    tokens = set(lowered.split("_"))
    for sig in _NAME_SIGNATURES:
        if "_" in sig.keyword:
            if sig.keyword in lowered:
                return sig
        elif sig.keyword in tokens:
            return sig
    return None


def _annotation_names(node: ast.expr | None) -> set[str]:
    """Every bare `Name.id`/`Attribute.attr` appearing anywhere in an
    annotation subtree (e.g. `Optional[EmailStr]` -> `{"Optional",
    "EmailStr"}`), so a wrapped/generic annotation still surfaces its inner
    type name to `_field_type_hit`."""
    if node is None:
        return set()
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def _field_type_hit(annotation: ast.expr | None) -> _FieldSignature | None:
    """The first `FIELD_SIGNATURES` type-kind entry whose keyword appears
    among `annotation`'s names (`_annotation_names`), or `None`."""
    names = _annotation_names(annotation)
    for sig in _TYPE_SIGNATURES:
        if sig.keyword in names:
            return sig
    return None


#: Base-class / decorator name fragments that mark a `ClassDef` as a data
#: structure worth scanning (pydantic `BaseModel`, `TypedDict`,
#: `NamedTuple`, `dataclasses.dataclass`, `attrs`/`attr.s` `define`).
_STRUCTURE_BASE_NAMES = frozenset({"BaseModel", "TypedDict", "NamedTuple"})
_STRUCTURE_DECORATOR_NAMES = frozenset({"dataclass", "define", "attrs", "frozen"})


def _decorator_name(node: ast.expr) -> str | None:
    """The bare name of a decorator expression (`@dataclass` -> `dataclass`,
    `@attr.s` -> `s`, `@dataclasses.dataclass(frozen=True)` -> `dataclass`),
    or `None` for a shape this doesn't recognize."""
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def _is_data_structure(cls: ast.ClassDef) -> bool:
    """Whether `cls` is a pydantic/dataclass/TypedDict/NamedTuple/attrs data
    structure -- the population PII010 scans field names/types over."""
    for base in cls.bases:
        base_name = (
            base.id if isinstance(base, ast.Name) else getattr(base, "attr", None)
        )
        if base_name in _STRUCTURE_BASE_NAMES:
            return True
    for decorator in cls.decorator_list:
        name = _decorator_name(decorator)
        if name in _STRUCTURE_DECORATOR_NAMES:
            return True
    return False


def _pii010_violation(
    rel_path: str, lineno: int, field_name: str, sig: _FieldSignature
) -> Violation:
    """The PII010 `Violation` for one PII-shaped field, built once so both
    the name-hit and type-hit call sites share identical message wording."""
    _log.warning(
        "PII010: %s:%d field %r matches %s (%s) -- category %s",
        rel_path,
        lineno,
        field_name,
        sig.id,
        sig.kind,
        sig.category,
    )
    return Violation(
        rule="PII010",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"PII010: {rel_path}:{lineno} field {field_name!r} is PII-shaped "
            f"(matches {sig.kind} signature {sig.keyword!r}, category "
            f"{sig.category!r}) with no PII declaration or waiver -- declare "
            f"it via a std.pii `carries` tag on the owning strata node, or "
            f'`frob:waive PII010 reason="..."` if this field is not '
            f"actually personal data"
        ),
    )


def _scan_class_fields(cls: ast.ClassDef, rel_path: str) -> list[Violation]:
    """Every PII010 hit among `cls`'s direct `AnnAssign` fields, for a class
    `_is_data_structure` already accepted."""
    violations: list[Violation] = []
    for stmt in cls.body:
        if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
            continue
        field_name = stmt.target.id
        name_sig = _field_name_hit(field_name)
        type_sig = _field_type_hit(stmt.annotation)
        sig = name_sig or type_sig
        if sig is not None:
            violations.append(_pii010_violation(rel_path, stmt.lineno, field_name, sig))
    return violations


# frob:doc docs/modules/gates.md#structural-pii-secrets-detection-t-0207
def _scan_python_fields(tree: ast.Module, rel_path: str) -> tuple[Violation, ...]:
    """PII010 over every data-structure `ClassDef` in `tree` (module
    docstring: pydantic/dataclass/TypedDict/attrs field names+types)."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_data_structure(node):
            violations.extend(_scan_class_fields(node, rel_path))
    return tuple(violations)


#: Attribute/function names an env-access call site's dotted path may end
#: in, for `_is_env_access` (corpus family 3: "os.environ[...]/os.getenv/
#: load_dotenv() ... process.env, std::env::var" -- Python subset here).
_ENV_CALL_ATTRS = frozenset({"getenv"})

#: T-0353: known-non-secret env var names -- process/terminal/platform
#: plumbing that definitionally carries no secret (display server socket
#: names, terminal capability flags, interpreter/tooling paths, CI/test
#: markers). A read of a NON-allowlisted var still fires SEC110; this is a
#: precision narrowing, not a blanket mute -- every entry here is a var
#: this codebase actually reads at a site with no secret-shaped payload.
_ENV_VAR_ALLOWLIST = frozenset(
    {
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "TERM",
        "NO_COLOR",
        "FORCE_COLOR",
        "PATH",
        "LD_LIBRARY_PATH",
        "HOME",
        "LANG",
        "TZ",
        "CI",
        "PYTEST_CURRENT_TEST",
        "VIRTUAL_ENV",
        "PYO3_PYTHON",
    }
)

#: Prefix-matched allowlist entries (`XDG_*` -- base-directory-spec vars,
#: all plain filesystem-location config, never a secret).
_ENV_VAR_ALLOWLIST_PREFIXES = ("XDG_",)


def _is_allowlisted_env_var(name: str) -> bool:
    """Whether `name` is a known-non-secret env var (`_ENV_VAR_ALLOWLIST`
    exact match or `_ENV_VAR_ALLOWLIST_PREFIXES` prefix match) -- T-0353."""
    if name in _ENV_VAR_ALLOWLIST:
        return True
    return any(name.startswith(prefix) for prefix in _ENV_VAR_ALLOWLIST_PREFIXES)


def _literal_str(node: ast.expr | None) -> str | None:
    """The literal string value of `node` if it is a bare `ast.Constant`
    string, else `None` -- used to statically name the env var an access
    site targets when the argument/subscript key is a literal (T-0353's
    allowlist match), never guessed from a dynamic expression."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _subscript_key(node: ast.Subscript) -> ast.expr:
    """The key expression of `node` -- `Subscript.slice` is already the
    bare key expr on the Python 3.9+ AST this repo targets (no legacy
    `ast.Index` wrapper to unwrap)."""
    return node.slice


def _dotted_prefix(node: ast.expr) -> str | None:
    """The dotted-name text of an `Attribute`/`Name` chain (`os.environ` ->
    `"os.environ"`), or `None` for anything else -- a small, local
    unparse rather than pulling in `ast.unparse` (stdlib 3.9+; kept local
    so the exact match surface is explicit and testable in isolation)."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return None
    return ".".join(reversed(parts))


def _is_environ_subscript(node: ast.Subscript) -> bool:
    """`os.environ["X"]` / `environ["X"]` (direct-import form)."""
    dotted = _dotted_prefix(node.value)
    return dotted in ("os.environ", "environ")


def _is_env_call(node: ast.Call) -> bool:
    """`os.getenv(...)` / `getenv(...)` (direct-import form) / `os.environ.
    get(...)` / `environ.get(...)`."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in _ENV_CALL_ATTRS
    if isinstance(func, ast.Attribute):
        if func.attr in _ENV_CALL_ATTRS:
            return True
        if func.attr == "get":
            dotted = _dotted_prefix(func.value)
            return dotted in ("os.environ", "environ")
    return False


def _sec110_violation(rel_path: str, lineno: int, site: str) -> Violation:
    """The SEC110 `Violation` for one unmapped env-access site."""
    _log.warning("SEC110: %s:%d env access %s", rel_path, lineno, site)
    return Violation(
        rule="SEC110",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"SEC110: {rel_path}:{lineno} reads {site} -- an env-var read is "
            f"a secret-source observation; map it to a declared std.secrets "
            f'node (T-0082), or `frob:waive SEC110 reason="..."` if this '
            f"var carries no secret"
        ),
    )


# frob:doc docs/modules/gates.md#structural-pii-secrets-detection-t-0207
def _scan_python_env_access(tree: ast.Module, rel_path: str) -> tuple[Violation, ...]:
    """SEC110 over every `os.environ[...]`/`os.environ.get(...)`/
    `os.getenv(...)` call/subscript site in `tree` (module docstring:
    family 3, env/secret sources)."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and _is_environ_subscript(node):
            var_name = _literal_str(_subscript_key(node))
            if var_name is not None and _is_allowlisted_env_var(var_name):
                continue
            violations.append(
                _sec110_violation(rel_path, node.lineno, "os.environ[...]")
            )
        elif isinstance(node, ast.Call) and _is_env_call(node):
            var_name = _literal_str(node.args[0]) if node.args else None
            if var_name is not None and _is_allowlisted_env_var(var_name):
                continue
            site = _dotted_prefix(node.func) or getattr(node.func, "attr", "getenv")
            violations.append(_sec110_violation(rel_path, node.lineno, f"{site}(...)"))
    return tuple(violations)


def _tracked_python_files(root: Path) -> tuple[str, ...]:
    """`git ls-files -- '*.py'` under `root`, root-relative POSIX paths,
    `()` on any git failure -- mirrors `frob.gates._secrets._tracked_
    files`'s degrade-don't-crash posture (module docstring: reuse, not a
    second copy of the same subprocess dance)."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", "*.py"))
    if spawned.is_err:
        _log.error("pii_structural_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.error("pii_structural_gate: git ls-files exited %d", result.returncode)
        return ()
    return tuple(line for line in result.stdout.splitlines() if line.strip())


# frob:doc docs/modules/gates.md#structural-pii-secrets-detection-t-0207
# frob:tests tests/test_pii_structural_gate.py::TestFieldNames.test_password_field_fires
# frob:tests tests/test_pii_structural_gate.py::TestEnvAccess.test_os_getenv_fires
# frob:tests tests/test_pii_structural_gate.py::TestSelfMatchExclusion.test_own_file_not_scanned  # noqa: E501
# frob:tests tests/test_pii_structural_gate.py::TestGateIsGreenOnItself.test_own_module_source_produces_no_self_finding  # noqa: E501
def pii_structural_gate(root: Path) -> tuple[Violation, ...]:
    """PII010/SEC110 (docs/modules/gates.md#structural-pii-secrets-
    detection-t-0207): every git-tracked `.py` file scanned for PII-shaped
    data-structure fields and env-var access sites. Self-excludes this
    module's own path (`_SELF_EXCLUDED_FILES`, T-0201 lesson)."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_python_files(root):
        if rel_path in _SELF_EXCLUDED_FILES:
            _log.debug("pii_structural_gate: skipping self-excluded %s", rel_path)
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(text, filename=rel_path)
        except (OSError, UnicodeDecodeError, SyntaxError):
            _log.debug("pii_structural_gate: skipping unparseable %s", rel_path)
            continue
        scanned += 1
        violations.extend(_scan_python_fields(tree, rel_path))
        violations.extend(_scan_python_env_access(tree, rel_path))

    _log.info(
        "pii_structural_gate: scanned %d tracked .py file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)


__all__ = [
    "FIELD_SIGNATURES",
    "_FieldSignature",
    "pii_structural_gate",
    "_scan_python_env_access",
    "_scan_python_fields",
]
