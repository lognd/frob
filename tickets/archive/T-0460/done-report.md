## Done report

Added the T-0460 render vocabulary follow-on to the T-0448 foundation:
table, tree, count_deltas total elements (plain/color shape parity, same
split as the rest of the vocabulary), and Progress (the T-0419 TTY-only,
clears-on-completion contract) with RenderWriter.progress as a context
manager. Renderer now resolves is_tty once (independent of the color
decision) and threads it into RenderWriter/Progress, since --no-color on a
real TTY must still gate progress on. Docs updated with per-element
sections; version bumped 0.35.0 -> 0.36.0 (additive minor per REL001) with
a CHANGELOG entry; ticket scope extended (frob ticket scope) to cover the
actual test file location (tests/unit/test_render.py, moved there by main
between ticket creation and this pass) plus CHANGELOG.md/pyproject.toml/
uv.lock for the version bump.

### Changed
```
 CHANGELOG.md                 |  13 +++
 docs/modules/render.md       |  65 +++++++++++++-
 pyproject.toml               |   2 +-
 src/frob/render/__init__.py  |  14 ++-
 src/frob/render/_elements.py |  75 +++++++++++++++-
 src/frob/render/_renderer.py | 128 +++++++++++++++++++++++++--
 tests/unit/test_render.py    | 201 +++++++++++++++++++++++++++++++++++++++++++
 tickets.md                   |  90 ++++++++++++++++++-
 uv.lock                      |   2 +-
 9 files changed, 570 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/unit/test_render.py::TestTableTreeCountDeltas::test_table_plain_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestTableTreeCountDeltas::test_table_color_paints_header_and_rule_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestTableTreeCountDeltas::test_tree_plain_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestTableTreeCountDeltas::test_tree_color_paints_only_depth_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_plain_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_positive_delta_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_color_has_no_ansi_in_plain` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestWriterTableTreeCountDeltas::test_write_table` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestWriterTableTreeCountDeltas::test_write_tree` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestWriterTableTreeCountDeltas::test_write_count_deltas` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestProgress::test_progress_updates_in_place_on_tty` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestProgress::test_progress_is_noop_on_non_tty` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestProgress::test_progress_clear_erases_the_line_on_tty` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestProgress::test_progress_clear_is_noop_on_non_tty` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestProgress::test_progress_context_manager_clears_on_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestProgress::test_progress_context_manager_clears_even_on_exception` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestProgress::test_progress_shorter_next_line_pads_over_stale_tail` (pytest node id, verified passing when recorded)
