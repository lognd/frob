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
  `FIELD_SIGNATURES` (the single-source keyword/type registry, `_signatures.
  py`) fires -- deny-by-default, exactly like PII001's "unknown category"
  default: a PII-shaped field with no accompanying `frob:waive PII010
  reason="..."` is treated as an undeclared PII surface, UNLESS the file is
  already code-bound to a strata `Node` `carries`-ing that same category
  (T-0351, `_declared_surface.py`) -- a real declaration now discharges the
  finding outright, not just a waiver.
- SEC110: an `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)` call
  site is a secret-SOURCE observation (corpus Part A intro: "env/secret
  sources ... must map to a declared strata secret node (T-0082 std.secrets)
  or be waived"). Same T-0351 join as PII010: a file code-bound to a
  Secret-clearance node discharges every SEC110 finding in it.

DISCIPLINE (ticket-mandated, non-negotiable):
- Single-source registry (`_signatures.FIELD_SIGNATURES`): every keyword/
  type entry lives in exactly one place.
- Self-match exclusion (T-0201 lesson, `_self_match.py`): this package's
  own path(s) can never be misread as an `AnnAssign` field name by this
  scanner running over its own source.
- Per-entry drift-lock: `tests/test_pii_structural_gate.py::TestDriftLock`
  parametrizes over `FIELD_SIGNATURES` and asserts each entry's keyword
  fires PII010 against a synthetic fixture class.

T-0348 (family 2, DB/DDL schema scanning, `_python_fields.py`) extended
PII010 to sqlalchemy ORM `Column(...)` declarations and raw-SQL `CREATE
TABLE` string literals embedded in tracked `.py` files.

T-0349 (family 4, email-shape values, `_emails.py`) added PII011: a
git-tracked `.py` file's string-literal constants scanned via `email.
utils.parseaddr` (an RFC 822 header parser, NOT a regex).

T-0350 (family 5, keyword sweep, `_keywords.py`) added PII012: every plain
identifier and every `#`-comment word token matching a `FIELD_SIGNATURES`
name-kind keyword, EXCLUDING sites PII010 already reports on. Fires at
WARN ("suggestion") severity -- explicitly advisory, never a deny-by-
default surface the way PII010/PII011/SEC110 are.

T-0351 joined every PII010/SEC110 finding to a loaded strata design's
std.pii/std.secrets declarations (`_declared_surface.py`).

T-0352 (`_crosslang.py`) extended the Python-only scan to TypeScript/Rust
field-shape and env-access equivalents. T-0762 extended TYPE-kind matching
to TS/Rust nominal secret-wrapper/branded-email types
(`_signatures._CROSS_LANG_TYPE_SIGNATURES`).

Deliberately NOT built (disclosed, not silently dropped -- see T-0207's
Done report for the filed follow-on ticket ids): non-Python DDL sources
such as `.sql` migration files.

T-0430 (`docs/design/registry/pii.yaml`'s six deferred sections) extended
`FIELD_SIGNATURES` toward GDPR Art.9(1) special-category / CCPA / HIPAA
Safe Harbor / PCI-DSS / NIST SP 800-122 field-name parity. Still not built:
PCI-DSS Sensitive Authentication Data field-name shapes and CCPA's
non-field-shaped categories -- both remain honest gaps for a follow-on
ticket, not silently dropped.

T-1076 split this module from a single 2177-line file into this package:
`_signatures.py` (the `FIELD_SIGNATURES` registry + name/type-hit lookup),
`_declared_surface.py` (T-0351 std.pii/std.secrets join), `_self_match.py`
(T-0201/T-0539 self-exclusion), `_tracked.py` (git-tracked file listing),
`_python_fields.py` (PII010 class-field + DDL/ORM scan, family 1+2),
`_emails.py` (PII011, family 4), `_keywords.py` (PII012, family 5),
`_env_access.py` (SEC110 Python, family 3), `_crosslang.py` (TS/Rust field
+ env scans, T-0352/T-0762). This `__init__.py` re-exports every public
and test-consumed private symbol so `from frob.gates._pii_structural
import ...` is unchanged for every existing caller (zero caller edits, per
the T-1072/T-0989 split discipline).
"""

# frob:ticket T-0207
# frob:ticket T-1076
from __future__ import annotations

import ast
from pathlib import Path

from frob.excludes import is_excluded, load_exclude_globs
from frob.gates._parse_failures import local_parse001_violation
from frob.logging import get_logger

from .._models import Violation
from ._crosslang import (
    _scan_cross_language_files,
    _scan_rust_env_access,
    _scan_rust_fields,
    _scan_ts_env_access,
    _scan_ts_fields,
)
from ._declared_surface import _DeclaredSurface, _load_declared_surface
from ._emails import _is_email_shaped, _scan_python_email_values
from ._env_access import _scan_python_env_access
from ._keywords import _scan_python_keyword_sweep
from ._node_index import _build_node_index
from ._python_fields import (
    _is_data_structure,
    _scan_python_ddl,
    _scan_python_fields,
)
from ._self_match import _SELF_EXCLUDED_FILES, _is_pii_self_pattern_file
from ._signatures import FIELD_SIGNATURES, _FieldSignature
from ._tracked import _tracked_python_files

_log = get_logger(__name__)


# frob:ticket T-0897
def _parse001_violation(rel_path: str, reason: str) -> Violation:
    """PARSE001 `Violation` for a file this gate's own read/parse could not
    get through (T-0897): delegates to `frob.gates._parse_failures.
    local_parse001_violation` (extracted T-0861) with this gate's own
    capability-loss clause so PII010/SEC110's message stays distinct while
    the rule id/severity/message shape is the ONE shared home."""
    return local_parse001_violation(
        rel_path,
        reason,
        "PII010/SEC110 cannot inspect it for PII-shaped fields or secret sources",
    )


# frob:ticket T-0976
def _scan_one_python_file(
    root: Path, rel_path: str, declared, exclude_globs
) -> list[Violation] | None:  # noqa: ANN001
    """One tracked python file's PII010/SEC110 contribution: parse it and
    run every `_scan_python_*` sub-scan, or -- an unparseable file not
    covered by `[graph].exclude` (T-0897) -- return a single PARSE001
    finding instead. `None` (not an empty list) signals "excluded, do not
    count as scanned", distinct from "scanned, zero findings".

    T-1209 perf: builds one `_NodeIndex` (`_build_node_index`, a single
    `ast.walk(tree)` pass) here and passes it to every sub-scan via its
    `_index` kwarg, instead of each sub-scan running its own `ast.walk`."""
    try:
        text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
        tree = ast.parse(text, filename=rel_path)
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        if is_excluded(rel_path, exclude_globs):
            # T-0897: `[graph].exclude` (frob.toml) already carves this
            # path out of frob's own obligation surface (e.g.
            # tests/fixtures/**'s deliberately-broken parser fixtures,
            # docs/modules/gates.md's `[graph].exclude` rationale) --
            # PARSE001 stays silent here, same as the graph-ingested
            # path already treats it, instead of forcing every such
            # fixture to carry its own waiver.
            _log.debug(
                "pii_structural_gate: skipping excluded unparseable %s", rel_path
            )
            return None
        return [_parse001_violation(rel_path, str(exc))]
    index = _build_node_index(tree)
    violations: list[Violation] = []
    violations.extend(_scan_python_fields(tree, rel_path, declared, _index=index))
    violations.extend(_scan_python_env_access(tree, rel_path, declared, _index=index))
    violations.extend(_scan_python_ddl(tree, rel_path, declared, _index=index))
    violations.extend(_scan_python_email_values(tree, rel_path, text, _index=index))
    violations.extend(_scan_python_keyword_sweep(tree, rel_path, text, _index=index))
    return violations


# frob:doc docs/modules/gates.md#structural-pii-secrets-detection-t-0207
# frob:tests tests/test_pii_structural_gate.py::TestFieldNames.test_password_field_fires
# frob:tests tests/test_pii_structural_gate.py::TestEnvAccess.test_os_getenv_fires
# frob:tests tests/test_pii_structural_gate.py::TestSelfMatchExclusion.test_own_file_not_scanned  # noqa: E501
# frob:tests tests/test_pii_structural_gate.py::TestGateIsGreenOnItself.test_own_module_source_produces_no_self_finding  # noqa: E501
# frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_interface_email_field_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_struct_ssn_field_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_process_env_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_env_var_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_unparseable_python_file_fires_parse001  # noqa: E501
# frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_unparseable_file_under_graph_exclude_is_silent  # noqa: E501
# frob:ticket T-0897
# frob:enforces SEC-PII-PII-GDPR_SPECIAL_CATEGORIES
# frob:enforces SEC-PII-PII-CCPA_CATEGORIES
# frob:enforces SEC-PII-PII-HIPAA_SAFE_HARBOR_IDENTIFIERS
# frob:enforces SEC-PII-PII-PCI_DSS_GLOSSARY_TERMS
# frob:enforces SEC-PII-PII-NIST_800_122_DEFINITION
# frob:enforces SEC-PII-PII-DETECTABLE_SHAPES_CROSSMAP
# frob:enforces SEC-PII-PII-STD_PII_CATEGORY_RECONCILIATION
# frob:enforces CHK-GATE-PII010
# frob:enforces CHK-GATE-SEC110
# frob:enforces CHK-GATE-PII011
# frob:enforces CHK-GATE-PII012
def pii_structural_gate(root: Path) -> tuple[Violation, ...]:
    """PII010/SEC110 (docs/modules/gates.md#structural-pii-secrets-
    detection-t-0207): every git-tracked `.py`/`.ts`/`.tsx`/`.rs` file
    scanned for PII-shaped data-structure fields and env-var access sites
    (T-0352 extended the Python-only T-0207 scan to TypeScript/Rust field-
    shape and env-access equivalents). Self-excludes this package's own
    paths (`_SELF_EXCLUDED_FILES`, T-0201 lesson). Joins every PII010/SEC110
    finding against a loaded strata design's std.pii/std.secrets
    declarations (`_load_declared_surface`, T-0351) -- a real declaration
    discharges a finding outright, not merely a waiver. A `.py` file this
    gate cannot read/parse fires PARSE001 instead of silently dropping out
    of the scan (T-0897), UNLESS the file matches a `[graph].exclude` glob
    (frob.toml) -- that config already carves the path out of frob's own
    obligation surface (e.g. `tests/fixtures/**`'s deliberately-broken
    parser fixtures), so PARSE001 stays silent there too."""
    root = Path(root)
    declared = _load_declared_surface(root)
    exclude_globs = load_exclude_globs(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_python_files(root):
        if rel_path in _SELF_EXCLUDED_FILES or _is_pii_self_pattern_file(
            root, rel_path
        ):
            _log.debug("pii_structural_gate: skipping self-excluded %s", rel_path)
            continue
        file_violations = _scan_one_python_file(root, rel_path, declared, exclude_globs)
        if file_violations is None:
            continue
        scanned += 1
        violations.extend(file_violations)

    cross_language_violations, cross_language_scanned = _scan_cross_language_files(
        root, declared
    )
    violations.extend(cross_language_violations)
    scanned += cross_language_scanned

    _log.info(
        "pii_structural_gate: scanned %d tracked file(s) (.py/.ts/.tsx/.rs), "
        "%d violation(s)",
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
    "_scan_ts_fields",
    "_scan_ts_env_access",
    "_scan_rust_fields",
    "_scan_rust_env_access",
    "_load_declared_surface",
    "_DeclaredSurface",
    "_is_data_structure",
    "_is_email_shaped",
]
