"""frob.app -- CLI dispatch layer (docs/modules/app.md).

Each `frob.app.<name>_runner` module's `run` is the genuine subcommand
entrypoint `frob.app.app` reaches via dynamic `importlib`/`getattr`
dispatch (T-0362); re-exported here module-aliased (`<name>_runner_run`)
since these modules share the bare name `run`. `frob.app._style`'s
`style_*` helpers are the shared CLI-output formatting layer used across
most runner modules, and `frob.app.telemetry`'s recorder/helper functions
are consumed cross-module (`app.app`, `app.ticket_runner`,
`app.stats_runner`, `frob.stats._agentic`, `frob.gates._pii_structural`,
tests) -- both re-exported for the same reason (T-0362, T-0599).
"""

from frob.app import (
    ack_runner,
    arch_runner,
    bind_runner,
    check_runner,
    clean_runner,
    cycle_runner,
    debt_runner,
    deploy_runner,
    docs_runner,
    doctor_runner,
    dup_runner,
    exports_runner,
    fleet_runner,
    gitlog_runner,
    graph_runner,
    map_runner,
    mutate_runner,
    outline_runner,
    parse_runner,
    perf_runner,
    pool_runner,
    registry_runner,
    release_runner,
    scaffold_runner,
    serve_runner,
    stats_runner,
    sys_runner,
    test_runner,
    ticket_runner,
    vet_runner,
    xref_runner,
)
from frob.app._style import (
    style_fail,
    style_header,
    style_ok,
    style_rule,
    style_state,
    style_ticket_id,
    style_warn,
)
from frob.app.app import App
from frob.app.config import (
    AppConfig,
    Subcommand,
    load_arch_config,
    stale_install_warning,
)
from frob.app.telemetry import (
    append_event,
    estimate_tokens,
    is_disabled,
    iso_now,
    record_cli_event,
    record_ticket_event,
    redact_command,
    timed_call,
    tree_hash,
)

ack_runner_run = ack_runner.run
arch_runner_run = arch_runner.run
bind_runner_run = bind_runner.run
check_runner_run = check_runner.run
clean_runner_run = clean_runner.run
cycle_runner_run = cycle_runner.run
debt_runner_run = debt_runner.run
deploy_runner_run = deploy_runner.run
docs_runner_run = docs_runner.run
doctor_runner_run = doctor_runner.run
dup_runner_run = dup_runner.run
exports_runner_run = exports_runner.run
fleet_runner_run = fleet_runner.run
gitlog_runner_run = gitlog_runner.run
graph_runner_run = graph_runner.run
map_runner_run = map_runner.run
mutate_runner_run = mutate_runner.run
outline_runner_run = outline_runner.run
parse_runner_run = parse_runner.run
perf_runner_run = perf_runner.run
pool_runner_run = pool_runner.run
registry_runner_run = registry_runner.run
release_runner_run = release_runner.run
scaffold_runner_run = scaffold_runner.run
serve_runner_run = serve_runner.run
stats_runner_run = stats_runner.run
sys_runner_run = sys_runner.run
test_runner_run = test_runner.run
ticket_runner_run = ticket_runner.run
vet_runner_run = vet_runner.run
xref_runner_run = xref_runner.run

__all__ = [
    "App",
    "AppConfig",
    "Subcommand",
    "ack_runner_run",
    "append_event",
    "arch_runner_run",
    "bind_runner_run",
    "check_runner_run",
    "clean_runner_run",
    "cycle_runner_run",
    "debt_runner_run",
    "deploy_runner_run",
    "docs_runner_run",
    "doctor_runner_run",
    "dup_runner_run",
    "estimate_tokens",
    "exports_runner_run",
    "fleet_runner_run",
    "gitlog_runner_run",
    "graph_runner_run",
    "is_disabled",
    "iso_now",
    "load_arch_config",
    "map_runner_run",
    "mutate_runner_run",
    "outline_runner_run",
    "parse_runner_run",
    "perf_runner_run",
    "pool_runner_run",
    "record_cli_event",
    "record_ticket_event",
    "redact_command",
    "registry_runner_run",
    "release_runner_run",
    "scaffold_runner_run",
    "serve_runner_run",
    "stale_install_warning",
    "stats_runner_run",
    "style_fail",
    "style_header",
    "style_ok",
    "style_rule",
    "style_state",
    "style_ticket_id",
    "style_warn",
    "sys_runner_run",
    "test_runner_run",
    "ticket_runner_run",
    "timed_call",
    "tree_hash",
    "vet_runner_run",
    "xref_runner_run",
]
