# frob:waive LARGE001 reason="T-1651: this module is one pydantic model (AppConfig) \
# plus its Subcommand enum and one validator helper -- the whole file IS the app's \
# single config surface (docs/guides/python-app.md's App/AppConfig pattern), not a \
# bundle of unrelated concerns. A line-count split would cut AppConfig's own \
# field/validator block in half with no behavioral or consumer-set boundary to hang \
# the cut on -- strictly worse than the warning per T-1651's own judgement standard. \
# _config_external.py and _config_meta.py already carry off the genuinely separable \
# parts (external-tool kwarg building, ARCH_DEFAULT_* constants); what remains here is \
# the single cohesive model."
from __future__ import annotations

import argparse
import enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator

from frob.app._config_external import _build_external_config_kwargs
from frob.app._config_meta import (
    ARCH_DEFAULT_GOD_MODULE_MIN_CLUSTERS,
    ARCH_DEFAULT_GOD_MODULE_MIN_EXPORTS,
    ARCH_DEFAULT_LCOM4_MIN_FIELD_USING_METHODS,
    ARCH_DEFAULT_LCOM4_MIN_METHODS,
    ARCH_DEFAULT_MAX_CLASS_METHODS,
    ARCH_DEFAULT_MAX_FILE_LINES,
    ARCH_DEFAULT_MAX_FUNCTION_LINES,
    ARCH_DEFAULT_MAX_LOCAL_IMPORTS,
    ARCH_DEFAULT_MAX_NESTING_DEPTH,
    ARCH_DEFAULT_MIXED_CONCERN_MIN_DECISION_POINTS,
    load_arch_config,
    stale_binary_warning,
    stale_install_warning,
)
from frob.gitlog import GranularityLevel
from frob.logging import get_logger
from frob.tickets._models import (
    Origin,
    Priority,
    ReviewVerdict,
    TicketKind,
    TicketState,
    TicketTier,
)

_log = get_logger(__name__)


# frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_state_lists_valid_values kind="unit"  # noqa: E501
def _validate_enum_choice(
    value: str | None, enum_cls: type[enum.Enum], field_label: str
) -> str | None:
    """Validate `value` is a legal member of `enum_cls`, raising a `ValueError`
    that lists every valid value inline (T-1271: replaces the bare
    `'open' is not a valid TicketState` `ValueError` a raw `TicketState(...)`
    call raises downstream, with no indication of what WOULD have been
    valid). `None` passes through unchanged -- these fields are all
    optional filters/inputs, not required."""
    if value is None:
        return value
    valid = [member.value for member in enum_cls]
    if value not in valid:
        raise ValueError(
            f"{value!r} is not a valid {field_label}; valid values are: "
            + ", ".join(valid)
        )
    return value


#: T-1270: `load_arch_config`/`stale_install_warning` and the ARCH_DEFAULT_*
#: constants live in `frob.app._config_meta` now (a real seam distinct from
#: the `AppConfig` schema); re-exported here so every pre-existing `from
#: frob.app.config import load_arch_config` (etc.) importer keeps working
#: unmodified.
__all__ = [
    "ARCH_DEFAULT_GOD_MODULE_MIN_CLUSTERS",
    "ARCH_DEFAULT_GOD_MODULE_MIN_EXPORTS",
    "ARCH_DEFAULT_LCOM4_MIN_FIELD_USING_METHODS",
    "ARCH_DEFAULT_LCOM4_MIN_METHODS",
    "ARCH_DEFAULT_MAX_CLASS_METHODS",
    "ARCH_DEFAULT_MAX_FILE_LINES",
    "ARCH_DEFAULT_MAX_FUNCTION_LINES",
    "ARCH_DEFAULT_MAX_LOCAL_IMPORTS",
    "ARCH_DEFAULT_MAX_NESTING_DEPTH",
    "ARCH_DEFAULT_MIXED_CONCERN_MIN_DECISION_POINTS",
    "AppConfig",
    "Subcommand",
    "load_arch_config",
    "stale_binary_warning",
    "stale_install_warning",
]


# frob:doc docs/modules/app.md#config
# frob:ticket T-1567
# frob:ticket T-1568
# frob:ticket T-1569
class Subcommand(str, enum.Enum):
    # frob:ticket T-0021
    scaffold = "scaffold"
    cycle = "cycle"
    # T-1238: `frob explore` groups map/outline/xref/docs-search.
    explore = "explore"
    # T-1567: `frob quality` groups check/test/dup/arch/bind/cycle/mutate/perf.
    quality = "quality"
    # T-1568: `frob design` groups sys/registry/docs/graph/exports.
    design = "design"
    # T-1569: `frob ops` groups release/natives/doctor/clean/fleet/deploy/
    # scaffold/gitlog/stats.
    ops = "ops"
    outline = "outline"
    map = "map"
    xref = "xref"
    parse = "parse"
    dup = "dup"
    arch = "arch"
    docs = "docs"
    bind = "bind"
    exports = "exports"
    check = "check"
    gitlog = "gitlog"
    graph = "graph"
    ack = "ack"
    ticket = "ticket"
    test = "test"
    vet = "vet"
    perf = "perf"
    release = "release"
    stats = "stats"
    serve = "serve"
    mutate = "mutate"
    sys = "sys"
    deploy = "deploy"
    doctor = "doctor"
    clean = "clean"
    # T-0412: list outstanding frob:debt entries.
    debt = "debt"
    # T-0407: unified registry capability -- per-registry disposition audit.
    registry = "registry"
    # T-0569: ratchet-pool baseline snapshot/clear.
    pool = "pool"
    # T-0573: cross-repo status/gate rollup and ticket routing.
    fleet = "fleet"
    # T-0441: `frob:` directive comment canonical-form wrap/unwrap.
    fmt = "fmt"
    # T-0864: frob-owned native crate build (maturin develop per declared
    # [[native]] rust crate, shared CARGO_TARGET_DIR).
    natives = "natives"
    # T-0638: list outstanding frob:deprecated entries.
    deprecated = "deprecated"
    # frob:ticket T-1525
    # T-1525: user-facing entrypoint for `frob.testing._coverage_refresh.
    # native_coverage_refresh` -- the frob-native coverage orchestration
    # T-1516 built as a library call with no CLI verb of its own.
    coverage = "coverage"
    # frob:ticket T-1697
    # T-1697: surface + operate the T-1686 unverified window (depth, age,
    # quarantine, attribution) -- status/now/explain/dispose.
    verify = "verify"


# frob:doc docs/modules/app.md#config
# frob:waive AFFECT001 reason="T-1150 added one new bool field (sys_check, frob sys \
# sync-interface --check); the established convention here IS a short per-field \
# paragraph (see the T-1004/T-1029/T-1057/T-1069/T-1130 precedents just above this \
# attr), but docs/modules/app.md is not in T-1150's declared scope and adding it \
# opened a scope-closure cascade over dozens of unrelated app/ symbols (SCOPE002, \
# verified) -- disclosed deferral, not a convention change; a follow-up should add the \
# T-1150 paragraph under its own scoped ticket"
# frob:ticket T-0030
# frob:ticket T-0085
# frob:ticket T-0115
# frob:ticket T-0877
# frob:ticket T-1150
# frob:ticket T-1525
# frob:ticket T-1567
# frob:ticket T-1568
# frob:ticket T-1569
# frob:ticket T-1697
class AppConfig(BaseModel):
    # frob:ticket T-0021
    subcommand: Subcommand | None = None

    # global output-layer flags (T-0448): resolved once into a
    # `frob.render.Renderer` per invocation, never re-read per command.
    color: Literal["auto", "always", "never"] | None = None
    no_color: bool = False

    # scaffold
    scaffold_command: str | None = None
    scaffold_type: str | None = None
    scaffold_name: str | None = None
    scaffold_output: Path | None = None
    scaffold_force: bool = False
    # scaffold pool (T-0877): `frob scaffold pool warm/lease/status`, wired
    # onto the T-0738 `frob.scaffold._pool` API.
    scaffold_pool_command: str | None = None
    scaffold_pool_n: int = 4

    # cycle
    cycle_path: Path | None = None
    cycle_lang: str | None = None
    cycle_suggest: bool = False

    # explore (T-1238): dispatches by explore_command onto the same
    # map/outline/xref/docs_* dests its standalone counterparts use.
    explore_command: str | None = None

    # quality (T-1567): dispatches by quality_command onto the same
    # check/test/dup/arch/cycle/mutate/perf_* dests its standalone
    # counterparts use. `bind` is dispatched directly by
    # `frob.__main__._dispatch`, never through this field.
    quality_command: str | None = None

    # design (T-1568): dispatches by design_command onto the same
    # sys/registry/docs/graph/exports_* dests its standalone counterparts
    # use.
    design_command: str | None = None

    # ops (T-1569): dispatches by ops_command onto the same
    # release/natives/doctor/clean/fleet/deploy/scaffold/gitlog/stats_*
    # dests its standalone counterparts use.
    ops_command: str | None = None

    # outline
    outline_file: Path | None = None
    outline_json: bool = False
    outline_all: bool = False

    # map
    map_path: Path | None = None
    map_json: bool = False
    map_depth: int | None = None
    map_all: bool = False

    # xref
    xref_symbol: str | None = None
    xref_path: Path | None = None
    xref_lang: str | None = None
    xref_json: bool = False
    xref_cross_file: bool = False

    # dup
    dup_path: Path | None = None
    dup_min_lines: int = 6
    dup_json: bool = False
    dup_probe: list[str] = []

    # arch
    arch_path: Path | None = None
    arch_json: bool = False
    arch_max_function_lines: int = 30
    arch_max_class_methods: int = 12

    # docs
    docs_path: Path | None = None
    docs_symbol: str | None = None
    docs_overview: bool = False
    docs_search: str | None = None
    docs_json: bool = False
    docs_sync_commands: bool = False  # T-1011

    # exports
    exports_path: Path | None = None
    exports_all: bool = False
    exports_exclude: list[str] = []
    exports_json: bool = False
    exports_write: bool = False
    # frob:ticket T-0876
    #: symbol to look up import-consumers for via `--consumers SYMBOL`;
    #: None means run the normal `exports_package` listing instead.
    exports_consumers: str | None = None
    # frob:ticket T-0876
    #: language override for `--consumers` (mirrors `xref_lang`'s choices).
    exports_lang: str | None = None

    # check (shared)
    check_path: Path | None = None
    check_type: str | None = (
        None  # "python", "cpp", "rust", "typescript", or None=auto-detect
    )
    check_json: bool = False
    check_valgrind: bool = False
    check_skip_tests: bool = False
    check_ticket: str | None = None
    check_base: str | None = None
    check_only: list[str] = []
    check_stamp_coverage: bool = False
    check_stamp_baseline: bool = False
    # frob:ticket T-1535
    #: `frob check --land-parity`: run the exact unscoped, cache-bypassed
    #: error evaluation the land pre-commit/post-land sweeps run, against
    #: the current tree, and exit -- lets a worktree agent converge before
    #: the coordinator ever lands. `False` (default) leaves normal
    #: full/`--only`/`--budget` behavior untouched.
    check_land_parity: bool = False
    # frob:ticket T-1764
    #: `frob check --census`: print the per-rule waive-rate table (fired,
    #: waived, waive-rate, dead-waiver count) from a full unscoped gate
    #: run and exit, instead of the normal full/`--only`/`--budget`
    #: dispatch. `False` (default) leaves existing behavior untouched.
    check_census: bool = False
    check_delta: bool = False
    # frob:ticket T-1260
    #: `frob check --fix`: apply every registered Tier-A deterministic
    #: auto-fix, then re-run the union of affected gates once in this same
    #: invocation. `False` (default) leaves `frob check` byte-identical to
    #: before this flag existed (T-1260 acceptance criterion 2).
    check_fix: bool = False
    # frob:ticket T-1004
    #: `frob check --budget N`: self-select and order stage chunks (the same
    #: `available_stages()` groups the playbook's chunked `--only` loop
    #: uses) to fit inside N seconds using persisted measured timings,
    #: instead of an agent hand-running the chunked loop itself. `None`
    #: (default) leaves normal full/`--only` behavior untouched.
    check_budget: int | None = None
    # frob:ticket T-0421
    #: `[check] skip_unchanged = true` in frob.toml only (no CLI flag, to
    #: keep __main__'s argument surface untouched) -- opts a polyglot
    #: auto-detect run into skipping a language's stage entirely when no
    #: file matching its own suffixes changed since `check_base`, reporting
    #: a visible SKIPPED (unchanged) line instead of silently re-running an
    #: untouched language every time.
    check_skip_unchanged: bool = False
    # frob:ticket T-1445
    #: `frob check --no-cache`: bypass `.frob/gate-cache.db` (T-0602/T-1346)
    #: and force every cacheable gate to recompute in full this run, a
    #: first-class CLI twin of the existing `FROB_NO_GATE_CACHE=1` env-var
    #: escape hatch. `False` (default) leaves normal cached behavior
    #: unchanged.
    check_no_cache: bool = False
    # -v/-vv count (T-0202): 0=summary+violations only, 1=INFO firehose,
    # 2+=full per-symbol DEBUG.
    check_verbose: int = 0
    # -v count for `frob ticket` (T-0768): 0=ticket output only (diagnostic
    # loggers clamped to WARNING), 1+=full INFO/DEBUG diagnostic firehose.
    ticket_verbose: int = 0
    # check (python)
    check_skip_ruff: bool = False
    check_skip_ty: bool = False
    check_skip_arch: bool = False
    check_skip_cycle: bool = False
    check_skip_dup: bool = False
    check_skip_bind: bool = False
    check_skip_exports: bool = False
    check_skip_gates: bool = False
    # check (cpp)
    check_build_dir: Path | None = None
    check_skip_build: bool = False
    check_skip_clang_tidy: bool = False
    check_skip_clang_format: bool = False
    # check (rust)
    check_skip_cargo_check: bool = False
    check_skip_clippy: bool = False
    check_skip_fmt: bool = False
    # check (typescript)
    check_skip_tsc: bool = False
    check_skip_eslint: bool = False
    check_skip_prettier: bool = False

    # gitlog
    gitlog_path: Path | None = None
    gitlog_granularity: GranularityLevel = "user"
    gitlog_since: str | None = None
    gitlog_until: str | None = None
    gitlog_limit: int | None = None
    gitlog_all: bool = False
    gitlog_json: bool = False

    # parse
    parse_tool: str | None = None
    parse_input: Path | None = None
    parse_exit_code: int = 0
    parse_json: bool = False
    parse_verbose: bool = False
    parse_passthrough: bool = False

    # graph
    graph_command: str | None = None  # build|query|why|affects
    graph_path: Path | None = None
    graph_ref: str | None = None
    graph_json: bool = False
    # frob:ticket T-0628
    graph_max_depth: int | None = None
    graph_max_nodes: int | None = None

    # ack
    ack_refs: list[str] = []
    ack_facet: str = "sig"
    ack_path: Path | None = None
    # frob:ticket T-1317
    ack_reason: str | None = None
    ack_reason_file: Path | None = None
    ack_list: bool = False

    # debt (T-0412)
    debt_path: Path | None = None

    # deprecated (T-0638)
    deprecated_path: Path | None = None
    deprecated_json: bool = False

    # registry (T-0407)
    registry_command: str | None = None  # audit|add
    registry_path: Path | None = None
    registry_json: bool = False
    registry_sync_gate_rules: bool = False  # T-0560
    debt_json: bool = False

    # registry add (T-0429)
    registry_add_file: str | None = None
    registry_add_key: str = "entries"
    registry_add_id: str | None = None
    registry_add_name: str | None = None
    registry_add_source_doc: str = ""

    # ticket
    ticket_command: str | None = None
    ticket_path: Path | None = None
    ticket_id: str | None = None
    ticket_ids: list[str] = []
    ticket_title: str | None = None
    ticket_kind: str | None = None
    ticket_origin: str | None = None
    ticket_acceptance: list[str] = []
    ticket_threat: str | None = None
    ticket_scope: list[str] = []
    ticket_blocked_by: list[str] = []
    ticket_parent: str | None = None
    # frob:ticket T-0715
    # `frob ticket new --tier epic|story|ticket` (default ticket).
    ticket_tier: str | None = None
    # frob:ticket T-0715
    # `frob ticket new --sprint LABEL` / `frob ticket sprint assign <id>
    # LABEL` / `frob ticket sprint show LABEL` -- the same field carries
    # all three (same reuse pattern as `ticket_component`).
    ticket_sprint: str | None = None
    ticket_body: str = ""
    # frob:ticket T-0737
    # `frob ticket new --body-file PATH` -- read the ticket body verbatim
    # from PATH instead of the shell (T-0737: long/backticked prose passed
    # inline through bash gets command-substituted before frob ever sees
    # it). Mutually exclusive with `--body`.
    ticket_body_file: Path | None = None
    # frob:ticket T-0737
    # `frob ticket new --acceptance-file PATH` -- read acceptance criteria
    # from PATH, blank-line-separated blocks (T-0737), instead of repeated
    # `--acceptance TEXT` flags. Mutually exclusive with `--acceptance`.
    ticket_acceptance_file: Path | None = None
    ticket_state: str | None = None
    # frob:ticket T-1528
    ticket_stats: bool = False
    ticket_by: str | None = None
    ticket_summary: str | None = None
    # frob:ticket T-1130
    # `frob ticket new/drop/fail --no-commit` -- opts out of the T-1130
    # auto-commit these three verbs perform on their own ledger write when
    # run against a git work tree (parity with T-1054's `start` auto-
    # commit). Default False: the commit happens unless explicitly opted
    # out, matching `start`'s own always-on precedent.
    ticket_no_commit: bool = False
    # frob:ticket T-0472
    # `frob ticket requeue <id> [--reason TEXT]` -- optional, logged only.
    ticket_reason: str | None = None
    # frob:ticket T-0579
    # `frob ticket drop <id> --reason TEXT [--absorbed-by T-####]`.
    ticket_absorbed_by: str | None = None
    ticket_caption: str = ""
    ticket_attach_path: Path | None = None
    ticket_json: bool = False
    ticket_show_blocked: bool = False
    ticket_ignore_lease: bool = False
    # frob:ticket T-0810
    # `frob ticket archive --force` -- override T-0764's live-cross-worktree-
    # lease refusal in `frob.tickets.archive`.
    ticket_force: bool = False
    # frob:ticket T-1762
    # `--force` (archive, land --finish) now requires --reason/--reason-file
    # -- the T-1733 escape-hatch-accountability principle applied to force
    # overrides: shared across both --force call sites since a single
    # invocation only ever exercises one of them.
    ticket_force_reason: str | None = None
    ticket_force_reason_file: Path | None = None
    # frob:ticket T-0455
    # `frob ticket scope <id> --add GLOB... --remove GLOB... --reason TEXT`
    ticket_scope_add: list[str] = []
    ticket_scope_remove: list[str] = []
    ticket_scope_reason: str | None = None
    # frob:ticket T-0737
    # `frob ticket scope <id> --reason-file PATH` -- read the scope-change
    # reason verbatim from PATH instead of the shell (T-0737). Mutually
    # exclusive with `--reason`.
    ticket_scope_reason_file: Path | None = None
    # frob:ticket T-0411
    ticket_priority: str | None = None
    ticket_priority_level: str | None = None
    # frob:ticket T-0834
    # `frob ticket kind <id> <kind>` -- the new kind value, same shape as
    # `ticket_priority_level`'s T-0411 precedent (`ticket_kind` above is
    # already taken by `frob ticket new --kind`).
    ticket_kind_value: str | None = None
    # frob:ticket T-1069
    # `frob ticket tier <id> <epic|story|ticket>` -- the new tier value, same
    # shape as `ticket_priority_level`'s T-0411 precedent (`ticket_tier`
    # above is already taken by `frob ticket new --tier`).
    ticket_tier_value: str | None = None
    # frob:ticket T-1613
    # `frob ticket runs-last <id> <on|off>` -- the new runs-last marker
    # value, same shape as `ticket_tier_value`'s T-1069 precedent.
    # argparse's own `choices=["on", "off"]` (see `_add_ticket_runs_last_
    # parser`) already restricts this at parse time, so no separate
    # enum-choice field validator is needed here the way `ticket_tier_value`
    # has one.
    ticket_runs_last_value: str | None = None
    ticket_evidence_ids: list[str] = []
    ticket_evidence_cmd: str | None = None
    # frob:ticket T-1670
    # `frob ticket evidence <id> --designate-repro NODE-ID`: mark NODE-ID
    # as the explicit BUG002 repro test, overriding the positional-first
    # default `_designated_repro_test` otherwise falls back to.
    ticket_designate_repro: str | None = None
    # frob:ticket T-1537
    #: `frob ticket evidence <id> --replace OLD-NODE-ID NEW-NODE-ID`: rebind
    #: one evidence id everywhere it appears (flat list + every acceptance
    #: binding), atomically. Empty (default) means no `--replace` given --
    #: `[]`/2-element `[old, new]` matches `dup_probe`'s own `nargs=2` shape.
    ticket_evidence_replace: list[str] = []
    # frob:ticket T-1733
    #: `frob ticket evidence <id> --replace OLD NEW (--reason TEXT |
    #: --reason-file PATH)`: why this evidence was rebound -- required,
    #: same T-0455 `frob ticket scope` precedent applied to evidence.
    #: Recorded in the ticket's `evidence_changes` audit trail so a
    #: weakened test can never be silently swapped in the way a shrunk
    #: `scope` already could not be.
    ticket_evidence_replace_reason: str | None = None
    # frob:ticket T-1733
    #: `--reason-file PATH` twin of the above, same mutual-exclusion shape
    #: as `ticket_scope_reason`/`ticket_scope_reason_file`.
    ticket_evidence_replace_reason_file: Path | None = None
    # frob:ticket T-1561
    # `frob ticket evidence <id> --replace OLD NEW --archived`: target an
    # archived ticket instead of an active one (COV003 scans the archive
    # too; the store's default single-ticket load/write only ever sees
    # active storage without this).
    ticket_evidence_archived: bool = False
    # frob:ticket T-0572
    # frob:ticket T-0749
    # `frob ticket evidence <id> <node-id>... --accepts N [N ...]` /
    # `frob ticket close <id> --evidence <node-id>... --accepts N [N ...]`
    # -- 0-based ticket.acceptance indices the given evidence ids also bind
    # to, in the same write as the evidence append (see add_evidence).
    # T-0749: `from_external` never copied this field from the parsed CLI
    # namespace into the AppConfig kwargs dict at all (missing from every
    # field-copy loop below) -- `--accepts N` was parsed by argparse into
    # `args.ticket_accepts` but silently dropped before `AppConfig(**d)`,
    # so the CLI always bound `accepts=[]` regardless of what was typed.
    # T-0572's own tests called `add_evidence`/`_apply_evidence` directly
    # and never exercised this CLI layer, so they never caught it.
    ticket_accepts: list[int] = []
    # frob:ticket T-0571
    # `frob ticket review <id> --verdict approve|reject --reviewer NAME
    # --findings-file PATH [--commit SHA]` -- records a structured
    # adversarial-review record as first-class evidence.
    ticket_review_verdict: str | None = None
    ticket_reviewer: str | None = None
    ticket_findings_file: Path | None = None
    ticket_review_commit: str | None = None
    # frob:ticket T-0571
    # `frob ticket close <id> --strict` -- config-gated
    # (`[tickets] require_review_for_close`), off by default: requires an
    # approve-verdict review record naming the current commit before close.
    ticket_close_strict: bool = False
    ticket_old_id: str | None = None
    ticket_new_id: str | None = None
    ticket_dry_run: bool = False
    # frob:ticket T-1492
    # `frob ticket migrate --to v2` -- wires migrate_v1_to_v2 (T-1259) onto
    # the existing `frob ticket migrate` subcommand; None (the default)
    # keeps today's collapse-dir-into-monofile behavior unchanged.
    ticket_migrate_to: str | None = None
    # frob:ticket T-0755
    # `frob ticket land <id> --skip-mutation-evidence` -- documented escape
    # hatch: a TEST016 confirmatory-only-evidence finding is logged but does
    # not refuse the land. For genuine false positives only.
    # frob:ticket T-1381
    # `frob release stamp --allow-unbumped` -- documented escape hatch for
    # the T-1381 refusal. Stamping rebaselines the recorded public API at
    # whatever version is current, so stamping an API change WITHOUT the
    # bump silences REL001 and the release never happens.
    release_allow_unbumped: bool = False
    # frob:ticket T-1768
    # `--allow-unbumped` now requires --reason/--reason-file whenever it
    # actually bypasses a real shortfall (mirrors T-1762's `ticket_force_
    # reason`/`ticket_force_reason_file` pattern exactly): the manifest
    # rewrite it triggers permanently redefines the REL001 baseline going
    # forward, unlike a one-invocation `--force` bypass.
    release_allow_unbumped_reason: str | None = None
    release_allow_unbumped_reason_file: Path | None = None
    ticket_skip_mutation_evidence: bool = False
    # frob:ticket T-1369
    # `frob ticket land <id> --allow-cross-ticket` -- documented escape
    # hatch for T-1355's CrossTicketLeakage refusal. A series worktree
    # legitimately hosts several tickets on one branch, and an open EPIC's
    # umbrella scope legitimately covers its own leaves' files, so the
    # refusal has false positives that would otherwise be unlandable.
    ticket_allow_cross_ticket: bool = False
    # frob:ticket T-0844
    # `frob ticket close <id> --skip-mutation-evidence` -- the close-path
    # twin of `ticket_skip_mutation_evidence` above: a TEST016 confirmatory-
    # only-evidence finding is logged but does not refuse the direct close.
    # For genuine false positives only.
    ticket_close_skip_mutation_evidence: bool = False
    # frob:ticket T-0631
    # `frob ticket land <id> --push`: after a real (non-dry-run) land
    # succeeds, push root's current branch to its upstream remote.
    ticket_land_push: bool = False
    # frob:ticket T-1175
    # `frob ticket land <id> --finish`: after a real land verifies clean
    # (proof line: commit is-ancestor-of-main + ticket state on main),
    # remove --worktree.
    ticket_land_finish: bool = False
    # frob:ticket T-1619
    # `frob ticket land <id> --retire-on-proof`: same verified-LAND-PROOF
    # gate as --finish, but ALSO deletes --worktree's branch after removing
    # the worktree checkout -- the one-command "verify then destroy" that
    # makes chaining `frob ticket land && git worktree remove` (unsafe: the
    # removal runs unconditionally, even after a failed land) structurally
    # unnecessary.
    ticket_land_retire_on_proof: bool = False
    # frob:ticket T-1269
    # `frob ticket land --plan --worktree PATH`: land a design-phase
    # worktree (docs + ledger changes, no closeable worked ticket)
    # atomically instead of a single ticket's own squash-land.
    ticket_land_plan: bool = False
    # frob:ticket T-1444
    # `frob ticket land <id> --worktree PATH --queue`: enqueue instead of
    # landing immediately (frob.tickets._land_queue.enqueue) -- returns
    # right away, does not wait for a drainer.
    ticket_land_queue: bool = False
    # frob:ticket T-1444
    # `frob ticket land --drain`: serially process every queued entry in
    # .frob/land-queue.json via frob.tickets._land_queue.drain_next, one
    # process, one invocation (not a long-running poll loop -- see
    # _land_drain's own docstring for why).
    ticket_land_drain: bool = False
    # frob:ticket T-1518
    # `frob ticket land --run-mutation-sweep`: standalone batch/nightly
    # processing of frob.tickets._mutation_sweep_queue's deferred TEST016
    # entries -- the same call --drain makes automatically after draining,
    # for a deployment that never calls --drain at all.
    ticket_land_run_mutation_sweep: bool = False
    ticket_worktree: Path | None = None
    # frob:ticket T-1243
    # `frob ticket brief --cluster <id>` / `frob ticket work --cluster <id>`
    # -- the epic/story id whose dispatchable descendants are briefed/
    # leased as one mission instead of a single ticket id.
    ticket_cluster: str | None = None
    # frob:ticket T-0474
    # `frob ticket start <id> --foreground` -- run the pre-work sweep
    # synchronously (the pre-T-0474 default) instead of backgrounding it.
    ticket_foreground: bool = False
    # frob:ticket T-0835
    # `frob ticket start <id> --steal` -- override a refusal caused by
    # another worktree holding a live cross-worktree lease on the ticket;
    # re-records the lease pinned to THIS worktree, invalidating the other
    # worktree's lease for any later close/land attempt.
    ticket_steal: bool = False
    # frob:ticket T-0476
    # `frob ticket reconcile [--apply] [--remove-orphans]`.
    ticket_reconcile_apply: bool = False
    ticket_reconcile_remove_orphans: bool = False
    # frob:ticket T-0458
    # `frob ticket done-report <id> (--why TEXT | --why-file PATH)` --
    # TEXT of "-" (or --why-file omitted with neither given) reads stdin,
    # so `frob ticket done-report T-#### -` works as documented.
    ticket_why: str | None = None
    ticket_why_file: Path | None = None
    ticket_base_ref: str = "main"
    # frob:ticket T-1684
    # `frob ticket sweep-async <id> --commit <sha>`: the land commit the
    # detached rapid-profile post-land sweep is verifying.
    ticket_sweep_commit: str | None = None
    # T-0323: `frob ticket merge-driver %O %A %B` -- git's merge-driver
    # protocol passes base/ours/theirs as temp file paths; ours (%A) is
    # both read and overwritten with the splice result.
    ticket_merge_base: Path | None = None
    ticket_merge_ours: Path | None = None
    ticket_merge_theirs: Path | None = None
    # frob:ticket T-0454
    # `frob ticket new --component NAME --label TAG...` (also read on
    # `frob ticket component <id> NAME` and `frob ticket label <id>
    # --add/--remove TAG...`).
    ticket_component: str | None = None
    ticket_labels: list[str] = []
    ticket_label_add: list[str] = []
    ticket_label_remove: list[str] = []
    # frob:ticket T-1029
    # `frob ticket accept <id> --criterion TEXT... | --criterion-file PATH`
    # -- append acceptance criteria to an EXISTING ticket (only `ticket new
    # --acceptance` supported this before).
    ticket_accept_criterion: list[str] = []
    ticket_accept_criterion_file: Path | None = None
    # frob:ticket T-1422
    # `frob ticket accept <id> --amend INDEX --text TEXT --reason TEXT` --
    # replace an existing criterion's text (a correction, not an append).
    ticket_accept_amend_index: int | None = None
    ticket_accept_amend_text: str | None = None
    # frob:ticket T-1422
    # `frob ticket accept <id> --remove INDEX --reason TEXT` -- drop an
    # existing criterion outright (unsatisfiable-by-construction case).
    ticket_accept_remove_index: int | None = None
    # frob:ticket T-1422
    # shared by --amend and --remove; same (--reason | --reason-file)
    # mutual-exclusion shape as `ticket_scope_reason`/`ticket_scope_reason_file`.
    ticket_accept_amend_reason: str | None = None
    ticket_accept_amend_reason_file: Path | None = None
    # frob:ticket T-0454
    # `frob ticket board [--component NAME] [--label TAG] [--json]`.
    ticket_board_component: str | None = None
    ticket_board_label: str | None = None
    # frob:ticket T-0715
    # `frob ticket doable --sprint LABEL [--by-parent]`.
    ticket_doable_sprint: str | None = None
    ticket_doable_by_parent: bool = False
    # frob:ticket T-1738
    # `frob ticket wave --agents N [--json] [--ignore-lease]`.
    ticket_wave_agents: int | None = None
    # frob:ticket T-0715
    # `frob ticket sprint assign|show` -- which sprint subcommand.
    ticket_sprint_command: str | None = None

    # test
    test_all: bool = False
    test_fuzz: bool = False
    test_collect: bool = False
    # frob:ticket T-0322
    test_wait_coverage: bool = False
    test_base: str | None = None
    test_lang: list[str] = []
    test_fallback: str | None = None
    test_json: bool = False
    test_path: Path | None = None

    # vet
    vet_path: Path | None = None
    vet_hook: str | None = None
    vet_json: bool = False
    # T-0147: local cvelistV5 mirror root for CVE matching, from
    # [tool.frob] in pyproject.toml (vet_cve_mirror key), CLI --cve-mirror
    # override.
    vet_cve_mirror: Path | None = None
    # T-0251: per-package scan timeout (seconds) and worker concurrency,
    # plumbed through to `scan_tree` (T-0208). `None`/1 preserve the
    # pre-existing untimed, single-worker behavior.
    vet_timeout: float | None = None
    vet_jobs: int | None = None

    # pool (T-0569): ratchet-pool baseline snapshot/clear.
    pool_command: str | None = None  # snapshot|clear
    pool_path: Path | None = None
    pool_rule: str | None = None
    pool_keys: list[str] = []
    pool_key: str | None = None
    pool_reason: str | None = None

    # verify (T-1697): surface + operate the T-1686 unverified window.
    verify_command: str | None = None  # status|now|explain|dispose
    verify_path: Path | None = None
    verify_json: bool = False
    #: `frob verify explain FINDING` -- `rule_id:file[:line]`.
    verify_finding: str | None = None
    #: `frob verify dispose` -- repeatable `rule_id:file:line=TICKET_ID`
    #: entries (line may be empty, e.g. `rule:file:=T-0001`).
    verify_dispose_filed: list[str] = []
    #: `frob verify dispose` -- repeatable `rule_id:file:line=REASON`
    #: entries (line may be empty).
    verify_dispose_dismissed: list[str] = []
    verify_dispose_reason: str | None = None
    verify_dispose_actor: str | None = None

    # release
    release_command: str | None = None  # stamp|check
    release_path: Path | None = None
    release_json: bool = False

    # stats
    stats_path: Path | None = None
    stats_days: int | None = None
    stats_json: bool = False

    # doctor
    doctor_json: bool = False
    doctor_usage: bool = False  # frob:ticket T-1360

    # clean (T-0457: tiered, artifact-only workspace cleanup)
    clean_path: Path | None = None
    clean_all: bool = False
    clean_deep: bool = False
    clean_yes: bool = False
    clean_json: bool = False

    # fmt (T-0441: frob: directive canonical-form wrap/unwrap)
    fmt_path: Path | None = None
    fmt_check: bool = False
    fmt_json: bool = False

    # perf
    perf_command: str | None = None  # profile|heat
    perf_path: Path | None = None
    perf_argv: list[str] = []
    perf_tests: bool = False
    perf_json: bool = False
    perf_smells: bool = False
    perf_top: int | None = None
    perf_annotate: Path | None = None
    perf_ref: str | None = None
    # frob:ticket T-0765
    perf_file: Path | None = None
    perf_format: str | None = None
    perf_sampler: bool = False
    perf_interval_s: float | None = None
    perf_max_depth: int | None = None
    # frob:ticket T-0712
    perf_by: str | None = None

    # serve
    serve_path: Path | None = None

    # mutate
    mutate_file: Path | None = None
    mutate_path: Path | None = None
    mutate_argv: list[str] = []
    mutate_json: bool = False

    # sys (T-0084 plan; T-0085 doc; T-0086 export; T-0115 audit;
    # check/trace/capacity/
    # threats are later phase-5 tickets, not yet landed)
    sys_command: str | None = None  # plan|doc|export|sync-interface (more per phase 5)
    sys_path: Path | None = None
    sys_apply: bool = False
    sys_view: str = "owasp-top-10"  # T-0085: `frob sys doc`'s baseline view
    sys_export_format: str | None = None
    sys_export_path: Path | None = None
    # frob:ticket T-1150
    sys_check: bool = False  # `frob sys sync-interface --check`: report, never write

    # deploy (T-0257: `frob deploy generate` -- install/status/uninstall
    # bash compiled from std.host HostManifest facts)
    deploy_command: str | None = None  # generate|audit per deploy epic T-0254
    deploy_path: Path | None = None
    deploy_out_dir: Path | None = None
    deploy_check: bool = False

    # fleet (T-0573): `frob fleet status [--manifest PATH] [--json]
    # [--skip-gates]` / `frob fleet route --repo NAME --title TEXT
    # [--kind K] [--priority P] [--scope GLOB...] [--body TEXT]`.
    fleet_command: str | None = None  # status|route
    fleet_manifest: Path | None = None
    fleet_json: bool = False
    fleet_skip_gates: bool = False
    fleet_repo: str | None = None
    fleet_title: str | None = None
    fleet_kind: str | None = None
    fleet_priority: str | None = None
    fleet_scope: list[str] = []
    fleet_body: str = ""

    # deploy audit (T-0259: `frob deploy audit --vm <name>` -- VirtualBox
    # snapshot-diff harness, NOT run by `make check`)
    deploy_vm: str | None = None
    deploy_ssh_host: str | None = None
    deploy_ssh_user: str = "root"
    deploy_ssh_key: Path | None = None
    deploy_base_snapshot: str = "base"
    deploy_audit_output: Path | None = None

    # frob natives (T-0864): frob-owned maturin-develop-per-crate build.
    natives_command: str | None = None  # build
    natives_path: Path | None = None

    # frob coverage (T-1525): user-facing CLI verb over `native_coverage_
    # refresh` (T-1516) -- `--full` forces a cold-start-style whole-suite
    # run instead of the default touched-set incremental refresh.
    coverage_full: bool = False
    coverage_path: Path | None = None
    # frob:ticket T-1572
    coverage_base: str | None = None

    # frob:ticket T-1271
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_state_lists_valid_values kind="unit"  # noqa: E501
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_valid_ticket_state_passes_through kind="unit"  # noqa: E501
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_none_ticket_state_passes_through kind="unit"  # noqa: E501
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_kind_lists_valid_values kind="unit"  # noqa: E501
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_kind_value_lists_valid_values kind="unit"  # noqa: E501
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_tier_lists_valid_values kind="unit"  # noqa: E501
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_tier_value_lists_valid_values kind="unit"  # noqa: E501
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_priority_level_lists_valid_values kind="unit"  # noqa: E501
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_origin_lists_valid_values kind="unit"  # noqa: E501
    # frob:tests tests/test_app_config.py::TestEnumFieldValidation.test_invalid_ticket_review_verdict_lists_valid_values kind="unit"  # noqa: E501
    @field_validator("ticket_state")
    @classmethod
    def _check_ticket_state(cls, v: str | None) -> str | None:
        """`frob ticket list --state/--status VALUE` (T-0578 alias): reject
        an unrecognized state with every legal value named inline, instead
        of the bare `ValueError` a raw `TicketState(v)` call downstream
        would raise (T-1271 acceptance criterion 0)."""
        return _validate_enum_choice(v, TicketState, "ticket state")

    @field_validator("ticket_kind")
    @classmethod
    def _check_ticket_kind(cls, v: str | None) -> str | None:
        """`frob ticket new --kind VALUE`: same inline-valid-values
        treatment as `_check_ticket_state` (T-1271)."""
        return _validate_enum_choice(v, TicketKind, "ticket kind")

    @field_validator("ticket_kind_value")
    @classmethod
    def _check_ticket_kind_value(cls, v: str | None) -> str | None:
        """`frob ticket kind <id> VALUE`: same inline-valid-values
        treatment as `_check_ticket_state` (T-1271)."""
        return _validate_enum_choice(v, TicketKind, "ticket kind")

    @field_validator("ticket_tier")
    @classmethod
    def _check_ticket_tier(cls, v: str | None) -> str | None:
        """`frob ticket new --tier VALUE`: same inline-valid-values
        treatment as `_check_ticket_state` (T-1271)."""
        return _validate_enum_choice(v, TicketTier, "ticket tier")

    @field_validator("ticket_tier_value")
    @classmethod
    def _check_ticket_tier_value(cls, v: str | None) -> str | None:
        """`frob ticket tier <id> VALUE`: same inline-valid-values
        treatment as `_check_ticket_state` (T-1271)."""
        return _validate_enum_choice(v, TicketTier, "ticket tier")

    @field_validator("ticket_priority_level")
    @classmethod
    def _check_ticket_priority_level(cls, v: str | None) -> str | None:
        """`frob ticket priority <id> VALUE`: same inline-valid-values
        treatment as `_check_ticket_state` (T-1271)."""
        return _validate_enum_choice(v, Priority, "ticket priority")

    @field_validator("ticket_origin")
    @classmethod
    def _check_ticket_origin(cls, v: str | None) -> str | None:
        """`frob ticket new --origin VALUE`: same inline-valid-values
        treatment as `_check_ticket_state` (T-1271)."""
        return _validate_enum_choice(v, Origin, "ticket origin")

    @field_validator("ticket_review_verdict")
    @classmethod
    def _check_ticket_review_verdict(cls, v: str | None) -> str | None:
        """`frob ticket review <id> --verdict VALUE`: same inline-valid-
        values treatment as `_check_ticket_state` (T-1271)."""
        return _validate_enum_choice(v, ReviewVerdict, "ticket review verdict")

    @classmethod
    # frob:tests tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_missing_file_falls_back_to_defaults kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_reads_and_merges_tool_frob_table kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_subcommand_is_resolved_to_the_enum kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_no_color_flag_is_copied_when_present kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_string_field_from_the_first_copy_loop_is_carried kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_bool_flag_from_the_second_copy_loop_defaults_false kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_bool_flag_from_the_second_copy_loop_is_set_true kind="unit"  # noqa: E501
    def from_external(cls, args: argparse.Namespace, file: Path) -> "AppConfig":
        # frob:doc docs/modules/app.md#config
        # frob:waive AFFECT001 reason="same T-1150 sys_check/scope-closure disclosed \
        # deferral as this class's own AFFECT001 waiver above -- this is the \
        # bool-field loop `sys_check` was added to, no separate rationale needed"
        # frob:ticket T-0021
        # frob:ticket T-0085
        # frob:ticket T-0030
        # frob:ticket T-1150
        # frob:ticket T-1270
        d = _build_external_config_kwargs(args, file, Subcommand)
        return cls(**d)

    @classmethod
    # frob:tests tests/unit/test_app_config_from_external_t1276.py::TestFromArgs.test_delegates_to_from_external_with_pyproject_default kind="unit"  # noqa: E501
    def from_args(cls, args: argparse.Namespace) -> "AppConfig":
        # frob:doc docs/modules/app.md#config
        return cls.from_external(args, Path("pyproject.toml"))
