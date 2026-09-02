"""Shared fixtures and test helpers for the tests/unit/arch_suite/
package (T-1201 split of tests/unit/test_arch.py): synthetic
module/graph-edge builders, the FIXTURES root, and the HAS_ARCH
availability guard reused across the arch-family test modules."""

from __future__ import annotations

from pathlib import Path

from frob.graph._models import Edge, EdgeKind

#: tests/unit/arch_suite/'s own parent-of-parent is tests/, same as
#: the original tests/unit/test_arch.py's own FIXTURES -- the split
#: added one more directory level, so this walks up one further than
#: the pre-split module did.
FIXTURES = Path(__file__).parent.parent.parent / "fixtures"

try:
    from frob.arch import (
        analyze_project,  # noqa: F401 -- re-exported for the split modules
    )

    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False

if HAS_ARCH:
    _DEEP_NEST_SRC = (FIXTURES / "arch_python" / "src" / "deep_nest.py").read_text()
else:
    _DEEP_NEST_SRC = ""


def _big_module_text(n_lines: int) -> str:
    """A syntactically trivial python module of at least `n_lines` lines,
    used to drive the large-file line-count threshold without dragging in
    any other arch category (T-0368 test helper)."""
    header = "from __future__ import annotations\n\n"
    body = "\n".join(f"X_{i} = {i}" for i in range(n_lines)) + "\n"
    return header + body


def _lsp_module(base, override):
    """Build a two-class `NormalizedModule` (T-0618) with `override`'s
    `bases` naming `base`'s class name -- the same-file base<->override
    linkage every `_solid.py` check resolves from."""
    from frob.arch._normalized import NormalizedModule

    return NormalizedModule(
        path="pkg/mod.py",
        language="python",
        classes=[base, override],
    )


def _isp_module(*classes):
    """Build a `NormalizedModule` (T-0619) from `classes`, mirroring
    `_lsp_module`'s convenience for ISP fixtures needing 2+ classes."""
    from frob.arch._normalized import NormalizedModule

    return NormalizedModule(path="pkg/mod.py", language="python", classes=list(classes))


def _stub_method(name: str, line: int):
    """A structurally empty override body (T-0619's `_is_stub_method`
    "empty shell" shape: no branches/loops/calls/field-accesses/catches,
    no value-returning return) for fat-interface fixtures."""
    from frob.arch._normalized import NormalizedFunction

    return NormalizedFunction(name=name, line=line, body_line_count=1, is_method=True)


def _real_method(name: str, line: int):
    """An override body with a real call event (T-0619) -- NOT a stub by
    `_is_stub_method`'s test, for fat-interface negative fixtures."""
    from frob.arch._normalized import (
        NormalizedCall,
        NormalizedFunction,
        NormalizedReturn,
    )

    return NormalizedFunction(
        name=name,
        line=line,
        body_line_count=2,
        is_method=True,
        calls=[NormalizedCall(callee="do_work", line=line + 1)],
        returns=[NormalizedReturn(line=line + 1, value_text="result")],
    )


def _transition(src: str, proto: str, frm: str, to: str) -> Edge:
    """Test helper: a `TRANSITION` edge shaped like `dsl.parse_directives`'s
    output, without needing real source files to drive the DSL parser."""
    return Edge(
        src=src,
        kind=EdgeKind.TRANSITION,
        target=proto,
        origin=f"{src}:1",
        attrs={"proto": proto, "from": frm, "to": to},
    )


def _requires(src: str, proto: str, state: str) -> Edge:
    """Test helper: a `REQUIRES` edge shaped like `dsl.parse_directives`'s
    output."""
    return Edge(
        src=src,
        kind=EdgeKind.REQUIRES,
        target=proto,
        origin=f"{src}:1",
        attrs={"proto": proto, "state": state},
    )


# frob:ticket T-0809
def _acquire(src: str, resource: str) -> Edge:
    """Test helper: an `ACQUIRE` edge shaped like `dsl.parse_directives`'s
    output for `frob:acquire <resource>`."""
    return Edge(src=src, kind=EdgeKind.ACQUIRE, target=resource, origin=f"{src}:1")


# frob:ticket T-0809
def _release(src: str, resource: str) -> Edge:
    """Test helper: a `RELEASE` edge shaped like `dsl.parse_directives`'s
    output for `frob:release <resource>`."""
    return Edge(src=src, kind=EdgeKind.RELEASE, target=resource, origin=f"{src}:1")


# frob:ticket T-0809
def _escapes(src: str, resource: str) -> Edge:
    """Test helper: an `ESCAPES` edge shaped like `dsl.parse_directives`'s
    output for `frob:escapes <resource>`."""
    return Edge(src=src, kind=EdgeKind.ESCAPES, target=resource, origin=f"{src}:1")
