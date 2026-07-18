# strata syntax highlighting for JetBrains IDEs

There is no dedicated IntelliJ plugin for strata. JetBrains IDEs can load a
VSCode-shaped TextMate bundle directly, and `editors/vscode-strata/` is
already exactly that shape (a `package.json` with a `contributes.grammars`
entry plus a `.tmLanguage.json` file), so pointing a JetBrains IDE at that
same directory gives it the identical grammar VSCode uses -- one grammar,
two consumers, zero drift between them. A second, hand-maintained IntelliJ
plugin would only be a second copy of the same keyword list to keep in sync
by hand, which is exactly what the drift-lock test in
`tests/unit/test_strata_tmlanguage.py` exists to prevent for the single
grammar; a full plugin is not worth the duplication for a TextMate-only
feature set (tokenization/coloring, no code intelligence).

## Setup (any JetBrains IDE with the TextMate Bundles plugin)

The TextMate Bundles plugin ships with IntelliJ IDEA, PyCharm, WebStorm,
CLion, GoLand, RubyMine, PhpStorm, and the other JetBrains IDEs (bundled by
default since 2019.1; enable it under Settings > Plugins > Marketplace >
"TextMate Bundles" if it has been disabled).

1. Open **Settings/Preferences > Editor > TextMate Bundles**.
2. Click **+** and select the `editors/vscode-strata/` directory in this
   repository (the directory containing `package.json` and `syntaxes/`).
3. Confirm the bundle is enabled (checkbox next to it in the bundle list).
4. Open **Settings/Preferences > Editor > File Types**, find the
   `.strata` extension (it should already show as recognized by the
   TextMate bundle once step 2 is done); if it does not, add `.strata`
   to the bundle's recognized patterns via the same File Types page so
   the IDE routes `*.strata` files to the strata TextMate scope
   (`source.strata`) instead of treating them as plain text.

## What this gives you, and what it does not

TextMate Bundles give tokenization-based syntax coloring only: keywords,
strings, comments, numbers/units, and punctuation are colored per the same
`syntaxes/strata.tmLanguage.json` grammar VSCode uses. It does not give
code completion, go-to-definition, inline diagnostics, or refactoring --
those would require a real Language Server Protocol integration or a
full IntelliJ plugin, neither of which exists yet for strata. See
`docs/guides/editors.md` for the honest capability list.
