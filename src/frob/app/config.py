# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/app/config.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"
# frob:waive SCOPE001 reason="T-0319 scope comma-joined, matches nothing (T-0241 bug)"
# frob:waive SCOPE001 reason="T-0458 needs new AppConfig dest fields for done-report's CLI flags; T-0455's formal scope protocol is queued, not built -- ad-hoc waive per existing T-0176/T-0220 precedent"  # noqa: E501
# frob:waive SCOPE001 reason="T-0455 itself needs new AppConfig fields (ticket_scope_add/remove/reason) for its own `frob ticket scope` CLI wiring -- T-0455's declared scope is tickets/**+ticket_runner.py+__main__.py, not config.py; bootstrap precedent, same as the T-0458 waive above"  # noqa: E501
from __future__ import annotations

import argparse
import enum
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from frob.gitlog import GranularityLevel
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#config
class Subcommand(str, enum.Enum):
    # frob:ticket T-0021
    scaffold = "scaffold"
    cycle = "cycle"
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


# frob:doc docs/modules/app.md#config
# frob:ticket T-0030
# frob:ticket T-0085
# frob:ticket T-0115
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

    # cycle
    cycle_path: Path | None = None
    cycle_lang: str | None = None
    cycle_suggest: bool = False

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

    # exports
    exports_path: Path | None = None
    exports_all: bool = False
    exports_exclude: list[str] = []
    exports_json: bool = False
    exports_write: bool = False

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
    check_delta: bool = False
    # frob:ticket T-0421
    #: `[check] skip_unchanged = true` in frob.toml only (no CLI flag, to
    #: keep __main__'s argument surface untouched) -- opts a polyglot
    #: auto-detect run into skipping a language's stage entirely when no
    #: file matching its own suffixes changed since `check_base`, reporting
    #: a visible SKIPPED (unchanged) line instead of silently re-running an
    #: untouched language every time.
    check_skip_unchanged: bool = False
    # -v/-vv count (T-0202): 0=summary+violations only, 1=INFO firehose,
    # 2+=full per-symbol DEBUG.
    check_verbose: int = 0
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
    graph_command: str | None = None  # build|query|why
    graph_path: Path | None = None
    graph_ref: str | None = None
    graph_json: bool = False

    # ack
    ack_refs: list[str] = []
    ack_facet: str = "sig"
    ack_path: Path | None = None

    # debt (T-0412)
    debt_path: Path | None = None

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
    ticket_body: str = ""
    ticket_state: str | None = None
    ticket_by: str | None = None
    ticket_summary: str | None = None
    # frob:ticket T-0472
    # `frob ticket requeue <id> [--reason TEXT]` -- optional, logged only.
    ticket_reason: str | None = None
    # frob:ticket T-0579
    # `frob ticket drop <id> --reason TEXT [--absorbed-by T-####]`.
    ticket_absorbed_by: str | None = None
    ticket_caption: str = ""
    ticket_attach_path: Path | None = None
    ticket_json: bool = False
    # frob:waive SCOPE001 reason="T-0453 scope omitted this file; doable --show-blocked/--ignore-lease need AppConfig fields, T-0176/T-0220 precedent (T-0455)"  # noqa: E501
    ticket_show_blocked: bool = False
    ticket_ignore_lease: bool = False
    # frob:ticket T-0455
    # `frob ticket scope <id> --add GLOB... --remove GLOB... --reason TEXT`
    ticket_scope_add: list[str] = []
    ticket_scope_remove: list[str] = []
    ticket_scope_reason: str | None = None
    # frob:ticket T-0411
    # frob:waive SCOPE001 reason="T-0411 needs new/priority AppConfig fields; T-0453/T-0455 bootstrap precedent, T-0446 tracks the general gap"  # noqa: E501
    ticket_priority: str | None = None
    ticket_priority_level: str | None = None
    ticket_evidence_ids: list[str] = []
    ticket_evidence_cmd: str | None = None
    ticket_old_id: str | None = None
    ticket_new_id: str | None = None
    ticket_dry_run: bool = False
    ticket_worktree: Path | None = None
    # frob:ticket T-0474
    # `frob ticket start <id> --foreground` -- run the pre-work sweep
    # synchronously (the pre-T-0474 default) instead of backgrounding it.
    ticket_foreground: bool = False
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
    # frob:waive SCOPE001 reason="T-0323 scope omitted this file, filed T-draft-bc39c17f"  # noqa: E501
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
    # frob:ticket T-0454
    # `frob ticket board [--component NAME] [--label TAG] [--json]`.
    ticket_board_component: str | None = None
    ticket_board_label: str | None = None

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

    # clean (T-0457: tiered, artifact-only workspace cleanup)
    clean_path: Path | None = None
    clean_all: bool = False
    clean_deep: bool = False
    clean_yes: bool = False
    clean_json: bool = False

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
    sys_command: str | None = None  # plan|doc|export (more per roadmap phase 5)
    sys_path: Path | None = None
    sys_apply: bool = False
    sys_view: str = "owasp-top-10"  # T-0085: `frob sys doc`'s baseline view
    sys_export_format: str | None = None
    sys_export_path: Path | None = None

    # deploy (T-0257: `frob deploy generate` -- install/status/uninstall
    # bash compiled from std.host HostManifest facts)
    deploy_command: str | None = None  # generate|audit per deploy epic T-0254
    deploy_path: Path | None = None
    deploy_out_dir: Path | None = None
    deploy_check: bool = False

    # deploy audit (T-0259: `frob deploy audit --vm <name>` -- VirtualBox
    # snapshot-diff harness, NOT run by `make check`)
    deploy_vm: str | None = None
    deploy_ssh_host: str | None = None
    deploy_ssh_user: str = "root"
    deploy_ssh_key: Path | None = None
    deploy_base_snapshot: str = "base"
    deploy_audit_output: Path | None = None

    # frob:waive TEST005 reason="from_external 87.2% branch cover, debt T-0160"
    @classmethod
    def from_external(cls, args: argparse.Namespace, file: Path) -> "AppConfig":
        # frob:doc docs/modules/app.md#config
        # frob:ticket T-0021
        # frob:ticket T-0085
        # frob:ticket T-0030
        file_cfg: dict = {}
        if file.exists():
            with file.open("rb") as f:
                data = tomllib.load(f)
            file_cfg = data.get("tool", {}).get("frob", {})

        d: dict = {**file_cfg}

        sub = getattr(args, "subcommand", None)
        if sub is not None:
            d["subcommand"] = Subcommand(sub)

        no_color = getattr(args, "no_color", None)
        if no_color is not None:
            d["no_color"] = no_color

        for field in (
            "color",
            "scaffold_command",
            "scaffold_type",
            "scaffold_name",
            "cycle_lang",
            "xref_symbol",
            "xref_lang",
            "parse_tool",
            "docs_symbol",
            "docs_search",
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
            "ticket_why",
            "ticket_base_ref",
            "ticket_scope_reason",
            "ticket_priority",
            "ticket_priority_level",
            "ticket_component",
            "ticket_board_component",
            "ticket_board_label",
            "test_base",
            "test_fallback",
            "vet_hook",
            "release_command",
            "perf_command",
            "perf_ref",
            "sys_command",
            "sys_view",
            "sys_export_format",
            "deploy_command",
            "deploy_vm",
            "deploy_ssh_host",
            "deploy_ssh_user",
            "deploy_base_snapshot",
        ):
            val = getattr(args, field, None)
            if val is not None:
                d[field] = val

        for path_field in (
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
            "pool_path",
            "registry_path",
            "ticket_path",
            "ticket_attach_path",
            "ticket_worktree",
            "ticket_merge_base",
            "ticket_merge_ours",
            "ticket_merge_theirs",
            "ticket_why_file",
            "test_path",
            "vet_path",
            "vet_cve_mirror",
            "perf_path",
            "release_path",
            "stats_path",
            "perf_annotate",
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
        ):
            val = getattr(args, path_field, None)
            if val is not None:
                d[path_field] = Path(val)

        # Int fields
        for int_field in (
            "map_depth",
            "dup_min_lines",
            "arch_max_function_lines",
            "arch_max_class_methods",
            "gitlog_limit",
            "perf_top",
            "stats_days",
            "check_verbose",
            "vet_jobs",
        ):
            val = getattr(args, int_field, None)
            if val is not None:
                d[int_field] = val

        # Int fields
        parse_ec = getattr(args, "parse_exit_code", None)
        if parse_ec is not None:
            d["parse_exit_code"] = int(parse_ec)

        # Float fields
        for float_field in ("vet_timeout",):
            val = getattr(args, float_field, None)
            if val is not None:
                d[float_field] = val

        # Multi-value list fields
        exports_exclude = getattr(args, "exports_exclude", None)
        if exports_exclude:
            d["exports_exclude"] = exports_exclude

        for list_field in (
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
            "ticket_labels",
            "ticket_label_add",
            "ticket_label_remove",
            "test_lang",
            "perf_argv",
            "mutate_argv",
            "dup_probe",
        ):
            val = getattr(args, list_field, None)
            if val:
                d[list_field] = val

        ticket_body = getattr(args, "ticket_body", None)
        if ticket_body is not None:
            d["ticket_body"] = ticket_body

        # Bool flags: only override when explicitly True
        for flag in (
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
            "graph_json",
            "registry_sync_gate_rules",
            "debt_json",
            "registry_json",
            "ticket_json",
            "ticket_show_blocked",
            "ticket_ignore_lease",
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
            "sys_apply",
            "ticket_dry_run",
            "ticket_foreground",
            "ticket_reconcile_apply",
            "ticket_reconcile_remove_orphans",
            "deploy_check",
            "clean_all",
            "clean_deep",
            "clean_yes",
            "clean_json",
        ):
            if getattr(args, flag, False):
                d[flag] = True

        return cls(**d)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "AppConfig":
        # frob:doc docs/modules/app.md#config
        return cls.from_external(args, Path("pyproject.toml"))


#: The calibrated arch thresholds (T-0373): `frob.arch.analyze_project`'s
#: own keyword defaults (30/12/8/4/500) are conservative fallbacks for
#: library callers with no `frob.toml` in scope; a real repo's `[arch]`
#: table -- or, absent one, these values -- is what `frob check`'s ARCH
#: stage and `frob arch` should actually enforce.
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_FUNCTION_LINES = 60
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_CLASS_METHODS = 12
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_LOCAL_IMPORTS = 8
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_NESTING_DEPTH = 4
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_FILE_LINES = 800


# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
# frob:tests tests/unit/test_config.py::test_reads_override
# frob:tests tests/unit/test_config.py::test_missing_toml_defaults
# frob:tests tests/unit/test_config.py::test_missing_section_defaults
# frob:tests tests/unit/test_config.py::test_partial_override
# frob:tests tests/unit/test_config.py::test_malformed_toml_defaults
def load_arch_config(root: Path) -> dict[str, int]:
    """The `[arch]` table from `root/frob.toml` (`max_function_lines`,
    `max_class_methods`, `max_local_imports`, `max_nesting_depth`,
    `max_file_lines`), defaulting every unset key to the calibrated values
    above -- the fix for T-0373: `frob.arch.analyze_project`'s own
    keyword defaults were reaching `frob check`'s ARCH gate unchanged,
    silently overriding the user's already-disclosed calibration decision
    (large-file at 500, long-function at 30) instead of honoring it.

    Returns a plain kwargs dict ready to splat into `analyze_project(root,
    **load_arch_config(root))`. A missing or malformed `frob.toml` (or a
    missing `[arch]` table) is not an error -- it just means "use the
    calibrated defaults", same posture as `frob.gates._dup_config` and
    every other per-section frob.toml reader in this codebase.
    """
    defaults = {
        "max_function_lines": ARCH_DEFAULT_MAX_FUNCTION_LINES,
        "max_class_methods": ARCH_DEFAULT_MAX_CLASS_METHODS,
        "max_local_imports": ARCH_DEFAULT_MAX_LOCAL_IMPORTS,
        "max_nesting_depth": ARCH_DEFAULT_MAX_NESTING_DEPTH,
        "max_file_lines": ARCH_DEFAULT_MAX_FILE_LINES,
    }
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return defaults
    try:
        with toml_path.open("rb") as fh:
            arch_cfg = tomllib.load(fh).get("arch", {})
        return {
            key: int(arch_cfg.get(key, default)) for key, default in defaults.items()
        }
    except (OSError, tomllib.TOMLDecodeError, ValueError, TypeError) as exc:
        _log.warning("load_arch_config: frob.toml unreadable, using defaults: %s", exc)
        return defaults


# frob:ticket T-0358
# frob:doc docs/modules/app.md#entry-point
# frob:tests tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch  # noqa: E501
# frob:tests tests/unit/test_config.py::test_stale_install_warning_none_for_editable_checkout  # noqa: E501
# frob:tests tests/unit/test_config.py::test_stale_install_warning_none_when_versions_match  # noqa: E501
def stale_install_warning(repo_root: Path) -> str | None:
    """A loud, one-line warning string if the RUNNING `frob` package is
    installed OUTSIDE `repo_root`'s own `src/frob/` (a globally `uv tool
    install`ed binary, e.g. `~/.local/bin/frob`) while `repo_root` is a
    frob source checkout whose `pyproject.toml` declares a DIFFERENT
    version -- the stale-global-binary phantom-numbers trap (T-0358):
    an old installed gate implementation silently runs against a newer
    working tree, so gate rule ids the new tree has waived (e.g. SEC110/
    PII010 added after the installed version was built) read back as
    'unrecognized rule id' and violation counts are simply wrong.

    `None` (no warning) when: `repo_root` has no `pyproject.toml`, that
    file does not declare `[project] name = "frob"` (not this repo at
    all), the running package's own `__init__.py` resolves to exactly
    `repo_root/src/frob/__init__.py` (an editable install / `uv run frob`
    from this same checkout -- never stale), or the installed and
    declared versions already match. Deliberately a pure string-or-None
    return, not a log call itself, so callers can decide severity (stderr
    print for `main()`, `_log.warning` for `frob doctor`/`frob check`)."""
    import importlib.metadata
    import importlib.util

    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        with pyproject.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = data.get("project", {})
    if project.get("name") != "frob":
        return None
    repo_version = project.get("version")
    if not repo_version:
        return None

    spec = importlib.util.find_spec("frob")
    if spec is None or spec.origin is None:
        return None
    running_init = Path(spec.origin).resolve()
    local_init = (repo_root / "src" / "frob" / "__init__.py").resolve()
    if running_init == local_init:
        return None

    try:
        installed_version = importlib.metadata.version("frob")
    except importlib.metadata.PackageNotFoundError:
        return None
    if installed_version == repo_version:
        return None

    return (
        f"frob: WARNING -- running installed frob {installed_version} "
        f"({running_init}) inside a checkout whose pyproject.toml "
        f"declares frob {repo_version}. Gate logic can differ between "
        f"versions and produce silently wrong results -- use "
        f"'uv run frob' or 'make check'/'make' instead of the bare "
        f"installed binary."
    )
