"""`AppConfig.from_external`'s argparse-Namespace-to-kwargs field-copy logic.

Split out of `frob.app.config` (T-1270): `AppConfig.from_external` is the
one large procedural block in an otherwise declarative pydantic-schema
module -- a real one-concern seam (mapping a parsed `argparse.Namespace`
plus an optional `pyproject.toml [tool.frob]` table onto `AppConfig`'s
flat field namespace), unlike the schema's field declarations themselves
(kept in `config.py`, see that module's `frob:waive LARGE001` for why they
were not also moved). Pure extraction, no behavior change -- every branch,
field-name tuple, and comment below is verbatim from the pre-split
`AppConfig.from_external` body.

T-1424: the extraction above moved a LARGE001 (over-long file) violation
out of `config.py` but landed a fresh ARCH001 (over-long function) one --
`_build_external_config_kwargs` was carried over as a single 392-line
body. This module now decomposes that body by field-type group (one
`_apply_*_fields` helper per argparse value kind: string/path/int/float/
list/bool), each a short loop over a module-level field-name tuple, so no
single function holds more than one group's worth of lines. The
field-name tuples themselves are unchanged from the pre-split body --
the loop bodies simply moved to where each type-group's helper lives.
"""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

# frob:ticket T-0021
# frob:ticket T-0085
# frob:ticket T-0030
# frob:ticket T-1150
_STRING_FIELDS = (
    "color",
    "scaffold_command",
    "scaffold_type",
    "scaffold_name",
    # frob:ticket T-0877
    "scaffold_pool_command",
    "cycle_lang",
    "xref_symbol",
    "xref_lang",
    "parse_tool",
    "docs_symbol",
    "docs_search",
    # frob:ticket T-0876
    "exports_consumers",
    "exports_lang",
    "check_type",
    "check_ticket",
    "check_base",
    "gitlog_granularity",
    "gitlog_since",
    "gitlog_until",
    "graph_command",
    "graph_ref",
    "ack_facet",
    "registry_command",
    "registry_add_file",
    "registry_add_key",
    "registry_add_id",
    "registry_add_name",
    "registry_add_source_doc",
    "pool_command",
    "pool_rule",
    "pool_key",
    "pool_reason",
    "ticket_command",
    "ticket_id",
    "ticket_title",
    "ticket_kind",
    "ticket_origin",
    "ticket_threat",
    "ticket_parent",
    "ticket_state",
    "ticket_by",
    "ticket_summary",
    "ticket_reason",
    "ticket_absorbed_by",
    "ticket_caption",
    "ticket_old_id",
    "ticket_new_id",
    "ticket_evidence_cmd",
    "ticket_review_verdict",
    "ticket_reviewer",
    "ticket_review_commit",
    "ticket_why",
    "ticket_base_ref",
    "ticket_scope_reason",
    "ticket_priority",
    "ticket_priority_level",
    "ticket_kind_value",
    "ticket_component",
    "ticket_board_component",
    "ticket_board_label",
    # frob:ticket T-0715
    "ticket_tier",
    # frob:ticket T-1069
    "ticket_tier_value",
    "ticket_sprint",
    "ticket_doable_sprint",
    "ticket_sprint_command",
    # frob:ticket T-1422
    "ticket_accept_amend_text",
    "ticket_accept_amend_reason",
    "test_base",
    "test_fallback",
    "vet_hook",
    "release_command",
    "perf_command",
    "perf_ref",
    "perf_format",
    "perf_by",
    "sys_command",
    "sys_view",
    "sys_export_format",
    "deploy_command",
    "deploy_vm",
    "deploy_ssh_host",
    "deploy_ssh_user",
    "deploy_base_snapshot",
    "fleet_command",
    "fleet_repo",
    "fleet_title",
    "fleet_kind",
    "fleet_priority",
    # frob:ticket T-0864
    "natives_command",
)

_PATH_FIELDS = (
    "scaffold_output",
    "cycle_path",
    "outline_file",
    "map_path",
    "xref_path",
    "parse_input",
    "dup_path",
    "arch_path",
    "docs_path",
    "exports_path",
    "check_path",
    "check_build_dir",
    "gitlog_path",
    "graph_path",
    "ack_path",
    "debt_path",
    "deprecated_path",
    "pool_path",
    "registry_path",
    "ticket_path",
    "ticket_attach_path",
    "ticket_worktree",
    "ticket_merge_base",
    "ticket_merge_ours",
    "ticket_merge_theirs",
    "ticket_why_file",
    "ticket_findings_file",
    # frob:ticket T-0737
    "ticket_body_file",
    "ticket_acceptance_file",
    "ticket_scope_reason_file",
    # frob:ticket T-1029
    "ticket_accept_criterion_file",
    # frob:ticket T-1422
    "ticket_accept_amend_reason_file",
    "test_path",
    "vet_path",
    "vet_cve_mirror",
    "perf_path",
    "release_path",
    "stats_path",
    "perf_annotate",
    "perf_file",
    "mutate_file",
    "mutate_path",
    "serve_path",
    "sys_path",
    "sys_export_path",
    "deploy_path",
    "deploy_out_dir",
    "deploy_ssh_key",
    "deploy_audit_output",
    "clean_path",
    "fleet_manifest",
    "fmt_path",
    # frob:ticket T-0864
    "natives_path",
)

_INT_FIELDS = (
    "map_depth",
    "dup_min_lines",
    "arch_max_function_lines",
    "arch_max_class_methods",
    "gitlog_limit",
    "perf_top",
    "perf_max_depth",
    "stats_days",
    "check_verbose",
    "ticket_verbose",
    "vet_jobs",
    # frob:ticket T-0877
    "scaffold_pool_n",
    # frob:ticket T-0628
    "graph_max_depth",
    "graph_max_nodes",
    # frob:ticket T-1422
    # Omitting these here is silent: argparse parses --amend/--remove,
    # this loop drops them, and `frob ticket accept` then reports that
    # it needs one of the very flags the user passed.
    "ticket_accept_amend_index",
    "ticket_accept_remove_index",
)

_FLOAT_FIELDS = ("vet_timeout", "perf_interval_s")

_LIST_FIELDS = (
    "check_only",
    "ack_refs",
    "pool_keys",
    "ticket_ids",
    "ticket_scope",
    "ticket_scope_add",
    "ticket_scope_remove",
    "ticket_blocked_by",
    "ticket_acceptance",
    "ticket_evidence_ids",
    # frob:ticket T-0749
    "ticket_accepts",
    "ticket_labels",
    "ticket_label_add",
    "ticket_label_remove",
    # frob:ticket T-1029
    "ticket_accept_criterion",
    "test_lang",
    "perf_argv",
    "mutate_argv",
    "dup_probe",
    "fleet_scope",
)

_BOOL_FLAGS = (
    "scaffold_force",
    "cycle_suggest",
    "outline_json",
    "outline_all",
    "map_json",
    "map_all",
    "xref_json",
    "xref_cross_file",
    "parse_json",
    "parse_verbose",
    "parse_passthrough",
    "dup_json",
    "arch_json",
    "docs_json",
    "docs_overview",
    "docs_sync_commands",
    "exports_all",
    "exports_json",
    "exports_write",
    "check_skip_ruff",
    "check_skip_ty",
    "check_skip_arch",
    "check_skip_cycle",
    "check_skip_dup",
    "check_skip_bind",
    "check_skip_exports",
    "check_skip_gates",
    "check_json",
    "check_valgrind",
    "check_skip_tests",
    "check_skip_build",
    "check_skip_clang_tidy",
    "check_skip_clang_format",
    "check_skip_cargo_check",
    "check_skip_clippy",
    "check_skip_fmt",
    "check_skip_tsc",
    "check_skip_eslint",
    "check_skip_prettier",
    "gitlog_all",
    "gitlog_json",
    "check_stamp_coverage",
    "check_stamp_baseline",
    "check_delta",
    "check_fix",
    "graph_json",
    "registry_sync_gate_rules",
    "debt_json",
    "deprecated_json",
    "registry_json",
    "ticket_json",
    "ticket_show_blocked",
    "ticket_ignore_lease",
    "ticket_force",
    "test_all",
    "test_fuzz",
    "test_collect",
    "test_wait_coverage",
    "test_json",
    "vet_json",
    "stats_json",
    "doctor_json",
    "mutate_json",
    "perf_tests",
    "perf_json",
    "perf_smells",
    "perf_sampler",
    "sys_apply",
    # frob:ticket T-1150
    "sys_check",
    "ticket_dry_run",
    # frob:ticket T-1381
    "release_allow_unbumped",
    "ticket_skip_mutation_evidence",
    # frob:ticket T-1369
    "ticket_allow_cross_ticket",
    "ticket_close_skip_mutation_evidence",
    "ticket_land_push",
    # frob:ticket T-1175
    "ticket_land_finish",
    "ticket_close_strict",
    "ticket_foreground",
    "ticket_steal",
    "ticket_reconcile_apply",
    "ticket_reconcile_remove_orphans",
    # frob:ticket T-0715
    "ticket_doable_by_parent",
    "deploy_check",
    "clean_all",
    "clean_deep",
    "clean_yes",
    "clean_json",
    "fleet_json",
    "fleet_skip_gates",
    "fmt_check",
    "fmt_json",
)


def _load_file_config(file: Path) -> dict:
    """Read `file`'s `[tool.frob]` table, or `{}` if `file` does not exist."""
    if not file.exists():
        return {}
    with file.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("frob", {})


# frob:waive OPAQUE001 reason="T-1038: every getattr(args, field, None)/ getattr(args, \
# flag, False) call below ranges over a closed, statically-declared tuple/string \
# literal of known AppConfig/argparse field names defined at module scope above -- not \
# attacker- or externally-controlled input; this is the standard \
# argparse-Namespace-to-model field-copy idiom, not an evasion surface. T-1424: this \
# waiver now covers every `_apply_*_fields` helper below, all of which share the same \
# closed-tuple shape as the original single-function body it was written for."
def _apply_string_fields(args: argparse.Namespace, d: dict) -> None:
    """Copy every present `_STRING_FIELDS` value from `args` into `d`, in place."""
    for field in _STRING_FIELDS:
        val = getattr(args, field, None)
        if val is not None:
            d[field] = val


def _apply_path_fields(args: argparse.Namespace, d: dict) -> None:
    """Copy every present `_PATH_FIELDS` value from `args` into `d` as a `Path`."""
    for field in _PATH_FIELDS:
        val = getattr(args, field, None)
        if val is not None:
            d[field] = Path(val)


def _resolve_ticket_worktree(d: dict) -> None:
    """Make `d["ticket_worktree"]` absolute if present (T-1057).

    `frob ticket land <id> --worktree <RELATIVE path>` broke: land's CLI
    wrapper (`ticket_runner._land`) spawns a `frob check` subprocess against
    `cfg.ticket_worktree` (via `_shared_check_spawn_fn`/`_python_for_tree`)
    BEFORE `frob.tickets._land.land()` ever runs its own internal
    `worktree.resolve()` -- that spawn joins the still-relative path with
    `.venv/bin/python` and passes it as BOTH the subprocess executable and
    `cwd=`, which fails with `[Errno 2]` because a relative executable path
    is resolved against the CALLING process's cwd, not the target `cwd=`.
    Resolving here, at argument-parse time -- the single place every
    `Path`-typed CLI arg is built -- makes `cfg.ticket_worktree` (and its
    `.venv/bin/python` join) absolute for every downstream consumer, so a
    relative `--worktree` behaves identically to an absolute one everywhere,
    not just inside `land()` itself."""
    if d.get("ticket_worktree") is not None:
        d["ticket_worktree"] = d["ticket_worktree"].resolve()


def _apply_int_fields(args: argparse.Namespace, d: dict) -> None:
    """Copy every present `_INT_FIELDS` value, plus the two ad-hoc int fields
    (`parse_exit_code`, `check_budget`) that need an explicit `int()` cast."""
    for field in _INT_FIELDS:
        val = getattr(args, field, None)
        if val is not None:
            d[field] = val

    parse_ec = getattr(args, "parse_exit_code", None)
    if parse_ec is not None:
        d["parse_exit_code"] = int(parse_ec)

    # frob:ticket T-1004
    check_budget = getattr(args, "check_budget", None)
    if check_budget is not None:
        d["check_budget"] = int(check_budget)


def _apply_float_fields(args: argparse.Namespace, d: dict) -> None:
    """Copy every present `_FLOAT_FIELDS` value from `args` into `d`, in place."""
    for field in _FLOAT_FIELDS:
        val = getattr(args, field, None)
        if val is not None:
            d[field] = val


def _apply_list_fields(args: argparse.Namespace, d: dict) -> None:
    """Copy every non-empty `_LIST_FIELDS` value, plus `exports_exclude`
    (kept separate since it predates the shared list-field loop)."""
    exports_exclude = getattr(args, "exports_exclude", None)
    if exports_exclude:
        d["exports_exclude"] = exports_exclude

    for field in _LIST_FIELDS:
        val = getattr(args, field, None)
        if val:
            d[field] = val


def _apply_scalar_overrides(args: argparse.Namespace, d: dict) -> None:
    """Copy `ticket_body`/`fleet_body`, the two free-text fields that are
    always full-string overrides rather than field-tuple loop members."""
    ticket_body = getattr(args, "ticket_body", None)
    if ticket_body is not None:
        d["ticket_body"] = ticket_body

    fleet_body = getattr(args, "fleet_body", None)
    if fleet_body is not None:
        d["fleet_body"] = fleet_body


def _apply_bool_flags(args: argparse.Namespace, d: dict) -> None:
    """Set every `_BOOL_FLAGS` entry that `args` carries as `True`; absent or
    `False` flags are left out of `d` (never explicitly forced `False`)."""
    for flag in _BOOL_FLAGS:
        if getattr(args, flag, False):
            d[flag] = True


def _build_external_config_kwargs(
    args: argparse.Namespace, file: Path, subcommand_cls: type
) -> dict:
    """Build the kwargs dict `AppConfig.from_external` passes to `cls(**d)`:
    merges `file`'s `[tool.frob]` table with every CLI flag `args` carries,
    field-type group by field-type group (string/path/int/float/list/bool),
    each applied by its own `_apply_*_fields` helper below. `subcommand_cls`
    is `frob.app.config.Subcommand`, passed in rather than imported to avoid
    a cycle back into `config.py`."""
    d: dict = _load_file_config(file)

    sub = getattr(args, "subcommand", None)
    if sub is not None:
        d["subcommand"] = subcommand_cls(sub)

    no_color = getattr(args, "no_color", None)
    if no_color is not None:
        d["no_color"] = no_color

    _apply_string_fields(args, d)
    _apply_path_fields(args, d)
    _resolve_ticket_worktree(d)
    _apply_int_fields(args, d)
    _apply_float_fields(args, d)
    _apply_list_fields(args, d)
    _apply_scalar_overrides(args, d)
    _apply_bool_flags(args, d)

    return d
