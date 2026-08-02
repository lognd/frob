"""RUNTIME_OPAQUE_CONSTRUCTS / OPAQUE_SOURCE_INVISIBLE /
RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS: the "runtime-opaque" evasion-
taxonomy tables (T-0665/T-1051) -- split out (T-1420) since these reason
about a distinct concern (source-invisible dynamic dispatch) from the
ordinary per-language dangerous-operation needle tables."""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from frob.vet._capability_registry._schemas import (
    _MatrixExcuse,
    _OpaqueConstruct,
    _OpaqueStructuralConstruct,
)

# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0665
# frob:ticket T-1047
# frob:waive AFFECT001 reason="T-1047 extended this tuple with 15 more entries (same \
# shape as the existing ones); docs/modules/vet.md is outside T-1047's declared scope \
# (src/frob/vet/**, src/frob/gates/_opaque.py, docs/design/registry/evasion.yaml, \
# tests/test_vet.py) -- matches T-0665's own precedent for the identical situation on \
# this same constant"
# frob:enforces EVA-PY-R01
# frob:enforces EVA-PY-R02
# frob:enforces EVA-PY-R03
# frob:enforces EVA-PY-R04
# frob:enforces EVA-PY-R05
# frob:enforces EVA-PY-R06
# frob:enforces EVA-PY-R07
# frob:enforces EVA-PY-R08
# frob:enforces EVA-PY-R09
# frob:enforces EVA-TSJS-R01
# frob:enforces EVA-TSJS-R02
# frob:enforces EVA-TSJS-R03
# frob:enforces EVA-TSJS-R04
# frob:enforces EVA-TSJS-R05
# frob:enforces EVA-TSJS-R06
# frob:enforces EVA-TSJS-R07
# frob:enforces EVA-TSJS-R08
# frob:enforces EVA-TSJS-R09
# frob:enforces EVA-RS-R01
# frob:enforces EVA-RS-R02
# frob:enforces EVA-RS-R03
# frob:enforces EVA-RS-R04
# frob:enforces EVA-RS-R05
# frob:enforces EVA-RS-R06
# frob:enforces EVA-C-R01
# frob:enforces EVA-C-R02
# frob:enforces EVA-C-R03
# frob:enforces EVA-C-R04
# frob:enforces EVA-C-R05
# frob:enforces EVA-CPP-R01
# frob:enforces EVA-CPP-R02
# frob:enforces EVA-CPP-R03
# frob:enforces EVA-CPP-R04
# frob:enforces EVA-CPP-R05
# frob:enforces EVA-KT-R01
# frob:enforces EVA-KT-R02
# frob:enforces EVA-KT-R03
# frob:enforces EVA-KT-R04
# frob:enforces EVA-KT-R05
RUNTIME_OPAQUE_CONSTRUCTS: tuple[_OpaqueConstruct, ...] = (
    _OpaqueConstruct(
        language="python",
        construct_name="eval",
        needle="eval(",
        literal_arg_index=None,
        rationale="arbitrary source text evaluated at runtime; no literal "
        "argument can make this statically resolvable",
        taxonomy_row="python:runtime:eval",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="exec",
        needle="exec(",
        literal_arg_index=None,
        rationale="arbitrary source text executed at runtime; no literal "
        "argument can make this statically resolvable",
        taxonomy_row="python:runtime:exec",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="getattr",
        needle="getattr(",
        literal_arg_index=1,
        rationale="a non-literal attribute name is resolved by runtime "
        'lookup; a literal name (`getattr(subprocess, "run")`) is '
        "equivalent to the plain attribute access the ordinary resolver "
        "already handles",
        taxonomy_row="python:runtime:getattr-dynamic-name",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="setattr",
        needle="setattr(",
        literal_arg_index=1,
        rationale="a non-literal attribute name means the mutated site is "
        "not visible to any static binding table -- mirrors getattr's split",
        taxonomy_row="python:runtime:setattr-monkeypatch",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="__import__",
        needle="__import__(",
        literal_arg_index=0,
        rationale="a non-literal module-name argument is resolved by "
        "runtime string computation",
        taxonomy_row="python:runtime:dunder-import-computed-name",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="importlib.import_module",
        needle="importlib.import_module(",
        literal_arg_index=0,
        rationale="same computed-module-name opacity as __import__, "
        "importlib's documented equivalent entry point",
        taxonomy_row="python:runtime:importlib-import-module",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="eval",
        needle="eval(",
        literal_arg_index=None,
        rationale="arbitrary source text evaluated at runtime",
        taxonomy_row="typescript:runtime:eval",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="Function constructor",
        needle="new Function(",
        literal_arg_index=None,
        rationale="arbitrary source text compiled into a new function at "
        "runtime, ECMA-262 20.2.1",
        taxonomy_row="typescript:runtime:function-constructor",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="dynamic import()",
        needle="import(",
        literal_arg_index=0,
        rationale="a non-literal specifier is resolved by runtime module "
        'loading; `import("literal/path")` is statically enumerable and '
        "belongs to the ordinary resolver path",
        taxonomy_row="typescript:runtime:dynamic-import-call",
    ),
    _OpaqueConstruct(
        language="c-cpp",
        construct_name="dlsym",
        needle="dlsym(",
        literal_arg_index=1,
        rationale="POSIX dynamic symbol lookup; a non-literal symbol-name "
        "argument is resolved by runtime string computation. A literal "
        'symbol name (`dlsym(h, "run_cmd")`) is still resolved by the '
        "dynamic LINKER at load time (not this scanner), but the source "
        "text at least names the target for a human/tool to grep -- the "
        "coordinator's category-1 split treats this as the ordinary-"
        "resolver boundary the same way it does for getattr/dlopen's "
        "python-side analog",
        taxonomy_row="c:runtime:dlopen-dlsym",
    ),
    _OpaqueConstruct(
        language="rust",
        construct_name="libloading symbol lookup",
        needle=".get(",
        literal_arg_index=None,
        rationale="a `libloading::Library::get` dynamic symbol lookup -- "
        "unconditionally opaque per the coordinator's T-0665 sign-off (no "
        "literal/non-literal split given for this row, unlike C's dlsym); "
        "this needle is deliberately broad (bare `.get(`) since the "
        "receiver type cannot be confirmed without full type inference -- "
        "a disclosed over-approximation gated to files that also import "
        "`libloading` (see `_rust_file_uses_libloading` in "
        "frob.vet._capability), not a claim of call-site precision",
        taxonomy_row="rust:runtime:libloading-dlsym",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="Class.forName",
        needle="Class.forName(",
        literal_arg_index=None,
        rationale="reflection resolves through JVM runtime metadata even "
        "when the class-name literal is visible in source -- unlike a "
        "plain import/attribute name, no literal argument makes the "
        "SUBSEQUENT .getMethod()/.invoke() chain statically resolvable",
        taxonomy_row="kotlin:runtime:class-forname-invoke",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="KCallable.call",
        needle=".call(",
        literal_arg_index=None,
        rationale="a `KCallable`/`KFunction` obtained dynamically (e.g. via "
        "`::class.members`) and invoked through `.call` -- the bound "
        "target is runtime metadata, unconditionally opaque; this needle "
        "is deliberately broad (`.call(` alone) since the receiver type "
        "cannot be confirmed without full type inference -- a disclosed "
        "over-approximation, not a claim of precision",
        taxonomy_row="kotlin:runtime:kcallable-call",
    ),
    # T-1047: closing the ~25 taxonomy runtime-opaque rows T-0666 found with
    # no `RUNTIME_OPAQUE_CONSTRUCTS`/`OPAQUE_SOURCE_INVISIBLE` entry. Each
    # needle below is the same deliberately-broad, disclosed-over-
    # approximation style as the libloading/`.call(` entries above -- a
    # fixed substring that names the evasion-indicative construct without
    # claiming call-site type precision; false positives are waivable
    # (category-1 doctrine, T-0665).
    _OpaqueConstruct(
        language="python",
        construct_name="functools.partial",
        needle="functools.partial(",
        literal_arg_index=None,
        rationale="a `functools.partial`/decorator indirection whose bound "
        "target is computed at runtime is not visible to the ordinary "
        "static resolver; unconditionally opaque since the target "
        "expression's literalness cannot be determined without full "
        "dataflow",
        taxonomy_row="python:runtime:functools-partial-dynamic-target",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="__getattr__ interception",
        needle="def __getattr__(",
        literal_arg_index=None,
        rationale="a class defining `__getattr__`/`__getattribute__` can "
        "route ANY attribute access to an arbitrary runtime-resolved "
        "target, making every subsequent access through an instance of "
        "that class opaque to the ordinary resolver",
        taxonomy_row="python:runtime:dunder-getattr-class-interception",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="sys.modules replacement",
        needle="sys.modules[",
        literal_arg_index=None,
        rationale="a direct `sys.modules[name] = fake_module` write "
        "replaces what every SUBSEQUENT `import name` in the process "
        "resolves to, at runtime -- the module identity a static import "
        "resolver assumes is a lie",
        taxonomy_row="python:runtime:sys-modules-replacement",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="globalThis[name]",
        needle="globalThis[",
        literal_arg_index=None,
        rationale="a computed-key access through `globalThis` reaches any "
        "global binding by a runtime-computed name, unconditionally "
        "opaque to a static resolver",
        taxonomy_row="typescript:runtime:globalthis-bracket",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="Reflect.get",
        needle="Reflect.get(",
        literal_arg_index=None,
        rationale="`Reflect.get` resolves its target property through "
        "runtime reflection metadata, same opacity class as Python's "
        "`getattr` with a non-literal name",
        taxonomy_row="typescript:runtime:reflect-get-dynamic-target",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="Reflect.apply",
        needle="Reflect.apply(",
        literal_arg_index=None,
        rationale="`Reflect.apply` invokes a runtime-resolved callable "
        "target through reflection metadata, unconditionally opaque",
        taxonomy_row="typescript:runtime:reflect-apply-dynamic-target",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="Proxy interception",
        needle="new Proxy(",
        literal_arg_index=None,
        rationale="a `Proxy` `get`/`apply` trap can route any property "
        "access or call through the target object to an arbitrary "
        "runtime-computed handler, opaque to the ordinary resolver",
        taxonomy_row="typescript:runtime:proxy-interception",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="monkeypatch module namespace",
        needle="require.cache[",
        literal_arg_index=None,
        rationale="mutating a loaded module's exports via `require.cache` "
        "rewrites what every OTHER importer of that module resolves to, "
        "at runtime -- the same module-identity opacity as Python's "
        "`sys.modules` replacement row",
        taxonomy_row="typescript:runtime:monkeypatch-module-namespace",
    ),
    _OpaqueConstruct(
        language="c-cpp",
        construct_name="reinterpret_cast to function pointer",
        needle="reinterpret_cast<",
        literal_arg_index=None,
        rationale="a `reinterpret_cast` from an integer/opaque handle to a "
        "function-pointer type synthesizes a call target with no "
        "compile-time relationship to any named function -- deliberately "
        "broad needle (any `reinterpret_cast<`) since confirming the "
        "target TYPE is a function pointer needs full type inference; a "
        "disclosed over-approximation, not a claim of precision",
        taxonomy_row="cpp:runtime:reinterpret-cast-function-pointer",
    ),
    _OpaqueConstruct(
        language="c-cpp",
        construct_name="RTTI-driven dispatch",
        needle="typeid(",
        literal_arg_index=None,
        rationale="`typeid`/`dynamic_cast`-driven branching selects "
        "behavior based on runtime type information rather than a "
        "statically-enumerable override set, unlike ordinary bounded "
        "virtual dispatch",
        taxonomy_row="cpp:runtime:rtti-driven-dispatch",
    ),
    _OpaqueConstruct(
        language="rust",
        construct_name="function pointer in container",
        needle="Vec<fn(",
        literal_arg_index=None,
        rationale="a function pointer read back out of a runtime-indexed "
        "container (`Vec<fn(...)>` read via a non-constant index) has no "
        "static binding to a single named function at the read site; "
        "deliberately broad needle (any `Vec<fn(` type annotation), a "
        "disclosed over-approximation matching the libloading needle's "
        "own precedent",
        taxonomy_row="rust:runtime:function-pointer-in-container",
    ),
    _OpaqueConstruct(
        language="rust",
        construct_name="Box<dyn Fn> runtime-selected",
        needle="Box<dyn Fn",
        literal_arg_index=None,
        rationale="a `Box<dyn Fn>` built from a runtime-selected source "
        "(one of several closures chosen by a runtime condition) erases "
        "which concrete closure is bound at the call site",
        taxonomy_row="rust:runtime:boxed-dyn-fn-runtime-selected",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="function value in container",
        needle="]!!(",
        literal_arg_index=None,
        rationale="a function value read out of a runtime-indexed "
        "container and immediately non-null-asserted and invoked "
        "(`handlers[key]!!(x)`) has no static binding to a single named "
        "function at the call site; deliberately broad needle (any "
        "`]!!(` non-null-assert-then-call), a disclosed over-"
        "approximation",
        taxonomy_row="kotlin:runtime:function-value-in-container",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="delegated property by",
        needle="by lazy {",
        literal_arg_index=None,
        rationale="a delegated property (`by lazy { ... }`) resolves its "
        "value through the delegate's runtime-evaluated initializer block "
        "rather than a statically-visible binding -- deliberately broad "
        "needle, a disclosed over-approximation (most `by lazy` blocks "
        "hold ordinary data, not callables; waivable per category-1 "
        "doctrine when the delegate is confirmed non-callable)",
        taxonomy_row="kotlin:runtime:delegated-property-by",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="dynamic classloading",
        needle="URLClassLoader(",
        literal_arg_index=None,
        rationale="`URLClassLoader`/reflection-based classloading resolves "
        "a class (and therefore any method invoked on it) from a runtime-"
        "computed name or byte source, unconditionally opaque",
        taxonomy_row="kotlin:runtime:dynamic-classloading",
    ),
)

# T-0665: source-invisible taxonomy rows (coordinator sign-off category 3)
# -- constructs no source-text or per-file AST scan can see because the
# resolution happens at a layer this scanner never observes (the dynamic
# linker/loader, a JIT'd vtable, or an out-of-process plugin loader).
# Each entry is a REG011-compliant "none -- <explanation>" disposition
# naming why source-level analysis cannot see it and what layer could,
# cross-registered in docs/design/registry/check-coverage.yaml so the REG
# gates keep these accountable forever rather than silently forgotten.
# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0665
# frob:ticket T-1047

OPAQUE_SOURCE_INVISIBLE: tuple[_MatrixExcuse, ...] = (
    _MatrixExcuse(
        capability_kind="opaque-capability-indirection",
        language="c-cpp",
        reason="none -- weak-symbol interposition (GNU/ELF __attribute__"
        "((weak))) and LD_PRELOAD-class symbol override are resolved by "
        "the DYNAMIC LINKER at process-load time, never visible to a "
        "per-source-file text/AST scan; the source at every call site is "
        "textually identical whether or not it gets interposed. Only a "
        "deploy/host-level obligation (frob.strata's host-isolation model, "
        "docs/strata/host.md) can observe the actual linked artifact set, "
        "not this file-level scanner.",
    ),
    _MatrixExcuse(
        capability_kind="opaque-capability-indirection",
        language="rust",
        reason="none -- a runtime vtable patch (unsafe raw-pointer rewrite "
        "of a trait object's vtable slot) is process-memory manipulation "
        "with no distinguishing source-text shape from ordinary unsafe "
        "pointer arithmetic; only runtime instrumentation (not a static "
        "source scan) could observe it.",
    ),
    # T-1047: two more rust source-invisible constructs, distinct from the
    # vtable-patch entry above -- each excused for its own reason, not a
    # shared blanket rust exemption (REG011 accountability per entry).
    _MatrixExcuse(
        capability_kind="opaque-capability-indirection",
        language="rust",
        reason="none -- an `extern` block FFI symbol is bound by the "
        "DYNAMIC LINKER at process-load time (same layer as C's weak-"
        "symbol interposition above), never visible to a per-source-file "
        'text/AST scan; the `extern "C" { fn ... }` declaration names '
        "the symbol, but which concrete implementation actually answers "
        "the call is a link-time/load-time fact this scanner cannot see.",
    ),
    _MatrixExcuse(
        capability_kind="opaque-capability-indirection",
        language="rust",
        reason="none -- a procedural/derive macro (`#[derive(...)]`, "
        "attribute or function-like proc-macros) synthesizes its expanded "
        "call sites inside a separate compiler-plugin crate that runs at "
        "macro-expansion time; the expansion is not present in the "
        "annotated source text at all, so no source-level scan of this "
        "file can see what call, if any, the macro emits. Mirrors the "
        "ordinary resolver's own honest non-detection of `macro_rules!` "
        "expansion (`test_macro_rules_expansion_emitting_fixed_call_not_"
        "detected`) -- proc-macros are the same opacity class one layer "
        "further from source visibility.",
    ),
)


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-1051
RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS: tuple[_OpaqueStructuralConstruct, ...] = (
    _OpaqueStructuralConstruct(
        language="python",
        construct_name="container dynamic-key call",
        kind="subscript_call",
        rationale="a callable read out of a container (dict/list) through a "
        "NON-LITERAL subscript key/index and immediately called -- the "
        "bound target depends on the container's runtime contents at the "
        "computed key, invisible to the ordinary resolver's bounded "
        "single-literal-binding dataflow. Covers both the taxonomy's "
        "'callable in a container, dynamic key' row and its 'computed "
        "member access, non-constant key' row -- identical source shape, "
        "`container[expr](...)`",
        taxonomy_row="python:runtime:container-dynamic-key-call",
    ),
    _OpaqueStructuralConstruct(
        language="typescript",
        construct_name="container dynamic-key call",
        kind="subscript_call",
        rationale="same shape as the python row: `handlers[key](x)`/"
        "`cp[key](x)` reads a callable out of an object/array through a "
        "runtime-computed key and calls it immediately. Covers both the "
        "'callable in container, dynamic key' row and the 'computed "
        "member access, non-constant key' row",
        taxonomy_row="typescript:runtime:container-dynamic-key-call",
    ),
    _OpaqueStructuralConstruct(
        language="c-cpp",
        construct_name="array-index function-pointer dispatch",
        kind="subscript_call",
        rationale="a function-pointer TABLE indexed by a non-constant "
        "expression and immediately called (`tbl[user_selected_index]"
        '("sh")`) -- the ordinary resolver already proves this stays '
        "unresolved as a static binding (`test_array_fn_ptr_nonconstant_"
        "index_not_detected`); this is the fail-closed obligation's own "
        "sibling catch",
        taxonomy_row="c:runtime:array-index-fnptr-dispatch",
    ),
    _OpaqueStructuralConstruct(
        language="c-cpp",
        construct_name="integer-cast to function pointer",
        kind="explicit_fnptr_cast_call",
        rationale="an explicit function-pointer TYPE cast "
        "(`((void(*)(const char*))addr)(...)`) of an arbitrary expression "
        "(commonly an integer/opaque handle) immediately called -- the "
        "cast type is visible in source, but the VALUE being cast is not "
        "provably a valid function address by any static check",
        taxonomy_row="c:runtime:integer-cast-to-function-pointer",
    ),
    _OpaqueStructuralConstruct(
        language="c-cpp",
        construct_name="void* back-cast to function pointer",
        kind="named_type_cast_call",
        rationale="a `void*` value cast through a named (often typedef'd) "
        "type and immediately called (`((Handler)p)(...)`) -- the cast "
        "TARGET TYPE cannot be confirmed as a real function-pointer "
        "typedef without full type inference, so this fires on the "
        "structural shape alone (a parenthesized single-identifier cast "
        "immediately called), a disclosed over-approximation",
        taxonomy_row="c:runtime:void-star-backcast-to-function-pointer",
    ),
)
