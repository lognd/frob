"""Typed surface of the strata-core kernels (docs/strata/kernel.md).

frob:describes strata-core/src/lib.rs
"""

def reachable(
    edges: list[tuple[str, str, str, bool, bool]],
    src: str,
    through_barriers: bool,
) -> dict[str, list[str]]: ...

# T-0690: the Rust side's `.expect("...")` on the condensation DAG's
# zero-indegree SCC lookup is a genuine (unreachable-in-practice, but
# statically real) panic site -- pyo3 surfaces any Rust panic as
# `PanicException` at this call boundary.
# frob:raises PanicException
def worst_age(
    edges: list[tuple[str, str, str, float]],
    target: str,
) -> tuple[float, list[str]]: ...
def demand(rates: list[tuple[str, float]], node: str) -> float: ...
def propagated_demand(
    edges: list[tuple[str, str, str, float | None, float]],
    target: str,
) -> tuple[float, list[str]]: ...
def parse_source(text: str) -> str: ...

# T-3042: was never stubbed here (a T-3007 gap only exposed once this
# ticket added the first real Python caller, frob.gates._vmodel.vmodel_gate)
#
# T-3044 H3: node/edge tuples grew a trailing `attrs` dict -- a `test` node
# requires `runnable`, an `artifact` node requires `code_ref`, a
# `supersedes` edge requires `reason`; any other kind accepts `{}`.
def vmodel_check(
    nodes: list[tuple[str, str, str | None, dict[str, str]]],
    edges: list[tuple[str, str, str, dict[str, str]]],
) -> tuple[list[str], list[tuple[str, str]]]: ...
