"""T-0701 SYS205 mode-conformance litmus fixtures (`frob.strata.
_mode_conformance`): each `AccessMode` gets a firing case and a clean
case, mirroring `test_access.py`/`test_effects.py`'s "construct a
`Node`/`Module` directly, write real source to `tmp_path`, join" shape.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, bind_code, check_mode_conformance
from frob.strata._ast import Module, ResourceDecl
from frob.strata._mode_conformance import SYS_MODE_NONCONFORMANCE


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestCheckModeConformance:
    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_read_mo\
    # de_fails_on_a_write_open
    def test_read_mode_fails_on_a_write_open(self, tmp_path: Path):
        """GIVEN a node declaring mode=read whose bound code opens the
        resource for writing WHEN sys checks run THEN a fail-closed error
        names the write site."""
        _write(tmp_path, "reader/main.py", 'open("cfg.json", "w").write("x")\n')
        model = KernelModel(
            nodes=(
                Node(
                    id="Reader",
                    trust="trusted",
                    attrs=("code=reader/**", "access=cfg:read"),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m")
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.rule == SYS_MODE_NONCONFORMANCE
        assert v.node == "Reader"
        assert v.resource == "cfg"
        assert v.file == "reader/main.py"
        assert v.line == 1
        assert v.category == "write_open"

    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_read_mo\
    # de_discharges_on_read_only_code
    def test_read_mode_discharges_on_read_only_code(self, tmp_path: Path):
        """GIVEN conforming code per mode THEN it discharges (read case)."""
        _write(tmp_path, "reader/main.py", 'data = open("cfg.json").read()\n')
        model = KernelModel(
            nodes=(
                Node(
                    id="Reader",
                    trust="trusted",
                    attrs=("code=reader/**", "access=cfg:read"),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m")
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert report.violations == ()

    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_append_\
    # mode_fails_on_a_truncating_write
    def test_append_mode_fails_on_a_truncating_write(self, tmp_path: Path):
        """APPEND: a non-append write (truncate/rewrite) is a violation."""
        _write(tmp_path, "logger/main.py", 'open("log.txt", "w").write("x")\n')
        model = KernelModel(
            nodes=(
                Node(
                    id="Logger",
                    trust="trusted",
                    attrs=("code=logger/**", "access=log:append"),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m")
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert len(report.violations) == 1
        assert report.violations[0].category == "write_open"

    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_append_\
    # mode_discharges_on_an_append_only_open
    def test_append_mode_discharges_on_an_append_only_open(self, tmp_path: Path):
        _write(tmp_path, "logger/main.py", 'open("log.txt", "a").write("x")\n')
        model = KernelModel(
            nodes=(
                Node(
                    id="Logger",
                    trust="trusted",
                    attrs=("code=logger/**", "access=log:append"),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m")
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert report.violations == ()

    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_exclusi\
    # ve_mode_fails_on_access_outside_the_arbiter
    def test_exclusive_mode_fails_on_access_outside_the_arbiter(self, tmp_path: Path):
        """GIVEN mode=exclusive with an access outside the arbiter context
        WHEN sys checks run THEN an error names the unguarded path."""
        _write(tmp_path, "writer/main.py", 'open("db.bin", "w").write("x")\n')
        model = KernelModel(
            nodes=(
                Node(
                    id="Writer",
                    trust="trusted",
                    attrs=("code=writer/**", "access=db:exclusive"),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m", resources=(ResourceDecl(id="db", lock="db_lock"),))
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.mode.value == "exclusive"
        assert v.file == "writer/main.py"
        assert v.line == 1

    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_exclusi\
    # ve_mode_discharges_inside_the_declared_lock
    def test_exclusive_mode_discharges_inside_the_declared_lock(self, tmp_path: Path):
        _write(
            tmp_path,
            "writer/main.py",
            'with db_lock:\n    open("db.bin", "w").write("x")\n',
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="Writer",
                    trust="trusted",
                    attrs=("code=writer/**", "access=db:exclusive"),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m", resources=(ResourceDecl(id="db", lock="db_lock"),))
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert report.violations == ()

    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_exclusi\
    # ve_mode_with_no_lock_declared_fails_closed
    def test_exclusive_mode_with_no_lock_declared_fails_closed(self, tmp_path: Path):
        """A bare (or `arbitrated_by`-only) resource has no code-checkable
        arbiter in v0 -- fails closed even with zero write observations."""
        model = KernelModel(
            nodes=(
                Node(
                    id="Writer",
                    trust="trusted",
                    attrs=("code=writer/**", "access=db:exclusive"),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m")
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert len(report.violations) == 1
        assert report.violations[0].category == "no_arbiter"

    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_alpha_m\
    # ode_fails_on_an_unguarded_write
    def test_alpha_mode_fails_on_an_unguarded_write(self, tmp_path: Path):
        _write(tmp_path, "upgrader/main.py", 'open("db.bin", "w").write("x")\n')
        model = KernelModel(
            nodes=(
                Node(
                    id="Upgrader",
                    trust="trusted",
                    attrs=("code=upgrader/**", "access=db:alpha"),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m", resources=(ResourceDecl(id="db", lock="db_lock"),))
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert len(report.violations) == 1
        assert report.violations[0].mode.value == "alpha"

    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_write_m\
    # ode_is_unrestricted_in_v0
    def test_write_mode_is_unrestricted_in_v0(self, tmp_path: Path):
        """WRITE: reads+writes are both allowed unconditionally (disclosed
        v0 cut, module docstring -- no path-level identity yet)."""
        _write(tmp_path, "writer/main.py", 'open("f.txt", "w").write("x")\n')
        model = KernelModel(
            nodes=(
                Node(
                    id="Writer",
                    trust="trusted",
                    attrs=("code=writer/**", "access=f:write"),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m")
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert report.violations == ()

    # frob:tests \
    # tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance.test_node_wi\
    # th_no_access_declarations_is_never_checked
    def test_node_with_no_access_declarations_is_never_checked(self, tmp_path: Path):
        _write(tmp_path, "plain/main.py", 'open("f.txt", "w").write("x")\n')
        model = KernelModel(
            nodes=(Node(id="Plain", trust="trusted", attrs=("code=plain/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        module = Module(name="m")
        report = check_mode_conformance(model, module, binding, tmp_path)
        assert report.violations == ()
