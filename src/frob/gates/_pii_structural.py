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

T-0348 (family 2, DB/DDL schema scanning) extended PII010 to sqlalchemy
ORM `Column(...)` declarations (`_scan_orm_columns`) and raw-SQL `CREATE
TABLE` string literals embedded in tracked `.py` files (`_scan_ddl_
strings`), reusing the same `FIELD_SIGNATURES` table -- schema headers are
the highest-value PII surface per the umbrella ticket body.

T-0349 (family 4, email-shape values) added PII011: a git-tracked `.py`
file's string-literal constants scanned via `email.utils.parseaddr` (an
RFC 822 header parser) plus a plain character-set validation of the parsed
local/domain parts (`_is_email_shaped`) -- explicitly NOT a regex, per the
ticket body's "regex is bad for email matching" mandate. Escaped the same
way T-0157's secrets scanner escapes a fixture: a `frob:secret-fake`
comment on the literal's own line or the line directly above it
(`_line_marks_fake_email`).

Deliberately NOT built this pass (disclosed, not silently dropped -- see
this ticket's Done report for the filed follow-on ticket ids): family (5)
keyword-only suggestion-severity sweep of identifiers/comments, and non-
Python languages (TS/Rust field-shape equivalents, and non-Python DDL
sources such as `.sql` migration files). `PII010`/`PII011`/`SEC110` cover
exactly families (1), (2), (3), and (4), scoped to Python via `frob.lang`'s
existing parse surface.

T-0430 (`docs/design/registry/pii.yaml`'s six deferred sections) extended
`FIELD_SIGNATURES` toward GDPR Art.9(1) special-category / CCPA / HIPAA
Safe Harbor / PCI-DSS / NIST SP 800-122 field-name parity (corpus B.1/B.2):
account/license/vehicle/device identifiers, medical-record/beneficiary
numbers, mother's maiden name, geolocation, and the GDPR Art.9(1) special-
category demographic fields (ethnicity, political affiliation, religion,
union membership, sexual orientation, genetic data) folded into the
`behavioral` bucket per the same B.3-documented seam (no dedicated
PII_CATEGORIES bucket for these). Still not built: PCI-DSS Sensitive
Authentication Data field-name shapes (track data, PIN block -- no safe
low-FP field-name keyword identified this pass) and CCPA's non-field-
shaped categories (commercial/purchase history, internet activity,
inferences) which are behavioral-content signals, not field-name
signals -- both remain honest gaps for a follow-on ticket, not silently
dropped.
"""

# frob:ticket T-0207
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from email.utils import parseaddr
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
    # T-0430: extend field-name coverage toward GDPR/CCPA/HIPAA/PCI-DSS/
    # NIST-800-122 parity (docs/design/secrets-pii-corpus.md B.1/B.2,
    # docs/design/registry/pii.yaml's six T-0430-deferred sections).
    # HIPAA Safe Harbor identifiers #10-13 (account/certificate/license/
    # vehicle/device numbers), not previously covered by any entry above.
    _sig("account_number", "account_number", "financial"),
    _sig("drivers_license", "drivers_license", "identifier"),
    _sig("license_number", "license_number", "identifier"),
    _sig("vehicle_id", "vehicle_id", "identifier"),
    _sig("vin", "vin", "identifier"),
    _sig("imei", "imei", "identifier"),
    _sig("mac_address", "mac_address", "identifier"),
    _sig("device_serial", "device_serial", "identifier"),
    # HIPAA #8/#9 (medical record / health plan beneficiary numbers) --
    # more precise field-name shapes than the existing bare "medical_record"
    # entry, which only matches the record itself, not the beneficiary id.
    _sig("medical_record_number", "medical_record_number", "health"),
    _sig("beneficiary_id", "beneficiary_id", "health"),
    # NIST SP 800-122's explicit clause-1 direct-identifier example
    # ("mother's maiden name").
    _sig("maiden_name", "maiden_name", "identifier"),
    # GDPR Art.4(1) "location data" identifier example / CCPA (G)
    # geolocation category -- the compound field name is schema/field-name-
    # detectable per corpus B.2 even though the coordinate VALUE itself has
    # no fixed shape; a bare "latitude"/"longitude" token is left out
    # deliberately (too FP-prone against ordinary non-PII geo/graphics code
    # in this codebase and elsewhere).
    _sig("geolocation", "geolocation", "identifier"),
    # GDPR Art.9(1) special categories (items 1,2,3,4,8) with no PCI/HIPAA
    # anchor and no dedicated PII_CATEGORIES bucket (corpus B.3: the closest
    # available bucket is "behavioral", the same seam B.3 already documents
    # for CCPA (D)/(F)/(K) -- these are demographic/opinion fields, not
    # usage-pattern fields, but "behavioral" is the least-wrong of the seven
    # fixed buckets and the corpus draws no finer distinction here).
    _sig("ethnicity", "ethnicity", "behavioral"),
    _sig("political_affiliation", "political_affiliation", "behavioral"),
    _sig("religion", "religion", "behavioral"),
    _sig("union_membership", "union_membership", "behavioral"),
    _sig("sexual_orientation", "sexual_orientation", "behavioral"),
    _sig("genetic_data", "genetic_data", "behavioral"),
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


#: `Column(...)`/`sa.Column(...)` call-name fragment (family 2, T-0348):
#: sqlalchemy ORM declarative-model column declarations. Matched on the
#: bare dotted-suffix, same posture as `_decorator_name`'s bare-name match
#: (no import-alias resolution attempted -- a local, testable surface).
_COLUMN_CALL_NAME = "Column"


def _is_column_call(node: ast.Call) -> bool:
    """Whether `node` is a `Column(...)`/`sa.Column(...)`/`sqlalchemy.
    Column(...)` call (T-0348 family 2: sqlalchemy ORM column declarations)."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == _COLUMN_CALL_NAME
    if isinstance(func, ast.Attribute):
        return func.attr == _COLUMN_CALL_NAME
    return False


def _column_call_string_name(node: ast.Call) -> str | None:
    """The literal column-name string of an alembic-style positional
    `Column("name", ...)` / `sa.Column("name", ...)` call (`op.create_
    table`'s column-list form), or `None` if the first arg is not a bare
    string literal (e.g. the ORM declarative form, which has no name arg
    at all -- the assignment target name covers that case instead)."""
    if not node.args:
        return None
    return _literal_str(node.args[0])


def _scan_orm_columns(tree: ast.Module, rel_path: str) -> list[Violation]:
    """PII010 over `name = Column(...)` declarative-model assignments and
    `Column("name", ...)` alembic-style positional column declarations
    (T-0348 family 2), matched against `FIELD_SIGNATURES` the same way a
    dataclass/pydantic field name is."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_column_call(node)):
            continue
        string_name = _column_call_string_name(node)
        if string_name is not None:
            sig = _field_name_hit(string_name)
            if sig is not None:
                violations.append(
                    _pii010_violation(rel_path, node.lineno, string_name, sig)
                )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not (isinstance(node.value, ast.Call) and _is_column_call(node.value)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                sig = _field_name_hit(target.id)
                if sig is not None:
                    violations.append(
                        _pii010_violation(rel_path, node.lineno, target.id, sig)
                    )
    return violations


#: `CREATE TABLE ... (col1 TYPE, col2 TYPE, ...)` column-list extraction
#: (T-0348 family 2: raw SQL DDL embedded as a Python string literal, e.g.
#: a raw-SQL alembic migration's `op.execute("CREATE TABLE ...")`).
_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+[\"'`]?\w+[\"'`]?\s*\((.*)\)", re.IGNORECASE | re.DOTALL
)


def _split_top_level_commas(body: str) -> list[str]:
    """Split a `CREATE TABLE(...)` column-list body on top-level commas
    only -- commas nested inside a `CHECK(...)`/`DEFAULT(...)`/type-param
    parenthesized clause (e.g. `NUMERIC(10, 2)`) must not split a single
    column definition in two."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


#: DDL table-constraint keywords a column-list entry may start with instead
#: of a column name (`PRIMARY KEY (...)`, `FOREIGN KEY (...)`, etc.) -- these
#: are not column names and must not be matched against `FIELD_SIGNATURES`.
_DDL_CONSTRAINT_KEYWORDS = frozenset(
    {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}
)


def _ddl_column_names(sql: str) -> list[str]:
    """Every column NAME token in the first `CREATE TABLE(...)` statement
    found in `sql`, skipping table-constraint entries (`_DDL_CONSTRAINT_
    KEYWORDS`) -- a small structural parse, not a full SQL grammar (module
    docstring precedent: `_pii_structural` favors a targeted, testable
    surface over a general parser)."""
    match = _CREATE_TABLE_RE.search(sql)
    if match is None:
        return []
    names: list[str] = []
    for entry in _split_top_level_commas(match.group(1)):
        tokens = entry.strip().split()
        if not tokens:
            continue
        first = tokens[0].strip('"`[]')
        if first.upper() in _DDL_CONSTRAINT_KEYWORDS:
            continue
        names.append(first)
    return names


def _scan_ddl_strings(tree: ast.Module, rel_path: str) -> list[Violation]:
    """PII010 over `CREATE TABLE` column names embedded in string-literal
    constants anywhere in `tree` (T-0348 family 2: raw-SQL migrations)."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        for column_name in _ddl_column_names(node.value):
            sig = _field_name_hit(column_name)
            if sig is not None:
                violations.append(
                    _pii010_violation(rel_path, node.lineno, column_name, sig)
                )
    return violations


# frob:tests tests/test_pii_structural_gate.py::TestDdlSchema.test_orm_column_password_fires  # noqa: E501
def _scan_python_ddl(tree: ast.Module, rel_path: str) -> tuple[Violation, ...]:
    """PII010 over sqlalchemy ORM `Column(...)` declarations and raw-SQL
    `CREATE TABLE` string literals (T-0348 family 2: DB/DDL schema
    scanning, deferred from T-0207)."""
    violations = _scan_orm_columns(tree, rel_path)
    violations.extend(_scan_ddl_strings(tree, rel_path))
    return tuple(violations)


#: T-0349 (family 4) shared fake-marker convention: the SAME literal
#: substring `frob.gates._secrets._FAKE_MARKER` uses (T-0157) -- not
#: imported directly (that module's fake-detection is line/entropy-aware
#: and secret-specific; PII011's escape hatch only needs the bare marker
#: string), but kept textually identical so one comment discharges both
#: gates' fixture literals at once.
_EMAIL_FAKE_MARKER = "frob:secret-fake"


def _line_marks_fake_email(lines: list[str], lineno: int) -> bool:
    """True if the 1-indexed `lineno` line or the line directly above it
    carries `_EMAIL_FAKE_MARKER` -- mirrors `_secrets.py::_line_marks_fake`'s
    same-line-or-line-above convention (T-0157)."""
    index = lineno - 1
    if index < 0 or index >= len(lines):
        return False
    if _EMAIL_FAKE_MARKER in lines[index]:
        return True
    if index > 0 and _EMAIL_FAKE_MARKER in lines[index - 1]:
        return True
    return False


#: Structural (non-regex) local-part/domain-label character allowances for
#: `_is_email_shaped` -- RFC 5322 dot-atom-text's common subset, kept as a
#: plain character set (`str.isalnum()` plus these) rather than a pattern.
_EMAIL_LOCAL_EXTRA_CHARS = frozenset("._%+-")
_EMAIL_LABEL_EXTRA_CHARS = frozenset("-")


def _is_email_shaped(value: str) -> bool:
    """T-0349 (family 4): whether `value` is structurally an email address,
    via `email.utils.parseaddr` (an RFC 822 header parser, NOT a regex --
    the ticket body's explicit "regex is bad for email matching" mandate)
    plus a plain character-set validation of the parsed local/domain parts.
    Whitespace anywhere rules a literal out outright (an email address
    never contains a space); `parseaddr` returning a DIFFERENT address than
    `value` itself means `value` was some other RFC 822 header shape
    (`"Name <addr>"`, a bare display name, ...), not a bare email literal."""
    if not value or any(ch.isspace() for ch in value):
        return False
    _, addr = parseaddr(value)
    if addr != value:
        return False
    local, sep, domain = addr.partition("@")
    if not sep or not local or not domain or "@" in domain:
        return False
    labels = domain.split(".")
    if len(labels) < 2 or any(not label for label in labels):
        return False
    if not all(ch.isalnum() or ch in _EMAIL_LOCAL_EXTRA_CHARS for ch in local):
        return False
    for label in labels:
        if label.startswith("-") or label.endswith("-"):
            return False
        if not all(ch.isalnum() or ch in _EMAIL_LABEL_EXTRA_CHARS for ch in label):
            return False
    return True


def _pii011_violation(rel_path: str, lineno: int, value: str) -> Violation:
    """The PII011 `Violation` for one email-shaped string literal (T-0349)."""
    _log.warning("PII011: %s:%d email-shaped literal %r", rel_path, lineno, value)
    return Violation(
        rule="PII011",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"PII011: {rel_path}:{lineno} string literal {value!r} is "
            f"email-shaped (structural parseaddr match) with no PII "
            f"declaration or waiver -- declare it via a std.pii `carries` "
            f"tag on the owning strata node, mark it a fixture with a "
            f"`{_EMAIL_FAKE_MARKER}` comment on this line or the line "
            f'above, or `frob:waive PII011 reason="..."` if this is not '
            f"actually personal data"
        ),
    )


# frob:tests tests/test_pii_structural_gate.py::TestEmailShapeValues.test_email_literal_fires  # noqa: E501
def _scan_python_email_values(
    tree: ast.Module, rel_path: str, text: str
) -> tuple[Violation, ...]:
    """PII011 over every email-shaped string-literal `ast.Constant` in
    `tree` (T-0349 family 4), skipping any literal marked fake via
    `_EMAIL_FAKE_MARKER` on its own line or the line directly above."""
    lines = text.splitlines()
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if not _is_email_shaped(node.value):
            continue
        if _line_marks_fake_email(lines, node.lineno):
            continue
        violations.append(_pii011_violation(rel_path, node.lineno, node.value))
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
        violations.extend(_scan_python_ddl(tree, rel_path))
        violations.extend(_scan_python_email_values(tree, rel_path, text))

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
    "_scan_python_ddl",
    "_scan_python_email_values",
]
