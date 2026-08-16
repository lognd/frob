"""Shared fast-YAML-loader selection (T-1206/T-1333 lineage, T-1204
PERF010 burn-down): the single home for "pick the fastest SAFE YAML
loader available, correctly, once" -- previously duplicated as
`frob.tickets._store._yaml_loader` (re-exported by `frob.gates.__init__`
as `_tickets_yaml_loader`) with every other `yaml.safe_load`/`yaml.load`
call site in the repo left on the slow pure-Python default. Every new
per-document YAML parse should call `fast_yaml_loader()` here rather
than re-deriving the libyaml-availability-and-coverage-tracer check.
"""

from __future__ import annotations

import sys

import yaml

__all__ = ["fast_yaml_loader"]


# frob:ticket T-1204
# frob:tests \
# tests/unit/test_ticket_store.py::TestYamlLoader.test_detects_coverage_tracer_by_modu\
# le_name  # noqa: E501
# frob:tests \
# tests/unit/test_ticket_store.py::TestYamlLoader.test_no_active_tracer_is_not_coverag\
# e  # noqa: E501
def _coverage_tracer_active() -> bool:
    """True when `sys.gettrace()` is installed by `coverage.py` (or a
    subclass of its tracer), so callers can avoid a known-bad interaction
    between that tracer and `yaml.CSafeLoader` (T-1333: the CSafeLoader/
    libyaml C extension corrupts frontmatter parses -- 'could not
    determine a constructor for the tag None' on otherwise-valid YAML --
    specifically when a `coverage.py` trace function is active; both
    bare `coverage run` and `pytest-cov` install their tracer this same
    way, and the pure-Python `SafeLoader` is unaffected). Detection is by
    the active tracer callable's module name rather than an env var,
    since that is the actual mechanism responsible for the corruption and
    stays accurate under any invocation style (`coverage run`, pytest-cov,
    a hand-rolled `sys.settrace`-based coverage tool)."""
    tracer = sys.gettrace()
    if tracer is None:
        return False
    module = getattr(tracer, "__module__", None) or getattr(
        type(tracer), "__module__", ""
    )
    return module.startswith("coverage")


# frob:ticket T-1204
# frob:doc docs/modules/tickets-data-storage.md#shared-yaml-loader-selection-frobyaml_io
# frob:tests \
# tests/unit/test_ticket_store.py::TestYamlLoader.test_prefers_csafeloader_when_libyam\
# l_present  # noqa: E501
# frob:tests \
# tests/unit/test_ticket_store.py::TestYamlLoader.test_falls_back_to_safeloader_withou\
# t_libyaml  # noqa: E501
# frob:tests \
# tests/unit/test_ticket_store.py::TestYamlLoader.test_falls_back_to_safeloader_under_\
# active_coverage_tracer  # noqa: E501
def fast_yaml_loader() -> type[yaml.SafeLoader]:
    """The fastest SAFE YAML loader available: `yaml.CSafeLoader` (libyaml,
    a C extension) when installed, else the pure-Python `yaml.SafeLoader`
    (T-1206: `yaml.safe_load` always uses the pure-Python `SafeLoader`
    even when `yaml.__with_libyaml__` reports the C extension is
    installed -- both loaders reject the exact same YAML constructs, so
    this swap is fail-open-preserving). Falls back to `SafeLoader`
    regardless of `__with_libyaml__` whenever a `coverage.py` trace
    function is active (T-1333: a known-bad CSafeLoader/coverage-tracer
    interaction that corrupts otherwise-valid parses) -- see
    `_coverage_tracer_active`'s docstring."""
    if yaml.__with_libyaml__ and not _coverage_tracer_active():
        return yaml.CSafeLoader
    return yaml.SafeLoader
