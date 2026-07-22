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
  is treated as an undeclared PII surface, UNLESS the file is already
  code-bound to a strata `Node` `carries`-ing that same category (T-0351,
  `_load_declared_surface`/`_DeclaredSurface._has_pii`) -- a real
  declaration now discharges the finding outright, not just a waiver.
- SEC110: an `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)` call
  site is a secret-SOURCE observation (corpus Part A intro: "env/secret
  sources ... must map to a declared strata secret node (T-0082 std.secrets)
  or be waived"). Same T-0351 join as PII010: a file code-bound to a
  Secret-clearance node (`DesignIds.secrets`'s existing "best-effort
  standing proxy for std.secrets" convention, reused here rather than
  re-derived) discharges every SEC110 finding in it
  (`_DeclaredSurface._has_secret`).

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

T-0350 (family 5, keyword sweep) added PII012: every plain identifier
(variable/parameter/function name, `_scan_identifier_keywords`) and every
`#`-comment word token (`_scan_comment_keywords`) matching a
`FIELD_SIGNATURES` name-kind keyword, EXCLUDING sites PII010 already
reports on (a bare local variable or parameter named `password` is a
weaker signal than a declared data-structure field -- "no hard fail on
names alone" per the ticket body). Fires at WARN ("suggestion") severity,
the same severity `frob check` already treats as non-failing by default --
this family is explicitly advisory, never a deny-by-default surface the
way PII010/PII011/SEC110 are.

T-0351 joined every PII010/SEC110 finding to a loaded strata design's
std.pii/std.secrets declarations (`_load_declared_surface`): the SAME
tier-2 code-binding join `sys_gate`'s SYS003 already uses (`bind_code`,
reused not re-derived) resolves each finding's file to an owning `Node`;
`frob.strata._pii.node_pii_tags` supplies that node's declared PII
categories (PII010's join key) and `Node.clearance == "Secret"` supplies
the std.secrets proxy (SEC110's join key, the exact convention
`_design_load.DesignIds.secrets` already documents). A repo with no
strata design directory degrades to `_EMPTY_DECLARED_SURFACE` -- every
finding still fires exactly as before this ticket, waiver-only. PII011/
PII012 are NOT joined this pass (disclosed, not silently dropped): PII011
fires on a bare string-literal VALUE with no natural "owning field" to
carry a category tag against, and PII012 is already suggestion-severity
advisory, not a deny-by-default surface a declaration needs to discharge.

Deliberately NOT built this pass (disclosed, not silently dropped -- see
this ticket's Done report for the filed follow-on ticket ids): non-Python
languages (TS/Rust field-shape equivalents, and non-Python DDL sources
such as `.sql` migration files). `PII010`/`PII011`/`PII012`/`SEC110` cover
exactly families (1) through (5), scoped to Python via `frob.lang`'s
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
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_pii_structural.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

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
from frob.strata._code_binding import bind_code
from frob.strata._design_load import load_design_ids
from frob.strata._pii import PII_CATEGORIES, node_pii_tags
from frob.vet._capability import is_self_pattern_path

_log = get_logger(__name__)

#: This module's own path relative to a repo root -- excluded from scanning
#: outright (T-0201 self-match lesson, module docstring). Compared against
#: the git-relative path `_tracked_python_files` yields.
_SELF_EXCLUDED_FILES = frozenset({"src/frob/gates/_pii_structural.py"})

# T-0539: the PII011/PII012 warn-pool histogram showed the overwhelming
# majority of findings landing on this gate's OWN detector-definition
# sources, the sibling secrets/fingerprint detectors' pattern tables, and
# those detectors' DEDICATED test/fixture files -- the exact self-match
# class T-0253's `is_self_pattern_path` discriminator already solved for
# `frob.vet._capability`'s SYS100 (a static-analysis tool's own keyword/
# needle tables and the tests that assert those tables fire legitimately
# CONTAIN the keyword text they detect). Reused here via `is_self_pattern_
# path`'s new `suffixes` parameter -- the SAME root-identity-gated
# discriminator (`_is_frob_repo_root` + path-suffix match), a second
# suffix list, not a second implementation. A genuine keyword hit in
# ordinary application code is NOT in this list and still fires.
_PII_SELF_PATTERN_SUFFIXES: tuple[tuple[str, ...], ...] = (
    ("frob", "gates", "_pii_structural.py"),
    ("frob", "gates", "_secrets.py"),
    ("frob", "strata", "_secrets.py"),
    ("frob", "gates", "_cve_fingerprint_scan.py"),
    ("frob", "strata", "_cve_fingerprint.py"),
    ("tests", "test_secrets_gate.py"),
    ("tests", "test_pii_structural_gate.py"),
    ("tests", "unit", "strata", "test_secrets.py"),
    ("tests", "unit", "strata", "test_cve_fingerprint_scan.py"),
    ("tests", "unit", "strata", "test_compliance.py"),
    ("tests", "unit", "strata", "test_litmus_deploy_secret.py"),
)


def _is_pii_self_pattern_file(root: Path, rel_path: str) -> bool:
    """Whether `rel_path` (root-relative) is a PII011/PII012 detector-
    definition/pattern-table/corpus/fixture self-match file (T-0539),
    via the shared `is_self_pattern_path` discriminator gated on `root`
    actually being frob's own repo checkout -- never true when scanning
    a third-party tree (e.g. `frob vet`'s dependency scan, if this gate
    is ever reused there)."""
    return is_self_pattern_path(
        root / rel_path, root, suffixes=_PII_SELF_PATTERN_SUFFIXES
    )


# RFC 2606 reserves `example.com`/`example.net`/`example.org` (plus the
# `.example` TLD) for documentation and testing use -- no real person can
# ever be registered there, so an email literal at one of these domains is
# STRUCTURALLY guaranteed non-personal regardless of what file it appears
# in (T-0539: 57 of this gate's 66 PII011 findings were exactly this
# shape, `test@example.com`/`legal@example.com`/`t@example.com`, spread
# across dozens of ordinary test files with no `frob:secret-fake` marker).
# This is a VALUE-shape fact like `_is_email_shaped` itself, not a file
# exclusion -- reused wherever the literal appears, not gated on path.
_RFC2606_RESERVED_EMAIL_DOMAINS = frozenset(
    {"example.com", "example.net", "example.org"}
)
_RFC2606_RESERVED_EMAIL_SUFFIX = ".example"


def _is_reserved_test_domain_email(value: str) -> bool:
    """True if `value`'s domain part is an RFC 2606 reserved documentation/
    testing domain (`_RFC2606_RESERVED_EMAIL_DOMAINS`/`_RFC2606_RESERVED_
    EMAIL_SUFFIX`) -- such an address can never resolve to a real person,
    so PII011 must not fire on it no matter where it appears."""
    domain = value.rpartition("@")[2].lower()
    if domain in _RFC2606_RESERVED_EMAIL_DOMAINS:
        return True
    return domain.endswith(_RFC2606_RESERVED_EMAIL_SUFFIX)


@dataclass(frozen=True)
class _DeclaredSurface:
    """T-0351: the per-file std.pii/std.secrets JOIN target -- which PII
    categories a code-bound strata `Node` already `carries` for a file, and
    whether a code-bound node for a file is a Secret-clearance node
    (`load_design_ids`'s existing "Secret-clearance node is the best-effort
    standing proxy for std.secrets" convention, `_design_load.py`'s
    `DesignIds.secrets` docstring -- reused here, not re-derived). A finding
    whose file already resolves to a matching declaration is DISCHARGED
    (no violation emitted) rather than merely waived -- the whole point of
    this ticket: a real declaration, not a bare `frob:waive`, is now a
    legitimate way to clear PII010/SEC110."""

    pii_categories: dict[str, frozenset[str]]
    secret_files: frozenset[str]

    def _has_pii(self, rel_path: str, category: str) -> bool:
        """Whether `rel_path`'s code-bound node already `carries` `category`."""
        return category in self.pii_categories.get(rel_path, frozenset())

    def _has_secret(self, rel_path: str) -> bool:
        """Whether `rel_path` is code-bound to a Secret-clearance node."""
        return rel_path in self.secret_files


#: The empty join target -- every scan function defaults to this so a repo
#: with no strata design directory (or no matching bindings) behaves
#: exactly as before T-0351 (every PII010/SEC110 site still fires,
#: waiver-only discharge).
_EMPTY_DECLARED_SURFACE = _DeclaredSurface(pii_categories={}, secret_files=frozenset())


# frob:tests tests/test_pii_structural_gate.py::TestDeclaredSurfaceJoin.test_pii010_discharged_by_matching_carries_tag  # noqa: E501
def _load_declared_surface(root: Path) -> _DeclaredSurface:
    """Load every `.strata` design file under `root` (`load_design_ids`,
    the SAME loader `sys_gate` already uses -- no second design-loading
    path) and join each file's tier-2 code-binding owner node
    (`bind_code`) to that node's `carries` PII tags (`node_pii_tags`) and
    Secret-clearance status (T-0351). A repo with no design directory, or
    whose design fails to load/bind, degrades to `_EMPTY_DECLARED_SURFACE`
    (never a crash -- gates degrade, they don't fail closed on a missing
    optional feature)."""
    design_ids = load_design_ids(root)
    pii_categories: dict[str, set[str]] = {}
    secret_files: set[str] = set()
    for model in design_ids.models:
        bound = bind_code(model, root)
        if bound.is_err:
            _log.warning(
                "_load_declared_surface: code binding ambiguous, skipping a model: %s",
                bound.danger_err,
            )
            continue
        nodes_by_id = {node.id: node for node in model.nodes}
        for rel_path, node_id in bound.danger_ok.owner.items():
            node = nodes_by_id.get(node_id)
            if node is None:
                continue
            for tag in node_pii_tags(node):
                category = tag.split(".", 1)[0]
                pii_categories.setdefault(rel_path, set()).add(category)
            if node.clearance == "Secret":
                secret_files.add(rel_path)
    _log.info(
        "_load_declared_surface: %d file(s) with declared PII categories, "
        "%d file(s) code-bound to a Secret-clearance node",
        len(pii_categories),
        len(secret_files),
    )
    return _DeclaredSurface(
        pii_categories={path: frozenset(cats) for path, cats in pii_categories.items()},
        secret_files=frozenset(secret_files),
    )


# frob:waive COV007 reason="docs/modules/gates.md's Public API section \
# also individually frob:describes this private dataclass by name \
# (T-0529) -- a deliberate architecture doc, not accidental drift onto a \
# private helper"
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


def _scan_class_fields(
    cls: ast.ClassDef,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> list[Violation]:
    """Every PII010 hit among `cls`'s direct `AnnAssign` fields, for a class
    `_is_data_structure` already accepted -- skipping any field whose
    category `declared` (T-0351) already `carries` for this file."""
    violations: list[Violation] = []
    for stmt in cls.body:
        if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
            continue
        field_name = stmt.target.id
        name_sig = _field_name_hit(field_name)
        type_sig = _field_type_hit(stmt.annotation)
        sig = name_sig or type_sig
        if sig is not None and not declared._has_pii(rel_path, sig.category):
            violations.append(_pii010_violation(rel_path, stmt.lineno, field_name, sig))
    return violations


def _scan_python_fields(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> tuple[Violation, ...]:
    """PII010 over every data-structure `ClassDef` in `tree` (module
    docstring: pydantic/dataclass/TypedDict/attrs field names+types),
    joined against `declared`'s std.pii carries tags (T-0351)."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_data_structure(node):
            violations.extend(_scan_class_fields(node, rel_path, declared))
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


def _scan_orm_columns(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> list[Violation]:
    """PII010 over `name = Column(...)` declarative-model assignments and
    `Column("name", ...)` alembic-style positional column declarations
    (T-0348 family 2), matched against `FIELD_SIGNATURES` the same way a
    dataclass/pydantic field name is; joined against `declared` (T-0351)."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_column_call(node)):
            continue
        string_name = _column_call_string_name(node)
        if string_name is not None:
            sig = _field_name_hit(string_name)
            if sig is not None and not declared._has_pii(rel_path, sig.category):
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
                if sig is not None and not declared._has_pii(rel_path, sig.category):
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


def _scan_ddl_strings(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> list[Violation]:
    """PII010 over `CREATE TABLE` column names embedded in string-literal
    constants anywhere in `tree` (T-0348 family 2: raw-SQL migrations),
    joined against `declared` (T-0351)."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        for column_name in _ddl_column_names(node.value):
            sig = _field_name_hit(column_name)
            if sig is not None and not declared._has_pii(rel_path, sig.category):
                violations.append(
                    _pii010_violation(rel_path, node.lineno, column_name, sig)
                )
    return violations


# frob:tests tests/test_pii_structural_gate.py::TestDdlSchema.test_orm_column_password_fires  # noqa: E501
def _scan_python_ddl(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> tuple[Violation, ...]:
    """PII010 over sqlalchemy ORM `Column(...)` declarations and raw-SQL
    `CREATE TABLE` string literals (T-0348 family 2: DB/DDL schema
    scanning, deferred from T-0207)."""
    violations = _scan_orm_columns(tree, rel_path, declared)
    violations.extend(_scan_ddl_strings(tree, rel_path, declared))
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
        if _is_reserved_test_domain_email(node.value):
            continue
        if _line_marks_fake_email(lines, node.lineno):
            continue
        violations.append(_pii011_violation(rel_path, node.lineno, node.value))
    return tuple(violations)


#: T-0350 (family 5) word-token extraction for a single comment string --
#: NOT the email-shape ban on regex (that ban is specific to family 4's
#: value-shape match); a bare `[A-Za-z_]+` run split is a tokenizer, not a
#: value-shape detector, the same kind of split `_field_name_hit` already
#: does via `str.split("_")` for identifiers.
_COMMENT_WORD_RE = re.compile(r"[A-Za-z_]+")


def _pii012_violation(
    rel_path: str, lineno: int, token: str, sig: _FieldSignature
) -> Violation:
    """The PII012 `Violation` for one keyword-sweep hit (T-0350 family 5) --
    SUGGESTION-level signal: an identifier or comment word alone is never
    proof of an actual PII surface (module docstring: "no hard fail on
    names alone"), so this fires at the same WARN severity `frob check`
    already treats as non-failing by default, explicitly worded as a
    suggestion rather than a declared-surface finding."""
    _log.warning(
        "PII012: %s:%d keyword-sweep hit %r matches %s (%s) -- category %s",
        rel_path,
        lineno,
        token,
        sig.id,
        sig.kind,
        sig.category,
    )
    return Violation(
        rule="PII012",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"PII012 (suggestion): {rel_path}:{lineno} identifier/comment "
            f"token {token!r} resembles a PII-shaped keyword (matches "
            f"{sig.kind} signature {sig.keyword!r}, category "
            f"{sig.category!r}) -- worth a second look, not a confirmed "
            f"PII surface on a name alone; declare via std.pii if this "
            f"really does carry personal data, or `frob:waive PII012 "
            f'reason="..."` to quiet a false positive'
        ),
    )


def _is_data_structure_field_target(node: ast.AST) -> bool:
    """Whether `node` is the `Name` target of an `AnnAssign` field already
    covered by PII010 (`_scan_class_fields`) -- excluded from the family-5
    keyword sweep so the same field name is not reported twice under two
    different rule ids for the identical site."""
    return (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and _field_name_hit(node.target.id) is not None
    )


#: T-0540: PII012's identifier/comment sweep is suggestion-only WARN
#: (module docstring: "no hard fail on names alone") and still fired
#: broadly on two overloaded single-word `FIELD_SIGNATURES` keywords --
#: "token" (a LEXER/parser/AST/git-ref/shell-command/LLM-context-budget
#: token throughout this codebase's OWN tooling -- `frob.dup`'s duplicate-
#: code tokenizer, `frob.lang`'s tree-sitter walkers, `frob.gates._refs`'s
#: symref tokens, `frob.map`'s LLM context-length estimate -- never an
#: auth token at any site below) and "secret" (this codebase's OWN
#: std.secrets DECLARATION construct -- `frob.graph.EdgeKind.SECRET`, a
#: strata Secret-clearance node id, or elaboration/threat-model prose
#: describing that construct -- never a literal secret value). A handful
#: of unrelated single-site homonyms round out the table: `passwd`/
#: `passwd_added`/`passwd_removed` (raw `/etc/passwd` text captured for
#: deploy-state diffing, already PII010-waived at the same fields per
#: T-0539's precedent -- no real password ever lives in `/etc/passwd`);
#: `run_diagnosis`/`test_run_diagnosis_*` (this codebase's own `frob
#: doctor` self-diagnostic feature name, docs/guides/install.md); `email`
#: (a docstring's tag-format EXAMPLE string `"identifier.email"`, not a
#: data-structure field); `_cve_fingerprint_scan` (a MODULE NAME mentioned
#: in a prose comment, not a biometric scan); `password` (a CWE catalog
#: entry TITLE string, `strata/_threat.py`'s WeaknessEntry table).
#:
#: `FIELD_SIGNATURES` itself is deliberately NOT narrowed for "token" or
#: "secret" (module docstring: single-source registry shared with
#: PII010's field scan, where a field genuinely named `token`/`secret` on
#: a real data structure must remain deny-by-default) -- this table
#: exempts PII012's weaker identifier/comment signal ONLY, one (file,
#: identifier) site at a time, each individually read at its call site
#: before being added here (T-0540 Done report), never a blanket keyword
#: mute. Matched on the identifier TEXT, not the line number, so a later
#: refactor that only shifts line numbers does not silently widen the
#: exemption -- a brand-new identifier introduced at the same site still
#: fires and gets its own review.
_PII012_REVIEWED_NON_PII: frozenset[tuple[str, str]] = frozenset(
    {
        # "token" homonym.
        ("src/frob/app/stats_runner.py", "_agentic_ticket_and_token_lines"),
        ("src/frob/app/telemetry.py", "token"),
        ("src/frob/arch/_python.py", "_TYPE_TOKEN_RE"),
        ("src/frob/arch/_python.py", "token"),
        ("src/frob/deploy/_conform.py", "token"),
        ("src/frob/dup/_exhaustiveness.py", "token"),
        ("src/frob/dup/_legacy_cpp.py", "_cpp_leaf_token"),
        ("src/frob/dup/_legacy_py.py", "_leaf_token"),
        ("src/frob/dup/_pipeline.py", "TOKEN"),
        ("src/frob/dup/_pipeline.py", "token"),
        ("src/frob/gates/__init__.py", "token"),
        ("src/frob/gates/_docblocks.py", "token"),
        ("src/frob/gates/_refs.py", "token"),
        ("src/frob/gates/_registry_exhaustiveness.py", "token"),
        ("src/frob/graph/dsl.py", "token"),
        ("src/frob/lang/_extract.py", "token"),
        ("src/frob/lang/_models.py", "token"),
        ("src/frob/lang/_walk_rust.py", "token_tree"),
        ("src/frob/map/__init__.py", "_CHARS_PER_TOKEN"),
        ("src/frob/map/__init__.py", "token"),
        ("src/frob/perf/_recursion.py", "Token"),
        ("src/frob/perf/_rules.py", "token"),
        ("src/frob/strata/_threat.py", "_CWE_ID_TOKEN"),
        ("src/frob/strata/_threat.py", "_RULE_ID_TOKEN"),
        ("src/frob/strata/_threat.py", "token"),
        ("src/frob/vet/_capability.py", "token"),
        ("src/frob/vet/_capability_registry.py", "token"),
        ("src/frob/vet/_hook.py", "token"),
        ("src/frob/xref/__init__.py", "token"),
        ("tests/test_dup.py", "token"),
        ("tests/test_gates.py", "token"),
        ("tests/test_graph.py", "token"),
        (
            "tests/test_perf_rules_internals.py",
            "test_operand_names_non_identifier_token_is_empty",
        ),
        ("tests/test_vet.py", "token"),
        (
            "tests/unit/strata/test_threat.py",
            "test_free_text_with_no_recognizable_token_passes",
        ),
        (
            "tests/unit/test_dup_core.py",
            "test_different_token_streams_hash_differently",
        ),
        ("tests/unit/test_dup_core.py", "test_identical_token_streams_hash_equal"),
        # "secret" homonym.
        ("src/frob/gates/__init__.py", "SECRET"),
        ("src/frob/gates/__init__.py", "secret"),
        ("src/frob/graph/_models.py", "SECRET"),
        ("src/frob/graph/_models.py", "Secret"),
        ("src/frob/graph/dsl.py", "Secret"),
        ("src/frob/graph/dsl.py", "secret"),
        ("src/frob/strata/_design_load.py", "secret"),
        ("src/frob/strata/_elaborate.py", "secret_expansions"),
        ("src/frob/strata/_facts.py", "secret_store"),
        ("src/frob/strata/_threat.py", "secret"),
        ("tests/test_telemetry.py", "test_redact_command_hides_recognizable_secret"),
        (
            "tests/test_telemetry_hook_script.py",
            "test_hook_redacts_secret_looking_input",
        ),
        ("tests/unit/graph/test_dsl.py", "test_secret_fake_is_silently_skipped"),
        ("tests/unit/strata/test_elaborate.py", "secret"),
        ("tests/unit/strata/test_elaborate.py", "secret_node"),
        (
            "tests/unit/strata/test_elaborate.py",
            "test_duplicate_secret_id_fails_closed",
        ),
        (
            "tests/unit/strata/test_elaborate.py",
            "test_secret_desugars_to_issue_revoke_reads_and_readers_claim",
        ),
        (
            "tests/unit/strata/test_elaborate.py",
            "test_secret_missing_revoke_fails_closed",
        ),
        (
            "tests/unit/strata/test_elaborate.py",
            "test_secret_unknown_issuer_fails_closed",
        ),
        (
            "tests/unit/strata/test_pii.py",
            "test_secret_label_is_at_or_above_pii_and_is_clean",
        ),
        # Single-site homonyms, one disposition each (see block comment).
        ("src/frob/deploy/_audit.py", "passwd_added"),
        ("src/frob/deploy/_audit.py", "passwd_removed"),
        ("src/frob/deploy/_vm_runner.py", "passwd"),
        ("tests/unit/deploy/test_audit.py", "passwd"),
        ("src/frob/doctor.py", "run_diagnosis"),
        ("tests/test_doctor.py", "test_run_diagnosis_natives_present"),
        ("tests/test_doctor.py", "test_run_diagnosis_natives_absent"),
        ("tests/test_doctor.py", "test_run_diagnosis_partial_availability"),
        ("tests/test_doctor.py", "test_run_diagnosis_reports_frob_version"),
        ("src/frob/strata/_pii.py", "email"),
        ("src/frob/gates/__init__.py", "_cve_fingerprint_scan"),
        ("src/frob/strata/_threat.py", "password"),
    }
)


def _is_pii012_reviewed_non_pii(rel_path: str, token: str) -> bool:
    """Whether `(rel_path, token)` is a manually-reviewed, dispositioned
    non-PII homonym site (`_PII012_REVIEWED_NON_PII`, T-0540) -- exact
    (file, identifier-text) match only, so a differently-named identifier
    at the same site (or the same identifier at a new site) is not
    silently covered by an unrelated review."""
    return (rel_path, token) in _PII012_REVIEWED_NON_PII


def _scan_identifier_keywords(tree: ast.Module, rel_path: str) -> list[Violation]:
    """PII012 over every plain identifier (variable/parameter/function
    name) matching a `FIELD_SIGNATURES` name-kind keyword, EXCLUDING sites
    `_scan_python_fields` (PII010) already reports on -- T-0350 family 5:
    "identifier/comment keyword hits", the broader, weaker-signal
    population PII010's data-structure-field scan deliberately excludes
    (a bare local variable, function parameter, or plain-class attribute
    named `password` is not itself a declared data-structure field) --
    and EXCLUDING `_PII012_REVIEWED_NON_PII` sites (T-0540)."""
    already_covered: set[int] = {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and _is_data_structure_field_target(node)
    }
    seen: set[tuple[int, str]] = set()
    violations: list[Violation] = []
    for node in ast.walk(tree):
        name: str | None = None
        lineno = 0
        if isinstance(node, ast.arg):
            name, lineno = node.arg, node.lineno
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name, lineno = node.name, node.lineno
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            name, lineno = node.id, node.lineno
        if name is None or lineno in already_covered:
            continue
        sig = _field_name_hit(name)
        if sig is None:
            continue
        if _is_pii012_reviewed_non_pii(rel_path, name):
            continue
        key = (lineno, name)
        if key in seen:
            continue
        seen.add(key)
        violations.append(_pii012_violation(rel_path, lineno, name, sig))
    return violations


#: T-0539: a `# frob:<directive>` comment (`frob:waive`, `frob:tests`,
#: `frob:ticket`, `frob:secret-fake`, ...) is machine-read metadata syntax,
#: not narrative prose about the code -- and the `frob:secret-fake` marker
#: convention itself literally contains the word "secret", so placing that
#: exact marker (the correct escape hatch for a PII011 email-shape finding)
#: would otherwise self-trigger PII012 on the very comment that discharges
#: a DIFFERENT rule's finding. Skipped as a class, not case-by-case.
_FROB_DIRECTIVE_RE = re.compile(r"^\s*frob:")


def _scan_comment_keywords(text: str, rel_path: str) -> list[Violation]:
    """PII012 over every `#`-comment line's word tokens matching a
    `FIELD_SIGNATURES` name-kind keyword (T-0350 family 5), EXCLUDING
    `# frob:...` directive comments (`_FROB_DIRECTIVE_RE`, T-0539 -- see
    its docstring), and `_PII012_REVIEWED_NON_PII` sites (T-0540). A plain
    line-oriented scan of `#`-prefixed trailing text, not a full tokenizer
    pass -- adequate for a comment-word suggestion signal and avoids
    misreading a `#` inside a string literal as a comment only in the
    rare case a string itself contains one, the same trade-off
    `_secrets.py`'s line-oriented scanner already documents as an honest
    limitation."""
    violations: list[Violation] = []
    seen: set[tuple[int, str]] = set()
    for lineno, line in enumerate(text.splitlines(), start=1):
        hash_index = line.find("#")
        if hash_index < 0:
            continue
        comment = line[hash_index + 1 :]
        if _FROB_DIRECTIVE_RE.match(comment):
            continue
        for match in _COMMENT_WORD_RE.finditer(comment):
            token = match.group(0)
            sig = _field_name_hit(token)
            if sig is None:
                continue
            if _is_pii012_reviewed_non_pii(rel_path, token):
                continue
            key = (lineno, token)
            if key in seen:
                continue
            seen.add(key)
            violations.append(_pii012_violation(rel_path, lineno, token, sig))
    return violations


# frob:tests tests/test_pii_structural_gate.py::TestKeywordSweep.test_identifier_keyword_fires_at_suggestion_severity  # noqa: E501
def _scan_python_keyword_sweep(
    tree: ast.Module, rel_path: str, text: str
) -> tuple[Violation, ...]:
    """PII012 (T-0350 family 5): identifier and comment keyword hits at
    suggestion severity, reusing `FIELD_SIGNATURES` -- no hard fail on a
    bare name/comment word alone."""
    violations = _scan_identifier_keywords(tree, rel_path)
    violations.extend(_scan_comment_keywords(text, rel_path))
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


def _scan_python_env_access(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> tuple[Violation, ...]:
    """SEC110 over every `os.environ[...]`/`os.environ.get(...)`/
    `os.getenv(...)` call/subscript site in `tree` (module docstring:
    family 3, env/secret sources), joined against `declared`'s
    Secret-clearance code binding (T-0351) -- a file already code-bound to
    a declared std.secrets node is discharged, not merely waivable."""
    if declared._has_secret(rel_path):
        return ()
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
    module's own path (`_SELF_EXCLUDED_FILES`, T-0201 lesson). Joins every
    PII010/SEC110 finding against a loaded strata design's std.pii/
    std.secrets declarations (`_load_declared_surface`, T-0351) -- a
    real declaration discharges a finding outright, not merely a waiver."""
    root = Path(root)
    declared = _load_declared_surface(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_python_files(root):
        if rel_path in _SELF_EXCLUDED_FILES or _is_pii_self_pattern_file(
            root, rel_path
        ):
            _log.debug("pii_structural_gate: skipping self-excluded %s", rel_path)
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(text, filename=rel_path)
        except (OSError, UnicodeDecodeError, SyntaxError):
            _log.debug("pii_structural_gate: skipping unparseable %s", rel_path)
            continue
        scanned += 1
        violations.extend(_scan_python_fields(tree, rel_path, declared))
        violations.extend(_scan_python_env_access(tree, rel_path, declared))
        violations.extend(_scan_python_ddl(tree, rel_path, declared))
        violations.extend(_scan_python_email_values(tree, rel_path, text))
        violations.extend(_scan_python_keyword_sweep(tree, rel_path, text))

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
    "_scan_python_keyword_sweep",
    "_load_declared_surface",
    "_DeclaredSurface",
]
