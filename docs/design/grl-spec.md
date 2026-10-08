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
8. **Bounded by construction.** No user recursion, closures are the
   engine's (two-pass and budgeted), the planner orders the work, every
   plan terminates in polynomial time for a fixed rule and reports its
   cost class (L11, P7). A budget
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
| 12 | reaches | `a reaches b via calls within 6` | closure; `within` is a budget |
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
           | "reaches" object "via" VERB_LIST [ "within" term ]
           | [ "certainly" | "possibly" ] VERB object ;
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
| `vocab(NAME)` | value | Q47 | an empty vocabulary is a NotApplicable cell decided per (rule, language) through `needs` (7.0.7); inside a formula it is the empty set |
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

This section is the meaning of a rule; 7.1-7.4 are readings of it for
authors. A rule denotes a function from a structure to an outcome per
binding: [[rule]] : Structure -> (Binding -> Outcome). It is defined
compositionally over the abstract syntax of sections 4 and 5 (the
concrete parse of a quantifier body followed by a connective is fixed by
section 5, ~K0FVJFM; the denotation does not depend on it).

#### 7.0.1 The semantic domain

**Truth values.** K3 = {No, Unknown, Yes}, Kleene's strong three-valued
logic (SEP "Many-valued logic", https://plato.stanford.edu/entries/logic-manyvalued/).
Two orders matter:

- the truth order No < Unknown < Yes, in which `and` is min, `or` is
  max and `not` swaps Yes and No;
- the information order <=_k, in which Unknown <=_k Yes and
  Unknown <=_k No, and Yes, No are incomparable. Unknown is "not yet
  decided", never a third answer.

Every construct below except `certainly` and `possibly` is monotone in
<=_k. That is the property soundness rests on: refining an Unknown input
to Yes or No can refine the output, never flip a Yes to a No (Cousot and
Cousot 1977, https://doi.org/10.1145/512950.512973; Sagiv, Reps and
Wilhelm 2002, https://doi.org/10.1145/514188.514190).

**Structures.** A rule is evaluated over a structure
S = (U, {(R_lo, R_hi)}_R, {D}) where:

- U is the finite set of nodes of the U terms in the rule's scope, plus
  the values their fields take (names, text, numbers, paths);
- for every relation R of the catalog (section 6: containment, position,
  edge verbs, `resolves to`, `tests`, ...) there is a pair
  R_lo <= R_hi of finite relations. A pair in R_lo is certain (a Must
  edge), a pair in R_hi but not R_lo is possible (a May edge). An
  Unknown or unclassified edge out of a node `a` puts `a` on the
  frontier: (a, b) is in R_hi for every b (gob-ir `Relation::unknown_out`,
  the H1 fix ~NZMJSTK);
- each kind `K` names a Bounds domain D_K = (lo, hi, open): lo <= hi are
  the nodes certainly and possibly of kind K, and `open` is true when
  the domain may have members that are not in U at all (an opaque
  region, a partial parse, an Unknown subject answer in scope).

**Adapter hypothesis (H).** For every relation, R_lo <= R_true <= R_hi,
where R_true is the relation in the source; for every domain,
lo <= D_true, and D_true <= hi unless `open`. This is the soundness
contract of universal-model.md 4.4, stated as an inequality. A
concretisation of S is any classical structure C over U (plus hidden
members of open domains) that satisfies the same inequalities;
gamma(S) is the set of them. Under (H) the true source is one of them.

**Atoms.** For a relation R and a tuple t:

    atom_R(t) = Yes      if t in R_lo
                No       if t not in R_hi
                Unknown  otherwise

and for a domain, mem_D(x) = Yes if x in lo, Unknown if x in hi minus
lo, No otherwise.

**Values and counts.** A term denotes a value or `unknown` (a field the
adapter cannot fix, a `const_value` over budget). A number-valued term
denotes an interval [l, h] with 0 <= l <= h <= inf; a known number n is
[n, n].

An environment `eta` maps the variables in scope to elements of U.
[[c]] eta is in K3.

#### 7.0.2 Conditions

| Construct | Denotation [[ . ]] eta |
|---|---|
| `t REL o` (containment, `in unit`, `under`, position, `peer of`) | atom_REL(eta t, eta o). These relations are syntactic, so lo = hi on parsed regions; a pair that touches an `opaque`, `hole` or parse-error node is Unknown. |
| `t VERB o` (`calls`, `imports`, `references`, `resolves to`, `owned by`, `tests`, ...) | atom_VERB(eta t, eta o) over the verb's (lo, hi) pair, frontier included. |
| `t VERB SHAPE`, `t inside SHAPE` (anonymous shape) | [[some x: SHAPE where t VERB x]] eta, x fresh (7.1). |
| `x is KIND`, `x is public`, `x has attr "k"` | the query answer as K3: Yes or No when the adapter answers it, Unknown when its answer is Unknown. |
| `t CMP t'` on values | the classical comparison when both values are known; Unknown when either is `unknown`. |
| `t CMP t'` on numbers | interval comparison of [a, b] and [c, d]: `<` is Yes iff b < c and No iff a >= d; `<=` is Yes iff b <= c and No iff a > d; `==` is Yes iff a = b = c = d and No iff the intervals are disjoint; `>`, `>=`, `!=` by symmetry and `not`. Otherwise Unknown. |
| `t ~ r`, `t matches g`, `t in xs` | classical on known values; a list on the right is the `or` over its elements; Unknown when `t` is `unknown`. |
| `x is SNIPPET` | Yes if the snippet matches the node; No if it does not and the match never inspected a `hole`, `opaque` or unexpanded `phase` node; Unknown otherwise. A metavariable used twice is an equality test, and the equality is alpha-equivalence of U terms (review 3.5). |
| `exists t` | Yes if the value is known to be present, No if known absent, else Unknown. |
| `not c`; `c and c'`; `c or c'`; `any { c1, ..., cn }` | Kleene: swap; min; max; max over the list. |
| `some x: SRC RELS where c` | the `or`, over x in hi(SRC), of mem(x) and [[RELS and c]] eta[x], and additionally `or` Unknown when SRC is `open` (a hidden member might satisfy c). |
| `no x: ...` | `not` of the matching `some`. |
| `count(x: SRC RELS where c)` | the interval [l, h] with l = #{x : mem(x) and [[RELS and c]] = Yes} and h = #{x in hi(SRC) : mem(x) and [[RELS and c]] != No}, and h = inf when SRC is `open`. |
| `t ARITH t'` | interval arithmetic: [a,b] + [c,d] = [a+c, b+d]; [a,b] - [c,d] = [a-d, b-c]; `*` takes the min and max of the four endpoint products (0 * inf = 0). Sound; it loses the correlation between two counts over the same domain (NEAT031), which can only add Unknown. |
| `a reaches b via V within N` | see 7.0.3. |
| `a reaches b via V` (no `within`) | see 7.0.3. |
| `certainly c`, `possibly c` | see 7.0.4. |
| `d(t1, ..., tk)` (def call) | V_d(eta t1, ..., eta tk), where V_d : U^k -> K3 is the def's view: V_d(u) = [[body]] [params := u], computed once per structure and stored. GRL009 forbids recursion and forward reference, so the views form strata in text order. A view has the same meaning as inlining (substitution) and polynomial cost; inlining a chain `d_i = d_{i-1} and d_{i-1}` is exponential (review 2.5 item 1). |

Two consequences worth stating. Evaluating a non-monotone predicate at
the endpoints of an interval is unsound ("count is even" with l = 1,
h = 3 is odd at both ends, but 2 is possible), which is why `count`
offers only interval comparison and arithmetic (Ross and Sagiv 1992,
https://doi.org/10.1145/137097.137852). And `not` needs no special
treatment: because (H) bounds R_true from above, an absent pair is No
only when it is outside R_hi, so `not t calls f` is Unknown, not Yes,
when the only call is a May edge.

#### 7.0.3 Closures

Let E be the union of the relations named in `via`, with E_lo and E_hi.

**Unbounded: `a reaches b via V`.** Two classical least fixpoints, one
per bound: Yes iff (a, b) is in E_lo^+, the transitive closure of the
certain edges; No iff (a, b) is not in E_hi^+ and no node reachable from
`a` in E_hi (`a` included) is on the frontier; Unknown otherwise, with the frontier
nodes as the reason. This is the two-pass computation of
`Relation::closure` (gob-ir eval/relation.rs). It is NOT the
information-order (Kripke-Kleene, Fitting 1985,
https://doi.org/10.1016/s0743-1066(85)80005-4) fixpoint, which leaves an
unfounded loop Unknown even on a closed structure (review 2.2 item 4);
on a closed structure lo = hi and the answer is the classical one.

**Bounded: `a reaches b via V within N`.** Unbounded reaches are legal; N is a budget, not part of
the question: the rule asks whether `a` reaches `b`, and N says how far
the engine may look. Let H_k be the nodes reachable from `a` by at most
k edges of E_hi.

- Yes iff a path of at most N certain edges leads from a to b.
- Otherwise Unknown, reason `may-edge`, if b is in H_N.
- Otherwise Unknown, reason the frontier, if some node of H_N is on the
  frontier.
- Otherwise No if H_(N+1) = H_N: the possible-edge search was
  exhausted within N steps, so no path of any length exists.
- Otherwise Unknown, reason `budget`: the search was truncated.

A certain path longer than N therefore gives Unknown `budget`, never No.
This is what keeps COV001 honest (review 2.4): a test that reaches `f`
at depth 13 with `within 12` makes the binding Unresolved, not a fire.
The cost is O(N * |E_hi|) per source.

When `b` is a call site, the closure ends at the unit containing it
(7.1).

Because an unbounded `reaches` is a two-pass fixpoint and always
terminates, GRL010 (closure without `within`) is retired (section 10).

#### 7.0.4 `certainly` and `possibly`

    [[certainly c]] = Yes if [[c]] = Yes, else No
    [[possibly c]]  = No  if [[c]] = No,  else Yes

They collapse Unknown, so they are not monotone in <=_k, and no
positional restriction alone makes them sound: in a positive position of
a P+ rule, `certainly` turns a May edge into No and certifies clean on a
guess, and `possibly` fires on a guess. Two rules together make them
sound:

1. **Position (GRL017).** They may occur only in positive positions:
   under an even number of `not` and `no`. Inside an `unresolved when`
   condition they are allowed, because that condition only adds doubt.
   This keeps each word meaning what it says (`certainly` can only
   remove fires, `possibly` can only add them).
2. **Collapse is an assumption.** Let V1 be the binding's value as
   defined above and V0 its value with every `certainly` and `possibly`
   read as the identity. Then V0 <=_k V1 (induction on the formula:
   both operators send a definite value to itself and every other
   construct is monotone), so a collapse can turn Unknown into a
   definite answer but never flip one. When V0 is Unknown and V1 is
   definite, the outcome is a conditional answer with reason
   `assumed:certainly@<span>` or `assumed:possibly@<span>`, as for
   unverified claims (7.0.6). A conditional fire is capped at Advisory.

#### 7.0.5 From value to outcome: polarity

A binding is an assignment of the `find` variables. Each `find x: SRC`
ranges over hi(SRC); the binding's value is

    F(eta) = (and over finds of mem(x)) and (and over where and quantifier clauses) and W

where W is the `or` of the `report ... when` conditions (W = Yes when a
`report` has no `when`). If a `find` source is `open`, the hidden
members are one Unresolved per opaque region, as in universal-model.md
4.2 subject accounting (vacuous, opaque subjects and `must_measure` are
unchanged). The polarity maps F to the outcome; no author code is
involved:

| Polarity | F = Yes | F = Unknown | F = No |
|---|---|---|---|
| P+ (the formula describes the bad thing) | fire | Unresolved | clean |
| P- (the formula describes the good thing) | clean | Unresolved | fire |

P0, Pn and Pc are the P+ map over a restricted formula: P0 is the P+ map
over an equality, and its formula is an equality or inequality of values (Unresolved unless both sides are
known), Pn's is an interval comparison of a count with a limit (max-type
`count > N` fires iff l > N and is clean iff h <= N; min-type
`count < N` fires iff h < N and is clean iff l >= N), Pc's is a closure
atom (7.0.3). The headers stay because they fix the formula shape GRL
accepts and the wording of the Unresolved message.

The reasons of an Unresolved are the reasons of the Unknown leaves F
depends on: `may-edge`, the frontier, `budget`, `parse-error`,
`opaque:<reason>`, `capability gap:<cap>`, `conflict:<a>-vs-<b>`
(universal-model.md 4.4.1), `assumed:<claim>`. A Belnap conflict between
two sources of one fact is resolved by the knowledge meet over the whole
fact, so the dependent answer is Unresolved with reason
`conflict:<a>-vs-<b>`. `rule why` prints them,
clause by clause; this is why-provenance (Green, Karvounarakis and
Tannen 2007, https://doi.org/10.1145/1265530.1265535) with a Must/May
annotation.

**`report ... when`.** In a P+ rule (and P0, Pn, Pc) a firing binding
uses the first `report` in text order whose `when` is Yes; earlier
clauses whose `when` is Unknown are attached as notes ("may also: ...").
A firing binding always has such a clause, because F = Yes implies
W = Yes. `report ... when` in a P- rule is a compile error (the next free GRL
code; no rule in section 12 needs it, and its message selection has no
sound reading when F is No).

**Witnesses.** A message names the first witness in source order whose
`some` body is Yes; an Unresolved message names the first whose body is
Unknown, as "possible witness".

**`unresolved when C because "r"`.** If [[C]] is Yes or Unknown for a
binding, its outcome is Unresolved with reason r, replacing fire or
clean.

#### 7.0.6 Conditional answers

An atom whose lo or hi bound rests on an UNVERIFIED claim (a
`grimble:effects` claim on an unanalysable body, an annotation without
checker closure, a `frob:calls` directive that narrows an Unknown
resolution) is evaluated with the claim, and every outcome whose
definiteness depends on it is conditional, with reason
`assumed:<claim>` (cohesion.md D121; D119's rule that an unverified
claim never narrows hi on its own). Dependence is decided as for
`certainly` in 7.0.4: evaluate once without the claim; if that value is
Unknown and the value with the claim is definite, the outcome is
conditional. A conditional clean counts as clean in check and CI and as
Unresolved at the release gate (D121). A conditional fire is emitted as
Advisory with the assumption in the message, never as Error or Warn
(universal-model.md Theorem 3(b) is about Error and Warn).

#### 7.0.7 NotApplicable is not a value

K3 has three values; there is no fourth. NotApplicable is a property of
a (rule, language) pair, decided before evaluation from the capability
matrix (gob-caps):

    needs(rule) = the capabilities declared in `needs`
                  plus the capability of every `find` source's kind
    App(rule, L) = NotApplicable                  if some cap in needs(rule) is NA in L
                   Unresolved("capability gap:c")  else if some cell c is a gap in L
                   Applicable                      otherwise

Inside a formula, a kind or relation whose cell is NA in L denotes the
empty set exactly (lo = hi = empty, not open). So `not d inside test` in
a language with no test convention is Yes, which is the classical
answer, and a P- rule that quantifies over tests (COV001) is excluded
by declaring `needs test_items`, not by a value that silently erases
every subject. An empty vocabulary is the same: a rule that is
meaningless without `vocab(NAME)` declares it in `needs`; otherwise
`v in knob.sources` is simply No. GRL018 is the compile-time special
case: a word that no language in `lang` answers can only ever be empty.
A NotApplicable pair produces no finding and is counted once per
language in the fidelity report (7.2).

#### 7.0.8 Cost

GRL is non-recursive first-order logic with counting over finite
relational structures, plus the engine's closures and external
relations: in database terms, non-recursive Datalog with stratified
negation and aggregation (universal-model.md 4.3). Such languages are
local and cannot express reachability (Libkin 2003,
https://doi.org/10.1016/s0304-3975(02)00736-3), which is why `reaches`
is a built-in.

- **Data complexity is polynomial for a fixed rule, when defs are
  materialised views (7.0.2).** A clause with k simultaneously live
  variables costs at most O(|U|^k) over stored relations; an unbounded
  closure is two graph searches per source, O(|V| * (|V| + |E|)); a
  bounded one is O(N * |E|) per source.
- **Engine relations are the engine's cost.** `cell`, owner resolution,
  `resolves to`, `const_value` and the closures each run under a stated
  budget; an overrun is Unknown with reason `budget`.
- **Snippets.** Matching a snippet whose metavariables each occur once
  is linear in the tree for a fixed pattern (such patterns are regular
  tree languages: Thatcher and Wright 1968,
  https://doi.org/10.1007/bf01691346; Doner 1970,
  https://doi.org/10.1016/s0022-0000(70)80041-1). A repeated SEQUENCE
  metavariable (`$$$XS` used twice) makes matching NP-complete in the
  size of the pattern (Angluin 1980,
  https://doi.org/10.1016/0022-0000(80)90041-0; Ehrenfeucht and
  Rozenberg 1979, https://doi.org/10.1016/0020-0190(79)90135-2); it is
  polynomial, n^k for k such variables, only for a fixed pattern. GRL
  therefore bounds them: a snippet may repeat at most two sequence
  metavariables (proposal: a new compile error, the next free GRL
  code), and every match runs under the rule's budget.
- **Combined complexity is not polynomial.** For the first-order core
  it is PSPACE-complete (Vardi 1982, https://doi.org/10.1145/800070.802186),
  and the plan validator's limit of 1024 variables makes "polynomial"
  meaningless for a hostile pack. The runtime budget is the guard, and
  `grimble rule check` reports, besides per file, per repository and
  closure depth, the plan's width: the largest number of simultaneously
  live variables. Joins are bounded by the AGM bound (Atserias, Grohe
  and Marx 2008, https://doi.org/10.1109/focs.2008.43), and acyclic
  joins run in time linear in input plus output (Beeri, Fagin, Maier and
  Yannakakis 1983, https://doi.org/10.1145/2402.322389).

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
- `a reaches b via calls within N` asks whether `a` reaches `b`; N is a
  budget on the search, and a longer path gives Unknown `budget`, never
  No (7.0.3). `b`
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
  rule has several `report ... when` clauses, the first in text order
  whose `when` is Yes produces the finding and earlier clauses whose
  `when` is Unknown become notes, so one binding never yields two
  findings (survey 8.6, 7.0.5). `report ... when` is a compile error in
  a P- rule.
- **Witnesses.** A `report` message may name a variable bound by `some`;
  it shows the first witness in source order (file path, then byte
  offset) whose body is Yes, or Unknown for an Unresolved message,
  which is deterministic (7.0.5).
- Lists on the right of `in`, `~` and `matches` mean "any element":
  `p matches lease.globs` is true if any glob matches. There is no
  second spelling.

### 7.2 Three values and polarity

Every condition evaluates to Yes, No or Unknown (Kleene's strong
three-valued logic, 7.0). Sources of Unknown: May edges, the Unknown
frontier of a resolution, Unknown visibility, partial parses, opaque
regions, budget overruns (including a `within` bound), and source
conflicts (`conflict:<a>-vs-<b>`). NotApplicable is not a value: it is
decided per rule and language before evaluation (7.0.7).

The rule's polarity (default P+) maps the three-valued value F of each
binding (7.0.5) to its outcome, with no author code:

| Polarity | Shape of the formula | F = Yes | F = Unknown | F = No |
|---|---|---|---|---|
| P+ (a bad thing exists) | any | fire | Unresolved, naming the Unknown atoms | clean |
| P- (a good thing is missing) | any; the formula describes the good thing | clean | Unresolved, naming the Unknown atoms | fire |
| P0 (a fact or an equality) | equality or inequality of values | fire | Unresolved unless both sides are known | clean |
| Pn (a count crosses a limit) | interval comparison (7.0.2) | fire (max-type: l > N; min-type: h < N) | Unresolved | clean (max-type: h <= N; min-type: l >= N) |
| Pc (a closure property) | closure atom (7.0.3) | fire (a path of certain edges) | Unresolved, naming the frontier | clean (no path even through possible edges) |

The formula is evaluated once, in K3, with May edges and Unknown
answers as Unknown atoms; no clause chooses an edge set. `certainly`
and `possibly` collapse Unknown; they are allowed only in positive
positions (GRL017) and an answer that depends on the collapse is
conditional, capped at Advisory when it fires (7.0.4). `unresolved when COND because "reason"` adds doubt the
engine cannot see (a malformed config entry). Hits on parse-error nodes
and absence claims over partially parsed files are Unresolved with
reason `parse-error`. NotApplicable never produces a finding; it is
counted once per language in the fidelity report.

`grimble rule why` and `explain` always print the polarity and, for
each clause, its value and the atoms that made it Unknown ("Unknown
because `t calls f` is a May edge at a.py:12; under `not` this keeps
the rule Unresolved"), so the invisible part of the semantics is
visible on request (survey 8.5 item 7).

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
a later one (GRL009). An unbounded `reaches` is an engine closure
(two-pass fixpoint) and `within N` is a budget (7.0.3); GRL010 is
retired. Counts and arithmetic are over finite sets. Every plan
therefore terminates, in polynomial time for a fixed rule with defs as
materialised views; combined complexity is not polynomial and the
budget is the guard (7.0.8, universal-model.md 4.3).
`grimble rule check` prints the plan's cost class (per file; per
repository; closure depth N), the plan's width (the largest number of
simultaneously live variables) and its prefilter (the node kinds a file
must contain for the rule to run), and a run over its budget reports
Unresolved `budget` (plugins.md 6.5).

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
| GRL010 | (retired 2026-10-08) closure without `within` | none: an unbounded `reaches` is a legal two-pass fixpoint and `within N` is a budget, not part of the question (7.0.3, D123) |
| GRL011 | missing fire or clean example (or the universal third example) | a scaffold of the missing example |
| GRL012 | explain without `## Remedy` | |
| GRL013 | (warning) variable bound and never used | |
| GRL014 | side relation used but not in `needs` | add it to `needs` |
| GRL015 | fix without applicability, or a plugin fix outside its span | |
| GRL016 | example expectation does not match (a test failure, not a compile error) | the diff of expected and actual findings |
| GRL017 | `certainly` or `possibly` in a negative position (under `not` or `no`) | "move it out of the negation, or drop the word: the rule's polarity already decides whether Must or May edges count" (7.0.4) |
| GRL018 | a word no language of `lang` answers (the rule would be NotApplicable everywhere) | add a language that answers it to `lang`, or remove the clause (7.0.7) |

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
when no test reaches `f` even through May edges, is Unresolved when only
May edges reach it, and is clean when a Must path exists.

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
  needs vocab(sources)
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

`v` is a witness of `some` (7.1), so the message can name it; NEAT013
declares the vocabulary in `needs` (`needs vocab(sources)`), so Lua is NotApplicable for the
rule as a whole and not reported clean; inside the formula an empty
vocabulary is the empty set (7.0.7).

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
2. **Error goldens** for GRL001-GRL018 written before the compiler, so
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
