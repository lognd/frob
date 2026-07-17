"""Typed surface of the strata-core kernels (docs/strata/kernel.md)."""

def reachable(
    edges: list[tuple[str, str, str, bool]],
    src: str,
    through_barriers: bool,
) -> dict[str, list[str]]: ...
def worst_age(
    edges: list[tuple[str, str, str, float]],
    target: str,
) -> tuple[float, list[str]]: ...
def demand(rates: list[tuple[str, float]], node: str) -> float: ...
