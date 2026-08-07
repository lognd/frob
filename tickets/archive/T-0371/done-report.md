## Done report

Resolved by PRIVATIZING the function: `collect_file_dispatch_refs` is an
internal detector helper (called only from `frob.arch.__init__::
_run_python_checks`), never a public API symbol -- it was public by
oversight in T-0360. Renamed to `_collect_file_dispatch_refs` in
`src/frob/arch/_python.py` and its one caller, which removes the public-API
obligation entirely (COV001 + TEST001 both clear, and reverts the spurious
REL001 public-API delta). Its behavior remains covered via the T-0360
dispatch-family tests through `analyze_project`. Landed with the load_graph
directive fix in the same coordinator commit.
