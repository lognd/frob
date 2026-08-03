# Editor support for .strata

<!-- frob:ticket T-0139 -->

One TextMate grammar, two editor families: `editors/vscode-strata/` is
consumed directly by VSCode and, unmodified, by JetBrains IDEs via their
TextMate Bundles feature. There is exactly one place the strata surface
keyword vocabulary is spelled out for editors, and
`tests/unit/test_strata_tmlanguage.py` drift-locks it bidirectionally
against `strata-core/src/parse/grammar_policy.rs`'s own dispatch table (post-T-1006 split out of the old monolithic parse.rs/mod.rs), so a keyword added
to the parser without a matching grammar update fails CI instead of
silently going unhighlighted (or, worse, a keyword removed from the parser
lingering forever in the grammar).

## What you get, honestly

The grammar in `editors/vscode-strata/syntaxes/strata.tmLanguage.json` is
TextMate tokenization only: it colors comments (`//`, `///`), string
literals, numeric quantities with their units (`5 req/s`, `250 ms`,
`4 KiB`, `15 %/month`), the top-level declaration keywords (`module`,
`node`, `flow`, `boundary`, `store`, `cache`, `queue`, `cdn`, `balancer`,
`policy`, `operation`, `scenario`, `secret`, `resource`, `assert`,
`assume`, `refine`),
the clause keywords used inside declaration bodies (`attr`, `capacity`,
`trust`, `delivery`, `issued_by`, `endorsed_by`, and the rest -- see the
grammar's `clause-keywords` pattern for the full list), the `->` arrow, and
punctuation.

It does **not** give you code completion, go-to-definition, hover
diagnostics, or refactoring. Those require a real Language Server Protocol
integration, which strata has no plan to build. If `.strata` files start
carrying enough weight to justify that investment, it is a new, separate
piece of tooling -- not an extension of this grammar.

## VSCode

1. Copy or symlink `editors/vscode-strata/` into your VSCode extensions
   directory (`~/.vscode/extensions/strata-syntax-0.1.0/` on Linux/macOS,
   `%USERPROFILE%\.vscode\extensions\strata-syntax-0.1.0\` on Windows), or
   open this repository in VSCode and use **Developer: Install Extension
   from Location...** pointed at `editors/vscode-strata/`.
2. Reload the window. `.strata` files now open with the `strata` language
   mode and syntax highlighting from `source.strata`.

No `activationEvents` are declared -- `contributes.languages` and
`contributes.grammars` alone are enough for VSCode to associate the
extension and load the grammar lazily when a `.strata` file is opened.

## JetBrains IDEs

See `editors/jetbrains/README.md` for the full walkthrough: install (or
enable) the TextMate Bundles plugin, add `editors/vscode-strata/` as a
bundle under Settings > Editor > TextMate Bundles, and associate the
`.strata` extension with it under Settings > Editor > File Types. This
route works unmodified in IntelliJ IDEA, PyCharm, WebStorm, CLion, GoLand,
RubyMine, and PhpStorm, since they all bundle the TextMate Bundles plugin
and all read the same VSCode-shaped grammar directory directly -- no
separate IntelliJ plugin exists or is planned (see that README for why).

## Keeping the grammar honest

Do not hand-edit the keyword lists in
`editors/vscode-strata/syntaxes/strata.tmLanguage.json` without also
running the tests:

```
pytest tests/unit/test_strata_tmlanguage.py -v
```

The test extracts the construct-keyword dispatch table and the
`at_keyword`/`expect_keyword` call sites directly from
`strata-core/src/parse/grammar_policy.rs` and asserts they match the grammar's
declaration- and clause-keyword patterns. If the parser's keyword
vocabulary and the grammar disagree, this is the test that catches it.
