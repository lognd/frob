"""Unit-level coverage for `frob.deploy._conform`'s DEPLOY002/DEPLOY003
bidirectional conformance check (T-0258): structured mutation-surface
extraction, the manifest-derived expected surface, and the tampered-
script litmus (a smuggled extra `useradd` fires DEPLOY002; a removed
required step fires DEPLOY003; clean generated scripts pass both).
"""

from __future__ import annotations

from pathlib import Path

from frob.deploy._conform import (
    _PARSE_ERROR_TARGET,
    MutationTarget,
    deploy_conformance_violations,
    expected_mutation_surface,
    extract_mutation_surface,
)
from frob.deploy._generate import generate_all, sorted_manifest_entries
from frob.strata._models import KernelModel, Node

_STRATA_SRC = """\
module deploy_conform_fixture

node api : trusted {
    clearance Internal;
    runs_as "api-svc";
    unit;
    owns "/etc/api" "0644";
    listens 8080;
}
"""


# frob:waive DUP001 reason="parallel test fixtures across 3 sibling test file(s) (3 \
# sites) sharing an arrange-act scaffold typical of exhaustive per-case/per-scenario \
# coverage; extracting would obscure per-case intent"
def _model() -> KernelModel:
    return KernelModel(
        nodes=(
            Node(
                id="api",
                trust="trusted",
                attrs=("runs_as=api-svc", "unit", "owns=/etc/api:0644", "listens=8080"),
            ),
        )
    )


def _write_design(root: Path) -> None:
    design = root / "design"
    design.mkdir(parents=True, exist_ok=True)
    (design / "fixture.strata").write_text(_STRATA_SRC)


def _write_clean_deploy(root: Path) -> Path:
    deploy_dir = root / "deploy"
    deploy_dir.mkdir()
    for filename, content in generate_all(_model()).items():
        (deploy_dir / filename).write_text(content)
    return deploy_dir


class TestExtract:
    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_install(self):
        install = generate_all(_model())["install.sh"]
        surface = extract_mutation_surface(install)
        assert MutationTarget(kind="user", target="api-svc") in surface
        assert MutationTarget(kind="path", target="/etc/api") in surface
        assert MutationTarget(kind="unit", target="frob-deploy-api.service") in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_unterminated_quote_is_parse_error(self):
        # A line that cannot be tokenized as shell at all (unbalanced
        # quote) must NOT be silently dropped -- it becomes the
        # fail-closed parse-error sentinel, exercising the
        # `_TokenizeError` except branch.
        surface = extract_mutation_surface('useradd "unterminated\n')
        assert MutationTarget(kind="parse-error", target=_PARSE_ERROR_TARGET) in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_no_heredoc(self):
        # The unit-file heredoc body carries unquoted systemd directives
        # (ReadWritePaths=, Description=, CapabilityBoundingSet=) that
        # must never be mistaken for a mkdir/chown/cp/install mutation.
        install = generate_all(_model())["install.sh"]
        assert "ReadWritePaths=" in install
        surface = extract_mutation_surface(install)
        assert (
            MutationTarget(kind="path", target="ReadWritePaths=/etc/api") not in surface
        )
        for target in surface:
            assert "ReadWritePaths" not in target.target


class TestEvasion:
    """The reviewer's REJECT battery on round 1's line-regex-with-a-
    quoting-requirement extractor: every one of these is ORDINARY,
    non-exotic shell and every one is an evasion a genuine tokenizer
    must NOT miss. Each fires DEPLOY002 via a real `useradd`/`systemctl`
    target that a red-team tamper would use to smuggle a user/unit past
    the checker."""

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_bare_word(self):
        # useradd evil            (no quotes)
        surface = extract_mutation_surface("useradd evil\n")
        assert MutationTarget(kind="user", target="evil") in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_single_quoted(self):
        # useradd 'evil'          (single quotes)
        surface = extract_mutation_surface("useradd 'evil'\n")
        assert MutationTarget(kind="user", target="evil") in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_systemctl_bare(self):
        # systemctl enable evil.service (unquoted)
        surface = extract_mutation_surface("systemctl enable evil.service\n")
        assert MutationTarget(kind="unit", target="evil.service") in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_full_path(self):
        # /usr/sbin/useradd "evil" (full binary path)
        surface = extract_mutation_surface('/usr/sbin/useradd "evil"\n')
        assert MutationTarget(kind="user", target="evil") in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_semicolon(self):
        # true; useradd "evil"     (;-prefixed compound)
        surface = extract_mutation_surface('true; useradd "evil"\n')
        assert MutationTarget(kind="user", target="evil") in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_env_wrapper(self):
        # env useradd "evil"      (wrapper)
        surface = extract_mutation_surface('env useradd "evil"\n')
        assert MutationTarget(kind="user", target="evil") in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_eval_wrap(self):
        # eval "useradd evil"      (wrapper)
        surface = extract_mutation_surface('eval "useradd evil"\n')
        assert MutationTarget(kind="user", target="evil") in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_line_cont(self):
        # useradd \<newline>"evil" (line-continued target)
        surface = extract_mutation_surface('useradd \\\n    "evil"\n')
        assert MutationTarget(kind="user", target="evil") in surface

    # frob:tests src/frob/deploy/_conform.py::extract_mutation_surface kind="unit"
    def test_compound_and(self):
        # true && useradd "evil"  (&& compound, not in the reviewer's
        # explicit list but the same class of evasion as ';')
        surface = extract_mutation_surface('true && useradd "evil"\n')
        assert MutationTarget(kind="user", target="evil") in surface

    # frob:tests src/frob/deploy/_conform.py::deploy_conformance_violations kind="unit"
    def test_evasion_fires_through_full_check(self, tmp_path):
        # End-to-end: an evasion shape hand-appended to a real generated
        # install.sh must still fire DEPLOY002 through the public
        # `deploy_conformance_violations` entry point, not just the
        # unit-level extractor.
        _write_design(tmp_path)
        deploy_dir = _write_clean_deploy(tmp_path)
        install_path = deploy_dir / "install.sh"
        tampered = install_path.read_text() + "\ntrue; useradd evil-backdoor\n"
        install_path.write_text(tampered)

        violations = deploy_conformance_violations(tmp_path)
        codes = {(v.code, v.kind, v.target) for v in violations}
        assert ("DEPLOY002", "user", "evil-backdoor") in codes


class TestExpected:
    # frob:tests src/frob/deploy/_conform.py::expected_mutation_surface kind="unit"
    def test_from_host(self):
        entries = sorted_manifest_entries(_model())
        expected = expected_mutation_surface(entries)
        assert expected == frozenset(
            {
                MutationTarget(kind="user", target="api-svc"),
                MutationTarget(kind="unit", target="frob-deploy-api.service"),
                MutationTarget(kind="path", target="/etc/api"),
            }
        )


class TestConform:
    # frob:tests src/frob/deploy/_conform.py::deploy_conformance_violations kind="unit"
    def test_no_dir(self, tmp_path):
        _write_design(tmp_path)
        assert deploy_conformance_violations(tmp_path) == ()

    # frob:tests src/frob/deploy/_conform.py::deploy_conformance_violations kind="unit"
    def test_clean_pass(self, tmp_path):
        _write_design(tmp_path)
        _write_clean_deploy(tmp_path)
        assert deploy_conformance_violations(tmp_path) == ()

    # frob:tests src/frob/deploy/_conform.py::deploy_conformance_violations kind="unit"
    def test_extra_002(self, tmp_path):
        _write_design(tmp_path)
        deploy_dir = _write_clean_deploy(tmp_path)
        install_path = deploy_dir / "install.sh"
        tampered = install_path.read_text().replace(
            'echo "install complete"\n',
            "useradd --system --no-create-home --shell /usr/sbin/nologin "
            '"rogue-backdoor"\n'
            'echo "install complete"\n',
        )
        install_path.write_text(tampered)

        violations = deploy_conformance_violations(tmp_path)
        codes = {(v.code, v.kind, v.target) for v in violations}
        assert ("DEPLOY002", "user", "rogue-backdoor") in codes
        # the untouched uninstall.sh must stay clean
        assert all(
            v.file != "deploy/uninstall.sh" or v.target == "rogue-backdoor"
            for v in violations
        )

    # frob:tests src/frob/deploy/_conform.py::deploy_conformance_violations kind="unit"
    def test_no_model_loads(self, tmp_path):
        """deploy/ exists but no design model loads at all -> `model is
        None` short-circuit branch, clean."""
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        (deploy_dir / "install.sh").write_text("# whatever\n")
        assert deploy_conformance_violations(tmp_path) == ()

    # frob:tests src/frob/deploy/_conform.py::deploy_conformance_violations kind="unit"
    def test_partial_committed(self, tmp_path):
        """Only install.sh is committed -- uninstall.sh hits the `not
        path.exists()` continue branch and is skipped entirely."""
        _write_design(tmp_path)
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        rendered = generate_all(_model())
        (deploy_dir / "install.sh").write_text(rendered["install.sh"])
        violations = deploy_conformance_violations(tmp_path)
        assert violations == ()

    # frob:tests src/frob/deploy/_conform.py::deploy_conformance_violations kind="unit"
    def test_missing_003(self, tmp_path):
        _write_design(tmp_path)
        deploy_dir = _write_clean_deploy(tmp_path)
        uninstall_path = deploy_dir / "uninstall.sh"
        original = uninstall_path.read_text()
        # Remove the userdel step entirely -- an incomplete uninstall
        # that would leave the service user behind.
        stripped_lines = [
            line for line in original.splitlines(keepends=True) if "userdel" not in line
        ]
        uninstall_path.write_text("".join(stripped_lines))

        violations = deploy_conformance_violations(tmp_path)
        codes = {(v.code, v.file, v.kind, v.target) for v in violations}
        assert ("DEPLOY003", "deploy/uninstall.sh", "user", "api-svc") in codes
