"""Unit tests for T-3964's dataset construct (`parent_store=<id>`,
`append_only` node attrs) and its SYS118 structural consumer.

Mirrors `tests/unit/strata/test_pii.py`'s hand-built-`KernelModel`
convention (and `tests/test_pii_provenance_trust_identity.py`'s
positive-control shape for T-3961's sibling attr-desugar constructs).
Each positive control plants the EXACT finding the rule exists to catch
and asserts it fires, then asserts the declared-correctly case does not.
"""

from __future__ import annotations

from frob.strata._dataset import (
    check_dangling_parent_store,
    node_is_append_only,
    node_is_dataset,
    node_parent_store,
)
from frob.strata._models import KernelModel, Node
from frob.strata._pii import node_pii_tags


def _node(node_id: str, trust: str = "trusted", attrs: tuple[str, ...] = ()) -> Node:
    """One `Node` with the given attrs, matching `test_pii.py`'s own
    minimal-fixture convention."""
    return Node(id=node_id, trust=trust, attrs=attrs)


class TestDatasetAttrParsing:
    # frob:tests src/frob/strata/_dataset.py::node_parent_store kind="unit"
    def test_node_parent_store_parses_attr(self):
        node = _node("audit_log", attrs=("parent_store=postgres",))
        assert node_parent_store(node) == "postgres"

    # frob:tests src/frob/strata/_dataset.py::node_parent_store kind="unit"
    def test_node_parent_store_none_when_absent(self):
        node = _node("postgres", attrs=("engine=postgres",))
        assert node_parent_store(node) is None

    # frob:tests src/frob/strata/_dataset.py::node_is_dataset kind="unit"
    def test_node_is_dataset_true_with_parent_store(self):
        node = _node("audit_log", attrs=("parent_store=postgres",))
        assert node_is_dataset(node) is True

    # frob:tests src/frob/strata/_dataset.py::node_is_dataset kind="unit"
    def test_node_is_dataset_false_without_parent_store(self):
        node = _node("postgres")
        assert node_is_dataset(node) is False

    # frob:tests src/frob/strata/_dataset.py::node_is_append_only kind="unit"
    def test_node_is_append_only_true(self):
        node = _node("audit_log", attrs=("parent_store=postgres", "append_only"))
        assert node_is_append_only(node) is True

    # frob:tests src/frob/strata/_dataset.py::node_is_append_only kind="unit"
    def test_node_is_append_only_false(self):
        node = _node("audit_log", attrs=("parent_store=postgres",))
        assert node_is_append_only(node) is False


class TestDatasetIndependentCarries:
    # frob:tests src/frob/strata/_dataset.py::node_is_dataset kind="unit"
    def test_dataset_carries_independent_of_parent_store(self):
        """F-177's own framing: a dataset nested under a store must be
        able to declare carries() independent of the parent's -- a
        password-hash dataset and an email dataset under the SAME store
        must not cross-contaminate each other's (or the store's own)
        `carries()` tags. Requires no new code (module docstring):
        `node_pii_tags` already reads attrs per-`Node`."""
        store = _node("postgres", attrs=("engine=postgres",))
        password_dataset = _node(
            "password_hashes",
            attrs=("parent_store=postgres", "pii=credentials.password_hash"),
        )
        email_dataset = _node(
            "user_emails",
            attrs=("parent_store=postgres", "pii=contact.email"),
        )
        assert node_pii_tags(store) == ()
        assert node_pii_tags(password_dataset) == ("credentials.password_hash",)
        assert node_pii_tags(email_dataset) == ("contact.email",)


class TestSys118DanglingParentStore:
    # frob:tests src/frob/strata/_dataset.py::check_dangling_parent_store kind="unit"
    def test_dangling_parent_store_fires_sys118(self):
        """Positive control: a dataset naming a parent_store id that does
        not exist in the model must fire."""
        dataset = _node("audit_log", attrs=("parent_store=nonexistent_store",))
        model = KernelModel(nodes=(dataset,))
        findings = check_dangling_parent_store(model)
        assert len(findings) == 1
        assert "nonexistent_store" in findings[0]
        assert "audit_log" in findings[0]

    # frob:tests src/frob/strata/_dataset.py::check_dangling_parent_store kind="unit"
    def test_existing_parent_store_does_not_fire_sys118(self):
        """A dataset whose parent_store resolves to a real node must NOT
        fire."""
        store = _node("postgres")
        dataset = _node("audit_log", attrs=("parent_store=postgres",))
        model = KernelModel(nodes=(store, dataset))
        assert check_dangling_parent_store(model) == ()

    # frob:tests src/frob/strata/_dataset.py::check_dangling_parent_store kind="unit"
    def test_node_without_parent_store_does_not_fire_sys118(self):
        node = _node("postgres")
        model = KernelModel(nodes=(node,))
        assert check_dangling_parent_store(model) == ()
