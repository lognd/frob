"""CUDA raw-to-`RawSymbol` walker (T-1602, epic T-1599 child).

DIALECT-FLAG DECISION (the ticket's own required decision, made explicit
rather than left implicit): `tree-sitter-language-pack`'s "cuda" grammar
is node-for-node identical to its "cpp" grammar for every construct
`_walk_c.py`'s `_walk_c_family` inspects -- classes, access specifiers,
namespaces, enums, typedefs, consts, and the `function_definition`/
`function_declarator` shape itself are all unchanged; `__global__`/
`__device__`/`__host__` kernel qualifiers simply show up as EXTRA direct
children of a `function_definition` node, exactly the same shape
`_has_static`'s `storage_class_specifier` check already reads (each
qualifier's own node TYPE is the literal qualifier text -- verified
interactively before writing any walker code). Because nothing else
differs, CUDA is wired here as a C++ DIALECT FLAG -- this module is a
thin ~30-line wrapper around `_walk_c_family`, not a second copy of its
240-line recursive descent. A distinct `_walk_cuda.py` module still
exists (rather than a bare call inlined at the `_extract.py` dispatch
site) only because `frob.lang._extract`'s per-language wiring convention
is one importable `_walk_<language>` callable per registered language,
matching every other adapter's own module boundary.

PUBLICNESS (the ticket's own second required decision): kernel
qualifiers ARE the execution-surface/visibility concept CUDA cares about,
per the ticket's own framing -- a `__global__` function is a KERNEL, the
entry point host code launches with `<<<...>>>` syntax, and is therefore
ALWAYS public regardless of any `static` storage-class specifier that
might otherwise suppress it under `_walk_c.py`'s plain C/C++ rule (a
`static __global__` kernel still has external launch visibility -- CUDA's
own `static` on a `__global__` function only affects LINKAGE across
translation units, not launchability, unlike a plain C free function).
A function marked `__device__` with NO `__host__` alongside it is the
opposite extreme: it can only ever be CALLED from other device code
(another `__global__`/`__device__` function), never from the host side a
caller "outside this file" would occupy in frob's own public/private
axis -- so it is always private, regardless of `static`, mirroring how
C#'s `internal` (T-1600) is treated as not-public even though it is
visible beyond a single file. Every other case (a plain host function,
`__host__` alone, or the `__host__ __device__` combination naming both
execution spaces) defers to `_walk_c.py`'s existing static-based rule
unchanged -- `_cuda_visibility` returns `None` for those, exactly the
"not a CUDA-specific case, ask the shared C++ rule" signal `_walk_c_
family`'s `visibility_override` hook contract expects.
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._models import RawSymbol
from frob.lang._walk_c import _walk_c_family

# frob:ticket T-1602
# frob:doc docs/modules/lang.md#per-language-walker-notes
# CUDA has the identical single comment node type C/C++ do (verified
# interactively, module docstring's own exploration).
COMMENT_TYPES = frozenset({"comment"})

#: T-1602: kernel-qualifier node TYPES this module's publicness override
#: recognizes -- a `function_definition`'s direct children whose own type
#: is one of these three literal keyword strings (never a wrapping node
#: with a field to look up; the grammar treats each qualifier as its own
#: bare terminal, same shape `_has_static` already reads for `static`).
_KERNEL_QUALIFIER = "__global__"
_DEVICE_QUALIFIER = "__device__"
_HOST_QUALIFIER = "__host__"


def _cuda_visibility(node: Node) -> bool | None:
    """CUDA publicness override for one `function_definition` node (module
    docstring): `__global__` kernels are always public; a `__device__`-
    only function (no `__host__` alongside it) is always private; every
    other case defers to `_walk_c.py`'s own static-based rule (`None`)."""
    qualifiers = {c.type for c in node.children}
    if _KERNEL_QUALIFIER in qualifiers:
        return True
    if _DEVICE_QUALIFIER in qualifiers and _HOST_QUALIFIER not in qualifiers:
        return False
    return None


# frob:ticket T-1602
# frob:tests tests/test_lang.py::TestCuda.test_global_kernel_is_public
# frob:tests tests/test_lang.py::TestCuda.test_device_only_function_is_not_public
# frob:tests tests/test_lang.py::TestCuda.test_host_device_function_defers_to_cpp_rule
# frob:tests tests/test_lang.py::TestCuda.test_static_global_kernel_is_still_public
# frob:tests \
# tests/test_lang.py::TestCuda.test_plain_host_function_follows_cpp_static_rule
# frob:tests tests/test_lang.py::TestCuda.test_class_method_with_device_qualifier
def _walk_cuda(root: Node) -> tuple[RawSymbol, ...]:
    """Every CUDA symbol -- delegates entirely to `_walk_c_family` (module
    docstring's dialect-flag decision), layering only the kernel-qualifier
    publicness override CUDA needs on top of C++'s own extraction."""
    return _walk_c_family(root, COMMENT_TYPES, visibility_override=_cuda_visibility)
