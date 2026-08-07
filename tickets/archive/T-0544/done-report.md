## Done report

Fixed `_walk_repo_files` (src/frob/graph/__init__.py) so top-level *.md
files (README.md, and any other repo-root note) are classified as doc
files, not only files under docs/. Previously `is_doc` required
`under_docs`, so a `frob:describes` anchor in README.md never produced a
DESCRIBES edge and its facet never existed for DRIFT001, even though
gates.doclink's own root set already treats README.md as a doc entry
point. Kept the single-pass os.walk shape (T-0245) rather than
duplicating gates' frob.toml-driven include/exclude glob resolution into
this leaf walker -- only top-level *.md files (cheap, one directory, no
extra traversal cost) are folded in.

Added a regression test exercising `_walk_repo_files` directly with a
root-level README.md, a docs/**/*.md file, and a non-root/non-docs *.md
file, asserting the doc set is exactly {README.md, docs/modules/foo.md}.

### Changed
(no changed files detected)

### Evidence
- `tests/test_graph.py::TestExclude::test_walk_repo_files_classifies_top_level_readme_as_doc` (pytest node id, verified passing when recorded)
