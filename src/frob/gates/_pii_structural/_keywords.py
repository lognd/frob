"""PII012: identifier/comment keyword sweep (T-0350 family 5) -- T-1076
split of `frob.gates._pii_structural`.

`_PII012_REVIEWED_NON_PII` (T-0540) is a manually-reviewed (file,
identifier-text) allowlist keyed by OTHER modules' paths, not this
package's own -- when a symref in that table moves to a new file (a
split like this one), its (file, token) entry must move with it, per the
same discipline this table's own header comment documents."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_pii_structural/_keywords.py's \
# exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim -- carried from the \
# pre-T-1076-split monolith's identical file-level waiver"

from __future__ import annotations

import ast
import re

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

from ._python_fields import _is_data_structure_field_target
from ._signatures import _field_name_hit, _FieldSignature

_log = get_logger(__name__)

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
# frob:ticket T-0971
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
        # T-1086's split moved `dup/_pipeline.py` into the `dup/_pipeline/`
        # package -- same reviewed "token" homonym, new per-file homes.
        ("src/frob/dup/_pipeline/__init__.py", "token"),
        ("src/frob/dup/_pipeline/_callgraph.py", "TOKEN"),
        ("src/frob/dup/_pipeline/_callgraph.py", "token"),
        ("src/frob/dup/_pipeline/_fingerprint.py", "token"),
        ("src/frob/dup/_pipeline/_normalize.py", "token"),
        ("src/frob/dup/_pipeline/_shared.py", "token"),
        ("src/frob/gates/__init__.py", "token"),
        # T-1072's split moved the waiver machinery (and its SEC110/secret-
        # fake vocabulary, the same reviewed non-PII homonyms below) from
        # gates/__init__.py into gates/_waive.py -- same tokens, new home.
        ("src/frob/gates/_waive.py", "token"),
        ("src/frob/gates/_waive.py", "SECRET"),
        ("src/frob/gates/_waive.py", "secret"),
        ("src/frob/gates/_waive.py", "_cve_fingerprint_scan"),
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
        # T-0971: PII010/PII012 burn-down -- the remaining 89 (file,
        # identifier) sites in the 167-finding unwaived measured baseline,
        # each individually read at its call site before being added here
        # (same T-0540 discipline, not a blanket mute). All are the same
        # already-documented "token" LEXER/parser/regex-name/CLI-token/
        # random-nonce homonym (a compiled `_*_TOKEN_RE` provability
        # pattern, a tree-sitter/markdown/CLI-invocation parse token, a
        # `ContextVar` reset token, or a `uuid4().hex` random directory
        # suffix -- never an auth token) or the "diagnosis"/"email"/
        # "password"/"secret"/"ssn"/"address" homonyms already established
        # above (this repo's own `frob doctor` diagnostic feature name,
        # PII010's own cross-language gate test names literally testing
        # the detector, and a plain-English comment word) -- confirmed by
        # reading each site, not inferred from the identifier text alone.
        ("src/frob/arch/_rust.py", "token"),
        ("src/frob/arch/_srp.py", "token"),
        ("src/frob/deploy/_generate_windows.py", "token"),
        ("src/frob/doctor.py", "test_run_diagnosis_unhealthy"),
        ("src/frob/gates/_docptr.py", "Token"),
        ("src/frob/gates/_docptr.py", "_CLI_TOKEN_RE"),
        ("src/frob/gates/_docptr.py", "token"),
        ("src/frob/gates/_protocol_summary.py", "_parse_transition_token"),
        ("src/frob/gates/_protocol_summary.py", "token"),
        ("src/frob/gitio.py", "token"),
        ("src/frob/graph/_core.py", "token"),
        ("src/frob/graph/callgraph.py", "token"),
        ("src/frob/scaffold/_pool.py", "token"),
        ("src/frob/strata/_backpressure.py", "_BOUNDED_INTAKE_TOKEN_RE"),
        ("src/frob/strata/_backpressure.py", "_TIMEOUT_TOKEN_RE"),
        ("src/frob/strata/_backpressure.py", "token"),
        ("src/frob/strata/_backpressure.py", "token_bucket"),
        ("src/frob/strata/_circuit_breaker.py", "_CIRCUIT_BREAKER_TOKEN_RE"),
        ("src/frob/strata/_circuit_breaker.py", "_TIMEOUT_TOKEN_RE"),
        ("src/frob/strata/_circuit_breaker.py", "token"),
        ("src/frob/strata/_clock_ordering.py", "_ORDERING_TOKEN_RE"),
        ("src/frob/strata/_clock_ordering.py", "_WALL_CLOCK_TOKEN_RE"),
        ("src/frob/strata/_clock_ordering.py", "has_real_token"),
        ("src/frob/strata/_clock_ordering.py", "token"),
        ("src/frob/strata/_delivery_semantics.py", "_DELIVERY_SEMANTICS_TOKEN_RE"),
        ("src/frob/strata/_delivery_semantics.py", "_SCHEMA_VERSION_TOKEN_RE"),
        ("src/frob/strata/_delivery_semantics.py", "token"),
        ("src/frob/strata/_distributed_txn.py", "_SAGA_TOKEN_RE"),
        ("src/frob/strata/_distributed_txn.py", "_TXN_TOKEN_RE"),
        ("src/frob/strata/_distributed_txn.py", "token"),
        ("src/frob/strata/_fallback.py", "_FALLBACK_TOKEN_RE"),
        ("src/frob/strata/_fallback.py", "_TIMEOUT_TOKEN_RE"),
        ("src/frob/strata/_fallback.py", "token"),
        ("src/frob/strata/_host_isolation.py", "Token"),
        ("src/frob/strata/_interactive_cost.py", "_BOUNDED_COST_TOKEN_RE"),
        ("src/frob/strata/_interactive_cost.py", "_BOUNDED_INTAKE_TOKEN_"),
        ("src/frob/strata/_interactive_cost.py", "token"),
        ("src/frob/strata/_message_schema.py", "_BOUNDED_INTAKE_TOKEN_RE"),
        ("src/frob/strata/_message_schema.py", "_SCHEMA_VERSION_TOKEN_RE"),
        ("src/frob/strata/_message_schema.py", "token"),
        ("src/frob/strata/_obligation_proof.py", "files_evidence_token"),
        ("src/frob/strata/_observability.py", "_OBSERVABILITY_TOKEN_RE"),
        ("src/frob/strata/_observability.py", "_TIMEOUT_TOKEN_RE"),
        ("src/frob/strata/_observability.py", "token"),
        ("src/frob/strata/_process_bounds.py", "_BOUNDED_INTAKE_TOKEN_RE"),
        (
            "src/frob/strata/_process_bounds.py",
            "_INTERFACE_CLASSIFICATION_TOKEN_RE",
        ),
        ("src/frob/strata/_process_bounds.py", "_PROCESS_BOUNDS_TOKEN_RE"),
        ("src/frob/strata/_process_bounds.py", "token"),
        ("src/frob/strata/_reliability.py", "_HEALTH_TOKEN_RE"),
        ("src/frob/strata/_reliability.py", "_TIMEOUT_TOKEN_RE"),
        ("src/frob/strata/_reliability.py", "token"),
        ("src/frob/strata/_retry.py", "_BACKOFF_TOKEN_RE"),
        ("src/frob/strata/_retry.py", "_TIMEOUT_TOKEN_RE"),
        ("src/frob/strata/_retry.py", "token"),
        ("src/frob/strata/_slo.py", "_SLO_TOKEN_RE"),
        ("src/frob/strata/_slo.py", "_TIMEOUT_TOKEN_RE"),
        ("src/frob/strata/_slo.py", "token"),
        ("src/frob/strata/_ssot.py", "_OWNER_TOKEN_RE"),
        ("src/frob/strata/_ssot.py", "_TIMEOUT_TOKEN_RE"),
        ("src/frob/strata/_ssot.py", "token"),
        ("src/frob/strata/_supply_chain_boot.py", "_ABI_COMPAT_WINDOW_TOKEN_RE"),
        ("src/frob/strata/_supply_chain_boot.py", "_BOOT_ATTESTATION_TOKEN_RE"),
        ("src/frob/strata/_supply_chain_boot.py", "_BOUNDED_INTAKE_TOKEN_RE"),
        ("src/frob/strata/_supply_chain_boot.py", "token"),
        ("src/frob/strata/_txn.py", "_OWNER_TOKEN_RE"),
        ("src/frob/strata/_txn.py", "_TXN_TOKEN_RE"),
        ("src/frob/strata/_txn.py", "token"),
        ("src/frob/tickets/_models.py", "token"),
        (
            "tests/system/test_cli_doctor.py",
            "test_run_diagnosis_healthy_after_scaffold_apply",
        ),
        (
            "tests/system/test_cli_doctor.py",
            "test_run_diagnosis_healthy_with_no_derived_state",
        ),
        (
            "tests/system/test_cli_doctor.py",
            "test_run_diagnosis_healthy_with_no_mutate_journals",
        ),
        (
            "tests/system/test_cli_doctor.py",
            "test_run_diagnosis_ignores_journal_owned_by_live_pid",
        ),
        (
            "tests/system/test_cli_doctor.py",
            "test_run_diagnosis_ignores_non_frob_directory",
        ),
        (
            "tests/system/test_cli_doctor.py",
            "test_run_diagnosis_unhealthy_when_derived_state_corrupt",
        ),
        (
            "tests/system/test_cli_doctor.py",
            "test_run_diagnosis_unhealthy_when_scaffold_blocks_missing",
        ),
        (
            "tests/system/test_cli_doctor.py",
            "test_run_diagnosis_unhealthy_with_stale_mutate_journal",
        ),
        (
            "tests/test_doctor.py",
            "test_run_diagnosis_holds_exclusive_lock_blocking_a_shared_reader",
        ),
        ("tests/test_gates.py", "test_rust_secret_newtype_type_field_fires"),
        ("tests/test_gates.py", "test_rust_struct_ssn_field_fires"),
        ("tests/test_gates.py", "test_ts_branded_email_type_field_fires"),
        ("tests/test_gates.py", "test_ts_class_field_token_fires"),
        ("tests/test_gates.py", "test_ts_interface_email_field_fires"),
        ("tests/test_gates.py", "test_ts_secret_wrapper_type_field_fires"),
        ("tests/test_gates.py", "test_ts_type_alias_password_field_fires"),
        ("tests/test_ticket_land.py", "address"),
        ("tests/test_ticket_land.py", "token"),
        ("tests/unit/strata/test_obligation_proof.py", "test_matches_a_real_token"),
        ("tests/unit/strata/test_registry_cross_refs.py", "token"),
        ("tests/unit/strata/test_reliability.py", "token"),
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
