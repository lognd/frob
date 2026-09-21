"""ROUTE001 tests (F-307 H3-7, frob:ticket T-4115): a route decorated
with a conventional HTTP-verb decorator that returns a bare dict literal
with no response model should be flagged -- a synthetic fixture, since
frob itself defines no HTTP routes (flagged per T-4115's own Done-report
instruction: not drawn from frob's own dogfood surface)."""

from pathlib import Path

from frob.findings import Severity
from frob.gates._route_response_model import route_response_model_gate
from tests.conftest import _git_init, _write


class TestRouteResponseModelGate:
    """Synthetic route-decorator/response-model fixture package, per
    T-4115's own fixture note."""

    # frob:tests src/frob/gates/_route_response_model.py::route_response_model_gate
    def test_bare_dict_literal_return_fires(self, tmp_path: Path) -> None:
        """FAIL before this rule exists (`frob.gates._route_response_model`
        did not exist -- the import would raise `ModuleNotFoundError`);
        PASS after: a route returning `return {"status": "ok"}` directly
        is reported. Must-fire fixture from T-4115's own ticket body."""
        _write(
            tmp_path,
            "src/pkg/routes.py",
            "class App:\n"
            "    def get(self, path):\n"
            "        def deco(fn):\n"
            "            return fn\n"
            "        return deco\n\n\n"
            "app = App()\n\n\n"
            '@app.get("/status")\n'
            "def status_route():\n"
            '    return {"status": "ok"}\n',
        )
        _git_init(tmp_path)
        violations = route_response_model_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "ROUTE001"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "src/pkg/routes.py"
        assert violations[0].line == 12
        assert "status_route" in violations[0].message

    # frob:tests src/frob/gates/_route_response_model.py::route_response_model_gate
    def test_typed_constructor_return_is_silent(self, tmp_path: Path) -> None:
        """Must-stay-quiet fixture from T-4115's own ticket body: a route
        returning an instantiated typed object (`StatusResponse(...)`,
        a call, not a dict display) never fires."""
        _write(
            tmp_path,
            "src/pkg/routes.py",
            "class App:\n"
            "    def get(self, path):\n"
            "        def deco(fn):\n"
            "            return fn\n"
            "        return deco\n\n\n"
            "app = App()\n\n\n"
            "class StatusResponse:\n"
            "    def __init__(self, status):\n"
            "        self.status = status\n\n\n"
            '@app.get("/status")\n'
            "def status_route():\n"
            '    return StatusResponse(status="ok")\n',
        )
        _git_init(tmp_path)
        assert route_response_model_gate(tmp_path) == ()

    # frob:tests src/frob/gates/_route_response_model.py::route_response_model_gate
    def test_pure_unpack_of_typed_dump_is_silent(self, tmp_path: Path) -> None:
        """Third case from T-4115's own ticket body, decided and
        documented explicitly here: `return {**model.model_dump()}` is a
        dict display in source, but its ONLY content is a double-starred
        unpack of a typed-looking expression -- this repo treats that as
        derived from a typed object, not a raw literal, so it stays
        quiet."""
        _write(
            tmp_path,
            "src/pkg/routes.py",
            "class App:\n"
            "    def get(self, path):\n"
            "        def deco(fn):\n"
            "            return fn\n"
            "        return deco\n\n\n"
            "app = App()\n\n\n"
            '@app.get("/status")\n'
            "def status_route(model):\n"
            "    return {**model.model_dump()}\n",
        )
        _git_init(tmp_path)
        assert route_response_model_gate(tmp_path) == ()

    def test_mixed_unpack_and_literal_key_fires(self, tmp_path: Path) -> None:
        """A dict display that mixes a `**` unpack with a literal
        key/value pair still contains an un-typed literal pair -- the
        exact surface this rule exists to catch -- so it DOES fire,
        distinct from the pure-unpack case above."""
        _write(
            tmp_path,
            "src/pkg/routes.py",
            "class App:\n"
            "    def get(self, path):\n"
            "        def deco(fn):\n"
            "            return fn\n"
            "        return deco\n\n\n"
            "app = App()\n\n\n"
            '@app.get("/status")\n'
            "def status_route(model):\n"
            '    return {**model.model_dump(), "extra": 1}\n',
        )
        _git_init(tmp_path)
        violations = route_response_model_gate(tmp_path)
        assert len(violations) == 1

    def test_undecorated_function_is_ignored(self, tmp_path: Path) -> None:
        """A plain function returning a bare dict literal, with no route
        decorator at all, is not this gate's concern."""
        _write(
            tmp_path,
            "src/pkg/helpers.py",
            'def build_payload():\n    return {"status": "ok"}\n',
        )
        _git_init(tmp_path)
        assert route_response_model_gate(tmp_path) == ()

    def test_file_scoped_waiver_covers_it(self, tmp_path: Path) -> None:
        """A `frob:waive ROUTE001` directive anywhere in the same source
        file waives the finding -- the standard file-scoped waiver
        mechanism, for a route deliberately without a response model."""
        _write(
            tmp_path,
            "src/pkg/routes.py",
            '# frob:waive ROUTE001 reason="deliberately untyped debug route"\n'
            "class App:\n"
            "    def get(self, path):\n"
            "        def deco(fn):\n"
            "            return fn\n"
            "        return deco\n\n\n"
            "app = App()\n\n\n"
            '@app.get("/status")\n'
            "def status_route():\n"
            '    return {"status": "ok"}\n',
        )
        _git_init(tmp_path)
        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only
        from tests.conftest import _snapshot  # noqa: PLC0415 - internal, test-only

        snapshot = _snapshot(tmp_path)
        raw = route_response_model_gate(tmp_path)
        assert len(raw) == 1
        kept, waived = _apply_waivers(raw, snapshot)
        assert kept == ()
        assert len(waived) == 1

    def test_no_python_files_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "README.md", "hello\n")
        _git_init(tmp_path)
        assert route_response_model_gate(tmp_path) == ()
