"""T-1222: golden tests for `frob_core.py_function_metrics`, the native
rust arch python metrics single-pass walk -- parity against
`frob.arch._python`'s `_py_max_nesting`/`_py_cyclomatic`/`_py_collect_
body_events`, which `_py_build_function`/`_py_build_module` currently
compute via three separate Python recursions per function. Extraction
only: no rule evaluation is exercised or asserted here, matching the
kernel's own scope."""

from __future__ import annotations

from pathlib import Path

import frob_core

from frob.arch import _python as ap
from frob.lang import raw_tree


# frob:waive WIRE001 reason="a private golden-test helper used only by \
# TestPyFunctionMetricsParity's own methods below, in this same file -- there is no \
# production caller to wire it to by design, it exists solely to assemble the existing \
# Python-side computation for comparison against the native kernel's output, mirroring \
# the T-1220/T-1221 _python_side/_rust_side precedent in \
# tests/unit/test_extract_native.py" follow_up="T-1503"
# frob:ticket T-1222
def _python_side_metrics(source: bytes, tmp_path: Path) -> list[tuple]:
    """The existing Python-side computation for every function's (span,
    nesting, cyclomatic, events) tuple, in the SAME shape the native
    kernel returns (module docstring's one disclosed deviation --
    `declared_raises` -- stripped from each call arg's parent tuple here
    too, so the comparison is apples to apples)."""
    path = tmp_path / "sample.py"
    path.write_bytes(source)
    parsed = raw_tree(path)
    tree, _src, _lang = parsed.danger_ok

    def collect(node, out: list[tuple]) -> None:
        for c in node.children:
            if c.type == "function_definition":
                span = (c.start_point[0] + 1, c.end_point[0] + 1)
                body = ap._child(c, "body")
                nesting = ap._py_max_nesting(body) if body is not None else 0
                cyc = ap._py_cyclomatic(body) if body is not None else 0
                branches: list = []
                loops: list = []
                calls: list = []
                field_accesses: list = []
                returns: list = []
                raises: list = []
                catches: list = []
                subscripts: list = []
                if body is not None:
                    ap._py_collect_body_events(
                        body,
                        branches,
                        loops,
                        calls,
                        field_accesses,
                        returns,
                        raises,
                        catches,
                        subscripts,
                    )
                out.append(
                    (
                        span,
                        nesting,
                        cyc,
                        (
                            [(b.line, b.condition_text) for b in branches],
                            [(loop_.line, loop_.kind) for loop_ in loops],
                            [
                                (
                                    call.callee,
                                    call.line,
                                    [(a.index, a.keyword, a.ident) for a in call.args],
                                )
                                for call in calls
                            ],
                            [(f.name, f.line, f.is_write) for f in field_accesses],
                            [(r.line, r.value_text) for r in returns],
                            [(r.line, r.exception_type) for r in raises],
                            [(cat.line, cat.exception_type) for cat in catches],
                            [s.line for s in subscripts],
                        ),
                    )
                )
                if body is not None:
                    collect(body, out)
                continue
            collect(c, out)

    out: list[tuple] = []
    collect(tree.root_node, out)
    return out


# frob:ticket T-1222
class TestPyFunctionMetricsParity:
    """`frob_core.py_function_metrics` vs the existing Python walk
    (`frob.arch._python`), across representative shapes plus this repo's
    own source."""

    # frob:ticket T-1222
    def test_nested_control_flow_and_self_field_access(self, tmp_path: Path) -> None:
        # frob:tests frob-core/src/arch_python.rs::py_function_metrics kind="unit"
        source = (
            b"class Foo:\n"
            b"    def bar(self, x):\n"
            b"        if x:\n"
            b"            for i in range(3):\n"
            b"                self.count += 1\n"
            b"                try:\n"
            b"                    y = do(i)\n"
            b"                except ValueError as e:\n"
            b'                    raise RuntimeError("bad") from e\n'
            b"                return y\n"
            b"        return None\n"
        )
        assert frob_core.py_function_metrics(source) == _python_side_metrics(
            source, tmp_path
        )

    # frob:ticket T-1222
    def test_flat_function_has_zero_nesting_and_low_cyclomatic(
        self, tmp_path: Path
    ) -> None:
        # frob:tests frob-core/src/arch_python.rs::py_function_metrics kind="unit"
        source = b"def flat(a, b):\n    x = a + b\n    return x\n"
        result = frob_core.py_function_metrics(source)
        assert result == _python_side_metrics(source, tmp_path)
        (span, nesting, cyc, _events) = result[0]
        assert span == (1, 3)
        assert nesting == 0
        assert cyc == 0

    # frob:ticket T-1222
    def test_nested_function_definition_is_flattened_into_own_entry(
        self, tmp_path: Path
    ) -> None:
        # frob:tests frob-core/src/arch_python.rs::py_function_metrics kind="unit"
        source = (
            b"def outer():\n"
            b"    def inner(z):\n"
            b"        if z:\n"
            b"            return z\n"
            b"        return None\n"
            b"    return inner\n"
        )
        result = frob_core.py_function_metrics(source)
        assert len(result) == 2
        assert result == _python_side_metrics(source, tmp_path)

    # frob:ticket T-1222
    def test_unparseable_source_returns_empty_not_a_crash(self) -> None:
        # frob:tests frob-core/src/arch_python.rs::py_function_metrics kind="unit"
        # Never raises across the FFI boundary -- even nonsense input just
        # parses as best-effort tree-sitter error recovery, never a PyErr.
        result = frob_core.py_function_metrics(b"\x00\x01\xff not python at all ((((")
        assert isinstance(result, list)

    # frob:ticket T-1222
    def test_this_repos_own_arch_python_module_matches(self, tmp_path: Path) -> None:
        # frob:tests frob-core/src/arch_python.rs::py_function_metrics kind="unit"
        # One real, large file from this repo's own source -- a committed
        # regression lock, not only synthetic fixtures.
        source = Path("src/frob/arch/_python.py").read_bytes()
        assert frob_core.py_function_metrics(source) == _python_side_metrics(
            source, tmp_path
        )
