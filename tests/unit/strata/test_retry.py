"""REL22x RETRY-obligation family unit coverage (T-0641,
`frob.strata._retry`) -- mirrors `test_reliability.py::TestUnprovenTimeout`'s
`tmp_path` real-file convention for proof-against-code (bind_code-backed,
so it needs a real file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from typani.result import Err

from frob.strata import Flow, KernelModel, Node, StrataError, Waiver
from frob.strata._retry import (
    REL_MISSING_BACKOFF,
    REL_NONIDEMPOTENT_RETRY,
    REL_UNPROVEN_BACKOFF,
    check_retry_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingBackoff:
    # frob:tests \
    # tests/unit/strata/test_retry.py::TestMissingBackoff.test_retry_flow_without_backo\
    # ff_fires
    def test_retry_flow_without_backoff_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted"),
                Node(id="worker", trust="trusted", attrs=("idempotent",)),
            ),
            flows=(Flow(id="f_missing", src="caller", dst="worker", attrs=("retry",)),),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_BACKOFF
        ]
        assert {v.sub_target for v in missing} == {"f_missing"}
        assert missing[0].node == "caller"

    # frob:tests \
    # tests/unit/strata/test_retry.py::TestMissingBackoff.test_discharged_and_non_retry\
    # _flows_clean
    def test_discharged_and_non_retry_flows_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted"),
                Node(id="worker", trust="trusted", attrs=("idempotent",)),
            ),
            flows=(
                Flow(
                    id="f_ok",
                    src="caller",
                    dst="worker",
                    attrs=("retry", "backoff_jitter"),
                ),
                Flow(id="f_no_retry", src="caller", dst="worker"),
            ),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_BACKOFF
        ]

    # frob:tests \
    # tests/unit/strata/test_retry.py::TestMissingBackoff.test_waiver_on_one_flow_keeps\
    # _sibling_flow_finding
    def test_waiver_on_one_flow_keeps_sibling_flow_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="caller",
                    trust="trusted",
                    waives=(
                        Waiver(
                            rule="REL220:f_missing",
                            reason="dev-only debug hook, tracked in T-0641",
                        ),
                    ),
                ),
                Node(id="worker", trust="trusted", attrs=("idempotent",)),
            ),
            flows=(
                Flow(id="f_missing", src="caller", dst="worker", attrs=("retry",)),
                Flow(id="f_other", src="caller", dst="worker", attrs=("retry",)),
            ),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        kept = {
            v.sub_target for v in report.violations if v.rule == REL_MISSING_BACKOFF
        }
        waived = {v.sub_target for v in report.waived if v.rule == REL_MISSING_BACKOFF}
        assert kept == {"f_other"}
        assert waived == {"f_missing"}


class TestNonIdempotentRetry:
    # frob:tests \
    # tests/unit/strata/test_retry.py::TestNonIdempotentRetry.test_retry_into_unguarded\
    # _dst_fires
    def test_retry_into_unguarded_dst_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted"),
                Node(id="worker", trust="trusted"),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="caller",
                    dst="worker",
                    attrs=("retry", "backoff_jitter"),
                ),
            ),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_NONIDEMPOTENT_RETRY
        ]
        assert {v.sub_target for v in violations} == {"f1"}
        assert violations[0].node == "caller"

    # frob:tests \
    # tests/unit/strata/test_retry.py::TestNonIdempotentRetry.test_idempotent_dst_disch\
    # arges
    def test_idempotent_dst_discharges(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted"),
                Node(id="worker", trust="trusted", attrs=("idempotent",)),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="caller",
                    dst="worker",
                    attrs=("retry", "backoff_jitter"),
                ),
            ),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_NONIDEMPOTENT_RETRY
        ]

    # frob:tests \
    # tests/unit/strata/test_retry.py::TestNonIdempotentRetry.test_idempotency_key_dst_\
    # discharges
    def test_idempotency_key_dst_discharges(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted"),
                Node(id="worker", trust="trusted", attrs=("idempotency_key",)),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="caller",
                    dst="worker",
                    attrs=("retry", "backoff_jitter"),
                ),
            ),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_NONIDEMPOTENT_RETRY
        ]


class TestUnprovenBackoff:
    # frob:tests \
    # tests/unit/strata/test_retry.py::TestUnprovenBackoff.test_declared_backoff_with_n\
    # o_code_evidence_fires
    def test_declared_backoff_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def call():\n    return remote()\n")
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted", attrs=("code=src/widget/**",)),
                Node(id="worker", trust="trusted", attrs=("idempotent",)),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="caller",
                    dst="worker",
                    attrs=("retry", "backoff_jitter"),
                ),
            ),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_BACKOFF
        ]
        assert {v.sub_target for v in violations} == {"f1"}
        assert violations[0].node == "caller"

    # frob:tests \
    # tests/unit/strata/test_retry.py::TestUnprovenBackoff.test_declared_backoff_with_r\
    # eal_code_evidence_discharges
    def test_declared_backoff_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def call():\n    return remote(backoff=0.5, jitter=True)\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted", attrs=("code=src/widget/**",)),
                Node(id="worker", trust="trusted", attrs=("idempotent",)),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="caller",
                    dst="worker",
                    attrs=("retry", "backoff_jitter"),
                ),
            ),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_BACKOFF
        ]

    # frob:tests \
    # tests/unit/strata/test_retry.py::TestUnprovenBackoff.test_declared_backoff_with_n\
    # o_bound_code_is_uncheckable_not_a_violation
    def test_declared_backoff_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted"),
                Node(id="worker", trust="trusted", attrs=("idempotent",)),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="caller",
                    dst="worker",
                    attrs=("retry", "backoff_jitter"),
                ),
            ),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_BACKOFF
        ]


class TestBindCodeErrorPropagation:
    def test_ambiguous_code_binding_error_propagates(self, tmp_path: Path, monkeypatch):
        # frob:tests \
        # tests/unit/strata/test_retry.py::TestBindCodeErrorPropagation.test_ambiguous_\
        # code_binding_error_propagates
        """`bind_code`'s `AmbiguousCodeBinding` must propagate unchanged out
        of `check_retry_obligations`, never be swallowed (deny by default, matching
        every other REL-family entrypoint's discipline)."""
        import frob.strata._retry as retry_mod

        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted"),
                Node(id="worker", trust="trusted", attrs=("idempotent",)),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="caller",
                    dst="worker",
                    attrs=("retry", "backoff_jitter"),
                ),
            ),
        )
        monkeypatch.setattr(
            retry_mod,
            "bind_code",
            lambda _model, _root: Err(StrataError.AmbiguousCodeBinding),
        )
        result = check_retry_obligations(model, tmp_path)
        assert result.is_err
        assert result.danger_err is StrataError.AmbiguousCodeBinding
