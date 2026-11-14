# The .grmb language specification

Status: draft
Owner: grimble
Decisions: D6, D58, D65, D70-D74, D77, D124-D133, D139-D207
Audience: rule author

Related grimble specs: [GRL](../shared/grl-spec.md), [capabilities v3](grimble-capabilities-v3.md), [binding](binding.md), [rule families](rule-families.md), [vet](../shared/charter.md#4231-grimble-vet-implemented).

The one normative specification of the .grmb language: the architecture
layer (G01, ticket 01M3Z712GP8XV2WEAS1VHQ7FD4) and the planning layer
(tickets ~83H49E3, ~T5VVDBY), merged into this file by the cycle 1 fix of
ticket ~MHGA5VN. Every design change since cycle 1 cites
[the evidence record](../../../notes/research/grmb-evidence/evidence.md); the
cycle log is [cycles.md](../../../notes/research/grmb-evidence/cycles.md).
Decision text lives only in [decisions.toml](../../decisions/decisions.toml);
the headings at the end of this file are its anchors. Worked mockups live
in [the corpus](../../../notes/research/grmb-corpus/README.md); this file keeps
one example (18.2). Sections 12-15 live in [planning-semantics.md](planning-semantics.md) and section 18 in [conformance.md](conformance.md), with their numbers unchanged (so a citation "12.8" or "18.3" still names the same section). Ids: `Cnn` cites an item of
notes/research/grmb-r1-synthesis.md, `Enn` and `Un` (corpus counts) a row
of the evidence record, `Dnnn` a decision.

Inputs: the model overview (sections 20-21 below),
shared/universal-model.md (sections 2, 3 and 5), shared/rules.md, shared/code-model.md
section 4 (the directive grammar), binding.md (the relation B and the SYS
rules), shared/sibling-contract.md 3.7 and 3.8, frob/tickets.md (the `implements`
link and close guards), notes/research/grmb-r1-synthesis.md and the two R2
notes (grmb-r2-faults.md, grmb-r2-verification.md).

## 1. Purpose and scope

A `.grmb` file declares a MODEL: a typed architecture graph of nodes,
flows, contracts, claims and V-model links, each of which binds to code
identities in any language (docs/design/grimble/binding.md section 13), and a planning layer
of systems, actors, goals, scenarios of typed steps, impls and pages
(sections 11-15). The language exists for three jobs and nothing else:

1. Declare intent and ceilings: what owns which code, what each owner
   may do, which data may move where, what is claimed about the system
   and what evidence backs it.
2. Give the kernel (docs/design/grimble/grmb-spec.md section 20.1) a closed, typed input:
   label closure over flows, claim verdicts, V-model closure.
3. Give frob and the editor a file in which a `frob:doc` or
   `frob:ticket` directive binds to an entity exactly as it binds to a
   function (docs/design/grimble/grmb-spec.md section 20.2).

Design stance, kept from v1 and the owner's direction: the grammar holds
only what v1 consumers measurably used (node, flow, boundary, claims, the
V-model, capability grants, matrix-build templates, exceptions). Everything else is a
DATA PACK.

A DATA PACK is a versioned, digest-pinned bundle of TOML under `packs/`
(packs-and-plugins.md) contributing atoms, detectors, obligations, node kinds, unit
aliases and rule parameters, referenced by a `pack` entity (4.6). A pack
NEVER contributes grammar, so the keyword table of 2.6 is the complete
input of the parser and of the editor grammar generator.

Non-goals. `.grmb` is not a programming language: no expressions beyond
selectors, no functions, no loops, no conditionals, no macros (so the
U encoding of section 9 never needs `phase`). It does not describe
runtime behaviour in general (the six-phase boundary blocks, sagas,
crash and breach scenarios, hosts, Kerberos, `refine`,
`entity/architecture`, `policy` and the `scenario` of v1 are not in the
language), because v1's behaviour constructs never reached the prover.

### 1.1 Layers

The planning layer (D124) re-admits behaviour in one checkable form: a
typed outcome per step and exhaustive handling, so that a design change
(a new failure variant) propagates like a compile error and becomes a
ticket. It does not describe timing, concurrency or state machines
(section 19).

The left arm of the V, each level more specific than the one above:

| Layer | Construct | UML analogue | Binds to |
|---|---|---|---|
| 0 | `system`, `actor` | system boundary, actors | - |
| 1 | `goal` variant tree | use cases, include, precedence | tickets (epics) |
| 2 | `scenario` of `step`s with outcome variants | activity and sequence diagrams, alternate and exception flows | tickets (stories), acceptance tests |
| 3 | `impl STEP for SCENARIO`, `page` | realization, components, navigation | code selectors, tickets (tasks), unit tests |
| 4 | code | - | symbols (binding.md) |

The V-model level of each construct is the one table of 13.3.

The right arm: every entity may carry `verified_by SELECTOR;`, the one
evidence clause (8.3, D150). The V-model level of a planning entity comes
from its construct kind, so the kernel's closure rules apply without
hand-written `vmodel` entities (13.3); `vmodel` stays for doc-anchored
artifacts.

## 2. Lexical structure

### 2.1 Encoding and lines

- Files are UTF-8 without a byte-order mark. Invalid UTF-8, a BOM or a
  NUL byte makes the whole file `opaque(reason=not-utf8)` in U (section
  9) and one MDL000 finding; nothing else is read from it.
- Line terminators are LF or CRLF; a bare CR (one not followed by LF) makes the whole file
  `opaque(reason=binary)` and one MDL000 finding, as for invalid UTF-8. `grimble fmt`
  writes LF and exactly one final newline.
- Tabs and spaces are whitespace. Whitespace separates tokens and is
  otherwise insignificant.
- Identifiers and keywords are ASCII. Strings and comments may hold any
  UTF-8 (this repository keeps its own files ASCII by project rule; that is
  not a property of the language).

### 2.2 Tokens

```
ident      = ( ALPHA | "_" ) { ALPHA | DIGIT | "_" } ;
number     = DIGIT { DIGIT } [ "." DIGIT { DIGIT } ] ;
quantity   = number , [ WS ] , unit ;          (* "30 s", "5 req/s", "4KiB" *)
date       = DIGIT DIGIT DIGIT DIGIT "-" DIGIT DIGIT "-" DIGIT DIGIT ;
string     = '"' , { char | escape } , '"' ;
escape     = "\\" ( '"' | "\\" | "n" | "t" | "r" | "u{" HEX { HEX } "}" ) ;
punct      = "{" | "}" | "(" | ")" | "[" | "]" | ";" | "," | ":" | "::"
           | "." | "=" | "->" | "<=" | "&" | "|" | "!" | "~" | "!="
           | "=>" | "-!>" | "*" ;                (* planning tokens, D125 *)
raw_ident  = "r#" ident ;                        (* identifier escape, D155 *)
```

The planning tokens `=>`, `-!>` and `*` are taken by maximal munch; each
was a lexical error (MDL000) before, so their addition is valid within
major 2 (3.4). `->` is never a prefix of a new token (`-!>` differs at the
second character), and `!` keeps its selector meaning: `a -!> b` never
lexes as `a - ! > b`. `*` is a token only in an impl header (`for *`);
inside a selector it is a glob character within a string. `r#` was a
lexical error before as well (`#` is no token), so the escape is additive.

One token, one meaning (D152, evidence E24, E39):

| Token | Meaning, everywhere it appears |
|---|---|
| `->` | follows or moves to: flow and claim endpoints `A -> B`, a scenario link |
| `-!>` | follows on `ok`, collecting every other variant (12.3) |
| `=>` | maps a pattern to its consequence, read left to right: a match `e => { arms }`, an arm `pattern => chain;`, an outcome-map entry `source => variant;` |
| `:` | has kind or type: node trust, flow endpoints, actor kind, step outcome type |
| `*` | every scenario, in `impl S for *` |

One keyword, one meaning, for the words that appear in several clauses
(D176):

| Word | Meaning, everywhere it appears |
|---|---|
| `for` | restricted to: `impl S for SC` (to one scenario), `verified_by ... for PAIR` (to one arm), `excuse A for SEL` (to a selection) |
| `kind` | the kind of this thing: node kind, vmodel kind, `kind(...)` unit-kind predicate |
| `on` | about or at a target: `accept R on REF`, `attests ... on NODE`, `on page P` |
| `in` | located in: `in node N` on an actor or an impl |
| `as` | renames a prefix: `use ... as P` only |

- A string contains no raw newline; a multi-line text is written as
  adjacent strings joined by the parser (`"a" "b"` is `"ab"`) only in
  value position, never in a selector. There are no raw strings.
- `date` is an ISO calendar date, UTC, validated (month 01-12, day valid
  for the month). It is the only date form (`until=`).
- A `quantity` is a number followed by a unit from the CLOSED table
  below. The unit may be attached (`30s`) or separated by blanks
  (`30 s`); `grimble fmt` prints one space, except `%` which is
  attached. A unit outside the table is MDL009. The table is closed
  because a unit is a type, as in v1; a pack may add an alias for an
  existing unit but not a dimension.

| Dimension | Unit tokens | Notes |
|---|---|---|
| time | `ns` `us` `ms` `s` `min` `h` `d` | durations (`age`, `timeout`) |
| size | `B` `KiB` `MiB` `GiB` `TiB` | binary prefixes only |
| count | `req` `msg` `evt` `op` | dimensionless counts with a name |
| ratio | `%` | |
| rate | `<count or size or ratio>/<time>` | `req/s`, `KiB/s`, `%/month` is not valid: `month` is not a unit, write `%/d` |

Comparison and arithmetic across dimensions is MDL009. Values are
normalized only by the printer's choice of spelling, never converted
(`1000 ms` stays `1000 ms`); the U `lit(kind=quantity)` carries the
lexeme and the kernel converts to base units when it reads it.

### 2.3 Comments and directives

- `// text` runs to end of line. `/* text */` may span lines and nests.
- `/// text` is a doc comment: prose attached to the next item; it
  becomes the Doc facet of that item (section 9). It carries no
  directives.
- A DIRECTIVE is a comment line (in a `//` comment or on a line of a
  `/* */` comment after an optional leading `*`) whose text starts with
  `<namespace>:<verb>`, exactly the rule of docs/design/shared/code-model.md section 4:
  text before the verb on that comment line makes it prose; backslash
  continuation and `frob:quote(...)` work as there; a malformed
  directive is never silently dropped (DSL findings under the parsing
  product's namespace). The directive parser is the shared
  `gob-directives` parser; .grmb defines only where a directive binds
  (section 8) and which verbs it accepts.
- Comments are trivia: they do not appear in the token stream the
  grammar sees and are attached to items by the rule in 8.1.

### 2.4 Line and block structure

Statements end with `;`. A block is `{ ... }`. Nothing is
line-oriented: a statement may span lines and several may share one. A
file is an ordered list of items for printing purposes only; the model
that results is order-independent (section 3.3).

### 2.5 Indentation policy

Indentation carries no meaning. `grimble fmt` prints two spaces per
nesting level, one clause per line, closing brace on its own line, and
wraps a line longer than 100 columns by breaking after `|`, `&` or
`,` with a continuation indent of four spaces. `grimble check` never
reports style: a badly indented file is a `grimble fmt --check`
difference (exit 1), not a rule finding.

### 2.6 Keywords

One table, the single source of the generated editor grammar and of the
parser's word lists (`cargo dev gen editors` reads it from the `Keyword`
derive in grimble-model; D155, evidence E2-E4, E18-E21). Classes:

- RESERVED: a keyword in every position; an identifier equal to one is
  MDL000 unless escaped.
- ITEM HEAD (contextual): a keyword at item position only (top level,
  inside `namespace`, inside a `system` body); an identifier elsewhere.
  An item position never started with an identifier before, so these were
  additive within major 2 (D125).
- PLANNING WORD (contextual): a keyword inside the header or body of a
  planning item only; an identifier everywhere else. Inside planning
  items it is reserved: a planning entity, variant or error name equal to
  one is MDL031 unless escaped.
- DEPRECATED (contextual): a word the parser still recognizes only to
  read a bridged major-2 spelling (11.1) and report MDL012; it is listed
  once, in the scope where the old spelling occurred.
- MARKER: recognized in one slot only (`outside` after a `use` path;
  `lang` as a selector predicate head). `kind(` and `attr(` are the
  reserved words `kind` and `attr` followed by `(`, decided by position.

| Class | Words |
|---|---|
| reserved | `accept age allocates alias as assumed at attests attr blocked_by bound boundary claim clearance condition consumer contract declassify decides defer digest endorse evidence excuse excuses extend fanout flow for growth hotfix include kind label latency level manual may module namespace node never noflow of on owns pack part policy producer proof provides rate reach ref refines renamed_from runnable satisfies shape size supersedes surface template tests transport use utilization verifies version versioning via vmodel when` |
| item head | `system actor goal step scenario impl page use` (`system` and `page` are also planning words, next row) |
| planning word | `_ ambient chain closed else end entry err escalate exclusive fails from handle idempotent in max non_goal ok one_of open page realizes requires restart retry sorry system terminate unknown verified_by with within` |
| deprecated (words and keys recognized only to report MDL012) | `title` (planning word; `title "t";` is MDL012, D159); the attribute key `review=` (MDL012, D160; the one key the parser must recognize). `evidence`, `runnable`, `tests` (reserved above) carry the deprecated evidence spellings (8.3) |
| marker | `outside` (after a `use` path); `lang` (selector predicate head) |

Notes. `noflow`, `reach`, `never` and `attests` are claim verbs and metric names
after `bound` are `age`, `rate`, `latency`, `size` and `utilization`, all
reserved. `evidence`, `runnable` and `tests` stay reserved for the
deprecated evidence spellings (8.3), `excuses` for MDL018 (4.8) and
`provides` for capability providers (grimble-capabilities-v3.md).
`verified_by` is a planning word inside planning items and a clause word
in every entity body (8.3). Attribute keys (`because=`, `ticket=`, `until=`, `owner=`,
`scheme=`, ...) are recognized only before `=` and are never keywords.
`via` is reserved for the capability grant (`may ... via SELECTOR`, 4.1)
and the `grimble:binds ... via=` key; it has no planning meaning. `system`
is an item head at item position and a planning word inside planning
items, where `system.X` names a reaction step (11.2). Words that left the
language in cycle 1 with NO bridge (never parsed by P1, so MDL000 like any
unknown word): `budget` (D158), `outcome` and the waypoint `via` (D152). A pack realization kind or actor kind equal to any word of this
table is refused when the pack loads (MDL031 on the pack reference),
because `chain {` and `KIND {` could not otherwise be told apart (E2).

Rev 2 audit (~4APZQA2). Every contextual word the rev 2 productions of
11.1 and 15 introduce (`chain sorry unknown open closed one_of exclusive
non_goal ambient idempotent`) is a row of the planning-word class above
and of `PLANNING_BODY_WORDS` in grimble-model, and the test
`crates/grimble-model/tests/it/keywords.rs` parses this table against the
code. `outcome` and the waypoint `via` are not keywords (they left the
language with no bridge, D152); `via` stays reserved only for capability
grants. Each invented spelling of the former corpus GAPS.md is either
defined in 11.1 or 15, or rejected as MDL000 or MDL012 as noted in 11.1.

ESCAPE. `r#name` is the identifier `name` anywhere, so older models keep
working (E4; C# `@field` E19, SysML `'name'` E24); fmt prints it only
where the bare word is a keyword.

### 2.7 Names

```
name   = ident ;                          (* an entity or namespace name *)
qname  = name { "." name } ;              (* a dotted path *)
ref    = [ "::" ] qname ;                 (* "::" anchors at the model root *)
atom   = [ ident "::" ] ident { "." ident } ;  (* capability atom, pack-qualified *)
```

Entity names are snake_case by convention and case-sensitive. Rule ids
are written in their id form only (`SYS004`, `CAP001`; a token matching
`[A-Z]+[0-9]+` is a `rule` token); slug aliases are not accepted (MDL000)
so a model never depends on a rename of an alias. There are no string
entity names: v1's claim ids such as `"weakness:CWE-78:vet"` are carried
by a pack-generated `attr id` on an identifier-named claim.

Planning names follow the same rules: dotted refs, never `::` paths
(`web_app.customer.place_order`); no string names and no `let`
bindings. A human label is a `///` doc comment (D159).

## 3. Files and `use`

The model follows the Rust crate model (owner decision D77): a crate root
by convention that `Cargo.toml` can override, modules reachable only
through `mod` declarations from the root, `mod foo;` resolving to a file
next to the declaring file, and `#[path]` as the explicit escape hatch.
Here the root is listed in `grimble.toml`, files join the model only
through `use`, a `use` resolves at or below the including file's
directory, and the `outside` marker is the `#[path]` analogue. Where
rustc silently ignores an unreachable file, grimble fails loudly (3.1).

### 3.1 Roots: one model from one declared entry

A MODEL is the set of files reachable from one ROOT file through
`use`. Roots are declared by the materialized enforcement knob

```
[grimble]
models = ["design/model.grmb"]      # the default; `grimble init` writes it
```

- grimble-check loads ONLY the files reachable from the listed roots. It
  never loads every `.grmb` file of the walk; the walk only supplies the
  candidate set and the paths a root may reach.
- A repository may list several roots; each is a separate, independent
  model with its own namespace and no reference crosses a root (section
  14; declared cross-model dependencies are out of scope). Two roots that
  declare one module name are MDL011.
- If `models` is empty, or names a file that is not a `.grmb` file of the
  walk, while `.grmb` files exist, the run reports one Unresolved MDL021
  per problem. It is a REQUIRED Unresolved (the gate fails, reason
  `zero-subjects: MDL021`) telling the user to declare a root. A
  repository with no `.grmb` file at all reports nothing.
- ORPHANS: a `.grmb` file of the walk that no root reaches and that
  `[check] exclude` does not exclude is MDL019 (Warn), naming the file and
  the three remedies: `use` it from a root, list it as a root, or
  exclude it. (Not reported while MDL021 holds, which already says no model
  is loaded.)

Every file in a model starts with the version header (3.4) and then one
of:

```
module frob;          // exactly one per model, in the root file
part of frob;         // every included file; the name must equal the root's
```

A mismatch is MDL011. `grimble init` seeds `design/model.grmb` as
`grimble = "2"; module model;` when the repository has no model file.

### 3.2 `use` semantics

```
use "gob.grmb";                       // one file, at or below this directory
use "services/*.grmb";                // a glob (path glob of section 6.2)
use "api.grmb" as api;                // mount under the prefix api
use "../shared/x.grmb" outside;       // explicitly climbing out (below)
use "../shared/*.grmb" as s outside;  // marker comes last, after `as`
```

Grammar: `use STRING [ "as" REFPATH ] [ "outside" ] ";"`. `outside` is
the only word recognized after the path and is not otherwise reserved
(it stays a valid identifier elsewhere).

- LOCATION MIRRORS HIERARCHY. A `use` may name only files at or below
  the directory of the including file (the way `mod foo;` finds `foo.rs`
  next to the declaring file). A `use` that climbs out is MDL020 and is
  skipped, unless it carries `outside`. Climbing means any `..` segment in
  the written path, or a resulting path (a leading `/` anchors the path at
  the repository root) that is not at or below the including directory.
  Globs follow the same rule: the pattern is checked as written and every
  file it matches must be at or below the including directory. `outside`
  on a `use` that does not climb is accepted and does nothing.
- Paths are POSIX, resolved relative to the directory of the including
  file (a leading `/` is relative to the repository root, never to the
  file system), and must stay inside the repository (a path that leaves it
  is MDL002 even with `outside`; so is a backslash). A glob expands to its
  files in byte-wise lexicographic order; a glob that matches nothing is
  MDL002 (a `use` that names a file that is missing is an error, a
  selector that matches nothing is a warning: `use` is structural,
  selectors are intent).
- A file is read once per model however many times it is used
  (identity by normalized path). The same file used under two
  different `as` prefixes is MDL001 on the first duplicate entity.
- `use ... as P` MOUNTS the file: every top-level entity and
  namespace the file declares gets the prefix `P.` (section 5.2). `as`
  is not allowed on a glob that matches more than one file.
- CYCLES ARE REFUSED. The `use` graph is walked depth first with the
  active stack; reaching a file on the stack is MDL003 naming the cycle,
  and the offending `use` is skipped so the rest of the model still
  loads. A diamond (two files including a third) is not a cycle.
- `use` is the only cross-file mechanism; there is no `import`,
  `export` or `layer` (v1 parse-only forms, dropped). A file that is
  used is a file of the model; one that is not reached is an orphan
  (3.1).

A `use` is a TOP-LEVEL item: written inside a `namespace` or `system`
body it is MDL000 (D181); a prefix comes only from its own `as`.

The spelling `include "path"` of the same item is the major-2 form,
accepted unchanged and reported MDL012 (Warn, deprecated spelling)
through major 2 (the bridge of 11.1); `grimble fmt` prints `use` (D156). `include` keeps exactly one
meaning, scenario invocation inside a chain (12.3); SysML v2 keeps
`include` for use-case inclusion too (E24), so the file form is the one
renamed.

### 3.3 Order independence

The semantics of a model does not depend on the order of items within a
file, on the order of files in an include list, or on which file
declares what. Merge is set union of entities plus additive `extend`
clauses (4.9). Consequently `grimble fmt` may sort items, and a model
split across files is the same model as one file with the same items.
The only ordered things are comments (they travel with the item they are
attached to) and the lexicographic expansion order of globs, which
affects diagnostics only.

### 3.4 Versioning header

```
grimble = "2";
```

- First statement of every file (comments may precede it and bind to the
  file module unit, 8.1). The value is the LANGUAGE major version as a
  string. Missing header or a major this binary does not read is MDL007
  and the file is refused whole (never parsed on a guess).
- All files of one model must carry the same value (MDL007). While only
  major 2 is read every other value is an unsupported major, so the
  mismatched-majors case is unreachable until a second major exists.
- Within a major version, additions only make previously invalid text
  valid; an older binary then reports MDL000 at the new construct. A
  change that would alter the meaning of valid text bumps the major. A
  RESPELLING keeps the old spelling valid with its old meaning through
  the whole major, reported MDL012 with the replacement; the old spellings
  are exactly the closed BRIDGE list of 11.1, and removing one is a major
  bump (D168). This holds for the planning layer as for every other text.
- The header is part of the language parameter of the U terms (the
  "edition" of shared/universal-model.md 2.2 item 5) and of the digest scheme
  input: a major bump makes every entity's digests stale with the reason
  recorded, exactly as a digest-scheme change does (docs/design/grimble/binding.md section 14).

## 4. Entities

An ENTITY is a named, declared thing; it is a `unit` in U. There are
eight kinds: `node`, `flow`, `contract`, `claim`, `vmodel`, `boundary`,
`pack` and `template` (`boundary` is kept by D6, `template` added by
D75). The planning layer adds seven kinds (`system`, `actor`, `goal`,
`step`, `scenario`, `impl`, `page`; section 11) in the same namespace.
Every statement inside an
entity body is a CLAUSE; a clause is an `attr` in U. A clause key may be
repeated only where the table says "list".

Common clauses, valid on every entity:

| Clause | Syntax | Meaning |
|---|---|---|
| `alias` | `alias old_name;` | an additional permanent name (list); resolves like the real name, no warning |
| `renamed_from` | `renamed_from old_name;` | transitional name after a rename (list); resolves with MDL012 Warn, and lets the ack planner carry lock entries to the new identity (5.5) |
| `attr` | `attr KEY [= VALUE];` | typed user attribute (list by distinct KEY); VALUE is a string, number, quantity, date, ident or a bracketed list of those |
| `verified_by` | `verified_by SEL [for STEP.VARIANT];` or `verified_by manual because="...";` | the one evidence clause (list; 8.3, D150); not accepted on `actor`, `step`, `boundary`, `pack` and `template` (MDL000); on a `system` it is a bridged spelling, ignored with MDL012 (11.1) |
| exception clauses | section 7 | `accept`, `defer`, `hotfix` (list) |
| doc | `/// text` before the item | the human label and description; the Doc facet (2.3, D159). An item has one Doc facet: when `/// text` and the bridged `title "t";` (MDL012) are both written, the `///` text is the facet and the `title` folds to nothing |

### 4.1 node

```
node cli : trusted {
  kind component;
  clearance Internal;
  owns "crates/frob/**";
  owns "crates/frob-check/src/lib.rs::run";
  may fs.read at "crates/frob/**";
  may net.connect("api.github.com") at "crates/frob-gh/src/lib.rs::GhClient.*";
  surface kind(function) & attr(vis = "pub") & "crates/frob/**";
  attr timeout = 30 s;
}
```

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `node NAME` | name | yes | entity name (section 5) |
| trust | `: LEVEL` | element of the trust lattice | yes (no security defaults) | `foreign` < `authenticated` < `trusted`; extra elements only from a pack, never from a model file |
| kind | `kind IDENT;` | node kind | no, default `component` | core kinds `component store queue cache gateway external`; a pack may add kinds (the v1 keywords cdn, balancer, queue, cache, secret, resource become kinds with typed attrs) |
| clearance | `clearance LABEL;` | element of the label lattice | no, default `Secret` | maximum data label that may rest here; labels `Public` < `Internal` < `Pii` < `Secret` |
| owns | `owns SELECTOR;` | selector (section 6) | list, none allowed (a node that owns nothing is legal: an external system) | the set of code identities this node owns |
| may | `may ATOM [ "(" ARGS ")" ] [ at SELECTOR ] [ via SELECTOR ] [ because="WHY" ] [ ticket="ID" ];` (full v3 grammar in grimble-capabilities-v3.md section 2) | grant | list | capability grant. ARGS is a typed argument list whose slots are defined per atom (host glob, port, scheme, path glob and operation set, binary, env name, ...; grimble-capabilities-v3.md section 3); under `grimble = "3"` a call-site argument that cannot be extracted is Unresolved, never a pass (v3 section 4), and under `"2"` a bare string argument is parsed but not enforced. The grant applies at SELECTOR, enforced per symbol (`FILE::SYMBOL` is not collapsed to its file), default the node's whole `owns` set; `via SELECTOR` limits it to uses through a sanctioned provider, `until=DATE` bounds it in time (an expired grant covers nothing and is CAP007, an error naming the date) and `profile=test|prod|NAME` (or `profile=[a,b]`) scopes it to a build profile: a use is judged under `test` when its file is under `tests/`, named `*_test.*` or `test_*.*`, otherwise `prod` (the `GRIMBLE_PROFILE` environment variable overrides it, else the `[grimble] profile` config key names the profile for every use), and a grant with profiles covers only uses in one of them; `owner=` is still planned (v3 sections 10, 11). Each observed use is judged on its own; one covered use never masks an uncovered use of the same atom This replaces v1's `of CONSTRAINT` and the colon form `net.connect:host`. A grant states why it exists with `because=` or `ticket=` (a non-blank string); a grant with neither is MDL008 at Warn severity, so adopters can ratchet it. `grimble status` reports grant count and breadth (see the grant ratchet below) |
| surface | `surface SELECTOR;` | selector | list (union) | the intended public API; SYS014 (reserved by binding.md 11.3) compares it with observed public symbols |
| attrs | `attr` | typed value | list | markers and magnitudes (`attr timeout = 30 s;`, `attr idempotency_key;`) |

**Grant ratchet.** `grimble status` reports, per node, the number of `may` grants
and their breadth (distinct files the grants' selectors match; a grant without
`at` covers the node's `owns` files), and the delta against the model as of the
newest first-parent commit that changed `grimble.lock`. Both sides are measured
over the same current walk, so a delta is a grant that changed, not a repo that
grew. Grants are matched by node and canonical grant identity: atom, canonical typed arguments, `at`/`via` selectors and profile set (v3 section 7). A grant that matches
a file its baseline did not is `widened` and listed by name; one that only loses
files is `narrowed`; new and deleted grants are `added` and `removed`. Without a
committed lock there is no baseline: counts only, `baseline` is null and there is
no delta. Grants that state no reason are listed as well.

**Trust zones and ungated nodes.** `grimble status` also lists each node that grants EVERY
registered leaf atom (a parent atom such as `fs` covers its children) at one broad `at` glob, one
without string arguments, whose text has `**` and no `::`, as a declared trust zone with the
files it covers; `trust_zone_files` counts the union, so overlapping zones count a file once.
Nodes that are not `kind external` and have no `owns` clause with a parsed selector are listed
as ungated (`ungated_nodes`), next to `gated_nodes` and `external_nodes` counts: no capability
rule (CAP001, CAP002) judges them. Pack-declared atoms are not in the every-atom universe.

A node without a `trust` is MDL008. A node carries NO excuse clause:
capabilities are denied by default (binding.md 7.2), so a node never
needs to say "not this atom"; a not-granted atom is simply denied, and
observed use of it is CAP001. A node-level `excuses ...` clause (the
D5-era spelling) is MDL018 (4.8). Capability atoms are resolved against
the one registry (docs/design/grimble/binding.md section 7); an atom that is in no registry
and no enabled pack is MDL016.

### 4.2 flow

```
flow f_walk : gob -> frob {
  label Internal;
  rate 100 req/s;
  producer "crates/gob-walk/src/lib.rs::walk";
  consumer "crates/frob-check/src/snapshot.rs";
  contract walk_result;
}
```

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `flow NAME` | name | yes | |
| from, to | `: A -> B` | refs to nodes | yes | directed data movement; `A -> B` where both resolve to `node` entities (MDL006 otherwise) |
| label | `label LABEL;` | label | yes | data label carried (no default: v1's default `Public` was a security default) |
| rate, age, size | `rate Q;` `age Q;` `size Q;` | quantity of the matching dimension | no | demand, staleness bound, payload size |
| fanout | `fanout N;` | number | no | |
| growth | `growth Q;` | rate of ratio per time (`15 %/d`) | no | growth of the flow's rate over time; see open question 8 of 19 |
| transport | `transport ATOM, ATOM;` | list of atoms | no | the atoms `in_process`, `http`, `ipc`, `ffi`, `file` (`in-process` is not lexable as an atom, 2.2); pack-extensible |
| condition | `condition on_ok;` or `condition on_err;` | ident | no | v1 `on Ok/Err` |
| producer | `producer SELECTOR;` | selector | no (SYS004 or SYS009 report absence of symbols, binding.md 6.4 and 6.9) | the code unit(s) that emit; may be any language |
| consumer | `consumer SELECTOR;` | selector | no | the code unit(s) that read |
| contract | `contract NAME;` | ref to a `contract` entity | no | the agreed data shape (4.3) |

Flows may form cycles (request and response, retry loops, feedback);
cyclic flows are legal and the kernel's longest-path age uses SCC
condensation (docs/design/grimble/grmb-spec.md section 20.1). v1's `utility` (non-transitive
hub edge) is `attr utility;` and its meaning is the kernel's.

### 4.3 contract

```
contract walk_result {
  shape "crates/gob-walk/src/lib.rs::WalkResult";
  versioning scheme=semver current="0.1.0" compat=backward;
}
```

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `contract NAME` | name | yes | |
| shape | `shape SELECTOR;` | selector | yes | the language-neutral shape: ONE unit whose Contract facet (shared/universal-model.md 7.1) is the shape. A selector that does not resolve to exactly one identity is SYS003 kind `ambiguous-singleton` (binding.md 2.5 item 4, G02); here only the grammar is fixed |
| versioning | `versioning scheme=S current="V" compat=C;` | attrs | no | `scheme` one of `semver`, `date`, `integer`, `none`; `current` a string in that scheme; `compat` one of `backward`, `forward`, `full`, `none`. Informational for SYS006: skew is detected from digests, versioning says what skew is allowed to be |

Contracts exist as entities (not as an inline selector in the flow)
because a contract is shared by flows, versioned, and is the subject of
the typed lock entries of docs/design/grimble/binding.md section 14: the flow lock entry
records the `contract` facet digest of each end against this entity.

### 4.4 claim

```
claim no_frob_to_grimble {
  noflow frob -> grimble;
  proof L2;
  verified_by "crates/frob/tests/wiring.rs";
}
```

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `claim NAME` | name | yes | |
| what | `noflow A -> B;` or `reach A -> B;` or `never NODE uses ATOM;` or `bound METRIC TARGET <= Q;` or `attests "STATEMENT" [on NODE];` | exactly one | yes | the proposition. `noflow` and `reach` take node refs; `never` takes a node ref and a capability atom with optional `(ARGS)` and is judged against the code the node owns (below); `bound` takes a metric (`age`, `rate`, `latency`, `size`, `utilization`), a TARGET and a quantity of the metric's dimension. TARGET is a node or flow, or a planning entity (a step, scenario, goal or system; D158): `bound latency pump.infuse <= 50 ms;` is the time budget of the scenario `pump.infuse`. `attests` is the assumption form with no flow proposition (below). `independent` and `readers(x) == S` of v1 had no surface and stay out |
| proof | `proof LEVEL;` | `L1`..`L5` | no, default from `[grimble] default_proof` | the required rung. The rung ladder is an ordered label to the kernel; its meaning is G03 |
| assumed | `assumed because="..." until=DATE owner=IDENT [ticket="..."];` | the debt key set (7); `because`, `until` and `owner` required | no | the claim is an assumption: named, owned, expiring (v1 `assume`); past `until` is REFUTED, as in v1. `review=DATE` is the major-2 spelling of `until=` (MDL012) |
| evidence | `verified_by SEL;` | list | no | what discharges the claim above L1: test units or a document unit (a markdown anchor is a unit, 4.5.1); the one evidence clause of 8.3. `evidence tests SEL;` and `evidence ref "S";` are the deprecated major-2 spellings |

Verdicts: a `noflow` with a declared flow path, or a `reach` with none, is REFUTED (CLAIM001, naming the path); a claim the model cannot decide, such as every `bound` today, is Unresolved with the reason (CLAIM003). A claim with `proof` above L1 and neither evidence nor `assumed` is likewise Unresolved (CLAIM003). A claim is never silently ok.

`never NODE uses ATOM;` is a negative guarantee checked against code, not against declared flows (CLAIM004). It is REFUTED when code the node owns uses the atom (or a child of it: `net` covers `net.connect`), directly or transitively through callees; the finding names the call path. A use the binding cannot pin to the node (code owned only at `may`, or an unresolved receiver) is Unresolved, never ok. No use observed is not proof of absence beyond what the detectors see. `never NODE uses ATOM(ARGS);` narrows the claim to uses whose statically known argument matches one of ARGS (the same typed matching as a grant argument): a matching use refutes it, a use with another argument does not, and a use whose argument cannot be folded is Unresolved, never refuted and never ok.

CLAIM005 (opt-in) is a lexical taint check over Python and Rust: a name assigned from a secret-named environment read (a variable containing KEY, SECRET, TOKEN, PASSWORD or CREDENTIAL) that reaches a print, log or HTTP call fires, unless the value passes through a symbol a node declares with `provides secret.declassify via SEL;`. It runs only when some node declares that boundary, sees one function at a time, and is not interprocedural.

<!-- frob:ticket 01M4FGYK3ZMG2PFK5FF7N3TMXS -->
The `attests` proposition. Many v1 assumptions state no flow at all: a
weakness the team accepts (`weakness:CWE-78:vet`), a data handling duty
(`pii:email:retention`). Encoding one as a `noflow` would be a false
proposition the kernel REFUTES, so `attests "STATEMENT" [on NODE];` says
only "an owner states this holds". STATEMENT is a non-empty string (empty
is MDL008); `on NODE` names the node it is about (an unresolved or
non-node ref is MDL006; without it the claim is about the whole model).
An `attests` requires `assumed` (MDL008 otherwise: an attestation with no
owner or expiry is not an assumption anyone holds); for the other forms
`assumed` stays optional. The model cannot decide an `attests`: with no
evidence it is Unresolved "attested by OWNER, no evidence" (CLAIM003)
whatever its `proof`, never PROVED by say-so and never REFUTED by the flow
graph; with evidence the kernel (G03) assigns the verdict of an evidenced
`assumed` claim at the declared rung; a past `until` is REFUTED. An
`extend` may not set `attests` (a scalar, MDL008).

```
claim cwe_78_vet {
  attr id = "weakness:CWE-78:vet";
  attests "shell arguments are vetted before exec" on shell;
  assumed because="inputs come from argv only" until=2026-10-15 owner=logan;
  verified_by "docs/threat/cwe-78.md";
}
```

Kernel findings: a flow whose `label` exceeds the destination clearance with no `declassify` boundary is FLOW001; a flow into a higher-trust node with no `endorse` boundary is FLOW002; a flow from a `foreign` node with no `rate` is FLOW003. Each names the flow.

Verdicts (PROVED, REFUTED with witness, UNPROVABLE, and the three-way
closure) are computed by the kernel and are not part of the language.

### 4.5 vmodel

```
vmodel req_gate_exit {
  kind artifact;
  level requirements;
  ref "docs/design/shared/cli-contract.md#12-output-contract";
  verified_by "crates/frob/tests/check_verb.rs::error_finding_exits_1_and_fail_on_none_exits_0";
}
```

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `vmodel NAME` | name | yes | |
| kind | `kind K;` | `artifact`, `decision`; `test` is deprecated (below) | yes | v1 node kinds |
| level | `level L;` | a level of the table below | yes | |
| ref | `ref "SYMREF";` | symref of a document anchor (4.5.1) or code unit | artifact: yes | the spec artifact |
| evidence | `verified_by SEL;` or `verified_by manual because="REASON";` | 8.3 | list | the tests (or the manual check) that verify this artifact; their level is the paired test level of the artifact's level, so it is never written |
| links | `satisfies X;` `verifies X;` `refines X;` `allocates X;` `decides X;` `supersedes X because="...";` `blocked_by X;` | ref to a vmodel or a planning entity (13.3) | list | edges from THIS entity to X; v1 `vmodel_edge`, with `supersedes` requiring `because`. The verbs are kept as they are (D164; SysML v2 keeps `satisfy`, `verify` and `allocate`, E24) |

Levels: ten, in five pairs, each pair requirement-side and test-side.
Canonical spellings are the first; the short alias after it is accepted
and printed canonical by the formatter.

| Requirement side | Paired test side |
|---|---|
| `requirements` | `customer_test` (alias `acceptance`) |
| `requirement_spec` | `customer_test_plan` |
| `system_spec` | `system_integration_test_plan` |
| `system_design` | `subsystem_integration_test_plan` |
| `component_design` | `component_unit_test` (alias `unit`) |

DEPRECATED TEST FORM. The major-2 spelling of evidence is a second
vmodel `{ kind test; level customer_test; runnable SEL; verifies
req_gate_exit; }` (or `manual because=...` in place of `runnable`). It
keeps its meaning through major 2: it is read as `verified_by SEL` on the
`verifies` target, the singleton rule below applies to each `runnable`,
and MDL012 (Warn) names the replacement. Its `level` is redundant (the
evidence level is derived from the target, 8.3): it is not checked
against the target's level, the MDL012 message says to drop it, and
PLAN050 judges the evidence scope exactly as for `verified_by` (D170). `grimble fmt` does not rewrite it
(the rewrite moves a clause between entities); a quick-fix of kind
`suggest` does (D150).

Construction errors are model-load errors (MDL014): a link whose
endpoints are of the wrong kind, a missing `ref`, a test vmodel with
neither or both of `runnable` and `manual`, an empty `manual` reason, a
duplicate link, a malformed `ref` (4.5.1). A repeated evidence clause is
MDL017 (below, D170). A link target that
resolves to nothing is MDL006; one that resolves to an entity that is
neither a vmodel nor a planning entity is MDL014. The five structural
closure rules (orphan requirement, unjustified design, untested artifact,
orphan test, trace cycle) and milestone known gaps belong to the kernel
(G03); their rule ids are open (19).

#### 4.5.1 Document anchors in `ref`

Moved to shared/code-model.md 2.1 (document anchors: heading slugs, explicit `{#ID}`, table-row ids, malformed refs, status).

#### 4.5.2 Several runner ids, and manual evidence

Evidence is verified by ALL of its clauses: `verified_by` repeats, one
clause per runner id or per glob,

```
vmodel req_gate_exit {
  kind artifact; level requirements; ref "docs/design/shared/cli-contract.md#12-output-contract";
  verified_by "crates/frob/tests/check_verb.rs::error_finding_exits_1";
  verified_by "web/e2e/gate.test.ts::[gate > shows exit state]";
}
```

A LITERAL clause (6.4 item 5: no wildcard in PATH or QUALNAME, with `::`)
must resolve to exactly one test unit; several are SYS003
`ambiguous-singleton`. A glob or file clause means every test unit it
selects. Two DIFFERENT clauses are never an ambiguity: the singleton
predicate is per clause. A clause whose FILE exists but which selects no test unit is SYS011
(`Error`) on that clause, so one broken runner id of three is named alone;
a clause whose file does not exist yet is `planned` (8.3). Two clauses
spelled identically, or two spellings resolving to the same unit, are one
duplicate: MDL017 (Advisory; `grimble fmt` removes an identical repeat).

Manual evidence is `verified_by manual because="REASON";`. It has no code
term, so SYS011 and SYS003 cannot fire; `grimble status` lists it as
`manual` with its reason, the kernel counts it at the manual rung only
(G03), and manual evidence for a claim that requires an automated proof
rung is that claim's SYS010. An empty REASON is MDL014.

Status: implemented for the deprecated form (ticket ~P7APFVH): `runnable`
repeats, the singleton predicate is per clause, `manual because=` parses
and is exposed as `Binding.manual_tests`, MDL014 covers neither, both and
an empty reason, two identically spelled clauses are MDL017. The
`verified_by` spelling on vmodel and claim entities, MDL012 on the old
spellings and the `grimble status` listing follow in the parser ticket of
cycle 1 (see notes/research/grmb-evidence/cycles.md).

#### 4.5.3 Runner ids and the selectors that name them

Moved to shared/code-model.md 2.2 (runner id to selector table, test-unit recognition, status).

### 4.6 boundary and pack

```
boundary b_vet endorse f_install : foreign -> trusted when "checksum_verified";
pack threat { ref "grimble/threat"; version "1.2.0"; digest "blake3:..."; }
```

boundary:

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `boundary NAME` | name | yes | |
| direction | `endorse` or `declassify` | keyword | yes | the only legal label or trust change |
| flow | `FLOWREF` | ref to a flow | yes | the flow on which it acts |
| from, to | `: A -> B` | lattice elements | yes | trust levels (endorse) or labels (declassify); the pair must be on the right lattice (MDL009) |
| predicate | `when "TEXT";` | string | no | opaque to the language; the kernel treats it as a named obligation |

A boundary ends with `;` or with a block holding common clauses only.
The six-phase block of v1 is dropped.

pack:

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `pack NAME` | name | yes | the prefix of pack-qualified atoms (`NAME::atom.path`) |
| reference | `ref "ID";` | string | yes | the pack identifier under `packs/` |
| version | `version "X.Y.Z";` | exact semver, no ranges | yes | the pinned version |
| digest | `digest "blake3:HEX";` | string | no, recommended | the digest of the pack contents; mismatch is MDL004 |

A pack named here but not enabled in `grimble.toml`, absent from `packs/`,
or whose version or digest differs from the pin is MDL004. Pins are
exact so that a model and a pack move together and a version change is a
visible edit of the model (no invisible variable).

### 4.7 template (matrix-build templates, D75)

A TEMPLATE is the only place an excuse can be written. It declares how
capability atoms apply across languages and unit kinds in the grimble IR:
"atom A does not apply to the units S selects, because R". It is not a
claim about a node. It is a matrix-build declaration that shapes the
capability matrix (binding.md 7.2) for every node whose code the
selection reaches. Templates live in two places only: in packs (packs-and-plugins.md
6.7, next to the atoms and detectors they qualify; a built-in pack
may ship them) and in a `template` entity of a model file (this section),
which is how a repository qualifies atoms for its own generated code. A
`template` is never a clause of a `node`.

```
template gen_proto {
  excuse net.listen
    for kind(function) & lang(rust) & attr(generated_by = "protoc")
    because="generated stubs declare a server trait but never bind a socket";
  excuse fs.write
    for "crates/*/src/gen/**" & lang(rust)
    because="build-time generated code only writes under OUT_DIR, which build.script already covers";
}
```

Grammar (EBNF, over the tokens of section 2):

```
template  = "template" name "{" { tclause } "}" ;
tclause   = excuse | alias_etc ;                (* alias_etc of 4.10: no verified_by on a template *)
excuse    = "excuse" atom "for" selector "because" "=" string ";" ;
atom      = ident { "." ident } | ident "::" ident { "." ident } ;
```

`selector` is the grammar of 6.1 and nothing else; it selects UNITS, so
the predicates `lang(L)`, `kind(k...)` and `attr(name [cmp value])` of
6.3 decide the languages, unit kinds and attributes the excuse covers
(`attr(generated_by = "protoc")` is how generated code is told apart; the
attribute comes from the adapter or from a `grimble:` directive).

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `template NAME` | name | yes | entity name (section 5); the reference the check output, the lock and exceptions use |
| excuse | `excuse ATOM for SELECTOR because="..."` | excuse | list, at least one | the atom does not apply to the selected units; ATOM resolves against the registry (unknown is MDL016); an atom whose registry entry lists no detector for a selected language is still excusable |

Rules.

- `because` is mandatory and a string; a missing or empty reason is
  MDL008. Reasons are judged by EXC rules, as for other reasons (7).
- `for SELECTOR` is mandatory: there is no "excuse everywhere". The
  selector has no `at` default; it never defaults to a node's `owns`
  set, because an excuse is about code, not about an owner.
- An excuse for A covers A and every descendant atom of A: `excuse
  fs.write` covers `fs.write` and nothing broader; `excuse fs` covers
  `fs.read` and `fs.write` (hierarchy, docs/design/grimble/binding.md section 7). An excuse
  with ARGS is not expressible: an excuse never narrows by argument.
- An excuse never hides an observed use. If detectors observe the excused
  atom in covered code, the result is CAP004 (binding.md 7.2), evaluated
  before the excuse; an uncertain detection is Unresolved, never a pass.
- An excuse that overlaps a grant `may A` of the model for the same atom
  (or an ancestor or descendant) is SYS012 (binding.md 6.12): the model
  both permits and declares not-applicable.
- Every template excuse is listed and counted in `grimble check --json`
  (shared/sibling-contract.md): a `template_excuses` array of
  `{template, atom, selector, because, source}` and a `template_excuses`
  total in the summary, so a reviewer sees the full set at a glance.
- Not-applicable is unchanged: it remains declared only by detector data
  (packs-and-plugins.md 6.5), never by a template. A template excuse is `excused`, a
  different cell.

### 4.8 Removed: the node-level `excuses` clause (MDL018)

The D5-era `excuses ATOM because="...";` on a `node` (or in an `extend
node`) is MDL018 (Error, D75). Grant the atom if the node uses it, leave it
ungranted if not (denied by default), or move reasoning about a kind of
code into a matrix-build template (4.7).

### 4.9 extend and namespace

```
extend node cli {            // same kind keyword as the target
  may fs.write at "crates/frob-fix/**";
}
namespace tools {            // names inside become tools.NAME
  node linter : trusted { owns "tools/lint/**"; }
}
```

`extend KIND REF { clauses }` adds clauses to an entity declared
elsewhere in the model (for example in a fragment owned by another
team). Only list clauses may be added (`owns`, `may`,
`surface`, `attr` with a new key, `alias`, exception clauses, `producer`
or `consumer` on a flow, links on a vmodel). A scalar field (`trust`,
`kind`, `clearance`, `label`, `shape`, `what`) in an `extend` is MDL008;
an `extend` whose target does not exist is MDL006. The extension is a
`unit` part with role `extension` of the same identity (shared/universal-model.md
2.6): one entity, many parts.

`namespace NAME { items }` groups items under a prefix. It is a
containment node, not an entity: it cannot have clauses.

### 4.10 Item grammar (EBNF)

The file and architecture-item productions (D175). Section 11.1 extends
`item` with the planning items; the field tables above give each clause's
type and multiplicity. A `///` doc comment may precede any item or clause.

```
file      = header [ module_ln ] { item } ;
header    = "grimble" "=" string ";" ;                       (* 3.4 *)
module_ln = ( "module" name | "part" "of" name ) ";" ;       (* 3.1 *)
item      = use | node | flow | contract | claim | vmodel | boundary | pack
          | template | extend | namespace | top_exc | ceiling | plan_item ;
use       = ( "use" | "include" ) string [ "as" ref ] [ "outside" ] ";" ;   (* include: bridged, 11.1 *)
node      = "node" name ":" ident ( ";" | "{" { node_cl } "}" ) ;
node_cl   = "kind" ident ";" | "clearance" ident ";" | "owns" selector ";"
          | "may" grant ";" | "use" name ";" | "surface" selector ";" | common ;
policy    = "policy" name "{" { "may" grant ";" | "use" name ";" | common } "}" ;
flow      = "flow" name ":" ref "->" ref ( ";" | "{" { flow_cl } "}" ) ;
flow_cl   = "label" ident ";" | ( "rate" | "age" | "size" | "growth" ) quantity ";"
          | "fanout" number ";" | "transport" ident { "," ident } ";"
          | "condition" ident ";" | ( "producer" | "consumer" ) selector ";"
          | "contract" ref ";" | common ;
contract  = "contract" name "{" { "shape" selector ";" | "versioning" { keyval } ";" | common } "}" ;
claim     = "claim" name "{" { what | "proof" ident ";" | assumed | common } "}" ;
what      = ( "noflow" | "reach" ) ref "->" ref ";"
          | "never" ref "uses" atom ";"
          | "bound" ident ref "<=" quantity ";"
          | "attests" string [ "on" ref ] ";" ;
assumed   = "assumed" { keyval } ";" ;                       (* the debt key set, 7 *)
vmodel    = "vmodel" name "{" { "kind" ident ";" | "level" ident ";" | "ref" string ";"
          | link | "runnable" selector ";" | "manual" keyval ";" | common } "}" ;
link      = ( "satisfies" | "verifies" | "refines" | "allocates" | "decides"
          | "blocked_by" ) ref ";" | "supersedes" ref keyval ";" ;
boundary  = "boundary" name ( "endorse" | "declassify" ) ref ":" ident "->" ident
            [ "when" string ] ( ";" | "{" { alias_etc } "}" ) ;
pack      = "pack" name "{" { ( "ref" | "version" | "digest" ) string ";" | alias_etc } "}" ;
extend    = "extend" kind_word ref "{" { clause } "}" ;     (* list clauses only, MDL008 *)
namespace = "namespace" name "{" { item - use } "}" ;      (* `use` is top-level only, D181 *)
top_exc   = exc_kind rule "on" ref { keyval } ";" ;
ceiling   = "ceiling" ident "forbids" atom { "," atom } ";" ;   (* 4.11 *)
common    = alias_etc | verified_by ;                        (* verified_by: 8.3, 11.1 *)
alias_etc = ( "alias" | "renamed_from" ) name ";" | attr_cl | exc_kind rule { keyval } ";" ;
attr_cl   = "attr" ident [ "=" attr_value ] ";" ;
attr_value = value | date | "[" value { "," value } "]" ;   (* value of 6.1 *)
exc_kind  = "accept" | "defer" | "hotfix" ;
keyval    = ident "=" ( string | date | ident | number ) ;
```

`grant` is the `may` argument form of 4.1 (grimble-capabilities-v3.md
section 2); `value` is the selector value of 6.1; `rule` is a rule-id token
(2.7); `kind_word` is the keyword of the extended entity; `clause` is any
list clause of that entity. A node, flow or boundary may end with `;`
when it has no clauses (`node order_svc : trusted;`); contracts, claims,
vmodels and packs always have a body, because each has a required clause.

### 4.11 ceiling (trust-level capability ceilings)

Node trust (`foreign < authenticated < trusted`, 4.1) otherwise never
reaches capability evaluation: a foreign node could be granted
`process.spawn` or `fs.write` and nothing would object. A `ceiling` item
declares atoms that nodes at or below a trust level may not be granted.

```
ceiling foreign forbids process.spawn, fs.write;
ceiling authenticated forbids process.spawn;
```

- `ceiling LEVEL forbids ATOM {, ATOM};` is a top-level item (also valid
  inside a `namespace`). `LEVEL` is one of `foreign`, `authenticated`,
  `trusted`; an unknown level is ignored with a warning.
- The ceiling binds every node whose declared trust rank is at or below
  `LEVEL`: `ceiling authenticated ...` binds `foreign` and `authenticated`
  nodes. A node with no declared trust is not judged.
- A grant exceeds the ceiling when its canonical atom equals a forbidden
  atom, lies under it (`fs.write.tmp` under `fs.write`) or covers it
  (`may fs` covers a forbidden `fs.write`). Aliases are canonicalised
  (`exec` is `process.spawn`); pack qualifiers are ignored.
- CAP006 (`cap-grant-exceeds-ceiling`, error) fires on the offending `may`
  clause; its message names the ceiling and the file that declares it.
- A `policy NAME { may ...; }` block names a reusable set of grants. A node
  (or another policy) applies it with `use NAME;` (an unknown name is MDL006,
  a cycle is MDL012); its grants then count as the node's own, and
  `grimble status` lists them per node with the policy they came from.
  `policy` and `use` (in a clause position) are keywords.
- `ceiling` and `forbids` are contextual words (an item head and a word
  after it), not rows of the 2.6 table: they remain valid identifiers
  everywhere else.

```
ceiling foreign forbids process.spawn, fs.write;
node a : foreign {
  owns "src/**";
  may process.spawn at "src/**";   // CAP006: exceeds `ceiling foreign forbids process.spawn`
  may fs.read at "src/**";         // fine
}
node b : trusted {
  owns "tools/**";
  may process.spawn at "tools/**"; // fine: trusted is above the ceiling
}
```

## 5. Names and scoping

### 5.1 One namespace per model

All entities of every kind (the eight of section 4 and the seven planning
kinds of section 11), all packs and all namespaces share ONE
flat-with-prefixes namespace per model. A flow and a node cannot share a
name. Capability atoms, lattice elements, rule ids, units and metric
names live in their own registries and never collide with entity names.

### 5.2 Qualified names

The full name of an entity is its declared name prefixed by the
enclosing `namespace` names and the `as` prefix of the `use` that
brought its file in, joined with `.`. `api.handlers` is the entity
`handlers` in `namespace api` or in a file used `as api`; both
spellings denote the same full name and a collision between them is
MDL001.

### 5.3 Resolution of a reference

A `ref` inside an item with enclosing prefix `P1.P2` resolves by looking
up, in order, `P1.P2.R`, `P1.R`, then `R` at the root; the first hit
wins. A leading `::` skips the search and anchors at the root
(`::cli`). A hit whose resolved entity shadows a different entity of the
same name at an outer level is MDL015 Advisory (shadowing is
legal and reported). No hit is MDL006. References are Must edges in the
scope graph (section 9).

### 5.4 Uniqueness

Full names are unique in a model. A second declaration of the same
full name is MDL001 reporting both locations, regardless of which files
or which `use` order produced them; the first in canonical (path,
byte) order is kept so that downstream rules still see one entity. The
`extend` form is the only legal way to add to an existing name. Aliases
and `renamed_from` names occupy the namespace too (an alias equal to
another entity's name is MDL001).

### 5.5 Identity and renames

The identity of an entity (shared/universal-model.md 2.2, docs/design/grimble/binding.md section 14)
is anchored on `(module, full name)`, not on the file path: moving an
entity between files of the same model keeps its identity and moves only
its location. The symref of an entity is
`<path>::<full name>` (for example `design/frob.grmb::cli`); the
logical location used in findings and in `design:` links is
`<kind>/<full name>` (`node/cli`). Content (the facets of section 9) is
not identity.

A rename is a new identity whose Body facet equals a vanished one
(SYS008 shape). To make that deterministic and cheap the author writes
`renamed_from old_name;` in the renamed entity; the ack planner then
migrates lock entries from the old identity to the new one instead of
reporting a rename, and MDL012 Warn fires for every reference that
still uses the old name until it is edited (and, deferred to G12 because it needs lock data, for the clause itself
once no lock entry or reference mentions it, so it gets removed).
`alias` is for names that are meant to stay (a v1 id, a name used by
generated documents).

## 6. Selector expressions

A selector denotes a set of code identities. One grammar serves `owns`,
`surface`, `may ... at`, `producer`, `consumer`, `shape`, `verified_by`,
the planning realizations and the CLI (`grimble select EXPR`). The grammar and the
evaluation are owned by gob-walk (ticket G07); grimble-model slices the
selector text from the token stream and calls `Selector::parse`, so
spans map back into the .grmb file.

### 6.1 Grammar

```
selector = disj ;
disj     = conj { "|" conj } ;
conj     = unary { "&" unary } ;
unary    = "!" unary | primary ;
primary  = glob | predicate | "(" selector ")" ;
glob     = string ;                                    (* see 6.2 *)
predicate= "lang" "(" ident ")"
         | "kind" "(" ident { "," ident } ")"
         | "attr" "(" ident [ cmp value ] ")" ;
cmp      = "=" | "!=" | "~" | "<=" ;
value    = string | number | quantity | ident ;
```

Precedence: `!` binds tightest, then `&`, then `|`; parentheses group.
`a & !b` is the set difference. A bare `!a` denotes the complement within
the walked files and is legal (rarely useful; it has the bottom
specificity of 6.4).

### 6.2 Glob strings

A glob string is `PATH [ "::" QUALNAME ]`.

- PATH is a repository-relative POSIX glob over files known to gob-walk.
  `*` matches within one path segment, `**` as a whole segment matches
  zero or more segments, `?` one character, `[abc]` and `[a-z]` a class,
  `{a,b}` alternation. A PATH ending in `/` means that directory
  recursively (`crates/frob/` is `crates/frob/**`). No leading `/` and no
  `..` (MDL009).
- QUALNAME is a dotted pattern over the unit qualnames of
  docs/design/shared/code-model.md section 2: `.` separates segments, `*` matches one
  segment, `**` any depth, `[...]` is the opaque bracket of a symref
  segment (`Type[Trait].method`). Literal text matches literally.
- For a `verified_by` the QUALNAME is the test unit's, and runner ids
  (pytest node ids, cargo test paths, vitest titles) are mapped to it by
  the table of 4.5.3; a bracketed segment `[..]` carries a title that is
  not a name.
- A PATH with no wildcard and no `::` names a FILE (and everything it
  contains); with `::` it names units. The empty PATH is MDL009.

### 6.3 Predicates

| Predicate | True for a unit when | Decided from |
|---|---|---|
| `lang(L)` | the unit's language tag is L (`rust`, `python`, `grmb`, `markdown`, ...) | the adapter's language tag, Exact |
| `kind(k1, k2)` | the unit kind is one of the list (`function`, `method`, `type`, `class`, `const`, `module`, `field`, `variant`, `macro`, plus adapter kinds) | the term, Exact |
| `attr(name)` | the unit carries an attribute `name` | `attr` nodes, Exact at F4, Unknown below F4 |
| `attr(name = v)`, `!=`, `~` (glob match on the string value), `<=` (quantity comparison) | the attribute's payload compares as stated; the visibility attribute is `vis` with values `pub`, `crate`, `private` | `attr` payload; Unknown when the adapter does not provide the attribute |

### 6.4 Semantics over gob-walk and the scope graph

`sel(S)` is a function from a selector and a snapshot (the gob-walk file
set and the U terms of those files) to an `Answer<Set<Identity>>` with a
status per identity, in the answer lattice of shared/universal-model.md 4.1.

1. File step. The files matching PATH are `Exact` (gob-walk is exact).
   Files that match but could not be read, or exceed the size cap, are
   recorded as UNSEEN files: they contribute nothing to `lo` and a hidden
   unit to `hi`. Files excluded by `[check] exclude` are not in the walk
   and are not Unknown: the selector says nothing about them.
2. Unit step. Without `::`, the identities are all units contained in
   each matched file (the file's module unit included). With `::`, they
   are the units whose qualname matches QUALNAME.
3. Status of one identity u in file f. It is MUST when the match depends
   only on Must facts: PATH membership, a Must containment chain from the
   file to u, and predicates that evaluated Yes. It is MAY when any step
   goes through a May edge, an unexpanded `phase`, a region the adapter
   marked as possibly defining units, or a predicate that evaluated
   Unknown (an attribute the adapter does not provide). In the U sense,
   `lo` holds the MUST identities and `hi` holds MUST and MAY ones.
4. The unseen remainder. If a matched file contains an `opaque`, an
   unexpanded `phase` or a `hole` (parse error), then `hi` additionally
   contains one UNKNOWN placeholder for that file: the selector may match
   units the term cannot show. A file at F0 contributes only its
   file-level unit (Must) and, if `::` is present, an Unknown
   placeholder.
5. Literal paths. A selector that is a single glob with no wildcard in
   PATH and no wildcard in QUALNAME is a LITERAL selector. It resolves
   through the symref resolution order of docs/design/shared/code-model.md section 2
   (exact, unique qualname, unique suffix); a unique resolution is Must,
   candidates are May, and no resolution in a file with no unseen
   remainder is `Exact(empty)`.
6. Boolean combinators use Kleene logic on membership (Yes, No, Unknown):
   `&` is the three-valued meet, `|` the join, `!` the complement
   (`Unknown` stays `Unknown`). `lo(!e)` is the walked universe minus
   `hi(e)` and `hi(!e)` the universe minus `lo(e)`, and an unseen
   placeholder is never in `lo`.

Reading of docs/design/grimble/binding.md section 13 ("Must for literal paths, May for globs
that match units with Unknown edges"): a glob is Must exactly where a
literal path would be, and degrades to May only along an Unknown or May
fact; the rule above is the same statement made total.

Polarity consequences (the framework applies shared/universal-model.md 4.2; this
is the instance): `selector matches nothing` (SYS004) is P-: it fires
only when `hi` is empty, so a selector over a file with an `opaque`
region or a macro is never reported as matching nothing; ownership
claims in SYS002 and SYS003 use the P+ reading of 6.5.

### 6.5 Specificity and owner(path)

`owner : Identity -> Answer<Option<Node>>` assigns each identity to at
most one node.

SPECIFICITY of a matching selector against an identity is a vector,
compared lexicographically, larger is more specific:

| Position | Component |
|---|---|
| 1 | LEVEL: 3 if the selector's matching glob has `::` (symbol), 2 if PATH has no wildcard (file), 1 otherwise (directory pattern) |
| 2 | number of literal (wildcard-free) PATH segments |
| 3 | minus the number of `**` segments |
| 4 | minus the number of segments containing `*`, `?`, `[` or `{` |
| 5 | number of literal QUALNAME segments |
| 6 | number of predicates and negations that restrict the match (`lang`, `kind`, `attr` count one each; `!` counts zero) |

For a compound selector: a `|` takes the maximum over the branches that
match the identity; an `&` takes the maximum of the component vectors and
adds the predicate counts; `!` alone has the bottom vector (a negation is
never more specific than a glob). Example from the review (M12):
`src/**` is `(1, 1, -1, 0, 0, 0)` and `src/*/mod.rs` is
`(1, 2, 0, -1, 0, 0)`, so `src/x/mod.rs` belongs to the second; the
order is total on selectors, so the winner never depends on a tool.

Then, for identity u:

1. If a `grimble:binds` directive binds u to an entity (8.2), that is the
   owner, status Must, and nothing below is consulted (10.3).
2. Else let C be the nodes with an `owns` selector that matches u, with
   specificity and status. The owner is the node whose maximal
   specificity is highest. If two nodes tie at the highest specificity
   the answer is Unknown with both in `hi` and SYS002 fires (a tie is
   never broken arbitrarily). If the winner's status is Must the answer
   is `Exact(Some(node))`; if any candidate with at least equal
   specificity has status May, the answer is `Bounds{lo: Must candidates
   at the top, hi: all at the top}`.
3. Else, pack inference (10.3, rank 3) may suggest an owner at status May.
4. Else `Exact(None)`, which is FOREIGN, if the identity has no unseen
   remainder; otherwise Unknown (the identity might be claimed through
   hidden units).

`owner(path)` on a file path is `owner` of that file's module unit.

## 7. Exceptions inside the model

The four exception kinds of shared/rules.md replace v1's `waive`. In a
.grmb file three of them are CLAUSES (attributes) and the fourth is
synthesized.

```
node cli : trusted {
  accept CAP001 because="docs/decisions/2026-10-02-bootstrap-path.md";
  defer SYS005 ticket="01J9QKX3M8Z4T7N2V5B6C0D1E2" because="producer lands next cycle" until=2026-12-01;
  hotfix SYS002 ticket="01J9QMA7R2K5W8Y1H3F6G9P4S0" because="split the tie before release";
}
accept SYS004 on cli because="one-way import by design";   // top-level form
```

| Kind | Clause | Required attrs | Optional | Notes |
|---|---|---|---|---|
| accept | `accept RULE [on REF] because="..." [until=DATE]` | `because` | `until=DATE` | permanent without `until`, expiring with it (7.1); REATTEST compares the entity's Body digest with the attested one (docs/design/shared/rules.md section 10.1) |
| defer | `defer RULE [on REF] ticket="ULID" because="..."` | `ticket`, `because` | `until=DATE` | the `ticket` value is an opaque non-empty string to grimble, which checks nothing else (frob checks that it is a full ULID; an abbreviation is frob's DSL002, D178); standalone grimble reports UnresolvedExit |
| hotfix | `hotfix RULE [on REF] ticket="ULID" because="..."` | `ticket`, `because` | | expiry from `[exceptions] hotfix_days`, evaluated by date from the creation event |
| baseline | none | | | never written in a .grmb file: pools live in `<product>-ratchet.lock.json` (docs/design/shared/rules.md section 10.2). `grimble graph` synthesizes an `attr(baseline)` node on each entity that a pool key names, for display and for suppressed-finding accounting only; a hand-written `baseline` is MDL000 |

THE DEBT KEY SET (D160). Every construct that records owned, expiring
debt uses one set of attribute keys with one type each: `because="..."`
(a non-empty string), `until=DATE`, `ticket="..."` (an opaque string,
never a ref) and `owner=IDENT`. The forms differ only in which keys they
require:

| Form | Required | Optional | Where |
|---|---|---|---|
| `accept` | `because` | `until` | above |
| `defer` | `ticket`, `because` | `until` | above |
| `hotfix` | `ticket`, `because` | | above |
| `assumed` | `because`, `until`, `owner` | `ticket` | claim (4.4) |
| `sorry` | none | `because`, `until`, `ticket`, `owner` | planning holes (15.3) |

A key outside the set, or a required key missing, is MDL013 (MDL008 for
`assumed`). `because = "..."` with blanks parses; `grimble fmt` prints
`because="..."` (D161).

- Position. Inside an entity body the target is that entity and `on` is
  omitted (writing it is MDL013). At top level `on REF` is required and
  names an entity (MDL006 if it resolves to nothing). A target is always
  an entity of this model: an exception that parks a rule at a code
  symbol is a `grimble:` directive in the code or a `[[grimble.exception]]`
  record in `exceptions.toml`, not a .grmb clause.
- One spelling per file kind. The directive spelling
  `grimble:accept RULE because="..."` is for code files; written in a
  .grmb comment it is MDL013 (use the clause). There is no
  `because "..."` (bare string) form: every attribute is `key=value`,
  matching the `because=` spelling of the shared directive parser (v1's
  bare `because "..."` is gone).
- Reasons are judged by EXC rules (reason quality, budgets, STALE,
  EXPIRED; docs/design/shared/rules.md section 10.6), not by MDL rules; MDL013 only
  checks structure (kind and attribute combination, position, known
  rule id, `ticket` and `until` shape).
- An accept cannot park an Unresolved finding (EXC016); that is checked
  at evaluation, not at parse.
- Matching: an exception on entity E suppresses findings of RULE whose
  logical location is `E` or lies inside E's clauses (for example
  `node/cli` and `node/cli/owns`). Rule id equality is exact.

### 7.1 Legacy ticket aliases and design-first suppression (ticket ~GB502FM)

LEGACY `ticket=` VALUES. `defer RULE ticket=T-0042 ...` in a repo migrated
from v1 is valid. `ticket=` stays an opaque non-empty string to grimble
(grimble never reads tickets, grimble-model.md section 7), so a v1 id such
as `T-0042` raises no MDL013: MDL013 fires only on an empty or missing
`ticket`, never on its spelling. Who resolves the alias: frob alone, through
the aliases the v1 import recorded in the ledger (the same resolution as
`frob:todo T-####` and `frob:ticket T-####`, ticket ~KP5659Y). grimble never
resolves, rewrites or validates the value. When the alias is unknown to the
ledger the finding is frob's DSL002 (unresolvable ticket reference); the
defer then does not count as a live exit, so the parked finding is reported
again rather than silently suppressed. Standalone grimble, with no ledger,
keeps reporting UnresolvedExit as above.

DESIGN-FIRST WITHOUT A TICKET. A selector for code not yet written is MDL005
(Warn). The way to park it needs no ULID and no ticket: an EXPIRING ACCEPT,
`accept MDL005 on REF because="code lands with the parser work" until=2026-12-01;`.
`accept` takes the optional `until=DATE` of the debt key set; with `until`
the accept is no longer permanent: past the date it is EXC EXPIRED and the
MDL005 finding is live again, so the planned marker cannot rot. Without
`until` an accept stays permanent and a `because=` alone is a reason, not a
date. `defer` is not used for this case because it requires a ticket.

In U each exception clause is an `attr(name=accept|defer|hotfix)` on the
entity unit (section 9), so it is in the Attr facet and does not change
the Body digest: adding an accept never makes its own entity "changed".

## 8. Directives inside .grmb

### 8.1 Where a directive binds

Directives are parsed from comments by the shared parser (2.3) and bind
to ITEMS: an entity, a namespace, a `use`, a clause or the file.

1. A directive comment binds to the first item whose first token follows
   it, skipping other comments (a blank line does not detach it).
2. A comment that follows an item on the same line (after its `;` or its
   opening `{`) binds to that item.
3. A comment immediately before a closing `}` with no following item
   binds to the enclosing entity.
4. A comment before the `grimble = "2";` header or with no item after it
   binds to the file's module unit.

This is the same rule as for code units (docs/design/shared/code-model.md section 4),
applied to the U term of section 9, so the directive's target is a `unit`
or an `attr` node and every downstream query (`attachments`,
`directives_for`) works unchanged.

### 8.2 Verbs accepted

| Verb | Binds to | Effect inside a .grmb file |
|---|---|---|
| `frob:doc PATH#anchor` | entity or file | the design doc for this entity; DRIFT is evaluated between the doc's digest and the entity's Body and Doc facets through `grimble graph --json` (docs/design/grimble/grmb-spec.md section 20.2) |
| `frob:ticket ULID` | entity or clause | the work item that changed this hunk; REF check by frob from the JSON |
| `frob:todo ULID` | entity or clause | deferred work marker |
| `frob:invariant`, `frob:decision`, `frob:deprecated`, `frob:until` | entity or clause | as in docs/design/shared/code-model.md section 4, bound to a unit |
| `grimble:binds SYMREF [via="manual"]` | entity (node, flow end, contract, claim, vmodel) | explicit binding, source rank 1 of 10.3: the entity is bound to the identity SYMREF at Must. For a node it adds SYMREF to the node's ownership regardless of `owns`; on a flow it is accepted before a `producer`, `consumer` or `contract` clause to bind that end |
| `frob:tests SYMREF` | any entity that accepts `verified_by` | reverse evidence binding: the target entity's evidence includes this test (normally written in test code, 8.3) |
| claim verbs `grimble:effects`, `grimble:core`, `grimble:shell`, `grimble:calls` (D120; the dropped spellings are DSL003 findings, not claims) | entity | parsed and bound (a `unit` is a legal target); the NEAT rules answer NotApplicable on `grmb` units (no effects), so they never produce findings here; reserved so a future claim about a model entity has a place (19, question 9) |
| `grimble:accept`, `grimble:defer`, `grimble:hotfix` | none | MDL013: use the clause (section 7) |
| `grimble:node`, `grimble:channel`, `grimble:boundary` | none | these are code-side attestations naming an entity; written in a .grmb file they are MDL013 |

A `frob:` directive evaluated by frob needs `grimble graph --json`; a
frob without grimble reports it Unresolved (docs/design/grimble/grmb-spec.md section 20.2). The
directive grammar, the verb registry and the typed validators are the
shared ones of docs/design/shared/code-model.md section 4; this file adds no verb.

### 8.3 The one evidence relation

`Evidence(e, u)` relates an entity e to a test unit or document unit u.
It has ONE clause spelling on the model side and one on the code side
(D150; SysML v2 has one `verify` keyword per relation, E24, and StrictDoc
one link plus a code-side marker, E30):

- `verified_by SEL [for STEP.VARIANT];` in the body of e, on every entity
  kind that can be verified (4); with `for`, the evidence covers only the
  arms that match that pair (13.2) or the waypoint it sits on (14.2);
- `verified_by manual because="REASON";` for a check a person performs
  (4.5.2);
- `frob:tests <symref of e>` written on the test (8.2).

The relation is the union of both sides, each row with its status from
6.4 (a literal is Must, a glob as in 6.4). The level of the evidence is
derived from e (the paired test level of e's level, 4.5 and 13.3); it is
never written.

One ladder decides what a clause that resolves to nothing is (D171):

| State of a `verified_by SEL` clause | Verdict |
|---|---|
| PATH matches no file in the walk (the test is not written yet) | `planned`: no Error; it counts as no evidence, so the entity keeps its PLAN005 obligation; MDL005 is not reported for `verified_by` (the clause exists to name future code) |
| PATH matches a file, but no test unit | SYS011 (Error): a wrong id |
| selects test units | evidence (`covered` once the entity is bound, 12.8) |

Deprecated major-2 spellings that produce the same rows,
each reported MDL012 (Warn) with the replacement: `evidence tests SEL;`
and `evidence ref "S";` on a claim, and the test vmodel of 4.5. A claim
above L1 with an empty Evidence set that is not `assumed` is UNPROVABLE
(kernel, G03); a `frob:tests` that names no entity is MDL006 reported from
the .grmb side by `grimble graph`.

## 9. The U encoding

Moved to [shared/code-model.md](../shared/code-model.md#11-the-u-encoding-of-grmb) section 11 so this
spec stays about the language. Subsection numbers 9.1-9.6 are kept there, so
citations of "grmb-spec 9.x" resolve by number.

## 10. The formal relation to code

Moved to [shared/code-model.md](../shared/code-model.md#12-the-formal-relation-to-code) section 12, subsections
10.1-10.3 unchanged.

## 11. Planning layer: grammar and entities

Part II: the planning layer (sections 11-19). Part I (sections 1-10) is the
architecture layer; sections 20-21 are the model overview.

The planning layer adds seven entity kinds to the eight of section 4:
`system`, `actor`, `goal`, `step`, `scenario`, `impl`, `page`. All live in
the one namespace of 5.1; anchors are `kind/full-name` (5.5):
`goal/web_app.customer.place_order`. It is ADDITIVE to major 2 (3.4):
every text that was valid before keeps its meaning, because its words are
contextual (2.6) and its tokens were lexical errors before (2.2). Cycle 1
respelled several planning forms (D150-D165); every spelling the shipped
P1 parser reads keeps its meaning through major 2 with MDL012 (the bridge
list of 11.1 and 3.4, D168).

### 11.1 Grammar (EBNF)

The one grammar of the planning layer, over the tokens of 2.2; `name`,
`ref`, `qname`, `string`, `number`, `quantity`, `date` and `selector` are
those of 2.2, 2.7 and 6.1; `common`, `alias_etc`, `attr_cl` and `item`
are the productions of 4.10, which this grammar extends; a `///` doc
comment may precede any item.

```
item        = ... | plan_item ;                     (* the item of 4.10, which already names plan_item *)
plan_item   = system | actor | goal | step | scenario | impl | page ;
body(C)     = "{" { C } "}" | sorry ";" ;           (* a planning body or a hole, 15.3 *)

system      = "system" ( ref ";" | name "{" { sys_member } "}" ) ;   (* marker or declaration, 11.2 *)
sys_member  = ( item - use ) | ambient | "non_goal" name ";" | alias_etc
            | verified_by ;                         (* bridged: ignored with MDL012, 11.1; no `use`, D181 *)

actor       = "actor" name ":" ident ( ";" | "{" { actor_cl } "}" ) ;
actor_cl    = "in" "node" ref ";" | alias_etc ;

goal        = "goal" ref "{" { variant | group | attr_cl } "}" ;   (* attr_cl: the `attr` clause of 4 *)
group       = "one_of" [ "exclusive" ] "{" { variant } "}" ;
variant     = name [ "requires" ref { "," ref } ] ( ";" | "{" { common } "}" ) ;

step        = "step" step_name [ ":" outcome_set ] { step_fact } ( ";" | "{" { alias_etc } "}" ) ;
step_name   = owner "." name ;
owner       = "system" | ref ;                      (* ref resolves to an actor *)
outcome_set = [ "closed" | "open" ] "{" outcome_v { "," outcome_v } [ "," ] "}" ;
outcome_v   = name [ "(" ref ")" ] ;                (* ref resolves to a contract *)
step_fact   = "idempotent" ;

scenario    = "scenario" name [ "realizes" ref { "," ref } ] [ fails ] body(sc_member) ;
fails       = "fails" "with" "{" name { "," name } [ "," ] "}" ;
sc_member   = chain_stmt | handle | ambient | common ;
chain_stmt  = chain ( ";" | (* nothing when the chain ends with "}" *) ) ;
chain       = { elem link } tail ;
link        = "->" | "-!>" ;
elem        = step_ref | "include" ref | sorry ;
step_ref    = [ "::" ] [ "system" "." ] qname ;     (* resolves to a step *)
tail        = elem "=>" arms | terminal ;
terminal    = "end" "ok" | "end" "err" "(" name ")" | repeat | sorry ;
repeat      = "retry" [ step_ref ] [ "max" number ] [ "within" quantity ] [ "else" chain ] ;   (* max required: MDL027 *)
arms        = "{" { arm } "}" ;
arm         = pattern "=>" chain_stmt ;
pattern     = "_" | "unknown" | name | pair ;     (* a variant, or a step-qualified variant *)
pair        = step_ref "." name ;                (* the LAST segment of a dotted pattern is the variant, the rest the step_ref *)
handle      = "handle" arms ;

impl        = "impl" step_ref "for" ( ref | "*" ) body(impl_cl) ;
impl_cl     = realization | "on" "page" ref ";" | "in" "node" ref ";"
            | "chain" "{" { waypoint } "}" | common ;
realization = ident [ name ] "=" ( selector | route ) ";" ;   (* the kind decides: route/topic take a name, 14.1 *)
waypoint    = ident [ name ] "=" ( selector | route ) ( ";" | "{" { wp_cl } "}" ) ;
route       = string ;                              (* a name, not a selector: "METHOD /path" for route, a channel for topic *)
wp_cl       = source { "," source } "=>" name ";" | verified_by ;
source      = ident | number | "_" ;                (* error type, status, or the rest *)

page        = "page" name ( ";" | body(page_cl) ) ;
page_cl     = "entry" ";" | "from" ref { "," ref } ";" | realization | common ;

ambient     = "ambient" policy ( ";" | "{" { verified_by } "}" ) ;
policy      = "escalate" | "terminate"
            | ( "retry" | "restart" ) [ "max" number ] [ "within" quantity ] [ "else" policy ] ;   (* max and else required: AMB003 *)
verified_by = "verified_by" ( selector [ "for" pair ] | "manual" "because" "=" string ) ";" ;
sorry       = "sorry" { debt_key } ;                (* the debt key set of section 7 *)
debt_key    = ( "because" | "ticket" ) "=" string | "until" "=" date | "owner" "=" ident ;
```

Notes on the productions.

- A clause of an `impl` or `page` body that starts with an identifier
  which is not a planning word is a realization clause. Because `chain` is
  a planning word and no realization kind may equal one (2.6), `chain {`
  is never a realization.
- `ok` is a name in `outcome_v` and `pattern`; it is the distinguished
  success variant. A step without `: outcome_set` has outcome `{ ok }`.
- `->` and `-!>` appear only between chain elements; `=>` only after a
  matched element, after an arm pattern and in an outcome-map entry (2.2).
- `retry` without `max` is parsed (so the message is specific) and
  reported MDL027, not MDL000. There is no placeholder token: a retry
  target defaults to the matched element (12.5, D154).
- Two-word spellings: an underscore joins the parts of ONE keyword
  (`verified_by`, `one_of`, `non_goal`, `renamed_from`); a space separates
  a PHRASE of keywords each of which keeps its meaning (`fails with`,
  `in node`, `on page`, `part of`, `end ok`) (D161).
- THE BRIDGE (D168). The closed list of major-2 spellings that keep their
  meaning through major 2, each reported MDL012 (Warn) naming the
  replacement; it is exactly what the shipped parsers read before cycle 1:
  `include "path"` for `use` (3.2); `evidence tests SEL;` and `evidence ref
  "S";` on a claim and the test vmodel of 4.5 for `verified_by` (8.3);
  `review=` for `until=` (7); `step S -> { .. }` for `step S : { .. }`;
  arm `p -> c` for `p => c`; `title "t";` for a `///` line; `requires page
  P;` for `on page P;`; actor `node N;` for `in node N;`; `verified_by` on
  a `system` (the clause is ignored, a system has no status, 12.8); `goal P
  as K { }` for `goal P { attr dimension = K; }` (11.4). Nothing else is
  bridged: the pre-cycle-1 waypoint forms (`->` hops, `via FLOW`,
  `outcome { v <- S; }`) were never parsed, so they are MDL000 like any
  unknown text. A written retry target equal to the default is not a
  deprecated spelling: it is valid, and only `grimble fmt` drops it (9.6).

### 11.2 system: an entity with an interior

`system NAME { ... }` declares an entity and a containment prefix, like a
`namespace` that has an identity: items inside get the prefix `NAME.`, and
its body holds the system's own clauses (`ambient`, `non_goal`). More
files join a system in one of two ways (D157):

1. MOUNT: `use "web_app/flow.grmb" as web_app;` gives the file's items the
   prefix; a mount prefix or namespace whose full name equals a system's
   full name is that system's interior, not an MDL001 collision.
2. MEMBERSHIP: a file whose top level declares exactly one system, either
   by the marker `system REF;` or by one braced `system NAME { ... }`,
   places its other top-level planning items in that system, as if they
   were written inside the braces. A system has at most one braced
   declaration (MDL001 on the second) and any number of markers (at most
   one per file).

One precedence joins the two (D167). Let M be the file's mount prefix
(empty when no `use ... as` reaches it). A braced `system NAME { }` in the
file is a declaration like any other, so its full name is `M.NAME` and the
file's items become `M.NAME.X`. A marker's REF is a reference, resolved by
5.3 from M:

- Unmounted file (M empty): REF resolves from the root; when it resolves
  to nothing, the marker declares the system REF (one segment) at the
  root.
- Mounted file: the marker never declares. REF must resolve to a system
  whose full name equals M or is a proper prefix of M; the marker is then
  redundant (the items keep the mount prefix `M.X` and belong to that
  system by the longest-prefix rule below, never `M.REF.X`). Any other
  result is MDL031 "a mounted file names a different system" (remedy:
  drop the marker or the `as`).

So `use "flow.grmb" as web_app;` with `system web_app;` in flow.grmb
gives `web_app.X` (the marker resolves to the root `web_app`, equal to
M), and `use "x.grmb" as api;` with `system web_app;` in x.grmb is
MDL031.

Every actor, goal, step, scenario, impl and page belongs to exactly one
system: the system whose full name is the longest proper prefix of the
item's full name after the rules above. A planning item with no enclosing
system, or at the top level of a file that declares two or more systems,
is MDL031 (the message names the remedy: nest it, mark the file, or split
it). Architecture entities (nodes, flows, contracts) may live anywhere;
they do not belong to systems. Membership is per file, not per position,
so order independence (3.3) holds.

`system` has ONE sense, the enclosing system entity: `system.X` in a step
name is the reaction step `S.system.X` of the system S that the item
belongs to. `system` is a planning word, so that segment never collides
with a user name; the former actor kind `system` is spelled `external`
(D143).

### 11.3 actor

```
actor customer : human;
actor payments : external { in node payment_api; }
actor tick : timer { attr period = 1 s; }
```

| Field | Clause | Required | Meaning |
|---|---|---|---|
| name | `actor NAME` | yes | full name `S.NAME` |
| kind | `: KIND` | yes | from the actor-kind vocabulary: core `human`, `external`, `timer`, `device`; a pack may add kinds (D126). Unknown is MDL031 |
| node | `in node REF;` | no | the node that IS this actor (typically `kind external` or a device driver node); its steps are then located in that node for SYS015. Same spelling as on an impl (D161) |
| attrs | `attr K = V;` | no | a timer's period is `attr period = Q;` (no clause of its own) |

Actors are the only irreducible event generators (D126): every scenario
starts with an actor step (MDL029); `system` steps are reactions.

### 11.4 goal: keyed variant sets

```
goal customer {
  attr dimension = action;
  browse_items;
  place_order requires browse_items;
  track_order requires place_order;
}
goal customer.place_order { guest; account; }
```

A `goal PATH { variants }` block declares a VARIANT SET at PATH, which
resolves to an actor or a goal (MDL006 otherwise). Each variant is a goal
entity with full name `PATH-full-name.VARIANT`
(`web_app.customer.place_order`). The Rust reading is `enum Customer {
BrowseItems, PlaceOrder(Path), TrackOrder }` with `enum Path { Guest,
Account }`. The optional `attr dimension = KEY;` names the dimension for
reports (the mockup's `with key "action"`); it is metadata, so it is an
`attr`, and `as` keeps its one meaning, a mount prefix (D176). The
major-2 `goal PATH as KEY { }` is bridged (11.1).

- An actor's variant set may have a single variant (an actor with one use
  case is a legal design); a goal refined into ONE sub-goal, or a `one_of`
  with one alternative, is PLAN014 (D187).
- Several blocks on one PATH are additive (one variant set, as `extend`);
  two different `dimension` values on one PATH are MDL031.
- Nesting refines: a block at a goal path enumerates the variants of
  that goal (a keyed variant set). A group of siblings defaults to `all`;
  `one_of { ... }` with an optional `exclusive` flag selects among
  alternatives (15.5; a `one_of` rolls up with the join, 12.8). There are
  no AND/OR formulas; `one_of` is a group inside the block, never a
  header word. A choice made by the
  INPUT is a goal variant; a choice made by the OUTCOME is an arm (C34,
  PLAN020 flags a variant duplicated as an arm). LEAVES are goals with no
  variant set.
- `requires X` is a precondition: X must have been achieved before. X
  resolves to a goal of the same system (MDL031 across systems). The
  relation is transitive and acyclic (MDL030).
- Goals and steps under one actor share the actor's prefix; a goal and a
  step with the same name are MDL001 (goals name outcomes, steps name
  actions, so a collision is a naming smell anyway).

### 11.5 step

```
step customer.submits_cart;
step customer.enters_payment : { ok, declined(decline_reason), timeout };
step system.queries_products : { ok, no_item_found } idempotent;
step payments.charges : open { ok, declined };
```

A step is declared once, with its OUTCOME TYPE, and then used by any
number of scenarios. Full name: `OWNER-full-name.NAME` for an actor owner,
`S.system.NAME` for a reaction. The outcome is a finite set of variant
names, default `{ ok }`; a variant may carry a payload that is a
`contract` entity (4.3): the UML class-diagram role is the
existing contract, bound to a code type, and there is no new type system.
A variant name may repeat across steps; equal names mean the same error
(Zig error-set semantics, 12.3). `:` reads "has type", as on nodes,
actors and flows (2.2; AADL `name : kind`, E39). A trailing `idempotent`
is a step fact read by PLAN016; `open` marks an outcome set
owned outside the model (15.4).

The outcome is part of the step's Sig facet (section 9): adding a variant
changes the step's signature, which is exactly the change this layer
exists to propagate.

### 11.6 scenario

```
scenario checkout realizes customer.place_order {
  customer.submits_cart
    -> system.shows_total
    -> customer.enters_payment => {
         ok => system.confirms_order -> end ok;
         declined => retry max 3;
         timeout => end err(timeout);
       }
}
```

| Field | Clause | Required | Meaning |
|---|---|---|---|
| name | `scenario NAME` | yes | full name `S.NAME` |
| realizes | `realizes G, ...` | no | goals this scenario realizes (UML realization of a use case); a scenario that realizes nothing and that no scenario includes is PLAN010 |
| fails with | `fails with { v, ... }` | no | the declared error set; collected variants listed here propagate to an including scenario instead of being handled (12.4) |
| main chain | one `chain` statement | yes, exactly one (or the whole-body `sorry`, 15.3) | the main success scenario with its alternates; zero or several are MDL026 and MDL031 |
| handle | `handle { arms }` | no, at most one | end-of-scenario exhaustive match over the collected set |
| verified_by | `verified_by SEL [for STEP.VARIANT];` | list | acceptance tests; with `for`, the arm(s) covering that pair (13.2) |

`scenario` is the construct name because `flow` is taken (data movement,
4.2). A grmb scenario is a USE-CASE-LEVEL flow: one triggering actor step,
a main success path and its alternates. What BDD and Gherkin call a
Scenario is ONE path (E22, E23), which here is one arm path; `frob plan`
writes one Given/When/Then per arm (17.6). The mapping is 11.10 (D163).
v1's unused `scenario` keyword was a different construct and stays
dropped.

### 11.7 impl: a step bound to code

```
impl system.shows_total for checkout {
  handler = "api/orders.py::compute_total";
  in node backend;
  verified_by "tests/api/test_orders.py::test_total*";
}
impl customer.submits_cart for * {
  on page order_page;
  ui order_button = "src/frontend/components/order/OrderButton.tsx::OrderButton";
}
```

| Field | Clause | Required | Meaning |
|---|---|---|---|
| step | `impl STEP` | yes | the step realized |
| target | `for SCENARIO` or `for *` | yes | one scenario, or every scenario that uses the step; a specific impl wins over `for *` for its scenario |
| realization | `KIND [NAME] = SELECTOR;` | list | KIND from the realization vocabulary: core `ui api cli handler isr driver topic`, plus pack kinds (a page is bound by its own `page` entity, never by a realization kind, D176) (never grammar, as node kinds, D127; never equal to a planning word, 2.6); the right-hand side is a selector (6), so B, SYS004, SYS007, SYS008 and `grimble ack` apply unchanged |
| chain | `chain { waypoints }` | no | the ordered waypoints from entry to last effect (14) |
| pages | `on page P;` | list | the step happens on page P (`page` here is the planning word of 2.6, D181); transitive navigation requirement (12.7). `requires` is reserved for goal precedence (D161, E40) |
| node | `in node N;` | no | declared location; when absent it is the owner of the bound identities (13.4) |

Full name (an entity needs one, 9.2 has no anonymous units):
`S.SCENARIO.OWNER.STEP` for a specific impl
(`web_app.checkout.system.shows_total`), and `S._.OWNER.STEP` for `for *`
(`_` is a planning word, so no scenario can be named `_`). An impl whose
step its NAMED target scenario never uses is MDL031 (a contradiction); an
impl `for *` whose step no scenario uses is PLAN013 (Advisory: code bound
ahead of its design, legal by law 2 of 12.9; D174).

### 11.8 page: the navigation graph

```
page home { entry; ui = "src/frontend/pages/Home.tsx::Home"; }
page catalogue { from home; ui = "src/frontend/pages/Catalogue.tsx::Catalogue"; }
page order_page { from catalogue; ui = "src/frontend/pages/Order.tsx::OrderPage"; }
```

Pages are entities so that the mockup's "transitively requires home page,
order browser" is computable: `from` edges form a navigation graph (cycles
allowed: navigation goes back), `entry` marks where a user starts. A
missing page is MDL006; reachability and the transitive requirement are
12.7. `page` is in the core vocabulary because navigation is generic
(screens on a device menu are pages too); what realizes a page is pack
vocabulary.

### 11.9 Common planning clauses

- `/// text`: the human label and description (Doc facet; relabelling
  never makes the entity changed). It replaces `title "..."` (D159).
- `verified_by` (8.3): list; on goals, scenarios, impls, pages and
  waypoints. Not accepted on actors and steps (MDL000): a step is
  verified through the impls and scenarios that use it. On a system it is
  ignored with MDL012 (a bridged spelling, 11.1): a system has no status
  (12.8).

### 11.10 UML and Gherkin mapping

| UML or BDD concept | Planning construct | Note |
|---|---|---|
| system boundary (use-case diagram) | `system` | interior prefix |
| actor | `actor NAME : KIND` | the only event generators |
| use case | goal leaf | variant of the actor's goal enum |
| use-case generalization | goal refinement (`goal G { attr dimension = K; ... }`) | keyed variant set; `one_of` for alternatives |
| use-case precedence | `requires` | acyclic, transitive |
| include | `include S` in a chain | outcome is the included scenario's ending set; SysML v2 keeps `include` for this (E24) |
| extend | `=>` arms and `handle` arms | an extension point is a step variant; exhaustiveness replaces the free-form extension condition |
| realization (use case to collaboration) | `scenario ... realizes G` | |
| activity diagram | scenario chain | arms are decisions, `end` is a final node, `retry` a bounded loop |
| sequence diagram | `Succ(s)` with `node(st, s)` | lifelines are actors and nodes |
| alt / opt / loop fragments | `=>` / `-!>` with handle / `retry ... max` | |
| exception handler | `handle` | |
| signal or operation result | step outcome | Zig error set, Rust enum |
| class, data type | `contract` (4.3) | payload of a variant |
| component | `node` | |
| component realization | `impl ... for` | with pack realization kinds |
| deployment, state machine | out of scope; open (19) | |
| Gherkin `Feature` / BDD story | a scenario (or the goal it realizes) | one story, several paths (E23) |
| Gherkin `Rule` | a goal leaf | the business rule the paths illustrate (E22) |
| Gherkin `Scenario` / `Example` | one arm path of a scenario | Given the path to the step, When it yields the variant, Then the arm's terminal (17.6) |

## 12. Planning semantics

Moved to [planning-semantics.md](planning-semantics.md) with the numbering kept (ticket ~EBGD47R). Sections 12 to 15 live there:

- 12 Planning semantics: [12.1 sets](planning-semantics.md#121-sets), [12.2 goals](planning-semantics.md#122-goals-refinement-precedence-realization-coverage), [12.3 scenario typing](planning-semantics.md#123-scenario-typing), [12.4 error sets](planning-semantics.md#124-error-sets-handle-and-propagation), [12.5 retry](planning-semantics.md#125-retry), [12.6 paths](planning-semantics.md#126-paths-start-succession-termination), [12.7 pages](planning-semantics.md#127-pages), [12.8 status](planning-semantics.md#128-status), [12.9 the Laws](planning-semantics.md#129-the-laws-rev-2-c10).
- 13 Planning binding, verification and the V-model: [section 13](planning-semantics.md#13-planning-binding-verification-and-the-v-model) (13.1 binding to 13.5 SYS015).
- 14 Impl chains and required waypoints: [section 14](planning-semantics.md#14-impl-chains-and-required-waypoints) (14.1 syntax to 14.7 required waypoints).
- 15 Ambient faults, holes, unknown and open sets: [section 15](planning-semantics.md#15-ambient-faults-holes-unknown-and-open-sets) (15.1 policy to 15.6).

## 16. Rules

All rule tables of the language are here and nowhere else in the design set; the generated rule pages (`grimble explain`, docs/reference/rules/) are derived from the `Rule` derive. Prose elsewhere names the id where the semantics is defined.

### 16.1 MDL: well-formedness (grimble-model)

`grimble check` runs these on the model itself, before and independent of
any code rule. They are the `MDL` family of crate grimble-model
(shared/charter.md owner), each derived once with the `Rule` derive; the
documentation page is generated (notes/research/documentation.md section 3). They are
P+ (presence) over the exact model term; a rule whose subject sits inside
a `hole(kind=parse-error)` or an `opaque` reports one Unresolved for that subject instead (a `sorry` is no such hole, but the Unknown type and trigger it causes make the rules that read them Unresolved, 12.3, 12.6)
of an Error (the model must fail loudly, not quietly pass).

| Id | Alias | Severity | Condition |
|---|---|---|---|
| MDL000 | MDL-SYNTAX | Error | lexical or syntax error, bad encoding, forbidden construct (a hand-written `baseline`, a bare `because "..."`, a slug rule alias) |
| MDL001 | MDL-DUPLICATE-ENTITY | Error | two declarations of one full name (including alias and `renamed_from` collisions) |
| MDL002 | MDL-UNRESOLVED-INCLUDE | Error | a `use`d file or glob matches nothing, escapes the repo, is not readable (the alias keeps its pre-`use` name) |
| MDL003 | MDL-INCLUDE-CYCLE | Error | the `use` graph has a cycle (the offending `use` is skipped) |
| MDL004 | MDL-UNKNOWN-PACK | Error | pack not in `packs/`, not enabled in `grimble.toml`, or version or digest differs from the pin |
| MDL005 | MDL-SELECTOR-NO-FILE | Warn | a selector's PATH matches no file in the walk. A WARNING by design: a model may legitimately describe code that does not exist yet. It suppresses SYS001 for the same selector so one root cause is one finding; a selector whose file matches but whose units do not is SYS001 |
| MDL006 | MDL-UNRESOLVED-REF | Error | a reference (flow endpoint, claim operand, link, exception target, `frob:tests` target) resolves to no entity, or to an entity of the wrong kind (except a V-model link target that is neither a vmodel nor a planning entity, which is MDL014) |
| MDL007 | MDL-VERSION | Error | missing header, unsupported major, or files of one model with different majors |
| MDL008 | MDL-FIELD | Error | a required field is missing (`trust`, flow `label`, contract `shape`, claim `what`, vmodel `kind` and `level`, a template's `excuse` clause, an excuse's `for` or non-empty `because`), a scalar clause appears twice, two waypoints of one chain share a name, or an `extend` sets a scalar; also a `may` grant with neither `because=` nor `ticket=` (Warn) |
| MDL009 | MDL-TYPE | Error | an ill-typed value: unit outside the table, comparing dimensions, a path with `..` or empty, a boundary pair on the wrong lattice, a malformed date |
| MDL010 | MDL-SELECTOR-EMPTY-BY-CONSTRUCTION | Warn | a selector that cannot match anything whatever the repository holds (`lang(rust) & lang(python)`, `a & !a`) |
| MDL011 | MDL-MODULE | Error | `part of` name differs from the root `module`, or two roots declare the same module name, or an included file declares `module` |
| MDL012 | MDL-DEPRECATED-NAME | Warn | a deprecated major-2 spelling that has a replacement (`include "path"`, `evidence tests`, `evidence ref`, a test vmodel, `review=`, and the rest of the closed bridge list of 11.1; the message names the replacement, D168); a reference by a `renamed_from` name, or a `renamed_from` clause that nothing needs any more (this second half needs lock data and is deferred to G12; grimble-model reports only the reference half) |
| MDL013 | MDL-EXCEPTION | Error | malformed exception clause: wrong attribute set for the kind, `on` inside a body, missing `on` at top level, unknown rule id, an empty `ticket` or a malformed `until`, a `grimble:accept` style directive in a .grmb comment |
| MDL014 | MDL-VMODEL | Error | V-model construction error (wrong endpoint kinds, including a link target that resolves to an entity that is neither a vmodel nor a planning entity; an unresolved link target is MDL006, missing `ref`, a test with neither or both of `runnable` and `manual`, an empty `manual` reason, a malformed `ref` anchor (4.5.1), duplicate link, `supersedes` without `because`) |
| MDL015 | MDL-SHADOW | Advisory | the resolved entity shadows a different entity of the same name at an outer level |
| MDL016 | MDL-UNKNOWN-ATOM | Error | a capability atom in no registry and no enabled pack |
| MDL017 | MDL-DUPLICATE-CLAUSE | Advisory | a list clause repeated with identical content; two evidence clauses that resolve to the same unit (4.5.2) |
| MDL018 | MDL-NODE-EXCUSE | Error | an `excuses` clause on a `node` or in an `extend node` (removed by D75). Remedy: move the reasoning into a matrix-build template (4.7) or grant the atom with `may`; ungranted already means denied |
| MDL019 | MDL-ORPHAN-FILE | Warn | a `.grmb` file of the walk that no declared root reaches through `use` and that is not excluded (3.1). Remedy: `use` it from a root, list it under `[grimble] models`, or exclude it in `[check] exclude` |
| MDL020 | MDL-INCLUDE-OUTSIDE | Error | a `use` (or glob) names a file above the using file's directory without the `outside` marker (3.2); the `use` is skipped |
| MDL021 | MDL-NO-ROOT | Unresolved (required) | no model root is declared (`[grimble] models` empty) while `.grmb` files exist, or a declared root is not a `.grmb` file of the walk (3.1) |
| MDL022 | MDL-NONEXHAUSTIVE | Error | a `=>` block or a `handle` does not match some variant of its domain (names the missing variants) |
| MDL023 | MDL-UNHANDLED | Error | a collected pair neither handled nor propagated; a pair collected inside a handle arm that is not in `fails with`; `end err(v)` with v outside a declared `fails with` |
| MDL024 | MDL-FALLIBLE-SEQUENCE | Error | `->` after an element whose outcome is not `{ ok }`; `-!>` on an outcome without `ok` |
| MDL025 | MDL-UNREACHABLE-ARM | Error | an arm that is redundant, names a variant foreign to its domain, or ties in specificity with another arm on one pair (three diagnostics, C7, each printing the outcome-set diff) |
| MDL026 | MDL-UNTERMINATED | Error | a scenario with no main chain (a whole-body `sorry` does not fire this, 15.3), a chain without a terminal (recovery), or a cycle in the scenario include graph |
| MDL027 | MDL-RETRY | Error | `retry` without `max`, `max 0`, outside an arm, a written target not on the path, an omitted target where the default is not one element (12.5), or no `else` under a `_` or `unknown` arm |
| MDL028 | MDL-WILDCARD-ARM | Warn | an arm with pattern `_` |
| MDL029 | MDL-SCENARIO-START | Error | the main chain starts with a `system` step or an include of a scenario that does (never on a whole-body `sorry`, 15.3) |
| MDL030 | MDL-REQUIRES-CYCLE | Error | a cycle in goal `requires` |
| MDL031 | MDL-PLANNING | Error | a planning item outside a system, or at the top level of a file that declares two or more systems, or a second `system REF;` marker in one file, or a marker in a mounted file that names a system not equal to or enclosing the mount prefix (11.2, D167); a planning word used as a name; an unknown actor kind or realization kind, or a pack kind equal to a planning word (2.6); two `dimension` values on one goal path; `requires` across systems; an impl for a step its scenario never uses; more than one main chain |
| MDL032 | MDL-UNKNOWN-ARM | Error | an `unknown` arm that is the only arm, or where a known variant has no arm (15.4) |
| MDL033 | MDL-OPEN-MATCH | Error | a match over an `open` outcome set with neither `unknown` nor `_` |
| MDL034 | MDL-EXCLUSIVE | Error | `one_of ... exclusive` whose alternatives overlap |

Unresolved references (unknown actor, undeclared step, missing page,
unknown contract payload, goal path of the wrong kind) are MDL006, as for
every other reference. The rules are P+ over the exact model term; a
subject inside a `hole` reports one Unresolved (above).

Adding a variant to a step therefore produces MDL022 in every scenario
that matches that step and MDL023 in every scenario that collects it
without a covering arm, and through `fails with` in every includer: the
change propagates like a compile error, and `frob plan --from-design
--findings` can turn each one into a ticket (17.6).

Cyclic flows are allowed and are not an MDL rule: a cycle is a legal
model and the kernel's age and demand computations handle it by SCC
condensation. What the kernel does with a rate-fed cycle (+infinity with a
witness, docs/design/grimble/grmb-spec.md section 20.1) is a kernel verdict. Include cycles
(MDL003) and V-model trace cycles (a kernel closure rule) are refused;
flow cycles are not.

Ids are `FAMILYNNN`, new family MDL registered in shared/rules.md by the
implementation ticket (G08); the aliases above are the slug aliases.

### 16.2 PLAN: obligations, coverage and waypoints (grimble-bind)

Family `PLAN`, ids PLAN001-PLAN099, owner grimble, crate grimble-bind
(status needs B). Registered in shared/rules.md 3 by P2. New PLAN rules ship
Advisory first and graduate by ratchet (C35); the Severity column is the
graduated target.

| Id | Alias | Severity | Condition | Obligation kind |
|---|---|---|---|---|
| PLAN001 | PLAN-UNREALIZED-GOAL | Advisory | a goal leaf covered by no scenario, except an unrealized alternative of a satisfied `one_of` (12.2) | `unrealized_goal` |
| PLAN002 | PLAN-COARSE-REALIZATION | Warn | a scenario realizes a goal that has refinements (12.2) | - |
| PLAN003 | PLAN-UNIMPLEMENTED-STEP | Advisory | a step use `(st, s)` with no impl, specific or `for *` | `unimplemented_step` |
| PLAN004 | PLAN-UNBOUND-IMPL | Advisory | an impl or page with no realization clause and no waypoint (an empty selector is SYS004, listed as the same obligation, not reported twice) | `unbound_impl` |
| PLAN005 | PLAN-UNVERIFIED | Advisory | a goal leaf, scenario, impl or page with no OWN EVIDENCE (12.8: no Evidence row of either spelling, or only `planned` clauses); not on the unrealized alternatives of a satisfied `one_of` (12.2) | `unverified` |
| PLAN006 | PLAN-ARM-UNCOVERED | Advisory | a pair (step, variant) with no covering `verified_by ... for` on its scenario or any waypoint of its step's impls; one obligation naming the pair, the arms and outcome-map entries (13.2, D184) | `uncovered_arm` |
| PLAN007 | PLAN-AFFORDANCE | Warn | the impl's realization kinds do not satisfy the affordance rule for the step owner's kind (core: `human` needs one of `ui`, `cli`, `api`; `external` needs `handler` or `api`; a `system` step needs `handler`, or also `isr` or `driver` when every scenario using it is triggered by a `timer` or `device` actor; `device` needs `isr` or `driver`; `timer` needs `handler` or `isr`; D181; Unknown triggers follow 12.6) | - |
| PLAN008 | PLAN-PAGE-UNREACHABLE | Warn | a page not reachable from an entry, or an `on page` target outside `Reach` (12.7) | - |
| PLAN009 | PLAN-NODE-MISMATCH | Warn | `in node N` differs from the Must owner of a bound identity, or from the node of the first waypoint (13.4) | - |
| PLAN010 | PLAN-UNJUSTIFIED-SCENARIO | Warn | a scenario that realizes nothing and that no scenario includes | - |
| PLAN011 | PLAN-UNMODELED-FAILURE | Advisory | a boundary failure of a step bound to code that no outcome variant models; when the step's set is `open` and the match has an `unknown` arm, the detail names that arm as the one that would receive it (PLAN017 retired into this rule, D193) | - |
| PLAN012 | PLAN-SWALLOWED-OUTCOME | Advisory | a non-ok variant whose arm ends `end ok` with no effect | - |
| PLAN013 | PLAN-UNUSED-IMPL | Advisory | an impl `for *` whose step no scenario uses (11.7; for a named target it is MDL031) | - |
| PLAN014 | PLAN-DEAD-OR-EMPTY | Advisory | a step used nowhere, a REFINEMENT set with one variant counting the variants inside its groups (a `goal` block whose PATH is a goal, or a `one_of` group); an actor's own set may have one variant (11.4, D187) | - |
| PLAN015 | PLAN-SORRY-POLICY | Warn; Error under a release profile | every `sorry` (one finding per `sorry`, naming its tainted dependents; D190) | - |
| PLAN016 | PLAN-RETRY-HAZARD | Warn | a `retry`, in an arm or in an ambient policy, whose repeated path contains a step that is not `idempotent` (one finding per retry, naming the steps; D169) | - |
| PLAN018 | PLAN-ONE-OF-UNREALIZED | Advisory | no alternative of a `one_of` is realized | - |
| PLAN020 | PLAN-VARIANT-AS-ARM | Advisory | an input-chosen alternative modeled as an outcome arm | - |
| PLAN021 | PLAN-COMPLETENESS-REGRESSION | Advisory | a completeness ratio (12.8 rollup) below its ratchet value | - |
| PLAN022 | PLAN-STALE-DESIGN | Advisory | an entity whose semantic digest changed while its bound code did not (or the reverse), against the lock | - |
| PLAN027 | PLAN-NON-GOAL-REALIZED | Warn | a scenario realizes a `non_goal` | - |
| PLAN030 | PLAN-MISSING-WAYPOINT | Error | a required waypoint (R1-R7, 14.7) absent from the chain; the fix is suggest-only | - |
| PLAN031 | PLAN-CHAIN-BREAK | Error; Unresolved on opaque | adjacent waypoints not connected by reach (14.2) | - |
| PLAN032 | PLAN-UNATTRIBUTED-ERROR | Error; Unresolved on opaque | a producible error with no waypoint and no map entry owning it | - |
| PLAN033 | PLAN-OFF-PATH-WAYPOINT | Error | a waypoint outside the step's derived cone | - |
| PLAN034 | PLAN-REDUNDANT-WAYPOINT | Advisory | a waypoint required by no R-item and not pinned for evidence | - |
| PLAN040 | PLAN-IMPL-IN-DESIGN-FILE | Advisory, off by default | an impl in a design file when a sibling `.impl.grmb` exists (14.6) | - |
| PLAN041 | PLAN-UNMAPPED-ERROR | Error; Unresolved (required) on opaque | a producible error of a waypoint's unit that no outcome-map source covers; Unresolved when the waypoint's error set is Unknown and no outcome map claims it (14.4; was ERR002; D185) | - |
| PLAN042 | PLAN-UNPRODUCIBLE-MAPPING | Warn | a mapped source the unit cannot produce, or a variant with no source (14.4; was ERR003) | - |
| PLAN044 | PLAN-OPEN-MAP-NO-REST | Error | an outcome map over an `open` set with no `_` source (14.4; was ERR005) | - |
| PLAN050, PLAN051, PLAN056-PLAN058 | verification rules | Advisory | PLAN050 LEVEL-MISMATCH (13.3), PLAN051 FLOW-UNVERIFIED (a cross-node flow with both ends bound and no OWN EVIDENCE on it or its contract), PLAN056-PLAN058 as specified in notes/research/grmb-r2-verification.md (its PLAN-G07..G09) | - |
| PLAN052 | PLAN-SUSPECT-EVIDENCE | Advisory | an entity whose semantic digest differs from the lock value recorded when an evidence item's test last changed or was acked (R2 PLAN-G03; reads the lock like PLAN022, so it ships in P3) | - |

Retired or reserved ids: PLAN019, PLAN023, PLAN026 reserved;
PLAN024 and PLAN025 retired by D158 (a budget is a `bound` claim; its
unproven state is CLAIM003); PLAN043 retired into PLAN006 by D184; PLAN017 retired into PLAN011 by D193; PLAN053, PLAN054, PLAN055, PLAN059 retired into PM046-PM049 by D204 (frob-side, 16.5). The outcome-map rules were ERR001-ERR006
before cycle 1; ERR001-ERR003 are grimble-lints code rules (shared/rules.md), so
the planning ones were renumbered (D165), and ERR001 and ERR006 of the old
range were never defined. One finding per root cause, keyed on (step,
waypoint) for PLAN030-PLAN034 (C11).

Advisory obligations are the design backlog: they are expected while
designing, so they never fail the default gate; a profile (shared/rules.md 7)
may raise them (a release profile raising PLAN001 and PLAN003 to Error is
the "design complete" gate).

### 16.3 SYS015 and SYS016 (grimble-bind, extend binding.md 6)

| Id | Alias | Polarity | Severity | Condition |
|---|---|---|---|---|
| SYS015 | SYS-BEHAVIOR-FLOW | P+ | Error | consecutive step uses, or adjacent waypoints, located in different nodes with no flow in that direction (13.5, 14.2); Unresolved when a node is Unknown |
| SYS016 | SYS-FLOW-ABSENT | P- | Warn | a declared flow that no step use or waypoint hop exercises (C19); Unresolved while a step use or hop that could exercise it has an Unknown node (P- over Unknown, shared/universal-model.md 4.2; D179) |

### 16.4 AMB: ambient faults (grimble-bind)

| Id | Alias | Severity | Condition |
|---|---|---|---|
| AMB001 | AMB-POLICY-MISSING | Error | a system with no ambient policy (quick-fix inserts `terminate`) |
| AMB003 | AMB-UNBOUNDED | Error | a `retry` or `restart` policy with no `max` or no `else` tail (parsed so the message is specific, as MDL027 for arm retries; D190) |
| AMB004 | AMB-RETRY-AMPLIFY | Warn | an arm `retry` whose step lies on the repeated path of the ambient `retry` that applies to it (15.1); ONE finding per (arm retry, applying policy), naming the policy and the product of the two `max` counts; an arm retry reached from triggered scenarios with different policies gets one finding per distinct policy (D188, D192, D196) |
| AMB005 | AMB-OVERCATCH | Error | an ambient type or root catch-all in an outcome map |
| AMB007 | AMB-DOMAIN-PANIC | Warn | a mapped domain error converted to a panic |
| AMB008 | AMB-POLICY-UNVERIFIED | Advisory | a system policy with no `verified_by` in its body (15.1) |
| AMB009 | AMB-RESTART-STATEFUL | Advisory | `restart` of a stateful node |

AMB002 (the ambient half of PLAN016, D169) and AMB006 (escalation to a
supervising node no construct can name, D177) are retired and reserved.

### 16.5 PM: the frob join (frob-pm; ids after PM036; PM042, PM044, PM045 unused R1 proposals)

| Id | Alias | Severity | Condition |
|---|---|---|---|
| PM037 | PM-UNPLANNED-OBLIGATION | Advisory | an obligation of the graph JSON whose entity has no live ticket (not outcome wont-fix, invalid or duplicate) with `implements` to the entity or to one of its design ancestors (impl, scenario, goal chain) |
| PM038 | PM-IMPLEMENTS-DECLARED | Error | a ticket reaching `done` (close or land) while an entity it `implements` has `status_hi = declared`; Unresolved when `status` and `status_hi` differ or grimble is absent. Evaluated as the close guard `design_bound` (17.5) |
| PM039 | PM-DONE-UNTOUCHED | Warn | a ticket closed `done` whose landed diff touches none of the identities bound to the entities it implements |
| PM040 | PM-MOVING-TARGET | Advisory | an implemented entity whose digest changed after the ticket started (C22) |
| PM041 | PM-STALE-LINK | Advisory | an `implements` link to an entity whose digest changed since the link was made (C22) |
| PM043 | PM-APPROVAL-GATE | Error when enabled | approval of the entity required before `design_bound` passes; opt-in top tier only, DEFAULT OFF (D146) |
| PM046 | PM-VERIFICATION-UNPLANNED | Advisory | a ticket that `implements` a scenario or goal leaf enters in-progress while the entity has no OWN EVIDENCE (12.8) (R2 PLAN-G04; was PLAN053) |
| PM047 | PM-DESIGN-VERIFIED | Error when enabled; DEFAULT OFF | opt-in close guard `design_verified`: a ticket reaches `done` only if every planning entity it implements is `verified` (12.8); Unresolved as 17.5 when the statuses differ or grimble is absent; until ~AMNDCCT lands an entity with a `manual` clause cannot pass (R2 PLAN-G05; was PLAN054) |
| PM048 | PM-NONTEST-UNRECORDED | Advisory | a `manual` OWN EVIDENCE row that is `not-run`, or whose passing attestation's stored `body_digest` differs from the current one (12.8) (R2 PLAN-G06; was PLAN055) |
| PM049 | PM-FLAKY-EVIDENCE | Advisory | a test OWN EVIDENCE row whose WINDOW records (12.8) are not all one verdict; its verdict is then `inconclusive`, so the entity is not `verified` (R2 PLAN-G10; was PLAN059; D205, D206) |

## 17. Graph JSON, the frob join and renderings

### 17.1 Graph JSON additions (grimble.graph/1, check --json)

All additions are optional keys, so the majors stay `grimble.graph/1` and
`gob.sibling/1` (shared/sibling-contract.md 4); sibling.json gains the `$defs`
and its strict producer schema is updated by P2.

Entity records (shared/sibling-contract.md 3.7) gain, for planning kinds:

| Key | Type | Meaning |
|---|---|---|
| `status` | `declared` `bound` `verified` | from `lo` (12.8; the rung `covered`). shared/sibling-contract.md 3.8.1, D151 |
| `status_hi` | same | from `hi`; equal to `status` unless a selector is May or Unknown |
| `level` | V-model level or null | 13.3 |
| `system` | anchor | the owning system |
| `plan` | object per kind | actor `{kind, node}`; goal `{dimension, parent, leaf, requires[]}`; step `{owner, outcome: [{variant, payload}]}`; scenario `{realizes[], fails_with, error_set[], collected: [{step, variant, handled_by}]}`; impl `{step, scenario (null for *), node, pages[]}`; page `{entry, from[]}` |
| `rollup` | object | goals, scenarios, systems: `{declared, bound, verified}` counts of the leaf impls below |

Top-level `obligations`: an array of `{rule, kind, anchor, detail}`,
one per PLAN obligation of 16.2 (kinds `unrealized_goal`,
`unimplemented_step`, `unbound_impl`, `unverified`, `uncovered_arm`),
sorted by anchor. It is listed whether or not the rule is enabled, so
frob's PM037 and `plan --from-design` see the full backlog.

`edges` kinds gain `realizes` (scenario to goal), `requires` (goal to
goal), `refines` (goal to parent goal), `succ` (step to step, with
`scenario`), `invokes` (scenario to scenario), `impl_of` (impl to step),
`impl_for` (impl to scenario), `on_page` (impl to page), `navigates`
(page to page), `in_node` (actor or impl to node), `waypoint_next`
(waypoint to waypoint). `bindings` roles gain `realization` (with
`realization_kind`, and for a waypoint its anchor `wp[NAME]` or `wp[K]` of 9.4 as `waypoint`) and
`verified_by`.

grimble never reads tickets (D28). Status is layered: grimble computes
design status and obligations (12.8, 17.1); frob overlays the ledger.

### 17.2 The canonical link

Moved to frob/pm-and-releases.md 10.1.

### 17.3 Overlay and rollup

Moved to frob/pm-and-releases.md 10.2.

### 17.4 Rules

Moved to frob/pm-and-releases.md 10.3.

### 17.5 Close guard `design_bound`

Moved to frob/pm-and-releases.md 10.4.

### 17.6 `frob plan --from-design`

Moved to frob/pm-and-releases.md 10.5.

### 17.7 Renderings

`grimble graph --mermaid` emits per scenario a sequence diagram (the
actors and `system` as lifelines; `Succ` pairs as messages, a `-!>` hop
dashed; one `alt` per `=>` match and per `handle` block, one branch per
arm; `retry` a `loop` carrying its `max`/`within` bound, an `else` chain
an `opt`) and an activity diagram (steps as nodes, arms as labelled
edges, terminals `end ok`/`end err(v)`/`sorry` as end nodes), and per
system a use-case diagram (actors outside the boundary, goals and the
`realizes` scenarios inside, `requires` as dotted edges); no
communication diagram (C17). The node lifelines of `node(st, s)` wait for
P6, and the structure view for a later phase. The payload is
`{"mermaid": "..."}` instead of the graph document. `grimble show
--prose` renders a scenario as prose (C18); `grimble trace` (14.5, 13.3)
shows the V; crunk's binding of `ui` realizations is designed elsewhere.

## 18. Conformance, example and milestones

Moved to [conformance.md](conformance.md) with the numbering kept (ticket ~EBGD47R): [18.1 conformance corpus](conformance.md#181-conformance-corpus), [18.2 example](conformance.md#182-example), [18.3 milestones](conformance.md#183-milestones).

## 19. Open questions

The one open-questions list of the language (it replaces the old
grmb-spec 14.2, the planning layer's two open-question lists and the corpus GAPS.md). An
item is closed by a decision in decisions.toml and removed here.

Architecture layer:

1. Lattices: is a pack the right owner of a fifth trust level, or
   should a model file have a `lattice` item (4.1)?
2. Cross-model references: roots are isolated (3.1); two models sharing
   a contract need a cross-root reference or one root.
3. Selector text is sliced from the .grmb token stream and re-parsed by
   gob-walk (G07); is that enough for span fidelity?
4. Ids of the kernel verdicts and the five V-model closure rules
   (review M3); MDL014 covers construction errors only.
5. The discharge conditions of the proof ladder `L1`..`L5` (G03).
6. Model exceptions are clauses (MDL013 refuses directives), so frob's
   `accept` verb must edit a .grmb file; is `exceptions.toml` the better
   home?
7. `until=` is a date only; a metric target is not expressible.
8. A `growth` period: add `w` and `mo` to the time units, or keep `%/d`?
9. Claim verbs (`grimble:effects`, ...) are inert on .grmb units; keep,
   or make them MDL013?
10. A glob `use` silently admits a new file; require a count marker?
11. Exact `pack` pins need a model edit for a security fix; may
    `grimble packs update` rewrite the pin?
12. Is `renamed_from` enough for the ack planner, or should lock entries
    also key on a generated entity id stored in the file?

Planning layer (G-ids are the corpus gap ids the mockups cite):

13. G1: fork/join and fire-and-forget; `->` serializes them (f05, d04).
14. G2: a loop over a SUCCESS outcome (pagination, polling) (f06, d11).
15. G4: state machines and modes across scenarios (d06, d07).
16. G5: per-item partial failure (d08); G7: generic payloads (d11).
17. G6: prose-to-grmb authoring; renderings are read-only (f16).
18. G8: cross-cutting properties that are not a path (d09, d10).
19. G9: preemption, priority and hard deadlines (d02, d07).
20. G10: branching code paths inside one impl chain; until decided every
    branch needs its waypoints (14.7).
21. G11: delivery semantics (at-least-once, ordering) (d03, d04).
22. Async hand-off: whether R7 holds through a queue or task spawn.
23. Which atoms count as observable effects for R4 (logging, metrics).
24. Whether `sorry` needs `draft` sugar (D142), and how `vmodel kind
    decision`, `frob:decision` and decisions.toml relate (D145).
25. Actor as stakeholder (an actor that is not an event generator).
26. Two acceptance channels: a scenario's `verified_by ... for` arms and
    the acceptance criteria of the story `frob plan` seeds from it
    (frob/pm-and-releases.md, PM015 vs PLAN006, PM038 vs PLAN004) judge one fact
    from two sides; the reconciliation is open.
27. `module`/`part of` and `system` both say "the unit this file belongs
    to"; a one-system-per-module model writes the name twice.
28. `flow ... condition on_ok|on_err` (4.2) is a second, untyped outcome
    mechanism next to step outcomes; whether it stays.
29. Whether a grmb `scenario` should be renamed (`use_case`) for Gherkin
    interop (D163 keeps it).

## 20. The model and the substrate

This section is the grimble model overview that stood in docs/design/grimble/grmb-spec.md section 20
(removed by ticket ~CTVPW94, docs/MOVED.toml): what the model is, its
kernel, and how it meets the substrate. The binding relation, identity and
the capability matrix are in [binding.md](binding.md) (sections 12 to 15
and 7). Provenance: written under T-0001 (a v1-format id that migrates
with an alias); ownership after shared/charter.md: the grimble model is a new
language, v1 strata is deprecated and has no migration path (D136), crates
`grimble-model`, `grimble-kernel`, `grimble-bind`. Inputs: notes/v1/strata.md
(surface grammar, kernel, 12 binding mechanisms, rule inputs, measured
adoption), the binding requirement in shared/charter.md, shared/code-model.md. Milestone 2
or later (D36).

### 20.1 What the model is

#### In one sentence

A typed architecture graph (nodes, flows, boundaries, claims, and a
V-model of requirements, designs, tests) whose elements bind to code
SYMBOLS in any language, checked by a small semantic kernel, with every
optional vocabulary (threat catalogs, reliability markers, compliance,
hosts) loaded as data packs rather than grammar.

Measured v1 adoption drives the cut: every consumer uses node, flow,
code, may, assert/assume, waive (now the exception kinds); two use the V-model; zero use policy,
scenario, refine, entity/architecture/configuration, host, Kerberos,
deploy, or the six-phase boundary grammar. 79 of 139 v1 keywords never
reached the prover.

The planning layer (sections 11-17, D124-D133) adds the left arm of
the V above the architecture: actors, goal variant trees, scenarios of
steps with typed outcomes and exhaustive handling, and impl blocks that
bind steps to code; it is the one behaviour construct, kept because it
is checkable.

#### Kernel

Crate `grimble-kernel`, ported from the v1 strata kernel (Rust already): label closure over flows with
boundary endorse/declassify, SCC longest-path age, summed demand and
capacity utilisation, V-model closure (paired levels, five structural
rules, milestone known gaps), claim verdicts PROVED / REFUTED(witness) /
UNPROVABLE with auto-generated assumes, assume ownership and expiry.
An assumption that states no flow (a CWE weakness, a PII duty) is an
`attests "..."` claim: owner and `until` date mandatory, Unresolved until
evidence, REFUTED once overdue, never a false `noflow` (section 4.4).
Everything else is a join between the model and the code graph.

#### Data packs

Threat obligations, reliability markers, compliance views, CVE
fingerprints, PII categories and every other optional vocabulary ship as
data packs, never as grammar; milestone 2 or later (D36). A pack
contributes capability atoms, detectors, callee vocabularies, inference
rules, claim templates, node kinds and (decision pending) lattice
extensions. packs-and-plugins.md (G04) is the definition: the pack format and its
JSON Schema, where packs live (built-in as inventory entries of the
shared registry crate, repository `packs/`, external by URL and digest),
the drift-lock `grimble.packs.lock`, materialization, how detectors
become matrix cells, and the three built-in packs `core-effects`,
`ci-github` and `rust-ecosystem`. This file does not repeat it.

#### Registry drift-lock

Kept in spirit: a registry row names a concept and its disposition
(`handled_by RULE`, `deferred ticket=<ulid>` with the ticket opaque to
grimble, `duplicate_of`, `out_of_scope caught_by`). In v2 the registry is generated from rule metadata plus
pack data, and the only hand-written part is dispositions for concepts
with no rule yet. Rows whose deferred ticket closes go red, as in v1.

#### Decided

Decided 2026-10-02: `.grmb` is its own language with its own parser
(leaf crate, spans for every construct, JSON export on day one, editor
grammar generated from the keyword table); FOREIGN symbols are Warn
until `[grimble] strict = true` in `grimble.toml`.

#### Corpus severities (decision, 2026-10-31)

The conformance corpus (`crates/grimble-model/tests/corpus`) expects only `error` and `unresolved`. Commit d7ea79ce8e retired Warn and Advisory (shared/rules.md 6.1.1), so every MDL rule that once warned (MDL005, MDL008 on `may` without a reason, MDL010, MDL012, MDL015, MDL017, MDL019) now reports as `error`; the stale `warn:` and `advisory:` expectations were rewritten, not the rules. The corpus parser rejects the retired keys so the test stays strict.

### 20.2 The model meets the substrate

The revision of 2026-10-04 audited the model against shared/universal-model.md
(notes/review/grimble-review.md found 4 HIGH, 12 MEDIUM and 7 LOW gaps) and
set the frame for the milestone-2 design tickets G01-G04: the full .grmb
specification (this file), binding semantics ([binding.md](binding.md)),
the sibling JSON contract (shared/sibling-contract.md), and packs and the
drift-lock (packs-and-plugins.md). The decisions below are D58.

#### The .grmb adapter

grimble-model owns a U adapter for .grmb at fidelity F4: entities are
`unit` nodes (kinds node, flow, contract, claim, vmodel, pack, template), selector
expressions are `apply(kind=select)` with May edges to the units they
match, and the four exception kinds are `attr` nodes (a matrix-build `template` is a unit of kind template whose `excuse` clauses are `attr` nodes), and
directives (`frob:doc`, `frob:ticket`, `grimble:...`) bind to entities
exactly as they bind to code units, so inside grimble every rule that
works on code works on the model, and `grimble fmt` is the alpha-normal
printer. frob cannot link grimble-model (products never depend on each
other, D28), and the substrate `Language` registry cannot name a
product adapter; so frob binds a `frob:` directive in a .grmb file only
from `grimble graph --json` (schema `grimble.graph/1`, generated at
docs/schemas/ next to sibling.json): the entity list with spans and
Body and Doc facet digests, from which DRIFT between a design doc and
its entity and REF from an entity to a ticket are evaluated. A frob
without grimble sees .grmb as F0 opaque, and a `frob:` directive inside
it is reported Unresolved, never silently unbound. The grammar specification is this file (G01). Which files form a model is decided by
declared roots (`[grimble] models`), not by the walk: only files reachable
from a root through `use` load, an unreachable file is the orphan
finding MDL019 (error), and an include may not climb above its own directory
without the `outside` marker (section 3, D77).

#### The sibling contract and absence

`grimble check --json` emits a versioned document, `gob.sibling/1` (schema in
docs/schemas/sibling.json, hand-written until the derive generates it)
whose fields, version negotiation, merge rules and failure cases are
defined once in shared/sibling-contract.md; the `grimble.graph/1` export of the .grmb adapter above is section 3.8 there. frob validates the schema version and the compute
digest. When grimble.toml exists and the binary is absent
or incompatible, `frob check` emits one Unresolved finding per missing
product marked `required`, so the gate fails with exit 1 under the
default `[check] fail_on_unresolved = "required"` and `[check]
require_siblings = true` (both materialized); docs/design/shared/cli-contract.md section 2 is the
one definition of this mechanism and it closes the audit's "absent
grimble passes" hole. A standalone grimble run applies the same
mechanism to its own required Unresolved findings.

#### Report caching and batched reads

The architecture and PATH reports are pure in the walked file digests, the
lock file and the `[grimble]` knobs (plus `large_lines`), so `grimble check`
stores them as artifacts under the same digest as the binding summary
(`grimble-check::report_cache`). A hit reads and parses no file. On a miss
both passes share one git content reader (`Core::with_content`) instead of
reopening the repository per file, and the PATH scan runs per file in
parallel with a sequential, deterministic fold.

#### Orchestration and crates

The check pipeline (walk, inputs, per-file and repo rules, exceptions,
render) moves from frob-check into the substrate crate `gob-check`
that both frob and grimble drive; exception matching moves into
gob-rules (today it lives in frob-obligations' `apply_exceptions`;
ticket G06 moves it). grimble depends on gob-walk, gob-cache, gob-exec,
gob-ir, gob-symbols, gob-lock, gob-check and gob-rules, never on a frob
crate. The verbs are check, status, graph, shrink, init, doctor, fmt,
packs, explore, ack, exceptions and serve --mcp; `vet`
follows the cut (docs/design/shared/cli-contract.md section 1.4). The milestone-2 order, the 19
tickets G01-G19 and the critical path are stated once in
shared/build-test-ci.md, Milestone 2; this file does not repeat them. Crate
owners per shared/charter.md, including grimble-lints (NEAT) and the new
grimble-ci crate (CI, DK).

#### What grimble needs from U

A stable identity separate from the content hash (done in
shared/universal-model.md 2.2); selector semantics as a U query; detector and
atom registries in shared crates (docs/design/grimble/binding.md section 7.5); the `contract` facet in the
adapter contract (universal-model.md 7.1; replaces the earlier
normalized-signature query); a build-manifest reader (Cargo.toml,
pyproject, package.json, and the repository's CI files for CI012) as an
F2 manifest adapter so ownership can follow packages and CI can be
joined to the repository; polarity and subject count on Rule and
Finding types (docs/design/shared/rules.md section 2).

## 21. What frob gets from the model

grimble never knows about tickets.

- Tickets link to grimble entities with an `implements` link
  (`design:node/cli`); frob validates the target only through
  `grimble graph --json` (Unresolved when grimble is absent). An epic can
  be "implement flow f_parse", and the flow's SYS005 finding closes when
  the ticket lands.
- Planning entities (`goal/...`, `scenario/...`, `impl/...`) are
  `implements` targets too; grimble emits their `status` and
  `obligations` in the graph export and frob adds the close guard
  `design_bound`, PM037-PM039, PM046-PM049 and `frob plan --from-design`
  (section 17).
- Exceptions that name a ticket (`defer`, `hotfix`): grimble parses the
  `ticket=` value as opaque and emits it in `--json`; standalone grimble
  reports such an exception as UnresolvedExit, and frob evaluates the
  exit and the close guard from that JSON (docs/design/shared/rules.md section 10.2).
- The V-model is the requirements-to-tests traceability Jira lacks:
  requirement -> design decision -> ticket -> test, all symbols, all
  checked.
- `grimble status` renders the model with per-node drift counts;
  `grimble graph --dot|--json` exports it; the frob GUI (shared/cli-contract.md) shows
  the same through grimble's `--json`.

## Decision records

Anchors only: the decision text is in [decisions.toml](../../decisions/decisions.toml), indexed by the generated [decision log](../../decisions/README.md); evidence rows are in notes/research/grmb-evidence/evidence.md.

### D65
The .grmb language: model, entities, names, selectors, exceptions, U encoding, binding, MDL001-MDL017.
### D70
File item order in `grimble fmt` (9.3).
### D71
A top-level exception hangs on the file unit (9.2).
### D72
`///` is `attr(doc)`, never trivia; comments never merge or drop (9.2, 9.3).
### D73
A pack's `module` and `part of` use `attr(name=module)` (9.2).
### D74
The Sig facet superset; Contract is Sig with names erased (9.2).
### D77
Model roots, `use` below the using directory, `outside`, orphans (3.1, 3.2).
### D124
The planning layer is admitted as the one behaviour construct (1.1, 11).
### D125
Planning words are contextual; new tokens were lexical errors (2.2, 2.6).
### D126
Actors are the only event generators (11.3).
### D127
`impl STEP for SCENARIO` binds a step with pack realization kinds (11.7).
### D128
Goals are keyed variant sets; `requires` is acyclic precedence (11.4, 12.2).
### D129
Scenario operators with Zig/Rust semantics (12.3-12.5).
### D130
Design status is layered; grimble never runs tests (12.8).
### D131
`implements design:` is the one ticket join (17.2).
### D132
`frob plan --from-design` (17.6).
### D133
Behaviour implies data flow, SYS015 (13.5).
### D139
Operator tokens `->`, `=>`, `-!>`, `*`; no `-?>` (2.2).
### D140
`_`, `unknown`, `closed` and `open` (15.4).
### D141
Goal groups `all` and `one_of [exclusive]` (15.5).
### D142
`sorry` is the one hole primitive (15.3).
### D143
Actor kind `external` (11.3).
### D144
GRL keeps its name.
### D145
No decision entity (19).
### D146
Approval gating is opt-in, default off (16.5).
### D147
No pedantic profile; ambient policies (15.1).
### D148
Impl blocks are ordered waypoint chains (14).
### D149
Required waypoints R1-R7 (14.7).
### D150
One evidence clause `verified_by` (8.3).
### D151
The rung is `covered`; exported as JSON `status` `verified` (12.8, 17.1). `covered` means verification is bound; `verified` is the frob overlay pass verdict (12.8, 17.3), so renaming the rung would give one word two meanings.
### D152
One meaning per token; `=>` arms and maps, `:` outcome types, list chains, no `via` (2.2, 11.1, 14.1).
### D153
One bounded-repeat grammar with a default target (12.5, 15.1).
### D154
No placeholder token (12.5).
### D155
One keyword table and the `r#` escape (2.6).
### D156
The file include is `use` (3.2).
### D157
System membership by marker or single top-level system (11.2).
### D158
`budget` is a `bound` claim (4.4, 15.6).
### D159
The label is `///`, not `title` (11.9).
### D160
One debt key set (7).
### D161
Small spellings: `on page`, `in node`, two-word rule (11.1).
### D162
`one_of` rolls up with the join (12.8).
### D163
Scenario and Gherkin mapping (11.6, 11.10).
### D164
Derived edges reuse surface words (13.3).
### D165
Documentation consolidation and rule renumbering (16.2).
### D166
The keyword table is complete; deprecated class (2.6).
### D167
Mount and marker precedence (11.2).
### D168
The closed deprecation bridge, through major 2 (3.4, 11.1).
### D169
PLAN016 covers every retry; AMB002 retired (16.2).
### D170
MDL014 drops level pairing; duplicates are MDL017 (4.5, 4.5.2).
### D171
The evidence ladder: planned, SYS011, evidence (8.3).
### D172
One spelling of a step-qualified variant, `pair` (11.1, 12.3).
### D173
A satisfied `one_of` has no per-alternative obligation (12.2).
### D174
PLAN013 for an unused `for *` impl (11.7).
### D175
The item grammar (4.10).
### D176
One meaning per keyword; goal dimension as `attr` (2.2, 11.4).
### D177
Ambient surface: one policy, evidence body, no node override (15.1).
### D178
Small rules: frozen U kinds, opaque ticket, retry else, non-code waypoints (9.2, 7, 12.5, 14.1).
### D179
SYS016 is Unresolved over Unknown nodes (16.3).
### D180
`sorry` is its own U sort; three positions (9.5, 15.3).
### D181
Small cycle 3 rules: `page` planning word, top-level `use`, PLAN007, `attr_value` (2.6, 3.2, 4.10, 16.2).
### D182
Ambient `retry` vs `restart` (15.1).
### D183
Waypoints bind (12.8).
### D184
One evidence fact per pair; PLAN043 retired (13.2).
### D185
PLAN041 owns the opaque error set (14.4, 16.2).
### D186
Respelled clauses take their current attr names (9.2).
### D187
PLAN014 judges refinement sets only (11.4, 16.2).
### D188
AMB004 defined (16.4).
### D189
A whole-body `sorry` stands for the body (15.3).
### D190
Small cycle 4 rules: AMB003, PLAN015, trigger, coverage subjects (12.6, 13.2, 16.2, 16.4).
### D191
`_` arms cover their pairs; `unknown` arms none (13.2).
### D192
Ambient policy of the outermost scenario; AMB004 per stack (15.1, 16.4).
### D193
PLAN017 retired into PLAN011; code-fact rules in P7 (16.2, 18.3).
### D194
Whole-body `sorry` details (15.3, 12.6).
### D195
Waypoint anchors (9.4).
### D196
Cycle 6: AMB004 per applying policy, `sorry` element typing, whole-body encoding, unique waypoint names (12.3, 15.3, 16.4).
### D197
Cycle 7: `fails with` bounds a `sorry`, Unknown outcomes make reading rules Unresolved, every scenario is triggered, `sorry` bodies on scenario, impl and page only (12.3, 12.4, 15.1, 15.3).
### D198
Cycle 8: a whole-body `sorry` scenario is `declared` and has no trigger; one encoding; `sorry` elements widen inferred sets (9.5, 12.3, 12.8, 15.3).
### D199
Cycle 9: empty scenario meet is `declared`; PLAN007 over Unknown triggers (12.6, 12.8, 15.1).
### D200
One OWN EVIDENCE test for `covered` (12.8).
### D201
The overlay rung `verified` (12.8, 17.3).
### D202
OWN EVIDENCE is the Evidence row set; manual attestation tie; trace states (12.8, 13.3).
### D203
Frob-side verification rules; anchor shape; manual status (12.8, 16.2, 18.3).
### D204
Frob-side verification rules are PM046-PM049 (16.5).
### D205
Row verdicts and the PM049 window (12.8, 16.5).
### D206
The evidence WINDOW and the semantic digest (12.8).
### D207
WINDOW commit ordering; record-field status (12.8).

### D6
The grimble model (v1 strata) keeps node/flow/boundary/claims/V-model; everything else is a data pack
### D58
grimble after the model (docs/design/grimble/grmb-spec.md section 20.2): binding is a relation between model entities and U identities with Must/May/Unknown from four ranked sources; .grmb is an F4 language with its own adapter; typed lock entries with roles and flow keys and a digest-scheme version; equality drift rules are Unresolved on partial languages; a versioned sibling JSON schema and a configured-but-absent sibling fails the gate; one capability-matrix definition with unknown reported as Unresolved and an open atom and detector registry; a shared gob-check pipeline; milestone-2 cut of 19 tickets (accepted 2026-10-04 on the owner's instruction to resume implementation after review)

Also logged against: notes/review/grimble-review.md.
