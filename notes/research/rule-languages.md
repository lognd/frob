# Rule languages survey: what GRL should copy, and what it must avoid

Date: 2026-10-02. Status: research input for grl-spec.md (ticket ~4QBTKCK, decision D80) and
for plugins.md sections 4 and 6. ASCII only. Raw data, clones and measurement scripts lived under
`<scratchpad>/grl/`
(never in the repo; clones deleted after writing, see section 9). Complements, does not repeat,
notes/research/plugins.md (which surveys plugin architecture, not rule-language usability).

## 0. Honest summary (read this first)

- Universe (denominator): 17 rule systems from the brief, all surveyed with at least one real rule
  copied from the project's own repository or docs: GritQL, Biome GritQL plugins, Semgrep, ast-grep,
  CodeQL, Souffle, tree-sitter queries, Rego/OPA, Comby, Coccinelle SmPL, ESLint
  `no-restricted-syntax`, Clippy handwritten lints, Oxlint JS plugins, Ruff (no DSL), PMD XPath,
  Checkstyle, Error Prone Refaster. Three extras found on the way: Glean Angle, Globstar (DeepSource),
  Regal (a linter written in Rego). Done: 17 of 17 plus 3 extras. Pending: 0. Blocked: 0.
- What is thinner than the rest, stated up front: (a) I executed only six of them locally and
  measured their error messages: ast-grep 0.45.3, Semgrep 1.179.0, Biome 2.5.15 (GritQL plugin),
  OPA 1.21.1, ESLint 9.39.5, and py-tree-sitter 0.26.0 for queries. For CodeQL, Souffle, Comby,
  Coccinelle, PMD, Checkstyle, Refaster, Clippy and Oxlint the "error quality" cells come from their
  own test goldens, source or docs, not from running them (no CodeQL bundle, no cargo builds, host is
  aarch64). (b) Newcomer-complaint evidence is strong for Biome/Grit, Semgrep, ast-grep, CodeQL,
  Souffle, Rego, Coccinelle, tree-sitter, Refaster, Ruff; weak for Comby, PMD, Checkstyle, Clippy,
  Oxlint (I found no complaint thread and say so). (c) Ratings in the comparison tables are my
  judgment (tag J) from the cited evidence; measured facts carry tag M, documented facts tag D.
  (d) Popularity numbers are proxies (stars, rule-file counts, npm keyword counts, Stack Overflow tag
  counts) taken on 2026-10-02 and are not quality measures.
- Phase-2 verdict: coverage of the declared list is complete; coverage of "all rule DSLs that exist"
  is not claimed. Not examined beyond a star count: Opengrep, OpenRewrite. Mentioned in a cited thread
  only: weggli, Joern.
- The three strongest lessons, one line each (full list in section 6):
  1. Start from pasted code, but make every name in it checked at compile time: the surveyed tools
     that let a typo become "no match" (Biome, ESLint, OPA, tree-sitter predicates, all measured)
     turn a rule bug into false cleanliness, which is exactly the failure frob's three-valued model
     exists to forbid.
  2. Containment must be transitive by default and negation must be anchored by a positive binding:
     the single most common silent failure is a shallow `inside` (measured in ast-grep and
     tree-sitter) and the most common maintainer-admitted confusion is `pattern-not` (Semgrep
     issues 8428 and 3967).
  3. Ship the test inside the rule and make the rule's own errors teach: every tool with inline
     fire/clean examples (Semgrep, Checkstyle, PMD, Clippy, Rego) has a healthier rule corpus than
     the ones without (Biome plugins, Comby), and Souffle shows the next step, golden tests for the
     compile errors themselves.

## 1. What GRL has to express (the requirements, from the design set)

Read for this note: docs/design/plugins.md sections 4-6, universal-model.md sections 4-5,
rules.md section 3, diagnostics.md, neatness.md, cicd.md, binding.md 6-7, plus the rule pages under
docs/reference/rules/.

1. Pattern rules: a language-tagged code snippet with metavariables (`$X`, `$$$ARGS`) and ellipsis,
   refined by `inside`, `has`, `not`, `all`, `any` (rules.md level 1; the gob-pattern combinators
   `follows`, `precedes`, `regex`, `kind` as well), optional fix template.
2. Relational rules: predicates over U (units, edges, attributes, scope graph with Must/May/Unknown
   status, counts, bounded closure), stratified-Datalog-shaped, polynomial (universal-model.md 4.3).
3. Three-valued results and polarity: P+, P-, P0, Pn, Pc fix which bound fires and which certifies
   clean; Unresolved is a finding, NotApplicable never is (universal-model.md 4.1-4.2).
4. One language, no second form (plugins.md section 4); std rules compiled ahead of time, disk packs
   compiled to plans, byte-identical findings (plugins.md 6.1).
5. Diagnostics that teach, fixes with applicability (machine, maybe-incorrect, has-placeholders,
   manual), `explain` text from the rule (diagnostics.md 2, 3, 6).
6. Embedded fire/clean tests; today the corpus format is `// error: ID` or `// warn: ID` trailing
   comments inside markdown examples (docs/reference/rules/TODO001.md, COV001.md), and a universal
   rule also needs a third fixture in a language lacking the feature (rules.md section 2).
7. Intuitive for someone who has never written a lint rule (the owner's reason for "no second form").

## 2. The survey, one tool at a time

Format per tool: the simplest rule; metavariables and ellipsis; negation; containment; relational or
cross-file facts; how it ships tests; how the rule's own errors read; documented newcomer
complaints; popularity. Paths are relative to the named repository unless a URL is given.

### 2.1 GritQL (getgrit/gritql) and Biome GritQL plugins (biomejs/biome)

Simplest rule (Biome docs, linter/plugins.mdx in biomejs/website):

```grit
`$fn($args)` where {
    $fn <: `Object.assign`,
    register_diagnostic(
        span = $fn,
        message = "Prefer object spread instead of `Object.assign()`"
    )
}
```

A pasted-code rewrite with a negated containment condition (getgrit/stdlib,
`.grit/patterns/js/no_console_log.md`; the file is also the test):

```grit
engine marzano(0.1)
language js

`console.log($arg)` => . where { $arg <: not within catch_clause() }
```

A relational-ish rule in grit's own repo (`.grit/patterns/no_panic.md` in getgrit/gritql):

```grit
language rust

file($name, $body) where {
  $name <: includes "marzano/lsp",
  $body <: contains `$foo.unwrap()` => `$foo?`,
}
```

- Metavariables: `$x` one node, `$...` a sequence, `$_` anonymous; same name twice means "same
  value" and, once bound, stays bound for the whole pattern (D: gritql/docs/src/pages/language/bubble.mdoc).
  Scope is escaped with `bubble` and `$GLOBAL_` names.
- Negation: `not` inside a match (`$x <: not within ...`) and `!` on a whole condition
  (language/conditions.mdoc).
- Containment: `contains` and `within`, both transitive (`includes` is a string test, not containment).
- Relational: file-local. A Hacker News reader on the launch thread notes the lack of name
  resolution ("replace every use of S::method" needs it; item 39770908, jcranmer).
- Tests: the pattern file is Markdown; a fenced `grit` block plus before/after sample pairs; YAML
  patterns carry `samples: [{input, output}]`; `grit patterns test` (D: guides/testing.mdoc). The
  test is input/output, not fire/clean, so a rule that must NOT fire is a sample whose output equals
  its input. Biome plugins: the three Biome docs pages I read contain no test facility (D, grep of
  linter/plugins.mdx, recipes/gritql-plugins.mdx, reference/gritql.mdx).
- Rule-error quality (M, Biome 2.5.15): a typo in a function name (`register_diagnostc(...)`) and an
  unbalanced parenthesis both print only `Error(s) during loading of plugins: Failed to compile the
  Grit plugin`, no location, no reason. A misspelled snippet (`consol.log($msg)`) and a misspelled
  metavariable in a condition (`$mgs <: ...`) both produce zero findings, exit 0, no warning.
  GritQL core errors are plain strings, e.g. `metavariable |{}| not found in snippet`
  (crates/core/src/pattern_compiler/pattern_compiler.rs line 477), without spans.
- Newcomer complaints (cited): "works with `grit apply`, produces no results as a Biome plugin"
  (biome#5980, plus #6426 variables inside quotes, #7446 spread metavariable fails on object
  members); "can't match interfaces or `type`... problems/holes in our grammar mapping"
  (biome#7363, maintainer morgante); "slow plugin" where the author wrapped everything in a
  top-level `contains` and the maintainer replied "we should refuse to accept such a rule" while
  another maintainer asked why ast-grep requires a positive matcher and Grit does not (biome#6210).
  Positive voice: a team found ts-morph's "barrier to entry felt high" and GritQL lowered it
  (HN 39770908, psalv).
- Popularity (2026-10-02): gritql 4601 stars; getgrit/stdlib 109 stars and 212 Markdown pattern
  files under `.grit/patterns`; biomejs/biome 25887 stars; npm keyword `biome-plugin` 20 packages.

### 2.2 Semgrep (semgrep/semgrep, rules in semgrep/semgrep-rules)

Simplest rule (semgrep-rules, python/lang/best-practice/hardcoded-tmp-path.yaml):

```yaml
rules:
  - id: hardcoded-tmp-path
    pattern: open("=~/^\/tmp.*/", ...)
    message: >-
      Detected hardcoded temp directory. Consider using 'tempfile.TemporaryFile' instead.
    severity: WARNING
    languages:
      - python
```

A typical combinator rule (python/lang/security/audit/dangerous-system-call-audit.yaml, abridged):

```yaml
- id: dangerous-system-call-audit
  patterns:
  - pattern-not: os.$W("...", ...)
  - pattern-either:
    - pattern: os.system(...)
    - pattern: |
        $X = __import__("os")
        ...
        $X.system(...)
```

Negation written as a regex (python/pyramid/audit/authtkt-cookie-samesite.yaml):

```yaml
patterns:
- pattern-either:
  - pattern: pyramid.authentication.AuthTktCookieHelper(..., samesite=$SAMESITE, ...)
- pattern: $SAMESITE
- metavariable-regex:
    metavariable: $SAMESITE
    regex: (?!'Lax')
```

- Metavariables and ellipsis: `$X`, `$...ARGS`, `...` (call arguments, statements, strings, fields),
  `<... pattern ...>` deep expression; type, import, literal, anonymous (`$_`) variants; "Limitations"
  section in the docs (D: semgrep-docs docs/writing-rules/pattern-syntax.mdx lines 724-830) says
  statements and expressions are matched differently, partial expressions are invalid, and `...`
  "does not jump from inner to outer statement blocks".
- Negation: `pattern-not`, `pattern-not-inside`, `pattern-not-regex`, `metavariable-regex`. Counts in
  semgrep-rules at a84ff9cc24 (M, python script over 2113 rule files, 2234 rules): `pattern-inside`
  2659 uses, `pattern-not-inside` 1014, `pattern-not` 939, `metavariable-regex` 518.
- Containment: `pattern-inside` (transitive), `pattern-not-inside`.
- Relational and cross-file: `mode: taint` (269 of 2234 rules) with sources, sinks, sanitizers; an
  experimental `mode: join` that runs several rules and joins their metavariables
  (docs/writing-rules/experiments/join-mode/overview.mdx):

  ```yaml
  join:
    refs:
      - {rule: flask-user-input.yaml, as: user-input}
      - {rule: unescaped-template-extension.yaml, as: unescaped-extensions}
    on:
      - 'user-input.$VAR == unescaped-extensions.$VALUE'
  ```

- Tests (D+M): a file next to the rule with `# ruleid: <id>` / `# ok: <id>` comments on the line
  before; `todoruleid` and `todook` record known gaps; `.fixed` files test `fix`;
  `semgrep --test`, `semgrep --validate` (docs/writing-rules/testing-rules.mdx). 2165 test files
  in semgrep-rules contain `ruleid:`.
- Rule-error quality (M, 1.179.0): an unquoted Python `def $F(...): ...` pattern in YAML dies with
  `Invalid YAML file ... mapping values are not allowed here in "<file>", line 6, column 31` (the
  YAML-colon trap the experimental-syntax page itself warns about). A typo key (`pattern-insde`)
  prints `Invalid rule schema --> s2.yaml:2`, underlines the whole rule (lines 2-11) and says
  `... is not valid under any of the given schemas`; no did-you-mean, no pointer to the typo. Simplest
  rule runs in 1.4 s wall including startup.
- Newcomer complaints (cited): `pattern-not` "only filters out a match if it is exactly the same
  match... `pattern-not-regex` filters out a match if it intersects with it. I agree it's confusing"
  (semgrep#8428, IagoAbal); "Associating pattern-not and pattern-inside... matches everything"
  answered "more of a confusing UX issue; we should probably address by getting rid of pattern-not
  altogether, or switching to the boolean syntax" (semgrep#3967, nbrahms); metavariables not shared
  between `pattern` and `pattern-inside` as expected (semgrep#4583); "docs are a little hard to
  navigate" (HN 38591578). Semgrep's answer is visible in the docs: an experimental boolean syntax
  `any`, `all`, `inside`, `not` that replaces `pattern-either`, `patterns`, `pattern-inside`, with
  the warning "You can't mix and match" (experiments/pattern-syntax.mdx). That is the gob-pattern
  shape rules.md section 3 already chose.
- Popularity: semgrep 16843 stars; semgrep-rules 1262 stars and 2234 rules (M); fork opengrep 3133
  stars; Stack Overflow tag `semgrep` 37 questions.

### 2.3 ast-grep (ast-grep/ast-grep, docs in ast-grep/ast-grep.github.io)

Simplest rule: no file at all (M, 0.45.3, 5 ms):

```text
$ ast-grep run -p 'print($$$A)' -l python a.py
a.py:3:    print("hi")
```

A YAML rule with relational operators (website/catalog/rust/avoid-duplicated-exports.md):

```yaml
id: avoid-duplicate-export
language: rust
rule:
  all:
     - pattern: pub use $B::$C;
     - inside:
        kind: source_file
        has:
          pattern: pub mod $A;
     - has:
        pattern: $A
        stopBy: end
```

- Metavariables: `$X` one node, `$$$X` many, `$_` anonymous, Pattern must be
  valid parseable code; for fragments use `pattern: {context: '{"key": "$VAL"}', selector: pair}`
  (website/advanced/faq.md "My pattern does not work, why?").
- Negation: `not:` composite; the compiler demands one positive matcher (M: a rule with only `not`
  fails with `Rule must specify a set of AST kinds to match. Try adding kind rule.`).
- Containment: `inside`, `has`, `follows`, `precedes`, each taking a sub-rule. Default depth is the
  immediate neighbour; `stopBy: end` goes transitive; `stopBy: <rule>` stops at a node
  (guide/rule-config/relational-rule.md). M: the rule "pattern print($$$A), inside kind
  function_definition" reports ZERO findings and exits 0 on a `print` in a function body; adding
  `stopBy: end` reports it. Nothing warns.
- Relational and cross-file: none; the project says it has no type, control-flow, data-flow or taint
  information (advanced/tool-comparison.md). The FAQ also records "Rule matching is ordered because
  previous rules' matched meta-variables can affect later rules" (advanced/faq.md).
- Tests: `valid:` and `invalid:` code lists in a test YAML next to the rules, plus snapshots
  (guide/test-rule.md). M: for the rule `no-print` the output was `[Wrong] No no-print baseline
  found.` for each invalid case (snapshots are mandatory) and `[Missing] Expect rule no-print to
  report issues, but none found in: x = 1`; summary `FAIL no-print ..WWM`. The four-quadrant
  vocabulary (Validated, Noisy, Reported, Missing) is the clearest test model in the survey.
- Rule-error quality (M): a typo field prints `Error: Cannot parse rule bad1.yml / Help: ... / See
  also: https://ast-grep.github.io/guide/rule-config.html / Caused by: unknown field insde, expected
  one of pattern, kind, regex, nthChild, range, inside, has, precedes, follows, all, any, not,
  matches`. Better than Semgrep (lists valid fields, doc link, `Help:` line, from the
  `ErrorContext` table in crates/cli/src/utils/error_context.rs that follows "consistent terminology,
  clear and concise, provide context, suggest a fix"), but no line or column inside the rule file, no
  did-you-mean, and a bad `kind` prints five nested `Caused by` lines ending `Kind function_defn is
  invalid`.
- Newcomer complaints: the FAQ's first two entries are "My pattern does not work, why?" and "My Rule
  does not work, why?", whose first advice is "Use the Playground"; "CLI and Playground produce
  different results" (parser version and utf-8 vs utf-16); issue 2300 `stopBy: end does not seem to
  work with include`; 2867 a grammar bump changed results.
- Popularity: ast-grep 16105 stars; catalog 63 rule pages; no registry (sharing is by copy);
  Stack Overflow tag `ast-grep` 15 questions; HN launch thread 292 points, 79 comments.

### 2.4 CodeQL QL (github/codeql)

Simplest query (python/ql/src/Statements/AssertOnTuple.ql, metadata header abridged):

```ql
/**
 * @name Asserting a tuple
 * @kind problem
 * @problem.severity error
 * @id py/asserts-tuple
 */
import python

from Assert a, string b, string non
where
  a.getTest() instanceof Tuple and
  ( if exists(a.getTest().(Tuple).getAnElt())
    then ( b = "True" and non = "non-" )
    else ( b = "False" and non = "" ) )
select a, "Assertion of " + non + "empty tuple is always " + b + "."
```

Negation and recursion (python/ql/src/Statements/UnnecessaryDelete.ql, abridged):

```ql
predicate isInsideLoop(AstNode node) {
  node.getParentNode() instanceof While or node.getParentNode() instanceof For
  or exists(AstNode prev | isInsideLoop(prev) | node = prev.getAChildNode())
}
from Delete del, Expr e, Function f
where f.getLastStatement() = del and e = del.getATarget() and f.containsInScope(e)
  and not isInsideLoop(del)
  and not exists(API::CallNode call | call = API::moduleImport("sys").getMember("exc_info").getACall()
                 and call.getScope() = f)
select del, "Unnecessary deletion of local variable $@ in function $@.", e, e.toString(), f, ...
```

- Variables are typed ranges in `from`; no metavariables over code, no pasted snippets. Ellipsis: none.
- Negation: `not`, `not exists(...)`; the compiler enforces binding (range-restriction).
- Relational: the strongest in the survey: whole-program classes, recursion with monotonic
  aggregates, global data flow. Shared cross-language libraries live in `shared/` (concepts,
  namebinding, dataflow, typeflow, ...), and a `unified/` extractor maps a language's tree onto a
  shared AST through a desugaring framework `yeast` whose query language is "inspired by tree-sitter
  queries" (shared/yeast/doc/yeast.md). That is the same architecture as U plus adapters.
- Tests: `X.qlref` names the query, `X.expected` is the golden result table, sources next to them
  (python/ql/test/query-tests/Statements/asserts/); inline-expectation comments also exist. Count at
  f7617abe60: 2064 `.qlref` files. Issue "InlineExpectationsTest documentation regarding `.expected`
  file is misleading" (github/codeql#5343).
- Errors: precise but in the vocabulary of the logic. `ERROR: 'funcName' is not bound to a value`
  for a `not exists` clause, solved by an annotation `bindingset[funcName]` (codeql#14974); `Non-
  monotonic recursion` (codeql#6118, #8341, #11361). The language reference is where users learn the
  reason (docs "evaluation of QL programs").
- Complaints: "chatgpt is completely unable to create even simple queries" (HN 43055733, mmsc);
  binding and monotonic-recursion errors above.
- Popularity: codeql repo 10158 stars; 2617 `.ql` queries under src (java 567, cpp 632, python 352,
  javascript 351, csharp 299, go 90, ruby 90, rust 55, swift 41); 5687 `.qll` library files;
  Stack Overflow tag `codeql` 90 questions; 452 GitHub discussions.

### 2.5 Souffle Datalog (souffle-lang/souffle)

Simplest rule set (tests/example/andersen/andersen.dl, abridged):

```text
.type var <: symbol
.decl AddressOf(y:var, x:var)
.input AddressOf()
.decl PointsTo(y:var, x:var)
.output PointsTo()
PointsTo(y, x) :- AddressOf(y, x).
PointsTo(y, x) :- Assign(y, z), PointsTo(z, x).
```

- Variables are logic variables; no code patterns; facts are extracted by an external tool (a hard
  prerequisite: first rule requires a fact extractor).
- Negation: `!rel(...)`, legal only when stratifiable and all variables grounded.
- Relational: native. Termination: the Datalog guarantee holds on finite domains; arithmetic
  functors and records can diverge (J, general Datalog knowledge; not tested here).
- Tests: golden outputs per test directory (`*.out`, `*.csv`) and, importantly, golden compile errors
  (`tests/semantic/choice/choice.err`):

  ```text
  Error: Unable to stratify relation(s) {chosen,diffchoice}
  Relation diffchoice in file choice.dl at line 16
  .decl diffchoice(s:Integer, p:Integer)
  ------^--------------------------------
  has cyclic negation in file choice.dl at line 25
  chosen(s, p) :- student(s, m, _), professor(p, m), !diffchoice(s, p).
  ----------------------------------------------------^-----------------
  1 errors generated, evaluation aborted
  ```

  632 `.dl` files in tests; `.err` goldens for `Ungrounded variable x` (`src/ast/transform/
  GroundedTermsChecker.cpp` line 49) and `Unable to stratify` (`SemanticChecker.cpp` line 232).
  `--provenance=explain` answers "why was this tuple derived" (src/MainDriver.cpp line 590).
- Complaints: `Error: Unable to stratify relation(s)` needs recursive aggregates, maintainer: "You
  need recursive aggregates which are currently developed" (souffle#2266); the workaround for
  negation is an auxiliary relation (souffle#1862, b-scholz); ungrounded-variable crashes
  (souffle#2318, #2293, #2294).
- Popularity: 1180 stars; no public rule registry.

### 2.6 tree-sitter queries (tree-sitter/tree-sitter)

Simplest query (docs/src/using-parsers/queries/1-syntax.md):

```scheme
(binary_expression operator: "!=" right: (null))
(class_declaration name: (identifier) @class_name !type_parameters)
```

- Captures `@name`; predicates `#eq?`, `#match?`, `#not-eq?`; anchors `.` for immediate siblings;
  quantifiers `*`, `+`, `?`.
- Negation: only `!field` (absent field) and `#not-eq?`/`#not-match?` predicates.
- Containment: only nesting shown in the pattern; there is no descendant operator (tree-sitter#880,
  11 comments, opened 2021-01, still open). M (py-tree-sitter 0.26.0): a query for `print` as a direct
  statement of a function body returns 1 match; the same query on a `print` nested in an `if` inside
  the function returns 0, silently.
- Relational: none (single tree); no unification across captures except by predicate.
- Tests: only for highlighting and tags: `// <- keyword` and `// ^ string` caret assertions in
  `test/highlight` (docs/src/3-syntax-highlighting.md line 390). There is no general rule-test
  facility.
- Errors (M): `Invalid node type at row 0, column 1: cal`; `Invalid field name at row 0, column 6:
  fn`; `Unexpected EOF`; the library formats `Query error at R:C. Impossible pattern:` for
  structurally impossible queries (lib/binding_rust/lib.rs line 3925). Row and column plus the bad
  word is better than most. BUT (M) an unknown predicate name (`#eqq?`) is silently accepted and the
  query matches regardless of it, and a mistyped predicate can therefore widen a rule.
- Complaints: "Specify descendant or ancestor in query" (#880); "Docs: improve specification of
  query behavior" (#5382); "Valid query patterns treated as (semi-)impossible" (#4687); `(MISSING)`
  and `(ERROR)` match when no such node exists (#5079).
- Popularity: tree-sitter 27110 stars; nvim-treesitter 14434 stars; the Globstar toolkit (below)
  and ast-grep both reuse the grammars.

### 2.7 Rego (open-policy-agent/opa; Regal in open-policy-agent/regal)

A real lint rule written in Rego, with its test (regal, bundle/regal/rules/style/
avoid-get-and-list-prefix/avoid_get_and_list_prefix.rego):

```rego
package regal.rules.style["avoid-get-and-list-prefix"]

import data.regal.ast
import data.regal.result

report contains violation if {
	some rule in input.rules
	strings.any_prefix_match(ast.ref_to_string(rule.head.ref), {"get_", "list_"})

	violation := result.fail(rego.metadata.chain(), result.location(rule.head))
}
```

Test in the same directory: `test_fail_rule_name_starts_with_get if { r := rule.report with input as
ast.policy(`get_foo := 1`); r == {{ ...full finding with category, description, location, level... }} }`.

- Variables and iteration: `some x in xs`; `input` is JSON, so "code" is data (here Regal's AST as
  JSON). No code patterns.
- Negation: `not expr`, with Rego's "undefined" semantics: an expression that references an undefined
  value is undefined, not false (docs/docs/policy-language.md line 92: "Expressions that refer to
  undefined values are also undefined. This includes comparisons such as `!=`").
- Relational: native joins over documents; no recursion beyond declared rules (recursion is a
  compile error `rego_recursion_error`, docs/docs/errors/).
- Tests: first-class: any rule named `test_*`, `with input as ...`, `opa test` (docs/docs/
  policy-testing.md). M (1.21.1): `opa test` prints `PASS: 1/1`.
- Errors (M): `p3.rego:5: rego_unsafe_var_error: var lnie is unsafe` for a mistyped variable; `p4.rego:4:
  rego_unsafe_var_error: var i is unsafe` for a variable first used under `not`; `undefined function
  q` with row and column in JSON mode. The docs call unsafe-var "one of the most common errors
  reported by OPA" (errors/rego-unsafe-var-error/var-name-is-unsafe.md). M, silent: a mistyped FIELD
  (`c.lne`) is simply undefined, the rule returns `[]`, and `opa check --strict` prints nothing.
- Complaints: "Improve reporting of rego_unsafe_var_error... especially for new users" (opa#6393;
  `var _ is unsafe` baffled a user), "Safety check too strict in iteration edge case" (opa#5505), `some x
  in xs` shadowing semantics (opa#4202).
- Popularity: opa 12305 stars; regal 409 stars with 222 `.rego` files under bundle/regal/rules (106
  non-test: a linter whose rules are written in its own rule language); gatekeeper-library 704 stars;
  opa/library 105 stars; Stack Overflow tags `open-policy-agent` 270 and `rego` 176 questions.

### 2.8 Comby (comby-tools/comby, docs in comby-tools/comby.dev)

Simplest rule, a command line with no file:

```text
comby 'Array.prototype.slice.call(:[arguments]);' 'Array.from(:[arguments])'
```

With a condition (website/docs/configuration.md, TOML form):

```toml
[my-second-pattern]
match='''
function :[[fn]](:[1], :[2]) {
  :[body]
};'''
rewrite='''
function :[[fn]](:[2], :[1]) {
  :[body]
};'''
rule='where :[fn] != "divide"'
```

- Holes: `:[x]` lazy, `:[[x]]` word, `:[x~regex]`, `:[x:e]` expression-like, `:[x.]`, `:[x\n]`,
  `:[ x]`: seven hole forms plus `...` and `:[_]` anonymous variants (docs/syntax-reference.md
  table). There is no tree, only balanced delimiters.
- Negation: `!=` in a `where` rule; "Rewrite expressions always return true, even if they don't
  succeed in rewriting" (docs/advanced-usage.md), a condition that cannot fail.
- Containment, relational: none ("no builtin way to match indentation-sensitive Python blocks",
  FAQ comparing to Semgrep).
- Tests: I found no rule-test facility in the docs (grep for "test" in faq.md, get-help.md,
  configuration.md finds only unrelated hits); the repository's `test/` directory tests Comby itself.
- Errors: not measured. Complaints: none found beyond the project's own "What is Comby not good at?"
  FAQ entry (no help with formatting). 80 open issues, not read.
- Popularity: comby 2681 stars; Stack Overflow tag `comby` 2 questions; HN launch thread 196 points.

### 2.9 Coccinelle SmPL (coccinelle/coccinelle)

Simplest rule (demos/check_region.cocci):

```text
@@
expression e1, e2;
@@

- if(check_region(e1,e2)!=0)
+ if(!request_region(e1,e2))
  { ... return ...; }
  <...
+ release_region(e1);
  return ...;
  ...>
- request_region(e1,e2);
```

A report-mode rule with positions, negated position sets and dependencies (Linux
scripts/coccinelle/null/deref_null.cocci, abridged): `@r depends on !context && (org || report) exists@
... position p!={pr1.p1,pr2.p2}; position ifm.p1; @@ if@p1 ((E == NULL && ...) || ...) { ... when !=
if (...) S1 else S2 ( iter(subE,...) S4 | ... ) }`.

- Metavariables are declared in a header with a type (`expression`, `identifier`, `statement`,
  `position`, `iterator`); `...` is a control-flow path ellipsis with `when !=` and `when strict`
  side conditions; `<... ...>` is "zero or more times along the path".
- Negation: `when !=`, `!` in dependencies, position exclusions, disjunction `( ... | ... )`.
- Containment and relational: control-flow paths over C (temporal-logic engine); cross-file only
  via a rule inheriting metavariables from another rule and Python/OCaml scripts.
- Tests: `tests/*.cocci` with `.c` input and `.res` expected output (909 `.cocci` files at
  11b93adb65); the output is a patch, not a finding list.
- Errors: not measured. Known weaknesses cited: "Coccinelle language grammar description is
  incomplete" (coccinelle#181), "In-place parallelized run ... seems to be stuck after 17 hours"
  where the maintainer's answer is "add a timeout to your command line... `--timeout 60`" (#416),
  "spatch is very slow when tagging end of function body" (#415).
- Newcomer complaint, verbatim (HN 47101156, pm215): "I find its documentation totally
  incomprehensible for some reason. I've read through it multiple times, but I always end up having
  to find some preexisting script that does what I want, or else to blunder around trying different
  variations at random until something works".
- Popularity: 818 stars; the Linux kernel carries about 73 `.cocci` scripts under scripts/coccinelle
  (counted through the GitHub contents API: api 20, free 8, iterators 5, locks 4, misc 27, null 4,
  tests 4, hid 1); Stack Overflow tag `coccinelle` 21 questions.

### 2.10 ESLint `no-restricted-syntax` selectors (eslint/eslint)

Simplest rule: a config string, no rule file (docs/src/rules/no-restricted-syntax.md):

```json
"no-restricted-syntax": ["error",
  { "selector": "CallExpression[callee.name='setTimeout'][arguments.length!=2]",
    "message": "setTimeout must always be invoked with two arguments." } ]
```

- Selectors are esquery, CSS-like: `A B` descendant, `A > B` child, `[attr=value]`, `:not(...)`,
  `:has(...)`, regex attribute values, `:exit`. Specificity ordering like CSS (docs/src/extend/
  selectors.md).
- Negation: `:not()`. Containment: space (descendant) versus `>` (child), which is how CSS users
  already think, and it is transitive by default.
- Relational/cross-file: none; per-node plus ancestors. Escape hatch is full JS (`create(context)`).
- Tests: `RuleTester` with `valid:` and `invalid:` and `errors: [{message}]` (docs/src/integrate/
  nodejs-api.md line 865); it is used by the bundled rules.
- Errors (M, 9.39.5): an unbalanced selector prints `Oops! Something went wrong! :( ... SyntaxError:
  Syntax error in selector "...[arguments.length!=2" at position 60: Expected " ", ".", "]", or
  [0-9] but end of input found.` followed by a JS stack trace. M, silent: `CallExpresion` (typo in
  the node type) lints clean with exit 0.
- Complaints: `Can't escape / (forward slash) in no-restricted-syntax rule` (eslint#16555);
  regex inside a JSON string needs a doubled backslash (docs note).
- Popularity: eslint 27531 stars, 193 million npm downloads in the week to 2026-10-01; 294 files
  under lib/rules; 6776 npm packages with keyword `eslintplugin` and 7180 with `eslint-plugin`;
  Stack Overflow tag `eslint` 7001 questions.

### 2.11 Clippy handwritten lints (rust-lang/rust-clippy), for contrast

A complete small lint (clippy_lints/src/needless_else.rs, abridged): a `declare_clippy_lint!` doc
block (what it does, why bad, example, "use instead"), then

```rust
impl EarlyLintPass for NeedlessElse {
    fn check_expr(&mut self, cx: &EarlyContext<'_>, expr: &Expr) {
        if let ExprKind::If(_, then_block, Some(else_clause)) = &expr.kind
            && let ExprKind::Block(block, _) = &else_clause.kind
            && !expr.span.from_expansion()
            && block.stmts.is_empty()
            && ... {
            span_lint_and_sugg(cx, NEEDLESS_ELSE, ..., "this `else` branch is empty",
                "you can remove it", String::new(), Applicability::MachineApplicable);
        }
    }
}
```

- Everything is code: full negation, full relational power through rustc's HIR and type
  information; no termination guarantee beyond Rust's; a lint author must understand the compiler's
  data structures (the book has a "Print HIR lint" section; book/src/development/adding_lints.md).
- Tests: UI tests: a `.rs` with `//~^ lint_name` markers, a `.stderr` golden, an optional `.fixed`
  golden, regenerated with `cargo uibless`/`cargo bless`. Fix applicability is first-class
  (`MachineApplicable` and friends), which diagnostics.md section 3 copies.
- Popularity: rust-clippy 13551 stars; README: "over 800 lints" (M, README text).
- Contrast point: all the above is why GRL exists. Clippy is the right model for what the language
  can express at the high end and the wrong model for who can write a rule.

### 2.12 Oxlint JS plugins (oxc-project/oxc, docs and blog in oxc-project/website)

```js
const rule = {
  create(context) {
    return {
      DebuggerStatement(node) { context.report({ message: "No debugger!", node }); },
    };
  },
};
```

- (src/blog/2025-10-09-oxlint-js-plugins.md.) The project asked the community "Oxlint can run
  existing ESLint plugins without modification" versus "an API that diverges", chose both: an
  ESLint-compatible API plus an alternative faster one (oxc discussion 10342; blog). Selectors are
  supported; token APIs came later (alpha post 2026-03-11).
- Tests and errors: inherited from the ESLint model (RuleTester-compatible); not measured.
- Popularity: oxc 22934 stars; npm keyword `oxlint` 709 packages.
- Lesson carried: the compatibility target, not the elegance of the API, drove the ecosystem
  decision; there is no DSL.

### 2.13 Ruff: a deliberate absence of a rule language (astral-sh/ruff)

- docs/faq.md line 102: "Ruff's primary limitation vis-a-vis Flake8 is that it does not support
  custom lint rules. (Instead, popular Flake8 plugins are re-implemented in Rust as part of Ruff
  itself.)". About 900 built-in rules.
- Issue 283, "Meta issue: plugin system", opened 2022, 95 comments, still open on 2026-10-02. The
  reasoning visible in the thread: Rust-only plugins give "a more cohesive codebase, performance,
  and avoid extensive cross-language FFI" (charliermarsh 2022-09-29); two kinds of rule exist, "custom
  to a codebase" and "applies to many codebases but does not belong in Ruff", and "most of those
  custom checks could be built atop ast-grep, but more complex checks would be limited by that
  approach" (2022-11-08); an offer to integrate GritQL (morgante, 2024-02-21); "we are in the middle of
  rewriting Ruff's compiler infrastructure to support multifile analysis" so a plugin design waits
  (MichaReiser, 2024-05-28).
- Lessons: (1) the maintainers consider the DSL tier (ast-grep, GritQL) good enough for
  codebase-specific rules and not enough for cross-file rules, which is the same split GRL tries to
  close; (2) the demand never went away in four years; (3) an engine that wants multi-file analysis
  first needs the model (U) before the plugin surface.

### 2.14 PMD XPath rules (pmd/pmd)

A real XPath rule (pmd-java/src/main/resources/category/java/errorprone.xml, EmptyCatchBlock):

```xml
<rule name="EmptyCatchBlock" language="java" since="0.1" message="Avoid empty catch blocks"
      class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
  <properties>
    <property name="xpath"><value><![CDATA[
//CatchClause[
  Block[ count(*) = 0 and ($allowCommentedBlocks = false() or @containsComment = false()) ]
  and CatchParameter/VariableId[not(matches(@Name, $allowExceptionNameRegex))]
]
]]></value></property>
    <property name="allowCommentedBlocks" type="Boolean" value="false"/>
    <property name="allowExceptionNameRegex" type="Regex" value="^(ignored|expected)$"/>
  </properties>
</rule>
```

- Variables: none (XPath axes and predicates); metavariables: none, but named properties
  (`$allowCommentedBlocks`) are the configuration channel (a model for GRL `knob`).
- Negation: `not(...)`; containment: `//` descendant, `/` child, familiar to XPath users.
- Relational: single-file plus type predicates (`pmd-java:typeIsExactly('java.lang.Exception')`).
- Tests (pmd-java/src/test/resources/.../errorprone/xml/EmptyCatchBlock.xml): `<test-code>` with a
  `<description>`, `<expected-problems>N</expected-problems>` and a CDATA `<code>`; "simple failure"
  and "ok" cases are the convention. Tooling: the Rule Designer GUI evaluates XPath live against the
  AST (docs/pages/pmd/userdocs/extending/your_first_rule.md).
- Errors, complaints: not measured. The tutorial opens "We assume here that you already know what
  XPath is and how to read basic XPath queries" (a statement of the prerequisite, J as a complaint
  proxy).
- Popularity: pmd 5494 stars; 483 `<rule>` entries in category XML across languages, 214 of them
  XPath rules (44 percent; M, count of `XPathRule` class attributes); Stack Overflow tag `pmd` 873.

### 2.15 Checkstyle (checkstyle/checkstyle)

A rule is configuration plus, for anything new, a Java class: 240 `*Check.java` classes at
a26ee03621. The only generic "query" check carries a warning in its own Javadoc
(checks/DescendantTokenCheck.java): "This is a very powerful and flexible check, but, at the same
time, it is low-level and very implementation-dependent because its results depend on the grammar we
use to build abstract syntax trees. Thus, we recommend using other checks when they provide the
desired functionality."

Docs examples ARE the tests (src/xdocs-examples/resources/.../coding/illegaltoken/Example1.java):

```java
/*xml
<module name="Checker">
  <module name="TreeWalker">
    <module name="IllegalToken"/>
  </module>
</module>
*/
class Example1 {
  void anotherMethod() {
    outer: // violation 'Using 'outer:' is not allowed'
```

- Tests: inline `// violation 'message'` comments in input files (src/test/resources/.../
  emptystatement/InputEmptyStatement.java), config in the file header; docs generated from tested
  examples. Tooling: `checkstyle -t` prints the AST (`--tree`, `--treeWithComments`).
- Complaints: none found for rule authors; this is a catalogue tool, not a rule language.
- Popularity: checkstyle 9587 stars; google_checks.xml has 108 module entries; Stack Overflow tag
  `checkstyle` 1323 questions.

### 2.16 Error Prone Refaster templates (google/error-prone)

A template is Java code (core/src/test/java/com/google/errorprone/refaster/testdata/template/
BinaryTemplate.java):

```java
public class BinaryTemplate {
  @BeforeTemplate public int divide(int a, int b) { return (a + b) / 2; }
  @AfterTemplate  public int shift(int a, int b)  { return (a + b) >> 1; }
}
```

- Metavariables are typed method parameters (`a`, `b`); `@Repeated` for sequences, `@Matches`,
  `@NotMatches`, `@OfKind`, `@AlsoNegation` for constraints (annotation package listing). Negation
  and containment are limited to those annotations; relational: none.
- Tests: `testdata/input/BinaryTemplateExample.java` with comment-labelled positive and negative
  examples, and `testdata/output/` golden. The positive/negative labelling inside one file is the
  same idea as fire/clean.
- Errors: "RefasterRuleCompiler silently ignores compilation errors in refaster templates" (error-
  prone#1053, open); "Refaster template compilation instructions are out of date or unclear"
  (#4261); "Availability of Google's Refaster templates?" (#649, 13 comments: the authoring tool
  was public while the large internal corpus was not).
- Popularity: error-prone 7244 stars; docs/bugpattern has 429 pages (handwritten checks); 73 Java
  files reference `@BeforeTemplate`, almost all of them tests.
- Lesson: before/after-as-code is the most readable form in the survey (it is the Grit and
  ast-grep "paste the code" idea 10 years early), and silent compile failure is how it lost trust.

### 2.17 Extras found

- Glean Angle (facebookincubator/Glean, 1418 stars): a Datalog-based query language with a
  guide, a style guide, and two pages that matter here: `efficiency.md` ("The order of fields in the
  schema matters a lot for efficiency") and `debugging.md` ("Angle is a very declarative language.
  There are often many ways to write the query that are correct, but not all of them will be
  fast"). Intro query: `D.declaration.memberDecl?.name where D : flow.FileDeclaration; D.file =
  src.File "project/myfile.js"`. Lesson: declarative power without a planner hands the author a
  performance puzzle.
- Globstar (DeepSourceCorp/globstar, 501 stars, 84 checker YAMLs): YAML wrapping a raw tree-sitter
  query, tests as sibling files with `// <expect-error> message` comments (checkers/go/cgi_import.yml
  and cgi_import.test.go). Launch thread: "I loved writing Clippy lints and I think applying that
  'it's just code' with custom checks is a powerful idea. I worked on a static analysis product and
  the rules for that were horrible, I don't blame the customers for not really wanting to write
  them" (HN 43209675, etyp). Simplest rule needs tree-sitter node names.
- Regal (see 2.7): proof a lint tool can ship 106 rules in its own language, each with a sibling
  test file.

## 3. Popularity proxies, side by side (2026-10-02)

| System | Repo stars | Public rule corpus measured | Other proxy |
|---|---|---|---|
| ESLint (selectors and JS rules) | 27531 | 294 core rule files | 6776 npm `eslintplugin` pkgs; 193M downloads/week; SO 7001 |
| Semgrep | 16843 | 2234 rules (semgrep-rules, 269 taint) | semgrep-rules 1262 stars; opengrep 3133; SO 37 |
| ast-grep | 16105 | 63 catalog pages | HN 292 pts; SO 15 |
| CodeQL | 10158 | 2617 queries, 5687 library files | 2064 test refs; SO 90 |
| Clippy | 13551 | over 800 lints (README) | handwritten Rust |
| Ruff | 49881 | about 900 built-in rules | no rule language |
| OPA/Rego | 12305 | Regal 106 rules; gatekeeper-library 704 stars | SO 270 + 176 |
| tree-sitter queries | 27110 | no lint corpus (highlight queries) | nvim-treesitter 14434 stars |
| Biome (GritQL plugins) | 25887 | 20 npm `biome-plugin` pkgs | issues cited in 2.1 |
| GritQL | 4601 | 212 stdlib patterns (stdlib 109 stars) | HN 280 pts |
| Oxlint (JS plugins) | 22934 | 709 npm `oxlint` pkgs | ESLint-compatible |
| PMD | 5494 | 483 rules, 214 XPath | SO 873 |
| Checkstyle | 9587 | 240 check classes | SO 1323 |
| Error Prone | 7244 | 429 bug-pattern pages | Refaster corpus not public |
| Comby | 2681 | none found | SO 2 |
| Coccinelle | 818 | about 73 kernel scripts | SO 21 |
| Souffle | 1180 | no registry (632 test programs) | SO none |
| Glean Angle | 1418 | schemas, not rules | |
| Globstar | 501 | 84 checkers | |

Reading it honestly: popularity follows the host ecosystem (ESLint, Semgrep's registry and security
market, CodeQL's GitHub integration), not the elegance of the language. The one clean inference is
negative: tools with no public rule corpus after years (Comby, Souffle for linting, Refaster outside
Google, Biome plugins at 20 packages) are the ones where the author must start from nothing.

## 4. Comparison tables

Scale 1 (poor) to 5 (best) for how well the tool does it for a first-time rule author or for
frob's needs; `n/a` where the tool has no such notion; `n/m` where I could not measure or find
evidence. Basis tags: M measured here, D documented in the cited source, J judgment. The "GRL needs"
column is the bar from section 1.

Table A: pattern-oriented tools.

| Criterion | GRL needs | Grit/Biome | Semgrep | ast-grep | Comby | Coccinelle | ESLint selectors | tree-sitter query |
|---|---|---|---|---|---|---|---|---|
| 1 time to first rule | minutes | 4 (J) | 5 (M 1.4 s) | 5 (M 5 ms one-liner) | 5 (D) | 2 (J, HN) | 4 (D) | 3 (J) |
| 2 readability to a non-author | high | 4 (J) | 4 simple, 3 combined (J) | 3 (nested YAML, J) | 4 (J) | 3 (J) | 3 (J) | 2 (J) |
| 3 relational or cross-file | yes, polynomial | 2 (D file-local) | 4 (D taint, join) | 1 (D) | 1 (D) | 3 (D paths) | 1 (D) | 1 (D) |
| 4 negation clarity | high | 3 (D) | 2 (D, M issues 8428/3967) | 3 (M positive-anchor rule) | 2 (D) | 3 (D) | 3 (D) | 2 (D) |
| 5 metavariable and ellipsis clarity | high | 4 (D) | 3 (D limitations) | 4 (D) | 2 (7 hole forms, D) | 3 (D) | n/a | 3 (D) |
| 6 containment clarity | high | 4 (D) | 4 (D) | 2 (M shallow default) | 1 (D) | 3 (D) | 4 (D) | 2 (M, #880) |
| 7 testability (shipped fire/clean) | mandatory | 4 (D) / Biome 1 (D) | 5 (D) | 4 (D, M snapshot friction) | 1 (D) | 3 (D golden patches) | 5 (D) | 2 (D highlight only) |
| 8 own-error quality | spans and fixes | Biome 1 (M) | 3 (M) | 3 (M) | n/m | n/m | 2 (M) | 4 (M) |
| 9 silent-wrong-match risk | none | 1 (M typo) | 3 (D) | 2 (M stopBy) | 2 (J) | 3 (J) | 1 (M typo) | 1 (M predicate) |
| 10 termination and cost guarantee | stated | 2 (D #6210) | 3 (D) | 4 (D) | 4 (J) | 1 (D #416) | 3 (J) | 4 (D match limit API) |
| 11 fix and rewrite | with applicability | 5 (D) | 4 (D) | 4 (D) | 5 (D) | 5 (D) | 2 (D) | 1 (D) |
| 12 tooling (playground, explain) | yes | 4 (D) | 5 (D) | 5 (D) | 4 (D) | 2 (J) | 5 (D) | 4 (D) |

Table B: relational, code and DSL-less tools.

| Criterion | GRL needs | CodeQL | Souffle | Rego | PMD XPath | Checkstyle | Clippy | Refaster | Oxlint JS | Ruff |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 time to first rule | minutes | 2 (J) | 3 (J fact extractor) | 4 (M) | 3 (D designer) | 4 config, 1 new check (D) | 1 (D) | 3 (D) | 4 (D) | n/a |
| 2 readability to a non-author | high | 3 (J) | 4 (J) | 3 (J) | 2 (D) | 5 config (J) | 2 (J) | 5 (D) | 4 (J) | n/a |
| 3 relational or cross-file | yes, polynomial | 5 (D) | 5 (D) | 4 (D over JSON) | 2 (D) | 1 (D) | 5 (D) | 1 (D) | 3 (J) | n/a |
| 4 negation clarity | high | 3 (D #14974) | 3 (D) | 2 (M undefined) | 4 (D) | n/a | 5 (code) | 3 (D annotations) | 5 (code) | n/a |
| 5 testability | mandatory | 4 (D) | 4 (D goldens) | 5 (M) | 5 (D) | 5 (D inline) | 5 (D) | 3 (D) | 4 (J) | n/a |
| 6 own-error quality | spans and fixes | 3 (D) | 4 (D caret goldens) | 3 (M row only) | n/m | n/a | 5 (rustc) | 1 (D #1053) | n/m | n/a |
| 7 silent-wrong-match risk | none | 3 (D) | 3 (D) | 1 (M field typo) | 3 (J) | 4 (J) | 4 (J) | 1 (D) | 2 (J) | n/a |
| 8 termination and cost guarantee | stated | 4 (D monotonic) | 4 (J finite domain) | 4 (D recursion error) | 4 (J) | 4 (J) | 2 (J) | 4 (J) | 2 (J budgets) | n/a |
| 9 tooling | yes | 4 (J) | 3 (D provenance) | 5 (D) | 5 (D) | 3 (D `-t`) | 3 (D print-hir) | 2 (D) | 3 (J) | n/a |
| 10 fix and rewrite | with applicability | 2 (D) | 1 | 1 | 1 | 1 | 5 (D) | 5 (D) | 4 (J) | n/a |
| 11 who can write a rule | anyone | analysts | researchers | policy authors | Java devs | Java devs | compiler-literate | Java devs | JS devs | maintainers only |
| 12 evidence of rule-writing demand | n/a | 2617 queries (D) | 632 tests (D) | Regal 106 (D) | 214 XPath rules (M) | 240 checks (D) | 800+ lints (D) | corpus private | 709 pkgs (M) | issue 283: 95 comments, open since 2022 (D) |

Basis notes for non-obvious cells. Semgrep negation 2: two maintainers call it confusing and one
proposes removal (D, issues 8428, 3967). ast-grep silent-wrong-match 2: the shallow default produced
zero findings and exit 0 on the natural rule (M). Grit/Biome typo cell 1: both typo cases printed
nothing, or an unlocated "Failed to compile" (M). ESLint typo cell 1: unknown node type lints clean
(M). tree-sitter predicate cell 1: unknown predicate accepted and ignored (M). Rego field typo 1:
undefined, `--strict` silent (M).

What the tables say in one paragraph: no surveyed tool scores well on both "time to first rule" and
"relational expressiveness"; the pattern tools win minute-one and stop at one file (Semgrep's join
mode and taint mode are the exceptions, both gated), the Datalog tools win relations and lose minute-
one. Nobody scores well on "silent wrong match": that column is empty at the top, which is the opening
for a three-valued language with compile-time name checking.

## 5. How the survey maps onto what GRL has to be

| GRL requirement | Closest prior art | What it got right | What it got wrong |
|---|---|---|---|
| paste code, get a rule | Grit, ast-grep, Semgrep, Comby, Refaster | one-line rules, rewrite as before/after | fragments that do not parse (ast-grep FAQ, Semgrep partial expressions) |
| relations over a model | CodeQL, Souffle, Rego, Glean | joins, closure, counting | steep first hour; planner-dependent speed (Angle docs); jargon errors |
| three-valued honesty | none | Rego has undefined but conflates it with false | every pattern tool turns "could not decide" into "no match" |
| tests inside the rule | Semgrep, Checkstyle, PMD, Clippy, Rego | inline annotations, doc examples as tests | Biome plugins, Comby have none; ast-grep needs snapshot files |
| errors that teach | rustc, Souffle goldens, ast-grep Help lines | caret, did-you-mean, stable codes, goldens for compile errors | Biome "Failed to compile", Semgrep whole-rule span, ESLint stack trace |
| termination | Datalog family, Rego recursion error | polynomial by construction | Grit top-level `contains` (O(n^2)), Coccinelle 17 hours |

## 6. Design lessons for GRL, each with its evidence

L1. Make "paste the code you want to catch" the first minute, and keep the first rule to three
lines. Evidence: ast-grep one-liner 5 ms and Semgrep one-liner 1.4 s (M); Comby and Grit one-liners (D);
Refaster's before/after-as-Java (D); Globstar's etyp quote that rules written as code beat rules
that were "horrible" (HN 43209675); Semgrep's growing combinator list is what newcomers trip on
(issues 8428, 3967). So GRL's smallest rule is `find` plus `report`; relations are added only when
needed (progressive disclosure, as ESLint goes from a one-line selector config to a rule file).

L2. Resolve every name at compile time against the U schema and the rule's own side-relation
schemas, and make an unresolved name a hard error with a did-you-mean. Evidence (all M): a typo'd
function (Biome) printed no reason; a typo'd snippet and metavariable gave zero findings; a typo'd
ESLint node type linted clean; a typo'd Rego field was undefined and `--strict` was silent; a typo'd
tree-sitter predicate was silently accepted; Semgrep and ast-grep did catch unknown YAML keys but
neither points at the typo (Semgrep underlined the whole rule). This is the single biggest
differentiator GRL can have, because frob's contract is "never silently clean".

L3. Containment and ordering words must mean the thing a reader assumes: `inside` is any ancestor,
`has` is any descendant, and "immediate" is the marked form (`directly`). Evidence: ast-grep's
shallow default produced zero findings on the natural rule (M) and needs `stopBy: end`, which is in
the docs only as the third paragraph; tree-sitter has no descendant operator and a nested `print`
returned 0 matches (M, issue 880); Semgrep `pattern-inside`, ESLint descendant selectors, PMD `//`
and Grit `within` are transitive by default and draw no such complaints.

L4. One negation, scoped to a binding, over a positive anchor, with the unbound-variable rule
explained in the error. Evidence: Semgrep `pattern-not` exact-match versus intersect (issue 8428),
"matches everything" (3967), maintainers floating removal and a boolean syntax, now shipping as
experimental `not`/`all`/`any`; ast-grep demands a positive matcher and says so (M); Grit's
unanchored `contains` was an O(n^2) plugin (biome#6210); CodeQL `not exists` unbound errors
(codeql#14974), Souffle ungrounded and unstratifiable (souffle#2266, #1862), Rego "one of the most
common errors reported" (rego unsafe var). GRL: `no x: ...` and `not` are legal only when every free
variable is bound by a positive clause, and the error says which clause to add.

L5. Keep three values visible in the surface, not just in the engine. Evidence: no surveyed tool
distinguishes "no match" from "could not decide"; Biome's grammar holes (issue 7363, "can't match
interfaces") and the HN complaint about missing name resolution (39770908) are the same failure:
the rule author sees silence. Rego's `undefined` is the nearest relative and it is a trap (field
typo, M). GRL: polarity is declared, `reaches` and `owner` pick Must or May edges from the
polarity table without the author choosing, `unresolved when ... because "..."` is available for
author-defined doubt, and `example unresolved` is a test form.

L6. Ship the test in the rule file and make it mandatory: at least one `fire` and one `clean`
example, plus `unresolved` and `other-language` examples for universal rules. Evidence: Semgrep's
`ruleid`/`ok`, Checkstyle's `// violation`, PMD's `expected-problems`, Clippy's `//~`, Rego's `test_`
rules, Regal's sibling test per rule, ast-grep's four-quadrant vocabulary (Validated, Noisy,
Reported, Missing); Biome plugins and Comby have none and no rule corpus; ast-grep's required
snapshot files are friction (M `[Wrong] No baseline found`). frob's existing `// error: ID` corpus
format and the "a rule whose doc example has no non-firing case does not compile" doctrine
(rules.md section 2) already match the best of these. Add Semgrep's `todoruleid` as `known-gap`.

L7. Test the compile errors too. Evidence: Souffle's `.err` goldens (632 `.dl` test programs, golden
messages for "Unable to stratify" and "Ungrounded variable"), Clippy's `.stderr` goldens, CodeQL
`.expected`. The error catalogue of GRL (GRL001...) gets one golden per code, so the "teaches like
rustc" promise (diagnostics.md) cannot rot.

L8. Give the author a way to see why a rule did not match. Evidence: ast-grep's first FAQ answer is
"use the playground" and `--debug-query`; PMD's Rule Designer; Souffle `--provenance=explain`; Glean
profiling; the CLI-versus-playground divergence in ast-grep's FAQ shows a playground that disagrees
with the CLI is worse than none. GRL: `frob rule why RULE path:line` prints, per clause, how many
candidates passed and where the first one failed; the same engine as `check`, never a second
implementation.

L9. Do not host the language in YAML, JSON or XML. Evidence: Semgrep's YAML colon failure on a
Python `def` pattern (M), the experimental-syntax page's own warning, ESLint's selectors inside JSON
needing doubled backslashes and no `/` (eslint#16555), PMD's XPath inside CDATA, Comby's TOML-quoting
note. Biome and Grit chose a dedicated `.grit` syntax with raw backtick snippets and had the better
docs-to-first-rule path. GRL uses its own file syntax with raw snippet and example blocks that need
no escaping except `$`.

L10. Bind variables once, say so, and scope the exceptions explicitly. Evidence: Grit's `bubble`
(without it the second `console.log` silently fails to match because `$message` is already bound,
language/bubble.mdoc); Semgrep metavariable unification across `pattern` and `pattern-inside`
(issue 4583); ast-grep's "rule order matters, only the first rule can specify what `$META_VAR`
matches" FAQ. GRL: a name is bound by exactly one positive clause; later uses are equality tests;
`some x` and `no x` open a fresh scope; the compiler warns about a name bound and never used and the
`why` output shows each binding.

L11. Let the planner order the work and print the cost class. Evidence: Glean's "many ways correct
but not all fast" (efficiency.md and debugging.md), Grit's O(n^2) top-level `contains`
(biome#6210), Coccinelle running 17 hours (#416) with a user-side `--timeout` as the maintainers'
only advice. GRL: no user recursion, closures take `within N`, joins are ordered by the planner,
`frob rule check` prints the cost class (per-file, per-repo, closure bound) and the prefilter set
(plugins.md 6.2), and a budget overrun is Unresolved with reason `budget` (plugins.md 6.5).

L12. Make the standard library the tutorial and keep it in the same language. Evidence: Regal ships
106 lint rules in Rego; ESLint's own `no-debugger` is the plugin example; Semgrep's 2234 rules and
CodeQL's 2617 queries are how users learn; the ESLint plugin count (6776) comes from authors copying
core rules. plugins.md already requires std rules to be GRL (section 4); this adds that each std
rule page shows its GRL source as the first code block.

L13. Treat compatibility with a familiar surface as an ecosystem lever, but not at the cost of the
guarantees. Evidence: Oxlint chose an ESLint-compatible API (npm keyword counts, a weak proxy: 709 for `oxlint`
versus 20 for `biome-plugin`, and 6776 for `eslintplugin` which Oxlint can reuse); Ruff's maintainers keep asking for
ast-grep or GritQL as the tier below Rust (issue 283). GRL's patterns reuse the metavariable names
`$X`, `$$$XS`, `$_` and the combinator names `inside`, `has`, `not`, `any` that ast-grep, Semgrep and
rules.md already share.

L14. Fix templates carry applicability in the language. Evidence: Clippy `Applicability`, Biome
`fix_kind = "safe"` and "unsafe by default", Semgrep `fix` plus `.fixed` tests, ast-grep `fix`,
Grit `=>`. diagnostics.md 3 has the four levels; GRL's `fix` clause takes one of them and an
example may assert the fixed output.

L15. Knobs are named, typed and documented where the rule is, never invisible. Evidence: PMD's
`<property name="allowExceptionNameRegex" type="Regex" value="...">` inside the XPath rule; Semgrep
metadata; ESLint `schema`. Matches CLAUDE.md's "no invisible variables".

## 7. Pitfalls to avoid, with evidence

P1. Typo becomes "no match" (Biome, ESLint, OPA, tree-sitter; all M). Counter: L2.
P2. Shallow containment default (ast-grep M; tree-sitter M). Counter: L3.
P3. Negation that means "exactly equal" in one operator and "intersects" in another (Semgrep issue
8428). Counter: one `not`, defined by set semantics, documented with a truth table.
P4. Patterns that are not parseable fragments (ast-grep FAQ: `"key": "$VAL"` is not valid JSON;
Semgrep "partial expressions are not valid patterns"; `foo` matches statements but not `import foo`).
Counter: `as KIND` hint and a compile-time "this snippet parsed as X; its tree is Y" message.
P5. YAML or JSON or XML as host (Semgrep colon M; ESLint `/` escape; PMD CDATA). Counter: L9.
P6. Silent rebinding or non-sharing of metavariables (Grit bubble, Semgrep 4583, ast-grep rule
order). Counter: L10.
P7. Author-ordered evaluation (Glean docs; Grit `contains` from the root; Coccinelle). Counter: L11.
P8. A compile error with no location or reason (Biome "Failed to compile the Grit plugin" M; ESLint
"Oops!" plus stack trace M; Semgrep whole-rule span M). Counter: spans, codes, help, goldens (L7).
P9. Dependence on a concrete grammar for rules that should be universal: grammar bumps changed
results (ast-grep#2867), CLI and playground parsers differ (ast-grep FAQ), Biome cannot match
`interface` or `type` because of holes in the mapping (biome#7363), Python import order changes
matches (semgrep#353). Counter: pin grammar versions in the pack lock (plugins.md 8), keep
universal rules on U roles, and report adapter holes as Unresolved, never clean.
P10. `undefined` conflated with false (Rego M). Counter: L5.
P11. Exposing the evaluation theory in errors: "Unable to stratify" and "not bound to a value"
(Souffle, CodeQL) force users to learn Datalog. GRL has no user recursion so stratification holds by
construction; the binding rule is explained in the user's terms ("`d` is only used inside `no`; add
a `find d:` clause that says where `d` comes from").
P12. A second language by accretion: Semgrep has patterns, taint mode, join mode, a deprecated
syntax and an experimental syntax; ast-grep has patterns, kinds, relational rules, `constraints`,
`transform`, utility rules; Checkstyle documents that its generic check is "low-level and very
implementation-dependent". Counter: the 20-construct budget in section 8 and a rule that anything
new must be expressed in existing constructs first (CLAUDE.md "no duplication").
P13. Tests that need machine-generated baselines (ast-grep `[Wrong] No baseline found`, Souffle
`.out`, Clippy `.stderr`) as the only form. Counter: inline expectation comments are the default;
goldens only for fix output and for compile errors.
P14. Docs that assume the prerequisite (PMD "we assume you know XPath"; Coccinelle docs
"incomprehensible", HN 47101156; Rego "can you spot the unsafe variable?" page). Counter: every
construct has an example that is a test (Checkstyle's xdocs-examples are the model), and the first
page is the three-line rule.
P15. Rule engines whose power outruns the author's mental model: CodeQL (ChatGPT cannot write a
simple query, HN 43055733), Coccinelle (random trial and error, HN 47101156). Counter: GRL's
hybrid is a conjunction of positive clauses with named relations; recursion and aggregates are not
in the surface.

## 8. A minimal GRL surface (sketch, not a spec)

Goals: a rule reads like the code it matches; relations read like English prepositions and verbs;
every name is checked; polarity, bounds and three-valued answers are framework business. Syntax
choices below are proposals for grl-spec.md; they differ from the plugins.md section 4 sketch
(`for u: unit(...) where ... find ... report`) mainly by putting a pasted snippet in the same
`find` slot as a unit kind.

### 8.1 The 20 constructs

| # | Construct | Reads as | Maps to | Borrowed from |
|---|---|---|---|---|
| 1 | `rule ID "slug" { ... }` with header keys `lang`, `polarity`, `severity`, `scope`, `must_measure` | the declaration | RuleMeta (rules.md 2) | frob derive, Semgrep metadata |
| 2 | backtick snippet, optional language tag and `as KIND`: `` `print($$$ARGS)` ``, `` rust`$X.unwrap()` as expr `` | "code that looks like this" | gob-pattern, Q44 | Grit, ast-grep, Semgrep |
| 3 | metavariables `$X` (one node), `$$$XS` (a sequence), `$_` and `$$$` (anonymous); in-snippet `...` | the holes | pattern binding | ast-grep |
| 4 | `find x: SHAPE` (a kind such as `function`, `call`, `comment`, `import`, `link`, `key`; or a snippet; or `(a \| b)`) | "find every x that is a ..." | U unit, apply, group roles; Q04, Q12, Q13 | CodeQL `from`, XPath step |
| 5 | `where COND` (comparison, `~ /re/`, `in SET`, `is KIND`, `and`, `or`) | extra conditions | constraints | Semgrep metavariable-*, Comby `where` |
| 6 | `not COND` and `any { ... }` (conjunction is the default) | negation and alternation | Kleene connectives (universal-model.md 4.1) | ast-grep, Semgrep experimental |
| 7 | `some y: SHAPE REL...` and `no y: SHAPE REL...` | exists and absence, fresh scope | existential or negated join | Rego `some`, CodeQL `exists` |
| 8 | containment: `inside`, `has` (transitive), `directly inside`, `directly has` | ancestor and descendant | Q27 contains, ancestors | ast-grep with default fixed, ESLint space versus `>` |
| 9 | sibling order: `before`, `after` (and `adjacent to`) | what follows what | location order (2.5), Q05 | ast-grep `follows`, `precedes` |
| 10 | edge verbs: `calls`, `imports`, `references`, `instantiates`, `extends`, `owned by`, `resolves to` | who points at whom | Q20, Q28, Q29, Q36 with Must/May status | CodeQL member predicates |
| 11 | bounded closure: `a reaches b via calls within N` | transitive reachability | Q30 closure, Pc polarity | Datalog, with the bound explicit |
| 12 | `count(y: SHAPE REL...) OP n` and arithmetic on counts | thresholds | Pn polarity | CodeQL aggregates, restricted here to counts |
| 13 | field and attribute access: `x.name`, `x.text`, `x.line`, `x has attr "k"`, `x is public` | properties | attributes (2.2 item 5), Q06-Q09 | XPath attributes |
| 14 | side relations with typed schemas: `row: config "invariants.forbid_imports"`, `p: path in diff.changed`, `lease.globs` | tables outside U | rule `needs` side inputs (universal-model.md 5 notes) | PMD properties, Rego `data` |
| 15 | `def name(args) = COND` | a named, non-recursive predicate | inlined at compile time | CodeQL predicate, Rego function |
| 16 | `knob name = default` | a documented, typed configuration value | `[rules.ID]` table (plugins.md 5 `config_tables`) | PMD property |
| 17 | `report x "text {..}" [when COND] [rollup LEVEL]` and `note y "text"` | the message and secondary spans | Finding with spans (diagnostics.md 2) | rustc, ESLint messages |
| 18 | `fix x -> `snippet` [applicability]` | the rewrite | Fix with applicability (diagnostics.md 3) | Grit `=>`, Clippy |
| 19 | `example fire\|clean\|unresolved\|other-lang LANG """ code """` with `//~ error` markers; `example error """ rule source """` expecting a compile error code | the test | mdtest corpus (rules.md 2), Souffle `.err` | Semgrep, Checkstyle, Clippy |
| 20 | `explain """ ... ## Remedy ... """` and `unresolved when COND because "reason"` | the page and author-defined doubt | `explain` (diagnostics.md 6), Unresolved reasons | rustc `--explain` |

Rules of the surface (these are the guarantees, stated once):
- A rule is a conjunction of clauses; clause order is irrelevant; the planner orders the work.
- Every identifier (kind, field, attribute, edge, vocabulary, side-relation column, knob) is
  checked against the U schema and the declared `needs`; unknown is a compile error with
  did-you-mean (L2).
- A variable is bound by exactly one positive clause (`find`, or a side-relation row); `not`,
  `no`, `unresolved when` may use variables but never bind them (L4).
- `reaches`, `owned by`, `resolves to` use the lo or hi edge set automatically from the polarity
  table; `certainly` and `possibly` are explicit overrides (rarely needed).
- Expectation markers in examples are a comment-introducer followed by `~` and a severity
  (Clippy's `//~`); the marker comment is not a subject of the rule under test.
- A snippet in a universal rule is an error (plan compiler, plugins.md 4); universal rules use
  kinds and role attributes (`branch`, `loop`, `call`, `assignment`) instead.

### 8.2 A grammar fragment (informal)

```text
rule      := "rule" ID STRING "{" header* clause* example* explain? "}"
header    := "lang" (NAME | "*" | "-" | list) | "polarity" P | "severity" S
           | "scope" ("file" | "repo") | "must_measure" | "needs" list | knob
knob      := "knob" NAME "=" literal
clause    := find | "where" cond | quant | def | report | note | fix | unresolved
find      := "find" NAME ":" shape rel*
shape     := KIND ["(" filter ")"] | SNIPPET ["as" KIND] | "(" shape ("|" shape)+ ")"
rel       := ["directly"] ("inside" | "has") term | ("before" | "after") term
           | VERB term | "reaches" term "via" kinds "within" INT | "in" term
quant     := ("some" | "no") NAME ":" shape rel* ["where" cond]
cond      := atom | "not" cond | cond ("and" | "or") cond | "any" "{" cond* "}"
atom      := term CMP term | term "~" REGEX | term "in" set | term "is" KIND
           | term "has" "attr" STRING | count CMP term | NAME "(" args ")"
report    := "report" NAME STRING ["when" cond] ["rollup" LEVEL]
fix       := "fix" NAME "->" SNIPPET ["[" APPLICABILITY "]"]
example   := "example" KIND [NAME] TRIPLE_QUOTED
```

### 8.3 Extra rules (not in the required ten) that show the pattern half

R0. The existing GPOL001 from rules.md, pattern only, with fix and tests:

```grl
rule GPOL001 "no-print-in-lib" {
  lang python
  severity warn

  find p: `print($$$ARGS)`
  where not p inside `@cli def $_($$$): $$$`
  report p "use the module logger, not print"
  fix p -> `_log.info($$$ARGS)` [maybe-incorrect]

  example fire python """
    print("x")                 #~ warn
  """
  example clean python """
    @cli
    def main():
        print("x")
  """
}
```

Awkward: the original is `not = { inside = { kind = "decorated_definition", has = { pattern = "@cli" } } }`;
the pasted form `@cli def $_($$$): $$$` is shorter and readable but its parse as a decorated
definition must be shown to the author (P4), and `maybe-incorrect` is right because `_log` may not
exist in the file.

R0b. A hybrid: a pasted pattern joined to a graph relation (the thing no surveyed pattern tool does
and no surveyed Datalog tool lets a newcomer write):

```grl
rule GPOL002 "print-reachable-from-public-api" {
  lang python
  polarity P+  severity warn
  knob depth = 6

  find p: `print($$$ARGS)`
  find api: function where api is public
  where api reaches p.unit via calls within knob.depth
  not p inside `if __name__ == "__main__": $$$`
  report p "print is reachable from public API {api.name}"
  note api "entry point"
}
```

Awkward: `p.unit` (nearest enclosing unit of a snippet hit) is needed to connect a pattern hit to the
graph; without it the author must write `p inside u` and risk the shallow/outer-unit problem (L3).

### 8.4 The ten required rewrites

Each rule below was written against its current implementation or description: TODO001, DOC002,
COV001, INV002, SCOPE001 from docs/reference/rules/*.md; SYS001 from docs/design/binding.md 6.1;
CAP001 from binding.md 7.2; NEAT013 and NEAT031 from docs/design/neatness.md (and the NEAT013
sketch in plugins.md section 4); CI002 from docs/design/cicd.md. Where a rule needs a relation the
design set names but does not yet specify (a typed schema for a side relation, a location
relation), I say so in "awkward".

#### Rule 1: TODO001 bare-work-marker

```grl
rule TODO001 "bare-work-marker" {
  lang *                                   # reads comments only: every language with comments
  polarity P+  severity error
  knob markers = ["TODO", "FIXME", "XXX", "HACK"]       # upper-case words only

  find c: comment
  find m: word in c.text where m in knob.markers
  where not c.text ~ /{m}\([0-9A-Z]{26}\)/              # TODO(<ulid>): owned inline
  no d: directive "todo" where d.line in (c.line - 1)..c.line     # frob:todo on this or the previous line
  report m "bare {m} marker: file a ticket, then add `frob:todo <ulid>`"

  example fire rust """
    /* TODO tidy this */           //~ error
    fn a() {}
  """
  example clean rust """
    /* frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2 tidy */
    /* TODO tidy this */
    fn a() {}
  """
  example clean rust """
    // todo is fine in lowercase
    fn a() -> &'static str { "TODO inside a string" }
  """
  example clean markdown """
    ```text
    TODO this is code
    ```
  """
}
```

Awkward: (1) "same or previous line" is line arithmetic; a named relation `d adjoins c` from the
location order (universal-model.md 2.5) would read better and survive non-line addresses.
(2) the owner check is two different mechanisms (an inline ULID in the comment, a directive
elsewhere); they are joined by `not` and `no`, which is correct but the first is a text test and the
second a join, so a newcomer must learn both spellings of "absent". (3) the fenced-block and string
exclusions come from U (code is not a comment); the example documents that rather than the rule
saying it. (4) `{m}` inside a regex is string interpolation into a pattern, a quoting hazard;
a `word in` relation avoids most of it.

#### Rule 2: DOC002 broken-markdown-link

```grl
rule DOC002 "broken-markdown-link" {
  lang markdown
  polarity P+  severity error

  find l: link where l.target.is_relative          # http(s) and mailto are not relative
  def dest = resolve(l.target.path, from l.file)  # a leading / means the repository root

  report l "link target {l.target.path} does not exist"
    when no f: path where f == dest
  report l "no heading #{l.target.anchor} in {dest}"
    when some f: file where f.path == dest and f is markdown and exists l.target.anchor
         and no h: heading inside f where h.slug == l.target.anchor

  example fire markdown """
    See [gone](missing.md).        <!--~ error -->
  """
  example clean markdown """
    See [home](https://example.com/x) and `[code](nope.md)`.
  """
}
```

Awkward: (1) two failure modes with two messages forced two `report ... when` clauses, so the rule
is really two rules sharing a `find`; if the design wants one finding per link the two clauses
must be exclusive and the spec must say so. (2) `resolve`, `slug` and `is_relative` are built-in
functions of the markdown adapter; they need typed signatures in a standard-relations catalog, not
ad-hoc names. (3) the file system is a side relation (`path`), not U; `no f: path where f == dest`
is the only spelling of "the file does not exist" and reads oddly. (4) three-valued behaviour is
free and good here: if the target file failed to parse, `no h: heading inside f` is Unknown and the
finding is Unresolved, which is the doc's own "clean" claim made honest without author code.

#### Rule 3: COV001 untested-public-function

```grl
rule COV001 "untested-public-function" {
  lang *
  polarity P-  severity warn  scope repo  must_measure
  knob depth = 12

  find f: function where f is public and not f.is_trait_impl_member and not f in test_file
  no t: test where t reaches f via calls within knob.depth
                or t tests f                     # a frob:tests directive pairs them
  report f "public {f.kind} `{f.name}` has no test that reaches it"

  example fire rust """
    /// Doubles.
    pub fn double(x: i32) -> i32 { x * 2 }       //~ warn
  """
  example clean rust """
    pub fn double(x: i32) -> i32 { x * 2 }
    #[cfg(test)] mod tests { use super::*; #[test] fn d() { assert_eq!(double(2), 4); } }
  """
  example unresolved python """
    def helper(cb): cb()         # a May call edge: the test might reach it
    def run(): helper(len)
  """
}
```

Awkward: (1) the interesting semantics (P-: May edges count as "might be reached" so the rule
does not fire; Must edges are needed to certify) are invisible in the text, which is the point,
but a newcomer reading `reaches` cannot see it; `frob rule why` must print "used hi edges because
polarity P-". (2) the unique-name call scan fallback in frob-tests is a detector concern, not
something GRL can or should express; the rule consumes `test` and `tests` from Q35 and the
directive. (3) `within knob.depth` is a bound the old rule did not have; picking 12 is a design
choice the spec must justify (or default to the graph diameter bound). (4) "trait-impl members
and items in test files are not checked" are two negative filters in the `find`; fine, but they are
adapter vocabulary (`is_trait_impl_member`) that must exist as a typed field.

#### Rule 4: INV002 forbidden-import

```grl
rule INV002 "forbidden-import" {
  lang *
  polarity P+  severity error  scope repo

  row: config "invariants.forbid_imports"                 # columns: from, to, reason
  find i: import where i.file ~ glob(row.from) and i.path starts_with row.to
  report i "{i.file} imports {i.path}: {row.reason}"
  unresolved when row.from is not a valid glob because "bad glob in [invariants]"

  example fire python """
    # config: forbid_imports = [{ from = "src/core/**", to = "requests", reason = "no network in core" }]
    # file: src/core/a.py
    import requests                #~ error
  """
  example clean python """
    # file: src/web/a.py
    import requests
  """
}
```

Awkward: (1) the first line is a side relation with a typed schema; GRL cannot know the columns
unless the config schema (docs/schemas/config.json) feeds the compiler, otherwise `row.frm` is the
P1 silent typo. Requirement: side relations are typed from the config JSON schema. (2) `starts_with`
on an import path should compare path segments, not characters (`requests` versus `requests_mock`);
a typed `Path` value with `under` would avoid the bug the string version invites. (3) the example
needs to set config and file name, so the test format needs `# config:` and `# file:` header lines
(or sub-blocks) beyond a code block. (4) the "an entry whose glob does not compile is reported as an
unresolved finding" case is an explicit `unresolved when`, the one place author-defined doubt is
needed.

#### Rule 5: SCOPE001 path-outside-lease

```grl
rule SCOPE001 "path-outside-lease" {
  lang -                                   # no U unit is involved: side relations only
  polarity P+  severity error  scope repo
  needs diff, lease

  find p: path in diff.changed
  where not p ~ glob any lease.globs and not p ~ glob any config "lease.shared_files"
  report p "{p} is outside the scope lease of {lease.ticket}"
  fix manual "widen the lease (`frob lease widen`) or move the change to a ticket that owns the path"

  example fire """
    # lease: crates/a/**
    # diff: crates/b/src/lib.rs      #~ error
  """
  example clean """
    # lease: crates/a/**    shared_files: Cargo.lock
    # diff: Cargo.lock
  """
}
```

Awkward: (1) this is not a structural rule at all, so `lang -` and a test format with no source
code are exceptions to the "reads like the code it matches" principle; honest but it shows GRL is
also a small relational language over non-U relations (diff, lease, config). (2) `glob any` is a
quantified predicate hidden in a function name; spelled out it is `no g: lease.globs where p ~ glob(g)`,
the same shape as COV001, so one of the two spellings should be the only one. (3) `lease.ticket`
used in the message is a scalar from a side relation; schema needed (as INV002). (4) the example
format again needs inputs that are not source code.

#### Rule 6: SYS001 unowned

```grl
rule SYS001 "unowned" {
  lang *
  polarity P-  severity warn  scope repo

  find a: artifact where not a.path ~ glob any config "grimble.exclude"
  no u: unit in a where u.owner exists          # P-: fires when no unit can have an owner
  report a "no node owns any part of {a.path}"  rollup directory

  example fire python """
    # model: node app owns "src/app/**"
    # file: scripts/legacy.py
    def f(): pass                   #~ warn
  """
  example clean python """
    # model: node app owns "src/app/**"
    # file: src/app/a.py
    def f(): pass
  """
  example unresolved python """
    # model: node app owns "src/**" except by a May selector
    # file: src/x/a.py
    def f(): pass
  """
}
```

Awkward: (1) `u.owner exists` hides the three-valued core: `owner(u)` is `Exact(None)`, `Exact(Some)`,
or a May-only bound; the rule text is two words and all the honesty comes from the P- polarity row.
That is the desired behaviour, but nothing in the text lets the author predict Unresolved without
reading the polarity table, so the `why` output must carry it. (2) `rollup directory` is a report
granularity (binding.md 6.1: "one line per directory"); it is a report-shape construct, not a logic
one, and may belong in the header. (3) "including the module unit of each artifact" is the
`unit in a` default; if the spec leaves it implicit, an adapter that has no module unit changes the
result. (4) the example needs a model block in the test, as INV002 needs config.

#### Rule 7: CAP001 undeclared-capability

```grl
rule CAP001 "undeclared-capability" {
  lang *
  polarity P+  severity error

  find u: effect_use                              # rows (unit, atom, status) from the detectors, Q34
  find n: node where n owns u.unit                # the grimble node, Q36
  no g: grant of n where g covers u.atom          # `covers` follows grant overlap (may A')
  no e: excuse of n where e.atom == u.atom and u.unit matches e.selector   # excused uses are CAP004's
  report u "node {n.name} uses {u.atom} without a grant (deny by default)"
  fix u -> add `may {u.atom} because "<reason>"` to n [has-placeholders]

  example fire rust """
    // node frob owns crates/frob/**, no grants
    fn serve() { std::net::TcpListener::bind("0.0.0.0:0"); }     //~ error
  """
  example clean rust """
    // node frob owns crates/frob/**, grants may net.listen
    fn serve() { std::net::TcpListener::bind("0.0.0.0:0"); }
  """
}
```

Awkward: (1) the rule as written is the projection of the matrix cell (binding.md 7.2 items 3 and
4); the matrix itself (excuse overlaps, precedence, `unknown`, CAP004 taking over) is a stratified
computation that GRL could express with `def` but at a length and with an interplay (E(n,a) removing
identities from the subject set) that no newcomer would write, so in practice the cell relation is
a derived relation supplied by tier 0 or tier 1 and GRL consumes it. The spec must decide whether
derived relations like `cell(n, a)` are "language-level" (defined in GRL in the std pack) or
"engine-level" (Rust). (2) `covers` and `matches e.selector` are domain predicates (grant overlap,
selector matching) that need typed built-ins. (3) the `fix` has placeholders and edits a model file,
not the unit; fix targets other than the finding's span need syntax. (4) polarity P+ firing "from
lo" means a May-status use never fires; the author did not write that, and it is correct.

#### Rule 8: NEAT013 ambient-source-call (the plugins.md sketch, rewritten)

```grl
rule NEAT013 "ambient-source-call" {
  lang *
  polarity P+  severity warn
  knob sources = vocab("clock" | "rng" | "env" | "fs" | "net" | "stdio" | "exit")

  find fn: function where not fn has attr "frob:shell"
  find c: apply where c.unit == fn and c.head resolves to v and v in knob.sources
  report c "{fn.name} calls {v.name}, an ambient source; inject it or mark the unit frob:shell"

  example fire python """
    def now_str():
        return time.time()          #~ warn
  """
  example clean python """
    # frob:shell
    def now_str():
        return time.time()
  """
  example other-lang lua """
    -- a language with no callee vocabulary: expected NotApplicable, not clean
    local t = os.time()
  """
}
```

Awkward: (1) the sketch's `apply(head=resolves_to(v)) inside u` has the nearest-unit problem:
`inside u` is transitive (by L3), so a call in a nested closure is "inside" the outer function too;
`c.unit == fn` is the spelling that avoids it, and every rule that cares about the enclosing unit
will need it, so it should be a first-class relation (`in unit fn`). (2) `vocab(...)` is a Q47
adapter query whose empty answer means NotApplicable, not "no hits"; the `other-lang` example
documents that, but the language must make `v in knob.sources` evaluate to NotApplicable (not
false) when the adapter has no vocabulary, or a clean report on Lua is a lie. (3) `resolves to` has
status Must or May; P+ fires from Must, which the author did not write. (4) a `where` that mixes a
field test, a join and a vocabulary test in one line is the densest line in the ten rules; the
formatter has to break it by clause.

#### Rule 9: NEAT031 dispatch-site-owns-logic

```grl
rule NEAT031 "dispatch-site-owns-logic" {
  lang *
  polarity P+  severity warn
  knob ratio = 0.7                      # share of statements that are guarded calls or calls

  def peer_call(s)    = s is call and s.head resolves to p and p is function and p peer of s.unit
  def guarded_call(s) = s is branch and count(x: stmt directly inside s) == 1
                        and some k: call directly inside s where peer_call(k)

  find d: function where not d has attr "frob:dispatcher"
  where count(s: stmt directly inside d where peer_call(s) or guarded_call(s))
        >= knob.ratio * count(s: stmt directly inside d)
  find b: (branch | loop) where b.unit == d and not guarded_call(b)
  report b "{d.name} dispatches to peers; this {b.role} does more than guard a call: move the logic to the callee or a named predicate"
  note d "dispatcher by shape"

  example fire python """
    def run(ctx):
        a(ctx)
        if ctx.x:
            y = ctx.x * 2          #~ warn
            b(y)
        c(ctx)
  """
  example clean python """
    def run(ctx):
        a(ctx)
        if ctx.x: b(ctx)
        c(ctx)
  """
}
```

Awkward: (1) the definition is "by shape" and a heuristic (neatness.md open question 2: false
positives on state machines), so the ratio is a knob and the rule should probably start Advisory;
`must_measure` and a corpus run belong in the process, not the language. (2) `branch`, `loop`,
`call` are U role attributes (universal-model.md 2.4), which is exactly why a pasted snippet cannot
express this universally: `if $C { $F($$$A) }` is single-language, and the universal form needs the
role vocabulary spelled out, which is less newcomer-friendly than any other rule here. A
snippet-to-roles bridge (`s is `if $C { $F($$$A) }` in rust`) is the missing piece. (3) arithmetic on
two counts is the most "programming" thing in the ten and is within the bounded model, but it is the
point where a newcomer leaves the happy path. (4) `peer of` (same parent module or class) is a new
relation not in the 47 queries; Q27 gives `parent`, so it is derivable with `def`, which costs a
line.

#### Rule 10: CI002 permissions-declared

```grl
rule CI002 "permissions-declared" {
  lang yaml
  polarity P-  severity warn

  find w: file matching ".github/workflows/*.{yml,yaml}"
  no k: key at "/permissions" in w                          # no top-level permissions
  some j: key at "/jobs/*" in w where no p: key at "/permissions" in j   # and some job lacks them
  report w "workflow has no top-level permissions and job {j.name} declares none"

  example fire yaml """
    # file: .github/workflows/ci.yml
    name: ci                                 #~ warn
    jobs:
      build:
        runs-on: ubuntu-latest
  """
  example clean yaml """
    # file: .github/workflows/ci.yml
    name: ci
    permissions: { contents: read }
    jobs:
      build: { runs-on: ubuntu-latest }
  """
}
```

Awkward: (1) `report w ... {j.name}` uses a variable bound inside `some`, which exposes a
"witness" semantics (which job is named when several qualify) that the rule text does not
decide; either `some` yields the first witness in source order (deterministic, say so), or the
rule reports per job and the old "one per workflow" is lost. This is the cleanest example of the
witness-versus-quantifier question. (2) JSON-pointer-like `key at "/jobs/*"` reuses the location
address sort (universal-model.md 2.5) and is fine, but `key at` plus `in` plus `inside` are three
prepositions on one shape; a newcomer will mix them. (3) the "file matching" test is a path glob,
a side relation again (as SCOPE001); a workflow is really a typed artifact kind the adapter should
provide (`find w: workflow`). (4) P- here fires from "hi contains no good thing", so a YAML parse
failure yields Unresolved for free, which is the right behaviour and costs nothing.

### 8.5 What the ten rewrites say, together

Pattern rules are short (R0 six lines, TODO001 is the nearest real rule); relational rules are
fifteen lines with their tests and read acceptably; the places where the draft strained are not the
ones expected from the survey. In order of how often they came up:

1. Location relations (`adjoins`, `same line`, `in unit`) came up in TODO001, NEAT013, NEAT031 and
   GPOL002. Offering `c.unit == fn`, `d adjoins c`, `p peer of u` as named relations is worth more
   than any extra operator.
2. Typed side relations and typed built-ins (config tables, diff, lease, vocab, glob, slug,
   resolve) came up in INV002, SCOPE001, SYS001, DOC002, NEAT013. If their schemas are not fed to
   the compiler, P1 (silent typo) comes back through the side door.
3. Test inputs that are not a single source file (config, lease, diff, model blocks) came up in
   five of ten rules; `example` needs sub-blocks (`config`, `file`, `diff`, `model`).
4. Witness versus per-witness findings (CI002) and exclusive branches (DOC002 `report when`) need
   one stated rule: findings are per `find` variable binding; a `some` variable can be referenced in
   `report` as its first witness in source order.
5. Derived relations that are really engine computations (the capability matrix in CAP001, owner
   resolution in SYS001, test reachability in COV001) are consumed, not defined. The spec should
   publish them as a catalog of typed relations (the 47 queries, renamed as relations) so the
   rule author sees the same list the compiler checks.
6. Universal structural shapes (NEAT031) are the weak spot of "paste code": roles are more
   universal than snippets, and the role vocabulary is less friendly. A bridge from a snippet to
   roles would help.
7. Polarity-driven behaviour (Must/May bound selection) is invisible in the rule text in every
   rule; it must be visible in `why` and `explain`, or authors will not trust it.

### 8.6 Open questions this survey cannot settle

- Is `find x: kind` or `for x in kind` the better first word for a reader who has never seen
  Datalog? The survey has no head-to-head evidence; ESLint and Semgrep never ask the user to
  introduce a variable for a simple rule, CodeQL always does. A five-minute newcomer test is the
  only evidence that would settle it (the walkthrough ticket ~4QBTKCK already plans one).
- Should `report ... when` exist, or should DOC002-style multi-message rules be two rules? Semgrep
  and ast-grep use one message per rule; PMD allows message arguments (`{0}`).
- How are grammar versions pinned for pattern rules and how are pattern hits on parse-error nodes
  reported (P9)? Not answered by any surveyed tool; ast-grep CLI and playground disagree today.

## 9. Reproducibility and the measurement log

Commands run (all in the scratchpad, none in the repo):

- Stars: `gh api repos/<owner>/<repo> --jq .stargazers_count` on 2026-10-02.
- Shallow clones (depth 1) and their commits: getgrit/stdlib 42d432f2f7; getgrit/gritql
  4ca283484a; semgrep/semgrep-rules a84ff9cc24; ast-grep/ast-grep 25334496c1;
  ast-grep/ast-grep.github.io 47a2c45821; github/codeql f7617abe60; open-policy-agent/opa
  3f2d1bd960; souffle-lang/souffle f53dab8bf4; coccinelle/coccinelle 11b93adb65; pmd/pmd
  8602a7d002; checkstyle/checkstyle a26ee03621; comby-tools/comby 3b6bdff7bc;
  comby-tools/comby.dev 907b486c90; tree-sitter/tree-sitter 20cf25c10f; google/error-prone
  72b2ac8558. Docs for Biome, Semgrep, ESLint, Oxlint, Clippy fetched by raw URL from their
  documentation repositories.
- Counts: Semgrep rules by loading every rule YAML with PyYAML (2113 files with a `rules` key,
  2234 rules, 16 files unparsable as rule files, 269 `mode: taint`); `ruleid:` files by `grep -rl`;
  CodeQL `.ql` under `*/ql/src` and `.qlref` by `find`; PMD rules by regex over
  `src/main/resources/category/**/*.xml`; ESLint `lib/rules` by the GitHub contents API; npm
  keyword counts by `registry.npmjs.org/-/v1/search?text=keywords:<k>&size=1`; Stack Overflow tag
  counts by the Stack Exchange API; Regal rule files by the git tree API.
- Measured tool runs: venv with `ast-grep-cli` 0.45.3 and `semgrep` 1.179.0 and `tree-sitter` 0.26.0
  + `tree-sitter-python`; npm `@biomejs/biome` 2.5.15 and `eslint@9`; OPA 1.21.1 arm64 static
  binary. Experiments: simplest rule, typo key, typo node type or function, unbalanced input,
  shallow `inside`, test runner output, unknown predicate, mistyped field. Raw outputs are
  summarised above with the tag M; the only claims not backed by a run are tagged D or J.
- Not executed (and why): CodeQL (bundle is over 1 GB), Souffle (needs a CMake build; no cargo or
  heavy builds were allowed), Comby and Coccinelle (no aarch64 binary or package route tried),
  PMD, Checkstyle and Refaster (JVM toolchains), Clippy (needs the pinned nightly), Oxlint JS
  plugins (alpha, not installed). Their error-quality cells are D or J.
- Cleanup: all clones and downloaded binaries under the scratchpad `grl/` directory were deleted
  after this file was written.

## 10. Coverage of the survey list (Phase-2 reconciliation)

| # | System | Real example copied | Run locally | Complaints cited | Popularity measured |
|---|---|---|---|---|---|
| 1 | GritQL | yes (stdlib, gritql repo) | no (Biome only) | yes | yes |
| 2 | Biome GritQL plugins | yes (docs) | yes (M) | yes | yes |
| 3 | Semgrep | yes (semgrep-rules, docs) | yes (M) | yes | yes |
| 4 | ast-grep | yes (catalog, docs) | yes (M) | yes | yes |
| 5 | CodeQL | yes (python queries) | no | yes | yes |
| 6 | Souffle | yes (tests/example, goldens) | no | yes | yes |
| 7 | tree-sitter queries | yes (docs, Globstar) | yes (M, Python binding) | yes | yes |
| 8 | Rego/OPA (and Regal) | yes (Regal rule and test) | yes (M) | yes | yes |
| 9 | Comby | yes (docs) | no | none found | yes |
| 10 | Coccinelle | yes (demos, kernel) | no | yes | yes |
| 11 | ESLint selectors | yes (docs) | yes (M) | yes | yes |
| 12 | Clippy | yes (needless_else.rs) | no | none found (positive quote only) | yes |
| 13 | Oxlint JS plugins | yes (blog) | no | none found | yes |
| 14 | Ruff (no DSL) | issue 283 and FAQ | n/a | yes | yes |
| 15 | PMD XPath | yes (errorprone.xml, test XML) | no | none found (docs prerequisite) | yes |
| 16 | Checkstyle | yes (xdocs example) | no | none found (Javadoc warning) | yes |
| 17 | Error Prone Refaster | yes (BinaryTemplate) | no | yes | partial (corpus private) |
| extra | Glean Angle, Globstar, Regal | yes | no | partial | yes |

Done 17 of 17; blocked 0; pending 0. Weakest evidence: Comby, PMD, Checkstyle, Clippy, Oxlint
(no complaint threads found), and every "error quality" cell not tagged M.
