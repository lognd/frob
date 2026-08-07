"""The single-source `FIELD_SIGNATURES` field-name/type keyword registry
and its lookup helpers (T-1076 split of `frob.gates._pii_structural`).

DISCIPLINE (ticket-mandated, non-negotiable, carried from the pre-split
module docstring): every keyword/type entry lives in exactly one place;
`_NAME_SIGNATURES`/`_TYPE_SIGNATURES` are derived views, never a second
hand-maintained table. Per-entry drift-lock:
`tests/test_pii_structural_gate.py::TestDriftLock` parametrizes over
`FIELD_SIGNATURES` and asserts each entry's keyword fires PII010 against a
synthetic fixture class -- a registry entry with no firing fixture fails
the test (T-0182 style)."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from tree_sitter import Node

from frob.lang import node_text
from frob.strata._pii import PII_CATEGORIES


# frob:waive COV007 reason="docs/modules/gates.md's Public API section also \
# individually frob:describes this private dataclass by name (T-0529) -- a deliberate \
# architecture doc, not accidental drift onto a private helper"
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
    #: Which language(s) this entry's `keyword` is meaningful in (T-0762):
    #: a NAME-kind keyword is the same structural signal in any language
    #: (default, all three); a TYPE-kind keyword is a concrete type name
    #: that only exists in one language's ecosystem (`EmailStr`/`SecretStr`
    #: are Python-only pydantic types; `SecretString`/`Secret` are the
    #: TS/Rust secret-wrapper equivalents named in the T-0762 ticket body),
    #: so TYPE-kind entries must scope themselves explicitly.
    langs: frozenset[str] = frozenset({"py", "ts", "rust"})


def _sig(
    id: str,
    keyword: str,
    category: str,
    kind: str = "name",
    langs: frozenset[str] | None = None,
) -> _FieldSignature:
    """Build one `_FieldSignature`, asserting `category` is a real PII_
    CATEGORIES member so the registry can never point at a category PII001
    would itself reject (deny-by-default consistency across both gates).
    `langs` defaults to all three supported languages (T-0762); pass an
    explicit narrower set for a TYPE-kind entry whose keyword only exists
    in one language's ecosystem."""
    if category not in PII_CATEGORIES:
        raise ValueError(f"_FieldSignature {id!r}: {category!r} not in PII_CATEGORIES")
    return _FieldSignature(
        id=id,
        keyword=keyword,
        category=category,
        kind=kind,
        langs=langs if langs is not None else frozenset({"py", "ts", "rust"}),
    )


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
    # Type-based signals (corpus Part B.2: EmailStr/SecretStr -- Python
    # only; every FIELD_SIGNATURES entry needs a firing fixture in
    # `tests/test_pii_structural_gate.py::TestDriftLock`, so a TS/Rust-only
    # type keyword belongs in `_CROSS_LANG_TYPE_SIGNATURES` below instead
    # -- see that table's comment for the T-0762 rationale).
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

#: TS/Rust-only TYPE-kind signals (T-0762): a field typed as a known
#: secret-wrapper type or a branded/nominal PII-shaped type, in an
#: ecosystem with no Python equivalent (so `FIELD_SIGNATURES`'s "every
#: entry needs a `TestDriftLock` Python fixture" contract, T-0182, does not
#: apply -- these are proven by the real TS/Rust fixtures in
#: `tests/test_gates.py::TestPiiStructuralCrossLanguage` instead). Kept as
#: a SEPARATE table from `FIELD_SIGNATURES` rather than mixed in with a
#: `langs` filter, specifically so that contract does not need bending: a
#: python fixture built from `sig.keyword` for `secrecy::SecretString`'s
#: bare `"SecretString"` would spuriously pass as a `SecretStr`-shaped hit
#: anyway, silently masking a truly-missing TS/Rust fixture.
_CROSS_LANG_TYPE_SIGNATURES: tuple[_FieldSignature, ...] = (
    # TS: known secret-wrapper type names (no single standard library
    # equivalent to pydantic's SecretStr -- these are the conventional
    # names used across TS secret-wrapper packages/patterns).
    _sig(
        "secret-type-ts", "Secret", "credentials", kind="type", langs=frozenset({"ts"})
    ),
    _sig(
        "secretstring-type-ts",
        "SecretString",
        "credentials",
        kind="type",
        langs=frozenset({"ts"}),
    ),
    _sig(
        "sensitivestring-type-ts",
        "SensitiveString",
        "credentials",
        kind="type",
        langs=frozenset({"ts"}),
    ),
    # TS: branded/nominal email type names (a field typed as one of these,
    # rather than plain `string`, is a nominal PII-shaped type by
    # convention).
    _sig(
        "brandedemail-type-ts", "Email", "contact", kind="type", langs=frozenset({"ts"})
    ),
    _sig(
        "brandedemailaddress-type-ts",
        "EmailAddress",
        "contact",
        kind="type",
        langs=frozenset({"ts"}),
    ),
    # Rust: `secrecy` crate wrapper types (ticket body: "secrecy::Secret,
    # SecretString").
    _sig(
        "secret-type-rust",
        "Secret",
        "credentials",
        kind="type",
        langs=frozenset({"rust"}),
    ),
    _sig(
        "secretstring-type-rust",
        "SecretString",
        "credentials",
        kind="type",
        langs=frozenset({"rust"}),
    ),
    # Rust: newtype PII wrappers by conventional name (`struct Email(String)`
    # style nominal wrappers named in the ticket body).
    _sig(
        "email-newtype-type-rust",
        "Email",
        "contact",
        kind="type",
        langs=frozenset({"rust"}),
    ),
)


#: T-0971 (gates-quality audit finding 5): a camelCase/concatenated field
#: name (`passwordHash`, `apiKey`, `ssnValue`, `dateOfBirth`) never produced
#: a `_`-split token under the old lowercase-then-split-on-`_` scheme, so
#: `_field_name_hit` silently missed the single most common non-snake_case
#: naming convention (TypeScript/JS-flavored pydantic models, camelCase
#: JSON aliases). Inserted before the existing lower+split logic runs, so
#: BOTH the single-word token match and the multi-word underscored-
#: substring match benefit from one normalization instead of two: a
#: boundary is a lowercase/digit run followed by an uppercase letter
#: (`passwordHash` -> `password_Hash`), or a multi-capital acronym run
#: followed by a lowercase letter (`APIKey` -> `API_Key`, so `Key` is its
#: own token, not glued to the acronym).
# frob:ticket T-0971
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


# frob:ticket T-0971
# frob:tests tests/test_pii_structural_gate.py::TestFieldNames.test_camelcase_password_hash_field_fires  # noqa: E501
def _camel_to_snake(name: str) -> str:
    """Insert `_` at every camelCase/acronym boundary in `name` (T-0971,
    `_CAMEL_BOUNDARY_RE`'s docstring) -- a no-op on an already-snake_case
    or single-word name, since neither contains a lower-to-upper or
    acronym-to-word boundary."""
    return _CAMEL_BOUNDARY_RE.sub("_", name)


# frob:ticket T-0971
# frob:tests tests/test_pii_structural_gate.py::TestFieldNames.test_camelcase_password_hash_field_fires  # noqa: E501
def _field_name_hit(field_name: str) -> _FieldSignature | None:
    """The first `FIELD_SIGNATURES` name-kind entry `field_name` matches, or
    `None`. Single-word keywords match a whole `_`-split token; multi-word
    (underscored) keywords match as a substring of the full lowered name.
    `field_name` is first camelCase-normalized (`_camel_to_snake`, T-0971)
    so `passwordHash`/`apiKey`-shaped names match exactly like their
    snake_case equivalents would."""
    lowered = _camel_to_snake(field_name).lower()
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


#: `_TYPE_SIGNATURES` (Python-only, `TestDriftLock`-covered) plus
#: `_CROSS_LANG_TYPE_SIGNATURES` (TS/Rust-only, T-0762) -- the combined
#: population `_type_hit` searches, so both `_field_type_hit` and the
#: TS/Rust `_ts_type_hit`/`_rust_type_hit` share one lookup.
_ALL_TYPE_SIGNATURES = _TYPE_SIGNATURES + _CROSS_LANG_TYPE_SIGNATURES


def _type_hit(names: set[str], lang: str) -> _FieldSignature | None:
    """The first `_ALL_TYPE_SIGNATURES` entry active for `lang` (`sig.
    langs`) whose keyword appears in `names`, or `None` -- the
    language-generic core `_field_type_hit` (Python), `_ts_type_hit`, and
    `_rust_type_hit` (T-0762) all funnel through, so the langs scoping
    lives in exactly one place."""
    for sig in _ALL_TYPE_SIGNATURES:
        if lang in sig.langs and sig.keyword in names:
            return sig
    return None


def _field_type_hit(annotation: ast.expr | None) -> _FieldSignature | None:
    """The first `FIELD_SIGNATURES` Python type-kind entry whose keyword
    appears among `annotation`'s names (`_annotation_names`), or `None`."""
    return _type_hit(_annotation_names(annotation), "py")


def _type_identifier_names(node: Node | None) -> set[str]:
    """Every bare type-identifier name appearing anywhere in a TS/Rust type
    subtree (a `type_annotation` wrapper, generics like `Secret<string>`/
    `Secret<String>`, scoped paths like `secrecy::SecretString`) -- the
    TS/Rust analogue of `_annotation_names`'s Python AST walk, shared by
    `_ts_type_hit` and `_rust_type_hit` (T-0762) so the walk logic lives in
    exactly one place regardless of which grammar's tree it is handed."""
    if node is None:
        return set()
    names: set[str] = set()
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type in ("type_identifier", "identifier"):
            names.add(node_text(current))
        stack.extend(current.children)
    return names


def _ts_type_hit(type_node: Node | None) -> _FieldSignature | None:
    """The first `FIELD_SIGNATURES` TS-scoped type-kind entry whose keyword
    appears in `type_node`'s identifier names (T-0762) -- the TS analogue
    of `_field_type_hit`."""
    return _type_hit(_type_identifier_names(type_node), "ts")


def _rust_type_hit(type_node: Node | None) -> _FieldSignature | None:
    """The first `FIELD_SIGNATURES` Rust-scoped type-kind entry whose
    keyword appears in `type_node`'s identifier names (T-0762) -- the Rust
    analogue of `_field_type_hit`."""
    return _type_hit(_type_identifier_names(type_node), "rust")
