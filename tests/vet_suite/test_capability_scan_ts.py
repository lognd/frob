from pathlib import Path

from tests.conftest import (
    _ts_find,  # noqa: F401 -- T-3596
    _ts_find_all,  # noqa: F401 -- T-3596
)


class TestCapabilityScanTsBindingResolution:
    """T-0377: TS/JS sibling of `TestCapabilityScanBindingResolution` --
    before this, TypeScript/JS capability scanning was pure lexical
    needle-matching, so any renamed/destructured/namespaced import to a
    dangerous module evaded it entirely. These tests lock the fix's
    litmus: every evasion case now DETECTED, every shadowing case NOT
    detected (no false positives).

    Deliberately uses the `net`/"axios." needle (dotted, no bare-module-
    name needle) rather than `exec`/"child_process" for the evasion-
    detection cases: `exec`'s needle table includes the bare substring
    "child_process", which the PRE-EXISTING raw-text lexical scan already
    matches on the import line itself regardless of aliasing -- a test
    built on it would pass even with the resolver disabled, and would not
    actually prove anything about the binding-aware fix. "axios." never
    appears literally in an aliased/namespaced/required import's source
    text (only the bare string literal `'axios'` does), so a positive
    result here can only come from the resolver."""

    def test_default_import_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case 1: `import ax from 'axios'; ax.get(url)` -- a
        # renamed default import; the raw text never contains "axios."
        # (only the quoted module specifier 'axios').
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import ax from 'axios';\nax.get(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_require_bare_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case 2: `const ax = require('axios'); ax.get(url)` --
        # CommonJS require bound to a renamed local, no ES `import` at all.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax.get(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_require_destructure_rename_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case 3: `const {get: g} = require('axios'); g(url)` --
        # CommonJS destructure WITH rename (`pair_pattern`), the sharpest
        # evasion: the call site is a bare `g(url)`, matching no needle at
        # all lexically.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const {get: g} = require('axios');\ng(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_namespace_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case 4: `import * as ax from 'axios'; ax.get(url)` --
        # namespace import, member access through the namespace alias.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import * as ax from 'axios';\nax.get(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_ts_import_require_clause_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case 5: `import ax = require('axios'); ax.get(url)` --
        # TS-only import-equals-require form.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import ax = require('axios');\nax.get(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_operation_names_registry_entry_for_aliased_import(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # `_scan_file_operations`'s resolver-backed sibling: a renamed
        # default import still names the real registry entry
        # (library="axios"), not just a bare kind label.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import ax from 'axios';\nax.get(url);\n")
        ops = _scan_file_operations(pkg)
        assert any(
            op.capability_kind == "net-connect" and op.library == "axios" for op in ops
        )

    def test_param_named_get_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No false positive: a LOCAL function parameter named `get` (never
        # imported from anywhere dangerous) must not be flagged.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("function fetch(get) {\n  get(url);\n}\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_param_shadowing_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Shadow case: a function parameter named `ax` shadows a `import
        # ax from 'axios'` default import for the duration of that
        # function -- calling `ax.get(...)` inside must not resolve to
        # `axios.get`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import ax from 'axios';\nfunction g(ax) {\n  ax.get(url);\n}\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_method_on_unrelated_object_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Shadow case: a class method named `get` on an unrelated object
        # (`new Job().get()`) must NOT resolve to a dangerous `get` symbol
        # -- `new Job()` is a `new_expression`, not an import-bound name,
        # so resolution deliberately stops there.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("class Job {\n  get() {}\n}\nnew Job().get();\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_bare_name_call_with_no_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No naive bare-name false positive: calling an undefined `get()`
        # with no matching import anywhere in the file must not resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("get(url);\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_direct_unaliased_call_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Regression: the pre-existing raw-text lexical scan (needle
        # "child_process") is unaffected by adding the TS resolver pass --
        # an ordinary unaliased `require('child_process').exec()` call
        # still fires once the resolver path is unioned in.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import {exec} from 'child_process';\nexec(cmd);\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_bracket_access_inline_require_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0377 reviewer round 2: bracket/computed-member access,
        # `require('axios')['get'](url)` -- a plain bracket-access RCE
        # shape the round-1 resolver missed entirely (it only ever
        # inspected `identifier`/`member_expression` nodes, never
        # `subscript_expression`).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("require('axios')['get'](url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_bracket_access_aliased_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0377 reviewer round 2: bracket access through an aliased
        # `require()` rebind -- `const ax = require('axios'); ax['get']
        # (url)`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax['get'](url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_dynamic_import_then_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0377 reviewer round 2: `import('axios').then(ax => ax.get(url))`
        # -- dynamic import is the STANDARD way to conditionally load a
        # module in TS/JS, a natural place to hide a dangerous one; the
        # round-1 resolver never recognized an `import(...)` call site at
        # all.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import('axios').then(ax => ax.get(url));\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_await_dynamic_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0377 reviewer round 2: `const ax = await import('axios');
        # ax.get(url)` -- the `async`/`await` sibling of `.then(cb)`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "async function f() {\n"
            "  const ax = await import('axios');\n"
            "  ax.get(url);\n"
            "}\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_child_process_bracket_and_dynamic_import_caught(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Realism confirmation (reviewer-requested): both new evasion
        # classes against the ACTUAL exec-family library, not just the
        # isolation proxy above. Note the raw-text lexical scan ALSO
        # matches these two (needle "child_process" is a bare substring
        # present on the `require('child_process')` line itself) -- this
        # test confirms the full production path (lexical union resolver)
        # still fires end-to-end on the real dangerous module; the axios/
        # "net" tests above are what isolate the RESOLVER's own
        # contribution from the lexical layer.
        from frob.vet._capability import scan_file_capabilities

        bracket_pkg = tmp_path / "bracket.ts"
        bracket_pkg.write_text("require('child_process')['exec'](cmd);\n")
        assert "exec" in scan_file_capabilities(bracket_pkg)

        dynamic_pkg = tmp_path / "dynamic.ts"
        dynamic_pkg.write_text("import('child_process').then(cp => cp.exec(cmd));\n")
        assert "exec" in scan_file_capabilities(dynamic_pkg)

    def test_computed_subscript_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Documented conservative limitation (module docstring, T-draft-e7c8b53c
        # follow-up filed): a FULLY COMPUTED (non-string-literal) subscript
        # whose key has no resolvable single-literal binding anywhere in
        # the file (T-0432's `_ts_local_string_bindings` closes the case
        # where it DOES, see `test_local_const_string_subscript_detected`)
        # -- `ax[dynamicKey](url)` where `dynamicKey` is never assigned a
        # literal -- cannot be resolved statically; the actual property
        # name is a genuine runtime value. This is an accepted
        # false-negative gap, not a bug: recorded here so the gap is a
        # checkable fact, not a silent one.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax[dynamicKey](url);\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_static_template_literal_subscript_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0377 reviewer round 3: a NO-INTERPOLATION template-literal
        # subscript -- `` ax[`get`](url) `` -- carries identical static
        # text to `ax['get'](url)` and must resolve the same. Template
        # literals are an everyday idiom (many lint configs PREFER them
        # over quotes), not an obfuscation trick, on the exact dangerous-
        # capability surface this ticket protects.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax[`get`](url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_interpolated_template_subscript_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Documented conservative limitation (module docstring, T-draft-
        # e7c8b53c follow-up filed): an INTERPOLATED template-literal
        # subscript whose substituted name has no resolvable single-
        # literal binding -- `` ax[`${dynamicKey}`](url) `` where
        # `dynamicKey` is never assigned a literal (T-0432's dataflow
        # closes the case where it IS, see
        # `test_local_const_template_substitution_subscript_detected`) --
        # is a genuinely computed key, unlike a static no-interpolation
        # template literal (`test_static_template_literal_subscript_detected`
        # above), and stays under the same accepted false-negative gap as
        # `test_computed_subscript_not_detected`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax[`${dynamicKey}`](url);\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_local_const_string_subscript_detected(self, tmp_path: Path) -> None:
        # T-0432: the trivial indirection the audit called out --
        # `const key = 'get'; ax[key](url)` -- is a local name bound to
        # exactly one string literal in the file, so the light dataflow
        # pass resolves it the same as `ax['get'](url)`.
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nconst key = 'get';\nax[key](url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_local_const_template_substitution_subscript_detected(
        self, tmp_path: Path
    ) -> None:
        # T-0432: the same trivial indirection through a single-
        # substitution template literal -- `` ax[`${key}`](url) `` where
        # `key` is a local single-literal constant.
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nconst key = 'get';\nax[`${key}`](url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_reassigned_const_string_subscript_not_detected(
        self, tmp_path: Path
    ) -> None:
        # Honest limit (T-0432, not a regression): a name bound to TWO
        # different literal values anywhere in the file is ambiguous --
        # this dataflow-lite pass never guesses which one is live at the
        # subscript site, so it stays silent (same as an unresolved
        # computed subscript) rather than risk resolving to the wrong
        # value.
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "let key = 'get';\n"
            "if (cond) { key = 'post'; }\n"
            "ax[key](url);\n"
        )
        assert "net" not in scan_file_capabilities(pkg)

    def test_non_literal_bound_subscript_not_detected(self, tmp_path: Path) -> None:
        # Honest limit (T-0432, NOT closed by this ticket, out of scope):
        # a name bound to a non-literal value (a function call result, a
        # concatenation, another variable) anywhere in the file is
        # excluded from the local-constant table entirely -- resolving it
        # would need real reaching-definitions dataflow, not the light
        # single-literal-binding heuristic this ticket implements.
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "const key = computeMethodName();\n"
            "ax[key](url);\n"
        )
        assert "net" not in scan_file_capabilities(pkg)

    def test_multi_substitution_template_subscript_not_detected(
        self, tmp_path: Path
    ) -> None:
        # Honest limit (T-0432, NOT closed by this ticket, out of scope):
        # a template literal with MORE than one substitution, or any
        # surrounding literal text, is still a genuinely computed key even
        # when every piece happens to be a single-literal-bound local --
        # only the exact `` `${key}` `` (one substitution, no other
        # content) shape resolves.
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "const a = 'g';\n"
            "const b = 'et';\n"
            "ax[`${a}${b}`](url);\n"
        )
        assert "net" not in scan_file_capabilities(pkg)


class TestCapabilityScanTsTaxonomyClosureResolution:
    """T-0660: TS/JS sibling of `TestCapabilityScanTaxonomyClosureResolution`
    (python T-0659) -- T-0377/T-0432 closed import/require/subscript-
    binding evasions but left this module's own documented gap open: "no
    scope-local alias copy-propagation" -- a name shadowed by a local
    binding was simply unresolved past that point, never chased through a
    further local reassignment. These tests lock the T-0660 fix's litmus
    against capability-evasion-taxonomy.md's TS/JS static-resolvable rows
    not already covered by T-0377/T-0432: simple/chained assignment, array
    destructuring, default-parameter forwarding, and member rebinding.
    Deliberately uses the axios/"net" needle (dotted, no bare-module-name
    needle), same isolation rationale as `TestCapabilityScanTsBindingResolution`."""

    def test_simple_assignment_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "simple assignment": `const f = require("child_process")
        # .exec; f(x)` -- here `const f = require('axios').get; f(url);`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const f = require('axios').get;\nf(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_chained_assignment_outer_target_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "chained assignment": `let a, b; a = b = cp.exec; b(x);`
        # -- here the OUTER target `a` is called.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nlet a, b;\na = b = ax.get;\na(url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_chained_assignment_inner_target_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Same chained assignment, INNER target `b` called instead.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nlet a, b;\na = b = ax.get;\nb(url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_array_destructure_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "destructuring bind (array)": `const [f] = [cp.exec];
        # f(x);`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nconst [f] = [ax.get];\nf(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_default_param_forwarding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "default parameter forwarding": `function f(cb = cp.exec)
        # { cb(x); }`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nfunction h(cb = ax.get) {\n  cb(url);\n}\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_member_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "member rebinding": `obj.run = cp.exec; obj.run(x);`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "const obj = {};\n"
            "obj.run = ax.get;\n"
            "obj.run(url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_closure_capture_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "closure capture": `function outer(){ const r = cp.exec;
        # return function(){ r(x); }; }`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "function outer() {\n"
            "  const r = ax.get;\n"
            "  return function() { r(url); };\n"
            "}\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_default_param_benign_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No regression: a default parameter forwarding an ORDINARY (non-
        # dangerous) callable must stay silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("function h(cb = doSomethingSafe) {\n  cb(url);\n}\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_member_rebind_benign_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No regression: rebinding a member to an ORDINARY value must stay
        # silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const obj = {};\nobj.run = doSomethingSafe;\nobj.run(url);\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_reassigned_alias_call_via_chained_target_still_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Sanity check on the alias table's own resolution chain, not just
        # the raw bare-member-expression finding a plain `const f =
        # ax.get;` already produces on its own (this scanner treats ANY
        # resolvable member-expression as a candidate, called or not,
        # T-0377): calling the ALIASED name a second time through a further
        # local copy (`const g = f; g(url);`) still resolves.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nconst f = ax.get;\nconst g = f;\ng(url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_named_import_with_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`import { name as alias } from`" row (ECMA-262
        # 16.2.2 ImportSpecifier) -- distinct from the CommonJS destructure-
        # rename case (`test_require_destructure_rename_detected` on the
        # sibling binding-resolution class): this is the ESM
        # `import {a as b} from` syntax specifically.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import { exec as e } from 'child_process';\ne(cmd);\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_export_from_reexport_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`export ... from` re-export" row. `_capability.py`
        # documents that TRUE cross-module linking of the re-export's own
        # USE site is not attempted (single-file scope) -- but the scanner's
        # file-wide member-expression over-approximation (T-0377: any
        # resolvable member-expression is a candidate, called or not) still
        # fires on the `child_process.exec` reference the re-export line
        # itself contains, so this row IS covered end to end, just via the
        # coarser mechanism rather than true re-export linking.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("export { exec } from 'child_process';\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_export_star_from_reexport_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`export * from` re-export" row -- the taxonomy
        # doc tags this row "best-effort; needs source-module
        # enumerability"; the scanner's raw operations scan still flags the
        # dangerous `child_process` module name on the re-export line.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("export * from 'child_process';\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_export_default_binding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`export default` binding" row. True resolution
        # at the import USE site (`import run from './m'; run(x)`) needs
        # cross-module linking this single-file scanner does not attempt --
        # but the `cp.exec` member-expression on the export line itself is
        # still a resolvable candidate under the file-wide over-
        # approximation, so the construct is covered.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const cp = require('child_process');\nexport default cp.exec;\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_class_field_holding_bound_reference_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "class field/method holding a bound reference"
        # row (`class C { run = cp.exec; }`). `_capability.py` documents
        # that TRUE points-to tracking through a later `new C().run(x)` call
        # site is not attempted -- but the field initializer's own
        # `cp.exec` member-expression is still a resolvable candidate under
        # the file-wide over-approximation (any resolvable member-
        # expression counts, called or not), so this row is covered, just
        # not via genuine instance points-to.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const cp = require('child_process');\n"
            "class C {\n"
            "  run = cp.exec;\n"
            "}\n"
            "new C().run(cmd);\n"
        )
        assert "exec" in scan_file_capabilities(pkg)


class TestCapabilityScanTsAliasTablePredicates:
    """T-0660 mutation-evidence follow-up (TEST016 land refusal): the
    `scan_file_capabilities`-level "detected"/"not detected" tests in
    `TestCapabilityScanTsTaxonomyClosureResolution` do NOT actually kill
    mutants of several alias-table guard predicates, because
    `_collect_ts_candidates`'s own file-wide tree walk independently
    re-resolves the SAME bare member/subscript expression a fixture's RHS
    happens to contain (e.g. `const f = ax.get;` flags "net" the instant
    `ax.get` exists ANYWHERE in the file, whether or not the alias-table
    machinery that copies it to `f` even runs) -- the full-scan API masks
    these predicates entirely. These tests call the private resolver
    functions DIRECTLY with a hand-parsed AST so each guard's outcome is
    the thing under test, not incidentally reproduced by a parallel code
    path. Confirmed by hand: reverting each guard's operator (`==`<->`!=`,
    `and`<->`or`, `strict=False`<->`strict=True`) locally and re-running the
    single matching test here flips it from pass to fail; reverted before
    committing (frob:ticket T-0660's Done report records which mutation was
    hand-verified for which test)."""

    def test_member_rebind_lookup_used_only_for_identifier_object(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_typescript.py::_resolve_ts_member \
        # kind="unit"
        # Kills the `_capability.py:2217` compare-Eq-swap mutant
        # (`obj.type == "identifier"` -> `!=`): with a real `identifier`
        # object and a matching alias-table rebind entry, `_resolve_ts_
        # member` must reach the rebind fallback and return its value;
        # the swapped comparison would skip the fallback for this exact
        # case and return `None` instead.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _TS_SCOPE_TYPES, _resolve_ts_member

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("obj.run(url);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        member = _ts_find(tree.root_node, "member_expression")
        assert member is not None
        program = tree.root_node
        assert program.type in _TS_SCOPE_TYPES
        alias_table = {program.id: {"obj.run": "axios.get"}}
        resolved = _resolve_ts_member(member, {}, {}, {}, alias_table)
        assert resolved == "axios.get"

    def test_member_rebind_lookup_skipped_without_alias_table(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_typescript.py::_resolve_ts_member \
        # kind="unit"
        # Kills the `_capability.py:2217` boolop-And-swap mutant (`and` ->
        # `or`): with `alias_table=None`, the real `and` short-circuits
        # before ever touching `_ts_attr_rebind_lookup`, returning `None`
        # cleanly; the swapped `or` would call `_ts_attr_rebind_lookup`
        # with `alias_table=None` anyway (since the identifier check alone
        # is enough to satisfy `or`), raising `AttributeError` the instant
        # it tries `None.get(...)`.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _resolve_ts_member

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("obj.run(url);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        member = _ts_find(tree.root_node, "member_expression")
        assert member is not None
        resolved = _resolve_ts_member(member, {}, {}, {}, None)
        assert resolved is None

    def test_attr_rebind_lookup_climbs_past_non_matching_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_typescript.py::_ts_attr_rebind_lookup \
        # kind="unit"
        # Kills the `_capability.py:2246` compare-Eq-swap mutant (`cur.type
        # == "program"` -> `!=`): the rebind entry lives TWO scope levels
        # above the call site (the outer function, not the immediately
        # enclosing inner one, which is a real intervening non-matching
        # scope) -- the real code must climb PAST that inner scope to find
        # it. The swapped comparison breaks the climb at the very first
        # non-"program" scope it checks (i.e. immediately), so it would
        # never reach the outer scope's entry at all.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _ts_attr_rebind_lookup

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "function outer() {\n  function inner() {\n    obj.run(url);\n  }\n}\n"
        )
        tree, _source, _lang = raw_tree(pkg).danger_ok
        call_site = _ts_find(tree.root_node, "member_expression")
        assert call_site is not None
        functions = []
        _ts_find_all(tree.root_node, "function_declaration", functions)
        assert len(functions) == 2
        outer_fn, inner_fn = functions
        assert outer_fn.start_byte < inner_fn.start_byte
        # inner's own scope binds nothing for "obj.run" -- only outer does.
        alias_table = {
            inner_fn.id: {},
            outer_fn.id: {"obj.run": "axios.get"},
        }
        resolved = _ts_attr_rebind_lookup("obj", "run", call_site, alias_table)
        assert resolved == "axios.get"

    def test_resolve_expr_peels_through_chained_assignment(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_typescript.py::_resolve_ts_expr \
        # kind="unit"
        # Kills the `_capability.py:2292` compare-Eq-swap mutant
        # (`node.type == "assignment_expression"` -> `!=`): resolving the
        # OUTER assignment_expression node of `a = b = ax.get` directly
        # must peel through to `ax.get`'s own resolution; the swapped
        # comparison would skip the peel-through branch entirely and fall
        # through to `_resolve_ts_expr`'s final `return None`.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _resolve_ts_expr

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("a = b = ax.get;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        outer_assignment = _ts_find(tree.root_node, "assignment_expression")
        assert outer_assignment is not None
        resolved = _resolve_ts_expr(outer_assignment, {"ax": "axios"}, {}, {}, None)
        assert resolved == "axios.get"

    def test_default_param_alias_recorded_for_identifier_pattern(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_typescript.py::_record_ts_default_param_aliases \
        # kind="unit"
        # Kills the `_capability.py:2472` compare-NotEq-swap mutant
        # (`pattern.type != "identifier"` -> `==`): a real identifier
        # default-parameter pattern with a resolvable default value must
        # get an alias entry; the swapped comparison would treat the
        # ordinary identifier case as the one to SKIP.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _record_ts_default_param_aliases

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("function h(cb = ax.get) { cb(url); }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        func = _ts_find(tree.root_node, "function_declaration")
        assert func is not None
        alias_table: dict = {}
        _record_ts_default_param_aliases(func, {"ax": "axios"}, {}, {}, alias_table)
        assert alias_table[func.id]["cb"] == "axios.get"

    def test_default_param_alias_skips_missing_default_value(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_typescript.py::_record_ts_default_param_aliases \
        # kind="unit"
        # Kills the `_capability.py:2472` boolop-Or-swap mutant (`or` ->
        # `and`): a plain parameter with NO default (`value is None`, the
        # other two clauses false) must be skipped by the real `or`. The
        # swapped `and` would let it through and call `_resolve_ts_expr`
        # on a `None` value node, raising `AttributeError`.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _record_ts_default_param_aliases

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("function h(cb) { cb(url); }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        func = _ts_find(tree.root_node, "function_declaration")
        assert func is not None
        alias_table: dict = {}
        _record_ts_default_param_aliases(func, {}, {}, {}, alias_table)
        assert alias_table.get(func.id, {}) == {}

    def test_destructure_alias_tolerates_length_mismatch(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/vet/_capability_typescript.py::_record_ts_destructure_alias \
        # kind="unit"
        # Kills the `_capability.py:2499` bool-False-negated mutant
        # (`strict=False` -> `strict=True`): the array pattern binds FEWER
        # names than the array literal has elements (a real, benign
        # over-provisioned RHS) -- the real `zip(..., strict=False)` must
        # silently truncate to the shorter side; `strict=True` would raise
        # `ValueError` instead.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _record_ts_destructure_alias

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const [f] = [ax.get, 0];\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        left_pattern = _ts_find(tree.root_node, "array_pattern")
        right_array = _ts_find(tree.root_node, "array")
        assert left_pattern is not None
        assert right_array is not None
        scope_aliases: dict = {}
        _record_ts_destructure_alias(
            left_pattern, right_array, {"ax": "axios"}, {}, {}, {}, scope_aliases
        )
        assert scope_aliases["f"] == "axios.get"

    def test_destructure_alias_binds_only_identifier_elements(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_typescript.py::_record_ts_destructure_alias \
        # kind="unit"
        # Kills the `_capability.py:2500` compare-NotEq-swap mutant
        # (`left_el.type != "identifier"` -> `==`): a real identifier
        # destructuring element paired with a resolvable RHS element must
        # get an alias entry; the swapped comparison would SKIP the
        # ordinary identifier case instead of an unsupported one.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _record_ts_destructure_alias

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const [f] = [ax.get];\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        left_pattern = _ts_find(tree.root_node, "array_pattern")
        right_array = _ts_find(tree.root_node, "array")
        assert left_pattern is not None
        assert right_array is not None
        scope_aliases: dict = {}
        _record_ts_destructure_alias(
            left_pattern, right_array, {"ax": "axios"}, {}, {}, {}, scope_aliases
        )
        assert scope_aliases["f"] == "axios.get"
