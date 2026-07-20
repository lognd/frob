"""frob.app -- CLI dispatch layer (docs/modules/app.md).

Each `frob.app.<name>_runner` module's `run` is the genuine subcommand
entrypoint `frob.app.app` reaches via dynamic `importlib`/`getattr`
dispatch (T-0362); re-exported here module-aliased (`<name>_runner_run`)
since 25 modules share the bare name `run`. `frob.app._style`'s
`style_*` helpers are the shared CLI-output formatting layer used across
most runner modules and are re-exported for the same reason.
"""

from frob.app import (
    ack_runner,
    arch_runner,
    bind_runner,
    check_runner,
    cycle_runner,
    deploy_runner,
    docs_runner,
    dup_runner,
    exports_runner,
    gitlog_runner,
    graph_runner,
    map_runner,
    mutate_runner,
    outline_runner,
    parse_runner,
    perf_runner,
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
from frob.app.config import AppConfig, Subcommand

ack_runner_run = ack_runner.run
arch_runner_run = arch_runner.run
bind_runner_run = bind_runner.run
check_runner_run = check_runner.run
cycle_runner_run = cycle_runner.run
deploy_runner_run = deploy_runner.run
docs_runner_run = docs_runner.run
dup_runner_run = dup_runner.run
exports_runner_run = exports_runner.run
gitlog_runner_run = gitlog_runner.run
graph_runner_run = graph_runner.run
map_runner_run = map_runner.run
mutate_runner_run = mutate_runner.run
outline_runner_run = outline_runner.run
parse_runner_run = parse_runner.run
perf_runner_run = perf_runner.run
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
    "arch_runner_run",
    "bind_runner_run",
    "check_runner_run",
    "cycle_runner_run",
    "deploy_runner_run",
    "docs_runner_run",
    "dup_runner_run",
    "exports_runner_run",
    "gitlog_runner_run",
    "graph_runner_run",
    "map_runner_run",
    "mutate_runner_run",
    "outline_runner_run",
    "parse_runner_run",
    "perf_runner_run",
    "release_runner_run",
    "scaffold_runner_run",
    "serve_runner_run",
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
    "vet_runner_run",
    "xref_runner_run",
]
