"""Direct unit coverage for `frob.strata._obligation_proof`'s shared
proof-against-code plumbing (T-0641) -- promoted out of `_reliability.py`
so `_retry.py`/future REL23x/REL24x modules share one implementation.
`test_retry.py`/`test_reliability.py` already exercise these functions
indirectly through their entrypoints; this file is the direct-call
coverage `TEST001` wants for each public symbol.
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.strata._obligation_proof import (
    bound_endpoints,
    files_evidence_token,
    node_has_bound_code,
    owner_index,
)


class TestOwnerIndex:
    # frob:tests tests/unit/strata/test_obligation_proof.py::TestOwnerIndex.test_inverts_file_to_node_map
    def test_inverts_file_to_node_map(self):
        owner = {"src/a.py": "node_a", "src/b.py": "node_a", "src/c.py": "node_b"}
        by_node = owner_index(owner)
        assert by_node == {"node_a": ["src/a.py", "src/b.py"], "node_b": ["src/c.py"]}


class TestNodeHasBoundCode:
    # frob:tests tests/unit/strata/test_obligation_proof.py::TestNodeHasBoundCode.test_true_when_files_present
    def test_true_when_files_present(self):
        assert node_has_bound_code("n1", {"n1": ["src/a.py"]})

    # frob:tests tests/unit/strata/test_obligation_proof.py::TestNodeHasBoundCode.test_false_when_absent
    def test_false_when_absent(self):
        assert not node_has_bound_code("n1", {})


class TestFilesEvidenceToken:
    # frob:tests tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken.test_matches_a_real_token
    def test_matches_a_real_token(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("call(backoff=1)\n", encoding="utf-8")
        pattern = re.compile(r"backoff\s*=")
        assert files_evidence_token(["a.py"], tmp_path, pattern)

    # frob:tests tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken.test_no_match_returns_false
    def test_no_match_returns_false(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("call()\n", encoding="utf-8")
        pattern = re.compile(r"backoff\s*=")
        assert not files_evidence_token(["a.py"], tmp_path, pattern)

    # frob:tests tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken.test_unreadable_file_skipped_not_treated_as_proof
    def test_unreadable_file_skipped_not_treated_as_proof(self, tmp_path: Path):
        pattern = re.compile(r"backoff\s*=")
        assert not files_evidence_token(["missing.py"], tmp_path, pattern)


class TestBoundEndpoints:
    # frob:tests tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints.test_both_endpoints_bound_src_first
    def test_both_endpoints_bound_src_first(self):
        owner_by_node = {"src": ["a.py"], "dst": ["b.py"]}
        assert bound_endpoints("src", "dst", owner_by_node) == ["src", "dst"]

    # frob:tests tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints.test_only_dst_bound
    def test_only_dst_bound(self):
        owner_by_node = {"dst": ["b.py"]}
        assert bound_endpoints("src", "dst", owner_by_node) == ["dst"]

    # frob:tests tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints.test_self_loop_deduped
    def test_self_loop_deduped(self):
        owner_by_node = {"n": ["a.py"]}
        assert bound_endpoints("n", "n", owner_by_node) == ["n"]

    # frob:tests tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints.test_neither_bound_empty
    def test_neither_bound_empty(self):
        assert bound_endpoints("src", "dst", {}) == []
