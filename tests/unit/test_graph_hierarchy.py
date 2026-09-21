"""Unit tests for `frob.graph._hierarchy` (T-3032): the generic
parent/child descendants-of-any-depth walk shared between
`frob.gates._milestone` and `frob.tickets._evidence`."""

from __future__ import annotations

from frob.graph._hierarchy import children_by_parent_id, descendant_ids


class TestChildrenByParentId:
    """`children_by_parent_id` -- adjacency-map construction."""

    def test_builds_adjacency_from_parent_pairs(self) -> None:
        """Each `(id, parent)` pair with a non-None parent contributes
        one entry to the parent's child list."""
        adjacency = children_by_parent_id(
            [("a", None), ("b", "a"), ("c", "a"), ("d", "b")]
        )
        assert adjacency == {"a": ["b", "c"], "b": ["d"]}

    def test_root_only_items_produce_empty_adjacency(self) -> None:
        """Items with no parent contribute nothing -- an all-roots input
        is a valid, empty adjacency map."""
        assert children_by_parent_id([("a", None), ("b", None)]) == {}

    def test_empty_input_is_empty_adjacency(self) -> None:
        """No items at all is the trivial empty case, not an error."""
        assert children_by_parent_id([]) == {}


class TestDescendantIds:
    """`descendant_ids` -- the any-depth BFS walk itself."""

    def test_direct_children_only(self) -> None:
        """A root with only direct children returns exactly those."""
        adjacency = {"root": ["a", "b"]}
        assert sorted(descendant_ids("root", adjacency)) == ["a", "b"]

    def test_multi_depth_walk(self) -> None:
        """A grandchild several levels deep is still found."""
        adjacency = {"root": ["a"], "a": ["b"], "b": ["c"]}
        assert sorted(descendant_ids("root", adjacency)) == ["a", "b", "c"]

    def test_root_itself_never_included(self) -> None:
        """The root id is never counted as its own descendant."""
        adjacency = {"root": ["a"]}
        assert "root" not in descendant_ids("root", adjacency)

    def test_leaf_with_no_children_returns_empty(self) -> None:
        """A root absent from the adjacency map (a leaf) has zero
        descendants -- not an error, an empty list."""
        assert descendant_ids("leaf", {}) == []

    def test_each_id_visited_at_most_once(self) -> None:
        """A diamond-shaped hierarchy (two parents sharing one child, via
        two separate parent entries pointing at the same child id) never
        double-counts the shared descendant."""
        adjacency = {"root": ["a", "b"], "a": ["shared"], "b": ["shared"]}
        result = descendant_ids("root", adjacency)
        assert result.count("shared") == 1
        assert sorted(result) == ["a", "b", "shared"]
