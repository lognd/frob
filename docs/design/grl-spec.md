# GRL: the grimble rule language

Status: ACCEPTED as the design (D80, ticket ~4QBTKCK); the newcomer test
of section 13 is still to run. Evidence:
notes/research/rule-languages.md (17 rule systems surveyed, six run
locally with their error messages measured, ten frob rules rewritten).
Depends on plugins.md (tiers, packs, compilation), universal-model.md
(U, the 47 queries, three-valued answers, polarity), rules.md (rule
metadata, mdtest corpora), diagnostics.md (messages, fixes, explain),
security.md (text origin, fixes owned by the host).

GRL is the only rule language of frob, grimble and crunk (owner
decision: one way to do a thing). Std rules and plugin rules are written
in it; std rules are compiled into the binary, plugin rules run as plans
(plugins.md 6.1). Because nobody can escape to a second form, GRL has to
be easy to start with for someone who has never written a lint rule.
That requirement shaped every choice below.

## 1. Principles

Each principle comes from a measured failure or success in the survey
(lesson numbers L1-L15 and pitfalls P1-P15 refer to
notes/research/rule-languages.md sections 6 and 7).

1. **Start from the code you want to catch.** The smallest rule is a
   pasted snippet and a message (L1). Relations are added only when a
   rule needs them.
2. **Every name is checked when the rule is compiled.** A misspelt kind,
   field, relation, metavariable, config column or knob is a compile
   error with a did-you-mean, never a rule that silently matches
   nothing (L2, P1). This is GRL's most important property: frob's
   contract is "never silently clean", and a typo is the most common way
   other tools break it.
3. **Words mean what a reader assumes.** `inside` and `has` look through
   any depth; `directly` marks the one-level form (L3, P2). There is one
   way to say "absent" for a join (`no`) and one for a condition
   (`not`) (L4, P3).
4. **Uncertainty is visible.** A rule never turns "could not decide"
   into "clean". The engine evaluates every clause three-valued; the
   rule's polarity decides what fires and what certifies clean; `why`
   shows which edges were used and why (L5, P10).
5. **The test lives in the rule.** A rule without at least one firing
   and one clean example does not compile (L6). The compiler's own
   errors have golden tests (L7).
6. **You can see why a rule did not match.** `rule why` prints, clause by
   clause, how many candidates passed and where the first one failed,
   using the same engine as `check` (L8).
7. **Its own syntax, not YAML.** Snippets are raw text in backticks; no
   escaping except `$` (L9, P5).
8. **Bounded by construction.** No user recursion, closures carry a
   bound, the planner orders the work, every plan terminates in
   polynomial time and reports its cost class (L11, P7). A budget
   overrun is Unresolved, never clean.
9. **Small.** Twenty constructs (section 4). Anything new must first be
   expressed with existing constructs (P12).

## 2. Your first rule in five minutes

This section is the newcomer walkthrough; the rest of the document is
reference.

**Goal:** stop `dbg!(...)` from being committed in Rust library code.

**Step 1. Start from real code.** Point the tool at a line that should
be caught:

```text
$ grimble rule new NOPE001 --from src/parse.rs:42
created rules/NOPE001.grl from: dbg!(tokens.len())
```

**Step 2. Read what it wrote.**

```grl
rule NOPE001 "no-dbg" {
  lang rust

  find d: `dbg!($$$ARGS)`
  report d "remove dbg! before committing"

  example fire """
    fn f(x: u32) -> u32 { dbg!(x) }        //~ warn
  """
  example clean """
    fn f(x: u32) -> u32 { x }
  """

  explain """
    `dbg!` prints to stderr and is meant for local debugging only.

    ## Remedy
    Delete the call, or log through `tracing` if the value matters.
  """
}
```

Read it top to bottom: in Rust, find every `d` that looks like
`dbg!(...)`, and report it. `$$$ARGS` stands for any arguments. The two
examples are tests: the first must produce a warning on the marked line,
the second must produce nothing.

**Step 3. Test it.**

```text
$ grimble rule test rules/NOPE001.grl
NOPE001  fire   ok (1 finding on line 1)
NOPE001  clean  ok (0 findings)
```

**Step 4. Allow it in tests.** Add one line, and an example proving it:

```grl
  find d: `dbg!($$$ARGS)`
  where not d inside test
  ...
  example clean """
    #[test] fn t() { dbg!(1); }
  """
```

`test` is a kind the Rust adapter knows (test functions and `#[cfg(test)]`
modules). If you had typed `tset`, the compiler would say:

```text
error[GRL001]: unknown kind `tset`
  --> rules/NOPE001.grl:5:23
  |
5 |   where not d inside tset
  |                      ^^^^ not a kind, field or relation
  = help: did you mean `test`?
  = explain: grimble explain GRL001
```

**Step 5. Run it on the repository.**

```text
$ grimble check
warning[NOPE001]: remove dbg! before committing
  --> src/parse.rs:42:5
```

If a line you expected is not reported, ask why:

```text
$ grimble rule why NOPE001 src/lexer.rs:17
find d: `dbg!($$$ARGS)`    1 candidate at 17:9
where not d inside test    failed: 17:9 is inside test `lexes_numbers` (src/lexer.rs:12)
```

That is the whole loop: paste, read, test, refine, run, ask why. Section
12 shows the same loop for rules that look across files.

## 3. Lexical structure

- Files end in `.grl`, are UTF-8 with ASCII-only syntax (identifiers,
  keywords, operators); strings and snippets may hold any text. One file
  may hold several rules; std rules use one rule per file named by id.
- Comments: `#` to end of line, outside snippets and strings.
- Identifiers: `[a-z_][a-z0-9_]*` for variables, defs and knobs; rule ids
  `[A-Z]+[0-9]{3}`; kinds and relations are lowercase words from the
  catalog (section 6), multi-word relations are written with spaces
  (`resolves to`, `owned by`).
- Strings: `"..."` with `\"`, `\\` and `\n`. Interpolation `{expr}`
  exists only in message positions: `report` and `note` text, `fix`
  replacement text, `unresolved ... because` reasons and `explain`. There
  `\{` and `\}` write literal braces. In every other position (globs,
  paths, regexes written as strings, config values, knob defaults,
  example inputs) braces are literal and need no escaping, so
  `".github/workflows/*.{yml,yaml}"` is a glob with an alternation.
  Triple-quoted `"""..."""` for blocks, with the common leading
  indentation removed.
- Snippets: backticks, optionally tagged with a language:
  `` `print($$$ARGS)` ``, `` rust`$X.unwrap()` ``. The text is raw; only
  `$` is special (`$$` for a literal dollar). A snippet with backticks
  inside uses double backticks: ``` ``a `b` c`` ```.
- A snippet must parse on its own. For constructs that only exist in a
  context (a Python `except:` clause, a struct field), write the context
  and select the node with `as KIND`: `` python`try: $$$ except: $$$` as
  except_clause `` matches the except clause, and the finding points at
  it. GRL002 shows how the snippet parsed when it does not.
- Metavariables inside snippets: `$X` one node, `$$$XS` a sequence,
  `$_` and `$$$` anonymous; `...` is the language's own ellipsis where
  the adapter supports it (gob-pattern).
- Language ids are bare words (`rust`, `python`, `javascript`,
  `typescript`, `markdown`, `yaml`, `toml`, `json`, ...), never quoted;
  `grimble rule catalog langs` lists them with their comment markers
  (section 9). `lang "*"` is accepted with a warning that says to drop
  the quotes.
- Numbers: integers, decimals for knobs and ratios.
- Regex: `/.../` with flags `i`, `m`; Rust regex syntax, size-limited.

## 4. The twenty constructs

| # | Construct | Example | Meaning |
|---|---|---|---|
| 1 | rule | `rule TODO001 "bare-work-marker" { ... }` | id, slug, body |
| 2 | header | `lang rust`, `polarity P+`, `severity error`, `scope repo`, `must_measure`, `needs diff, lease` | metadata (rules.md 2) |
| 3 | snippet | `` `print($$$ARGS)` `` ``rust`if $C { $F($$$A) }` as roles`` | code that looks like this |
| 4 | metavariables | `$X`, `$$$XS`, `$_` | holes in a snippet |
| 5 | find | `find f: function where f is public` | bind a variable to each thing of a shape |
| 6 | where | `where c.text ~ /TODO/` | a condition |
| 7 | not, and, or, any | `not d inside test`, `any { a, b }` | three-valued connectives |
| 8 | some, no | `no t: test where t reaches f via calls within 12` | exists, absent (fresh scope) |
| 9 | containment | `inside`, `has`, `directly inside`, `directly has`, `in unit` | ancestors and descendants |
| 10 | position | `before`, `after`, `adjoins` | order and adjacency |
| 11 | edge verbs | `calls`, `imports`, `references`, `resolves to`, `owned by`, `tests`, `extends`, `instantiates` | graph edges with Must/May status |
| 12 | reaches | `a reaches b via calls within 6` | bounded closure |
| 13 | count | `count(s: stmt directly inside d) > 40` | counting |
| 14 | fields | `x.name`, `x.text`, `x.line`, `x.unit`, `x is public`, `x has attr "k"` | properties |
| 15 | side relations | `find row: config.invariants.forbid_imports`, `p in diff.changed` | typed tables outside U |
| 16 | def | `def peer_call(s) = s is call and s.unit peer of s` | named, non-recursive predicate |
| 17 | knob | `knob depth: int = 12 "how many call levels to follow"` | typed, documented setting |
| 18 | report, note | `report f "..."`, `note api "entry point"` | the finding and extra spans |
| 19 | fix | `fix d -> `` `x` `` [machine]` | a rewrite with applicability |
| 20 | example, explain, unresolved when | see section 7 | tests, the rule page, author-declared doubt |

## 5. Grammar

```text
file       = { rule } ;
rule       = "rule" RULE_ID STRING "{" { header } { clause } { example } explain "}" ;

header     = "lang" lang_set
           | "polarity" ( "P+" | "P-" | "P0" | "Pn" | "Pc" )
           | "severity" ( "error" | "warn" | "advisory" )
           | "scope" ( "file" | "repo" )
           | "must_measure"
           | "needs" NAME { "," NAME }
           | "rollup" ( "file" | "directory" | "unit" )
           | knob ;
lang_set   = "*" | "-" | LANG | "[" LANG { "," LANG } "]" ;
knob       = "knob" NAME ":" type "=" literal STRING ;
type       = "int" | "float" | "string" | "bool" | "glob" | "regex"
           | "vocab" | "list" "<" type ">" ;

clause     = find | where | quant | def | report | note | fix | unresolved ;
find       = "find" NAME ":" source { rel } [ "where" cond ] ;
source     = shape | side ;
field_eq   = [ "." ] NAME "=" literal ;         (* `.tag = "img"` and `tag = "img"` parse alike; the printer emits the bare form *)
shape      = KIND [ "(" field_eq { "," field_eq } ")" ]
           | SNIPPET [ "as" ( KIND | "roles" ) ]
           | "(" shape { "|" shape } ")" ;
side       = side_path ;                       (* config.x.y, diff.changed, lease.globs, model.nodes *)
where      = "where" cond ;
quant      = ( "some" | "no" ) NAME ":" source { rel } [ "where" cond ] ;
def        = "def" NAME "(" [ NAME { "," NAME } ] ")" "=" cond ;

cond       = disj ;
disj       = conj { "or" conj } ;
conj       = unary { "and" unary } ;
unary      = "not" unary | "any" "{" cond { "," cond } "}" | "(" cond ")" | quant | atom ;
atom       = term rel
           | term CMP term
           | term "~" ( REGEX | term )              (* regex match; a list means any *)
           | term "matches" term                    (* glob match; a list means any *)
           | term "in" term                         (* membership; ranges a..b allowed *)
           | term "is" ( KIND | WORD )              (* kind test or boolean field: is public *)
           | term "has" "attr" STRING
           | term "is" SNIPPET [ "as" "roles" ]
           | NAME "(" [ term { "," term } ] ")"    (* def call *)
           | "exists" term ;
rel        = [ "directly" ] ( "inside" | "has" ) object
           | "in" "unit" object
           | "under" term                           (* module or path segments, not characters *)
           | ( "before" | "after" | "adjoins" ) object
           | VERB object
           | "reaches" object "via" VERB_LIST "within" term ;
object     = term | shape ;                         (* a bound variable, or an anonymous shape *)
term       = NAME { "." NAME } | literal | "knob" "." NAME | count | term ARITH term ;
count      = "count" "(" NAME ":" source { rel } [ "where" cond ] ")" ;

report     = "report" NAME STRING [ "when" cond ] ;
note       = "note" NAME STRING ;
fix        = "fix" [ ( "before" | "after" ) ] NAME "->" SNIPPET "[" APPLICABILITY "]"
           | "fix" "delete" NAME "[" APPLICABILITY "]"
           | "fix" "host" NAME "(" term { "," term } ")" "[" APPLICABILITY "]"   (* std only *)
           | "fix" "manual" STRING ;
unresolved = "unresolved" "when" cond "because" STRING ;

example    = "example" EXPECT [ LANG ] [ STRING ] "{" { input } "}"
           | "example" EXPECT [ LANG ] [ STRING ] TRIPLE ;
EXPECT     = "fire" | "clean" | "unresolved" | "notapplicable" | "known-gap" ;
input      = "file" STRING TRIPLE | "config" TRIPLE | "model" TRIPLE
           | "diff" "[" STRING { "," STRING } "]" | "lease" "[" STRING { "," STRING } "]"
           | "expect" STRING                         (* "line 3: warn", for languages without comments *)
           | "fixed" TRIPLE ;                        (* the expected output of the rule's fix *)
explain    = "explain" TRIPLE ;                     (* markdown; must contain "## Remedy" *)

APPLICABILITY = "machine" | "maybe-incorrect" | "has-placeholders" ;
CMP        = "==" | "!=" | "<" | "<=" | ">" | ">=" ;
ARITH      = "+" | "-" | "*" ;
```

`VERB`, `KIND` and the field names come from the relation catalog
(section 6), so the grammar is closed but the vocabulary is generated
from the engine; an unknown word is GRL001, not a parse error.

## 6. The relation catalog

The catalog is the single list of everything a rule can name: kinds,
each kind's fields (with types and one example), verbs, side relations,
and language ids with their comment markers, each with its type, its universal
query (universal-model.md 5), which languages answer it, and whether its
answer can be Unknown. It is generated from the engine's registry into
`docs/reference/grl/catalog.md` and embedded in the binary, so the page,
the compiler and the engine read one source. `grimble rule catalog
[WORD]` prints it. The core:

| Word | Kind of word | Query | Notes |
|---|---|---|---|
| `artifact`, `file` | kind | Q01, Q02 | `file` is an artifact with text; `f is markdown` tests its language |
| `unit`, `function`, `method`, `type`, `module`, `field`, `param` | kind | Q04, Q06, Q15 | adapter kinds map onto these closed core kinds |
| `test` | kind | Q35 | NotApplicable where a language has no test convention |
| `call`, `import`, `comment`, `literal`, `stmt`, `branch`, `loop`, `assignment` | kind | Q12, Q13, Q14, Q16 | `branch` and `loop` are U roles, so they work in universal rules |
| `heading`, `link`, `fence`, `table` | kind | Q11 | prose |
| `key` | kind | Q19 | TOML, JSON, YAML keys; `key(path = "/jobs/*")` addresses by key path |
| `element`, `attribute` | kind | Q48, Q51 | markup in tsx, jsx, html; `element(tag, kind)`, `attribute(name, value, spread, tokens)`; `.value` is a `const_value` answer and may be Unknown; `e has attribute(name = "alt")` is Unknown when a spread may supply it; `.tokens` is `class_tokens` |
| `style_rule`, `declaration`, `custom_property` | kind | Q49 | css and scss; `declaration` also from tsx and jsx inline style objects; `style_rule(selector)`, `declaration(property, value, important)`, `custom_property(name, value)` |
| `directive` | kind | (gob-directives) | `directive "todo"` |
| `effect_use`, `node`, `grant`, `excuse`, `cell` | kind | Q34, Q36, binding.md 7 | grimble; `cell` is the capability matrix cell, computed by the engine |
| `.name`, `.text`, `.line`, `.file`, `.path`, `.kind`, `.role` | field | Q03, Q05, Q06 | on every kind; `.file` is a file, `.file.path` its repository-relative path |
| `call(.callee, .args)` | fields | Q13, Q20 | `.callee` is the callee as written (`exit`, `sys.exit`, `std::process::exit`); `.callee.name` its last segment |
| `link(.target, .text)` | fields | Q11 | `.target` is the destination as written; `.target.path`, `.target.anchor`, `.target.scheme`, `is relative`; `.text` is the visible text |
| `function(.name, .params, .returns)` | fields | Q15 | `is public`, `is async` where the language has them |
| `key(.path, .name, .value)` | fields | Q19 | `.path` is the slash path from the document root |
| `comment(.text)`, `literal(.value)`, `heading(.text, .level, .slug)` | fields | Q10, Q14, Q11 | |
| `.unit` | field | Q05 | the nearest enclosing unit (not any ancestor) |
| `is public`, `is exported` | field | Q07, Q33 | may be Unknown |
| `has attr "k"` | field | Q08 | |
| `.doc` | field | Q09 | |
| `inside`, `has`, `directly inside`, `directly has` | relation | Q27 | transitive unless `directly` |
| `in unit` | relation | Q05 | `c in unit fn` means fn is c's nearest enclosing unit |
| `before`, `after` | relation | location order | within one file |
| `adjoins` | relation | location order | same line, or the line directly above the first line |
| `peer of` | relation | Q27 | same parent unit |
| `under` | relation | Q21, Q23 | module or path prefix by segments (`a.b` is under `a`, `ab` is not) |
| `calls`, `references`, `imports`, `extends`, `instantiates` | verb | Q28, Q29 | Must, May or Unknown status |
| `resolves to` | verb | Q20, Q21 | One, Candidates or Unknown |
| `owned by` | verb | Q32, Q36 | the grimble node owning a unit |
| `tests` | verb | Q35 plus `frob:tests` | a test linked to a callable |
| `reaches ... via ... within N` | closure | Q30 | Yes, No or Unknown with the frontier |
| `vocab(NAME)` | value | Q47 | empty means NotApplicable, never "no hits" |
| `config.<table>` | side relation | config schema | typed from docs/schemas/config.json |
| `diff.changed`, `diff.added` | side relation | gob-git | needs `diff` |
| `lease.globs`, `lease.ticket` | side relation | frob-lease | needs `lease` |
| `model.nodes`, `model.selectors` | side relation | grimble-model | needs `model` |
| `glob(s)`, `resolve(path, from)`, `slug(s)`, `valid_glob` | function | built in | typed signatures in the catalog |

Side relations are typed from their JSON schemas (config, diff, lease,
model); a misspelt column is GRL001 like any other name (survey 8.5
item 2). A rule that reads a side relation must declare it in `needs`,
which also decides when the rule must re-run (rules.md 3).

In a kind pattern the field name may be written with or without its
leading dot: `element(.tag = "img")` and `element(tag = "img")` are the
same pattern. The bare form is canonical and is what the printer emits
(decision recorded under ~1PBDXSF); the dotted form is accepted because
the dot is how the same field is read in a condition (`e.tag`, section 6).

## 7. Semantics

### 7.0 Denotational semantics

This section is the definition; 7.1 to 7.4 state its consequences in
the words a rule author uses. The meaning of a rule is given once, by
a compositional function into the strong Kleene logic K3 (values No <
Unknown < Yes, ordered by truth; Unknown is "the facts do not settle
it"). It follows the formal review of 2026-10-08 (section 2.3, 2.4 and
2.7 of notes/review/formal-review-2026-10-08.md).

**Structure.** A subject is read as a finite relational structure whose
every relation R has a lower and an upper extension, `lo(R)` within
`hi(R)`. Must facts are in `lo`; May facts are in `hi` only; a tuple
outside `hi` is certainly absent. A kind `K` is a unary relation, and
a kind whose capability is NotApplicable for the language denotes the
empty set exactly (`lo = hi = {}`). A closed relation has `lo = hi`.
An environment `rho` maps each bound variable to one element of the
domain.

**Atoms.** For an atom `R(t1..tn)`:

- `[[R(t)]]rho = Yes` if `rho(t)` is in `lo(R)`;
- `No` if it is not in `hi(R)`;
- `Unknown` otherwise (a May fact, an Unknown status, a partial parse,
  an opaque region).

Field reads and built-in functions (`slug`, `resolve`, `glob`) are
total on known inputs and give Unknown on an Unknown input
(`const_value`, `is public` with Unknown visibility).

**Connectives (Kleene).** `[[not c]] = neg [[c]]` swapping Yes and No
and fixing Unknown; `and` is the minimum and `or` the maximum under
No < Unknown < Yes. `any { c1, c2 }` is `or`; a `where` list is `and`.
Every connective is monotone in the information order (Unknown below
Yes and No), which is the lemma soundness rests on.

**Quantifiers.** `some x: K where c` is the maximum of `[[c]]rho[x:=e]`
over every `e` in `hi(K)`, with `[[x in K]]` folded in: an element in
`hi(K)` but not `lo(K)` contributes at most Unknown. If the domain may
have hidden members (a partially parsed file, an opaque region, an
exhausted budget), one further disjunct Unknown is added, so a
`some` with no visible witness is Unknown rather than No. `no x: K
where c` is `not some x: K where c`. A `some` is Yes only through a
witness in `lo`.

**Counts as intervals.** `count(x: K where c)` denotes the pair `[lo,
hi]`: `lo` counts elements with `[[c]] = Yes` (and `x` in `lo(K)`),
`hi` counts elements with `[[c]]` not No (and `x` in `hi(K)`); hidden
members raise `hi` to infinity. Arithmetic is interval arithmetic.
`A >= B` is Yes if `lo(A) >= hi(B)`, No if `hi(A) < lo(B)`, otherwise
Unknown; the other comparisons are defined likewise. So a count that is
only possibly over a limit is Unknown, never a finding.

**Closure and `within N`.** `a reaches b via V within N` is the
bounded transitive closure. Let `lo_N` be the pairs joined by a path of
at most N edges using only `lo(V)` edges, and `hi_*` the pairs joined by
any `hi(V)` path of any length. Then it is Yes if `(a, b)` is in
`lo_N`. It is No only if `(a, b)` is not in `hi_*`, that is, no path of
any length exists even through May edges. Otherwise it is Unknown, with
the frontier (the nodes at depth N whose expansion was cut off, or whose
edge status is Unknown) as the reason. A depth bound is a budget, not a
fact: truncation yields Unknown with Unresolved reason `budget`, never
No. A test that reaches `f` at depth 13 when N is 12 therefore leaves
COV001 Unresolved, and the rule cannot fire on a truncated reach. When
the reachable set is exhausted before depth N, the closure is complete
and the answer is exact.

**`certainly` and `possibly`.** `certainly c` is Yes when `[[c]]` is
Yes and No otherwise; `possibly c` is No when `[[c]]` is No and Yes
otherwise. They send Unknown to a definite value, so they are not
monotone in the information order. They are therefore allowed only in
positive position (under an even number of `not`, `no` and `unresolved
when`, and not under a count or a P- rule's good-thing clause); anywhere
else is GRL017. Their finding message must say "possibly" when it rests
on `possibly`.

**Defs as views.** A `def` is a materialised view: `def p(x) = c` is the
relation from each argument tuple `e` to the K3 value `[[c]]rho[x:=e]`, computed
once per distinct argument and shared by every call site. Calling
`p(e)` denotes `[[c]]rho[x:=e]`, so a def adds no new semantics and,
being non-recursive (GRL009), the view layers form a finite stratification.

**Static NotApplicable.** NotApplicable is not a value of K3 and never
appears inside a formula. It is a property of a (rule, language) pair,
decided before evaluation from the rule's `needs`, the words it uses and
the capability matrix: if a word the rule must have (a `vocab` that is
empty, a `test` convention a P- rule quantifies over) is NotApplicable
for the language, the pair is NotApplicable and produces no finding;
it is counted once per language in the fidelity report. Inside a formula
over an applicable pair a NotApplicable kind is simply the empty set, so
`d inside test` is No in a language with no tests, as classical logic
says, and `not d inside test` is Yes.

**Rule verdict.** For a rule with `find` variables `v`, the formula `C`
is the conjunction of its `where`, quantifier and relation clauses, and
the K3 value `V = [[C]]rho` is computed once per binding `rho`. The
polarity then maps `V` to a verdict:

| Polarity | `V` = Yes | `V` = Unknown | `V` = No |
|---|---|---|---|
| P+ (C describes the bad thing) | fire | Unresolved | clean |
| P- (C describes the good thing) | clean | Unresolved | fire |
| P0 (C is a fact to report) | fire | Unresolved | clean (no finding) |

`Pn` and `Pc` are instances of the same map: Pn applies it to the
interval comparison above and Pc to the closure value. An `unresolved
when` clause makes a Yes or No verdict Unresolved when it holds. Hits
on parse-error nodes make `V` at most Unknown (reason `parse-error`).
Equivalently, evaluating positive occurrences of May-edge atoms on `lo`
and negative occurrences on `hi` gives the same verdict; the table is the
definition, and nothing is ever evaluated "on Must facts" as a whole.

Worked check, P+ with a negation: `not f has attr "frob:shell" and not
some t: test where t calls f`, with the only test call a May edge. The
atom is Unknown, `some` is Unknown, `not` leaves it Unknown, the `and` is
Unknown, so the rule is Unresolved. Substituting Must facts for the
whole formula would have made `not some` Yes and fired a false error.

**Cost class.** The cost class of a plan is the number of variables
simultaneously bound in the widest clause (its width `w`): a quantifier
or count over a domain of size `n` costs `n^w` for fixed `w`, a closure
adds a factor of N, and defs are shared. This is the data complexity of
7.4, stated per rule.

### 7.1 Bindings and findings

- A rule is a conjunction of clauses. Clause order does not matter; the
  planner orders the work.
- A variable is bound by exactly one `find` (or by the head of `some`,
  `no` and `count`, inside their own scope). Using a name again is an
  equality test, never a rebinding (L10, P6). Binding a name twice is
  GRL004; binding a name and never using it is warning GRL013.
- `some` and `no` are conditions and may appear anywhere a condition
  can, including inside `any` and inside another quantifier; a
  quantifier written as a clause (`no t: test where ...`) is the same as
  `where no t: test where ...`. A def's parameters are its own scope.
  Inside a quantifier every variable of the enclosing rule is visible
  (`no t: test where t calls f` uses the outer `f`).
- Relations and verbs are conditions, usable in any `where`: `t calls
  f`, `p inside test`. Their object is a bound variable or an anonymous
  shape: `p inside function(name = "main")`, `p inside test`,
  `c inside `@cli def $_($$$): $$$``. An anonymous shape is the same as
  `some x: SHAPE where p inside x`, without having to name `x`.
- `directly inside` means one structural level: the statements directly
  inside a function are its top-level body statements, not those nested
  in its branches and loops.
- `a reaches b via calls within N` follows at most N call edges; a
  path cut off at N is Unknown (reason `budget`), never No (7.0). `b`
  may be a unit, or a call site (then the closure ends at the unit that
  contains the call): `f reaches call(callee = "exit") via calls within 3`.
  Verbs never introduce names: to name the target of an edge, bind it
  with `some` (`some v: unit where c resolves to v`).
- `not`, `no` and `unresolved when` use variables but never bind them;
  every variable they use must be bound by a positive clause outside
  them (L4). The error names the variable and suggests the `find` that
  would bind it (GRL003).
- **One finding per binding.** A finding is produced for each distinct
  assignment of the `find` variables that satisfies every clause. If a
  rule has several `report ... when` clauses, they are tried in text
  order and the first that holds produces the finding, so one binding
  never yields two findings (survey 8.6).
- **Witnesses.** A `report` message may name a variable bound by `some`;
  it shows the first witness in source order (file path, then byte
  offset), which is deterministic.
- Lists on the right of `in`, `~` and `matches` mean "any element":
  `p matches lease.globs` is true if any glob matches. There is no
  second spelling.

### 7.2 Three values and polarity

Every condition evaluates to Yes, No or Unknown (section 7.0;
universal-model.md 4.1, Kleene connectives). Sources of Unknown: May
edges, Unknown visibility, partial parses, opaque regions, budget
overruns, an Unknown-status closure frontier. NotApplicable is not a value: it is decided statically per (rule,
language) pair from `needs` and the capability matrix (empty vocabulary,
no test convention), and inside a formula such a kind is the empty set.

The rule's polarity (default P+) maps the one K3 value of the formula
to a verdict per binding (7.0), with no author code. P- means the
formula describes the good thing:

| Polarity | Yes | Unknown | No |
|---|---|---|---|
| P+ (a bad thing exists) | fire | Unresolved | clean |
| P- (a good thing is missing) | clean | Unresolved | fire |
| P0 (a fact to report) | fire | Unresolved | no finding |
| Pn (a count crosses a limit) | lower bound crosses: fire | bounds straddle the limit | upper bound stays under: clean |
| Pc (a closure property) | Must closure proves it | the frontier is Unknown or truncated | complete May closure disproves it |

May atoms are Unknown, so the table never reads one edge set for a
whole formula; that reading is unsound under negation.

So `reaches`, `calls` and `owned by` pick Must or May edges themselves;
`certainly` and `possibly` before a verb override the choice, are
rarely needed and are allowed only in positive position (GRL017).
`unresolved when COND because "reason"` adds doubt the
engine cannot see (a malformed config entry). Hits on parse-error nodes
and absence claims over partially parsed files are Unresolved with
reason `parse-error`. A NotApplicable (rule, language) pair never produces a finding; it is
counted once per language in the fidelity report.

`grimble rule why` and `explain` always print the polarity and which
edge set each clause used ("used May edges because polarity P-"), so the
invisible part of the semantics is visible on request (survey 8.5
item 7).

### 7.3 Universal rules and roles

`lang *` rules may use only universal words: kinds, roles, fields and
verbs that the catalog marks universal. A plain snippet in a universal
rule is GRL006. A snippet with `as roles` is allowed: it is parsed in
its tagged language, lifted to U operators and role attributes (Q46),
and matched in every language; any node that does not lift to a
universal operator is GRL007, naming the node. This is the bridge from
"paste code" to universal structure:

```grl
find b: rust`if $C { $F($$$A) }` as roles     # a branch whose body is one call, in any language
```

`lang -` rules read only side relations (SCOPE001); `lang [rust,
python]` rules may use those adapters' words and snippets in those
languages.

### 7.4 Bounds and cost

No construct recurses. `def` may call earlier defs but never itself or
a later one (GRL009). `reaches` requires `within N` (a literal or knob;
GRL010 without it). Counts and arithmetic are over finite sets. Every
plan therefore terminates in polynomial time (universal-model.md 4.3).
`grimble rule check` prints the plan's cost class (per file; per
repository; closure depth N) and its prefilter (the node kinds a file
must contain for the rule to run), and a run over its budget reports
Unresolved `budget` (plugins.md 6.5).

### 7.5 The ten rules, by hand

Each verdict follows from 7.0; `V` is the K3 value of the rule formula.

| Rule | Polarity | Compositional reading | Verdicts |
|---|---|---|---|
| TODO001 | P+ | `V` = marker match and not owned and `no d` (a directive adjoining); an unparsed region makes `no d` Unknown | fire on Yes, clean when a directive adjoins, json is NotApplicable (no `comment` kind) |
| DOC002 | P+ | each `report ... when` is a K3 value; `no h` over headings is Unknown when the target is partly parsed | fire on Yes, Unresolved on Unknown |
| COV001 | P- | `V` = `any` of a bounded closure and `tests`; truncation gives Unknown | clean on a Must path within depth, fire only when the closure is complete and empty, Unresolved at truncation or May edges (the python `helper(cb)` example) |
| INV002 | P+ | conjunction of glob match and `under`; `unresolved when` forces Unresolved on a bad glob | fire on Yes, Unresolved on a bad glob |
| SCOPE001 | P+ | `not matches` over closed side relations, so `lo = hi` and `V` is never Unknown | fire or clean only |
| SYS001 | P- | `some u ... some n: u owned by n`; May owner is Unknown | clean on Must owner, Unresolved on May owner, fire on none |
| CAP001 | P+ | `observed and not granted and not excused` over a closed `cell` relation | fire or clean; an Unknown observation is Unresolved |
| NEAT013 | P+ | `some v: c resolves to v and v in knob.sources`; a Candidates resolution is Unknown | NotApplicable per language when the vocabulary is empty; otherwise fire, Unresolved or clean |
| NEAT031 | P+ | count interval comparison, then `not guarded_call(b)` | fire when the count comparison is Yes (`lo` of the call count at least `hi` of the scaled total); Unresolved when the intervals overlap; clean when No |
| CI002 | P+ | `no k` Unknown on an unparsed workflow | Unresolved, not clean, on parse failure |

COV001 never fires on a truncated reach: the only way its good-thing
clause is No is a complete closure, and truncation leaves the frontier
Unknown.

## 8. Messages, notes, fixes and explain

- `report x "text {x.name}"`: the primary span is `x`. Interpolation
  takes fields, knobs and witnesses; it never takes arbitrary
  expressions. Rendered text from a pack carries `origin = pack:NAME`
  and is escaped (security.md 2.10).
- `note y "text"` adds a secondary span.
- `fix x -> `...` [applicability]` replaces `x`; `fix before x` and
  `fix after x` insert; `fix delete x` removes; `fix manual "steps"` is
  the help text when no edit exists. Metavariables bound in `find`
  snippets may be used in the replacement. Applicability is required
  (no default), and a plugin's fix may edit only inside the finding's
  primary span unless the pack holds `fix.machine` (security.md 2.10).
  Fixes that edit another file (CAP001 adds a grant to the model) are
  std-only and use a host fix by name: `fix host add_grant(n, u.atom)
  [has-placeholders]`.
- `explain """..."""` is the rule page: markdown, must contain
  `## Remedy` (GRL012), rendered by `explain RULE` and into
  docs/reference/rules/ID.md with the rule's GRL source as the first code
  block (L12).

## 9. Examples are tests

- Every rule needs at least one `fire` and one `clean` example (GRL011).
  A universal rule also needs one `notapplicable` or `unresolved`
  example in a language that lacks the feature (rules.md 2).
- An example's language defaults to the rule's `lang`; examples of a
  multi-language or universal rule must name one.
- Expected findings are marked with the language's comment introducer
  followed by `~` and a severity, on the line where the reported node
  starts (for `report f` on a function, the line of its header, not of
  the call inside it): `//~ warn` (Rust, C, JavaScript, TypeScript,
  Java, Go), `#~ error` (Python, YAML, TOML, shell), `--~ warn` (Lua,
  SQL), `<!--~ error -->` (Markdown, HTML). `//~ unresolved` marks an
  expected Unresolved. For languages without comments (JSON), use
  `expect "line 3: warn"` lines in the example header.
- Inputs other than one source file are sub-blocks: `file "path"
  """..."""` (several allowed), `config """toml"""`, `model
  """grmb"""`, `diff ["path", ...]`, `lease ["glob", ...]`.
- `known-gap` examples document a known miss; they must not fire, and
  they turn into failures when they start firing (so a fix is noticed).
- `example ... fixed """..."""` asserts the output of the rule's fix.
- `grimble rule test` runs every example, prints per-example results,
  and is part of `frob check` for std and repository packs.

## 10. Compile errors (each has a golden test)

| Code | Meaning | Help line shape |
|---|---|---|
| GRL001 | unknown word (kind, field, verb, relation, knob, config column) | did you mean `X`? plus the catalog command |
| GRL002 | snippet does not parse in its language | shows the parse tree it got and suggests `as KIND` |
| GRL003 | variable used in `not`, `no` or `unresolved when` but bound nowhere | add `find v: ...` that says where it comes from |
| GRL004 | variable bound twice | rename one; use `==` to compare |
| GRL005 | type mismatch (string compared with int, glob used as regex) | the expected type |
| GRL006 | language-specific word or plain snippet in a universal rule | use a role, or `as roles`, or narrow `lang` |
| GRL007 | `as roles` snippet contains a node with no universal operator | names the node |
| GRL008 | metavariable used in a fix or message but bound by no snippet | |
| GRL009 | def recursion or forward reference | |
| GRL010 | closure without `within` | add `within knob.depth` |
| GRL011 | missing fire or clean example (or the universal third example) | a scaffold of the missing example |
| GRL012 | explain without `## Remedy` | |
| GRL013 | (warning) variable bound and never used | |
| GRL014 | side relation used but not in `needs` | add it to `needs` |
| GRL015 | fix without applicability, or a plugin fix outside its span | |
| GRL016 | example expectation does not match (a test failure, not a compile error) | the diff of expected and actual findings |
| GRL017 | `certainly` or `possibly` outside positive position | move it out from under `not`, `no`, `unresolved when` or `count` |

Error messages use the user's words, never the theory's: "`d` is only
used inside `no`; add a `find d:` clause" rather than "ungrounded
variable" or "unable to stratify" (P11).

## 11. Tooling

All verbs exist in every product (gob-cli), so frob, grimble and crunk
rules are written the same way.

| Verb | What it does |
|---|---|
| `rule new ID --from FILE:LINE` | scaffolds a rule from real code: the snippet at that line with names turned into metavariables, a fire example from that code, an empty clean example, an explain stub |
| `rule test [PATH]` | runs the examples |
| `rule why ID FILE:LINE` | per-clause trace for one location: candidates, the first failing clause, edges and polarity used |
| `rule check [PATH]` | compiles without running: errors, cost class, prefilter |
| `rule catalog [WORD]` | the relation catalog |
| `rule fmt` | the canonical layout (one clause per line, examples last) |
| `explain ID` | the rule page |

A playground may come later; if it does it runs the same engine
compiled to WASM, never a second implementation (survey L8: ast-grep's
playground and CLI disagree).

## 12. The ten rules, rewritten

These are the acceptance examples: existing rules from the design set
written in this grammar. Each fits on one screen with its tests; the
survey's notes on what was awkward were folded into the language
(`in unit`, `adjoins`, typed side relations, sub-block inputs, the
witness rule, `as roles`).

### TODO001 bare-work-marker

```grl
rule TODO001 "bare-work-marker" {
  lang *
  severity error
  knob markers: regex = /\b(TODO|FIXME|XXX|HACK)\b/ "words that need an owner"

  find c: comment where c.text ~ knob.markers
  where not c.text ~ /\b[A-Z]+\([0-9A-Z]{26}\)/
  no d: directive "todo" where d adjoins c
  report c "bare work marker: file a ticket, then add `frob:todo <ulid>`"

  example fire rust """
    /* TODO tidy this */           //~ error
  """
  example clean rust """
    // frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2
    /* TODO tidy this */
  """
  example clean rust """
    fn a() -> &'static str { "TODO inside a string" }
  """
  example notapplicable json """
    { "note": "TODO" }
  """
  explain """
    A work marker with no ticket is work nobody owns.
    ## Remedy
    File a ticket and put `frob:todo <ulid>` on the marker's line or the line above.
  """
}
```

### DOC002 broken-markdown-link

```grl
rule DOC002 "broken-markdown-link" {
  lang markdown
  severity error

  find l: link where l.target is relative
  def dest_exists(l) = some f: file where f.path == resolve(l.target.path, l.file)
  report l "link target {l.target.path} does not exist" when not dest_exists(l)
  report l "no heading #{l.target.anchor} in {l.target.path}"
    when exists l.target.anchor
     and no h: heading where h.file.path == resolve(l.target.path, l.file) and slug(h.text) == l.target.anchor

  example fire """
    See [gone](missing.md).        <!--~ error -->
  """
  example clean {
    file "a.md" """
      See [b](b.md#intro).
    """
    file "b.md" """
      # Intro
    """
  }
  explain """
    A relative link must point at a file (and heading) that exists.
    ## Remedy
    Fix the path or anchor, or remove the link.
  """
}
```

### COV001 untested-public-function

```grl
rule COV001 "untested-public-function" {
  lang *
  polarity P-  severity warn  scope repo  must_measure
  knob depth: int = 12 "call levels a test may go through"

  find f: function where f is public and not f inside test
  where any { some t: test where t reaches f via calls within knob.depth,
              some t: test where t tests f }
  report f "public {f.kind} `{f.name}` has no test that reaches it"

  example fire rust """
    pub fn double(x: i32) -> i32 { x * 2 }       //~ warn
  """
  example clean rust """
    pub fn double(x: i32) -> i32 { x * 2 }
    #[cfg(test)] mod tests { #[test] fn d() { assert_eq!(super::double(2), 4); } }
  """
  example unresolved python """
    def helper(cb): cb()                          #~ unresolved
    def test_run(): helper(len)
  """
  explain """
    Public callables should be reached by at least one test.
    ## Remedy
    Add a test that calls it, or link one with `frob:tests`.
  """
}
```

Polarity P- means the `where` describes the good thing: the rule fires
when the good thing is No (no test reaches `f` through any edge, and the
closure is complete), is Unresolved when it is Unknown (only May edges
reach it, or the search was truncated at `knob.depth`), and is clean when
a Must path of at most `knob.depth` edges exists. A test at depth 13 with
depth 12 is Unresolved `budget`, never a finding (7.0).

### INV002 forbidden-import

```grl
rule INV002 "forbidden-import" {
  lang *
  severity error  scope repo
  needs config

  find row: config.invariants.forbid_imports              # columns from, to, reason (typed)
  find i: import where i.file.path matches row.from and i.target under row.to
  report i "{i.file.path} imports {i.target}: {row.reason}"
  unresolved when not row.from is valid_glob because "invalid glob in [invariants] forbid_imports"

  example fire python {
    config """
      [[invariants.forbid_imports]]
      from = "src/core/**"
      to = "requests"
      reason = "no network in core"
    """
    file "src/core/a.py" """
      import requests              #~ error
    """
  }
  example clean python {
    config """
      [[invariants.forbid_imports]]
      from = "src/core/**"
      to = "requests"
      reason = "no network in core"
    """
    file "src/core/a.py" """
      import requests_mock
    """
  }
  explain """
    Some modules must not depend on others; the table lives in [invariants].
    ## Remedy
    Remove the import or move the code; change the table only with a decision.
  """
}
```

`under` compares module path segments (`requests` is not under
`requests_mock`), which a string prefix would get wrong.

### SCOPE001 path-outside-lease

```grl
rule SCOPE001 "path-outside-lease" {
  lang -
  severity error  scope repo
  needs diff, lease, config

  find p: diff.changed
  where not p matches lease.globs and not p matches config.lease.shared_files
  report p "{p} is outside the scope lease of {lease.ticket}"
  fix manual "widen the lease with `frob lease widen`, or move the change to a ticket that owns the path"

  example fire {
    lease ["crates/a/**"]
    diff ["crates/b/src/lib.rs"]
  }
  example clean {
    lease ["crates/a/**"]
    config """
      [lease]
      shared_files = ["Cargo.lock"]
    """
    diff ["Cargo.lock"]
  }
  explain """
    A ticket may only change the paths its lease covers.
    ## Remedy
    Widen the lease or move the change.
  """
}
```

`lang -` rules have no source-code examples; their expectations are on
the inputs (a `diff` entry with a finding is expected to fire per entry
unless the example is `clean`).

### SYS001 unowned

```grl
rule SYS001 "unowned" {
  lang *
  polarity P-  severity warn  scope repo  rollup directory
  needs model, config

  find a: artifact where not a.path matches config.grimble.exclude
  where some u: unit where u inside a and some n: node where u owned by n
  report a "no node owns any part of {a.path}"

  example fire python {
    model """node app owns "src/app/**";"""
    file "scripts/legacy.py" """
      def f(): pass                  #~ warn
    """
  }
  example clean python {
    model """node app owns "src/app/**";"""
    file "src/app/a.py" """
      def f(): pass
    """
  }
  explain """
    Every file should belong to a design node.
    ## Remedy
    Add an `owns` selector to a node, or exclude the path in grimble.toml.
  """
}
```

P- makes the `where` the good thing: the rule fires when no unit of the
artifact has an owner even on May facts, and a May-only owner is
Unresolved.

### CAP001 undeclared-capability

```grl
rule CAP001 "undeclared-capability" {
  lang *
  severity error
  needs model

  find c: cell where c.observed and not c.granted and not c.excused
  report c "node {c.node.name} uses {c.atom} without a grant (deny by default)"
  fix host add_grant(c.node, c.atom) [has-placeholders]

  example fire rust {
    model """node frob owns "src/**";"""
    file "src/a.rs" """
      fn serve() { std::net::TcpListener::bind("0.0.0.0:0"); }   //~ error
    """
  }
  example clean rust {
    model """node frob owns "src/**" { may net.listen because="the server"; }"""
    file "src/a.rs" """
      fn serve() { std::net::TcpListener::bind("0.0.0.0:0"); }
    """
  }
  explain """
    Capabilities are denied unless granted (D75).
    ## Remedy
    Add `may ATOM because="..."` to the node, or remove the use.
  """
}
```

The capability matrix is an engine computation (binding.md 7.2); GRL
consumes its `cell` relation rather than re-deriving precedence, excuses
and overlaps. Engine-level relations are in the catalog like any other
word; whether a relation is engine-level or defined in GRL in the std
pack is invisible to rule authors.

### NEAT013 ambient-source-call

```grl
rule NEAT013 "ambient-source-call" {
  lang *
  severity warn
  knob sources: vocab = vocab("clock", "rng", "env", "fs", "net", "stdio", "exit") "ambient sources"

  find fn: function where not fn has attr "frob:shell"
  find c: call where c in unit fn
  where some v: unit where c resolves to v and v in knob.sources
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
  example notapplicable lua """
    local t = os.time()
  """
  explain """
    Calls to clocks, randomness, the environment, files, network or stdio make a
    function impure and hard to test.
    ## Remedy
    Pass the source in as a parameter, or mark the unit `frob:shell`.
  """
}
```

`v` is a witness of `some` (7.1), so the message can name it; an empty
vocabulary makes the (rule, language) pair NotApplicable statically (7.0),
so Lua is not reported clean.

### NEAT031 dispatch-site-owns-logic

```grl
rule NEAT031 "dispatch-site-owns-logic" {
  lang *
  severity advisory
  knob ratio: float = 0.7 "share of statements that are calls or guarded calls"

  def peer_call(s) = s is call and some p: function where s resolves to p and p peer of s.unit
  def guarded_call(s) = s is rust`if $C { $F($$$A) }` as roles and some k: call where k directly inside s and peer_call(k)

  find d: function where not d has attr "frob:dispatcher"
  where count(s: stmt directly inside d where peer_call(s) or guarded_call(s))
        >= knob.ratio * count(s: stmt directly inside d)
  find b: (branch | loop) where b in unit d and not guarded_call(b)
  report b "{d.name} dispatches to peers; this {b.role} does more than guard a call"
  note d "dispatcher by shape"

  example fire python """
    def run(ctx):
        a(ctx)
        if ctx.x:                   #~ advisory
            y = ctx.x * 2
            b(y)
        c(ctx)
  """
  example clean python """
    def run(ctx):
        a(ctx)
        if ctx.x: b(ctx)
        c(ctx)
  """
  example notapplicable json """
    {}
  """
  explain """
    A function that mostly dispatches to its peers should not also own logic.
    ## Remedy
    Move the logic into the callee or a named predicate.
  """
}
```

### CI002 permissions-declared

```grl
rule CI002 "permissions-declared" {
  lang yaml
  severity warn

  find w: file where w.path matches ".github/workflows/*.{yml,yaml}"
  no k: key(path = "/permissions") inside w
  some j: key(path = "/jobs/*") inside w where no p: key(name = "permissions") directly inside j
  report w "workflow has no top-level permissions and job {j.name} declares none"

  example fire { file ".github/workflows/ci.yml" """
    name: ci                                 #~ warn
    jobs:
      build:
        runs-on: ubuntu-latest
  """ }
  example clean { file ".github/workflows/ci.yml" """
    name: ci
    permissions: { contents: read }
    jobs:
      build: { runs-on: ubuntu-latest }
  """ }
  explain """
    Without explicit permissions a workflow token gets the repository default,
    often write access.
    ## Remedy
    Add `permissions:` at the top level or to every job.
  """
}
```

The report names the first job without permissions (the witness rule,
7.1). A workflow that fails to parse makes `no k` Unknown, so the result
is Unresolved, not clean.

## 13. Validating "intuitive"

The owner's condition for one language is that it be intuitive, which a
design document cannot prove. Before the grammar is frozen:

1. **Newcomer test.** Three readers who have never written a lint rule
   (people, or fresh agents given only section 2 and the catalog) each
   write three rules from plain-language descriptions: one pattern rule,
   one with `not ... inside`, one with a relation. Record the time, the
   errors they hit and their first-attempt syntax. Any construct that
   two of three get wrong on the first try is redesigned or gets a
   better error message.
   Round 1 (2026-10-04, three fresh agents given only sections 2-6
   and 9, nine rules): the three plain pattern rules were written
   correctly with high confidence; every low-confidence answer traced
   to five gaps, all fixed above: relations that take a shape
   (`inside function(name = "main")`), the callee name of a call, a
   `reaches` that ends at a call site, snippets for constructs that
   need context (`as KIND` selection), and per-kind fields, language
   ids and comment markers in the catalog. Scoping of outer variables
   in quantifiers and the meaning of `directly` are now stated. Round 2
   runs with people, or with the implemented `rule test`, before the
   grammar is frozen.
2. **Error goldens** for GRL001-GRL017 written before the compiler, so
   the messages are designed, not accidental.
3. **The std pack as corpus.** Every std rule is written in GRL, and its
   source is the first block of its reference page (L12).

## 14. Decisions taken here

1. `find NAME: SHAPE` is the first word of every rule. Rejected
   alternatives: implicit variables (ESLint, Semgrep), which cannot
   scale to relational rules without a second spelling; `for x in`,
   which suggests iteration order. The newcomer test may revisit this.
2. `report ... when` is allowed, tried in text order, one finding per
   binding (DOC002).
3. A `some` variable in a message shows its first witness in source
   order (CI002).
4. Lists on the right of `in`, `~`, `matches` mean any element; there
   is no `any` function form.
5. Engine-level relations (the capability matrix, owner resolution,
   test reachability) are consumed through the catalog, not
   re-derived in GRL.
6. Grammar versions of pattern rules are pinned in the pack lock
   (plugins.md 8); hits on parse-error nodes are Unresolved
   `parse-error`.
7. Fixes that edit other files are host fixes, std only (security.md
   2.10).
