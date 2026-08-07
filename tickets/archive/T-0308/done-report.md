## Done report
ALREADY RESOLVED by prior frob work -- the sibling-repo FROBLEMS entries
were written 2026-07-18, before these landed. (a) Comment-awareness shipped
via T-0209: `_capability.py::_comment_byte_spans` (frob.lang raw_tree +
COMMENT_TYPES) and `_needle_hits_outside_comments` exclude any needle fully
inside a tree-sitter COMMENT node, for python `#` and `//`,`/* */` for
TS/JS/rust/C/C++, applied in scan_file_capabilities/operations/fingerprints.
(b) Word-boundary needles shipped via T-0305/T-0019: the TS `ffi` needle no
longer carries a bare `napi` substring; `_has_word_boundary_napi` requires
non-identifier bytes on both sides, so `openapi` never fires while
`require('napi')`/`ffi-napi` still do. Audited the full ~150-needle table --
every short needle is paren-terminated (`eval(`,`open(`) or dotted/hyphenated
(`os.exec`,`ffi-napi`); no other bare-fragment-of-a-common-word risk.
Verified all four litmus scenarios pass on current main (comment-only
requests.get -> no net; openapi(ts) -> no ffi; real requests.get -> net;
real napi import -> ffi). Locked by the evidence tests above. No source
change needed; closing as resolved-by-T-0209/T-0305/T-0019.
