from __future__ import annotations

import argparse
import enum
import tomllib
from pathlib import Path

from pydantic import BaseModel

from frob.gitlog import GranularityLevel


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


# frob:doc docs/modules/app.md#config
# frob:ticket T-0030
# frob:ticket T-0085
# frob:ticket T-0115
class AppConfig(BaseModel):
    # frob:ticket T-0021
    subcommand: Subcommand | None = None

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
    ticket_caption: str = ""
    ticket_attach_path: Path | None = None
    ticket_json: bool = False
    ticket_evidence_ids: list[str] = []
    ticket_old_id: str | None = None
    ticket_new_id: str | None = None
    ticket_dry_run: bool = False
    ticket_worktree: Path | None = None

    # test
    test_all: bool = False
    test_fuzz: bool = False
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

    # release
    release_command: str | None = None  # stamp|check
    release_path: Path | None = None
    release_json: bool = False

    # stats
    stats_path: Path | None = None
    stats_days: int | None = None
    stats_json: bool = False

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

        for field in (
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
            "ticket_caption",
            "ticket_old_id",
            "ticket_new_id",
            "test_base",
            "test_fallback",
            "vet_hook",
            "release_command",
            "perf_command",
            "perf_ref",
            "sys_command",
            "sys_view",
            "sys_export_format",
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
            "ticket_path",
            "ticket_attach_path",
            "ticket_worktree",
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
        ):
            val = getattr(args, int_field, None)
            if val is not None:
                d[int_field] = val

        # Int fields
        parse_ec = getattr(args, "parse_exit_code", None)
        if parse_ec is not None:
            d["parse_exit_code"] = int(parse_ec)

        # Multi-value list fields
        exports_exclude = getattr(args, "exports_exclude", None)
        if exports_exclude:
            d["exports_exclude"] = exports_exclude

        for list_field in (
            "check_only",
            "ack_refs",
            "ticket_ids",
            "ticket_scope",
            "ticket_blocked_by",
            "ticket_acceptance",
            "ticket_evidence_ids",
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
            "ticket_json",
            "test_all",
            "test_fuzz",
            "test_json",
            "vet_json",
            "stats_json",
            "mutate_json",
            "perf_tests",
            "perf_json",
            "perf_smells",
            "sys_apply",
            "ticket_dry_run",
        ):
            if getattr(args, flag, False):
                d[flag] = True

        return cls(**d)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "AppConfig":
        # frob:doc docs/modules/app.md#config
        return cls.from_external(args, Path("pyproject.toml"))
