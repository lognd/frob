# The .grmb language specification (G01)

Status: draft
Owner: grimble
Decisions: none
Audience: rule author

Provenance: DRAFT under T-0001 (a v1-format id that migrates with an alias);
written under ticket 01M3Z712GP8XV2WEAS1VHQ7FD4 (G01). It is the grammar
that grimble-model.md section 9.3 promised: until it landed, sections 1-3
of grimble-model.md were illustrative. Where this file and those sections
disagree, this file wins; section 14 lists every disagreement.

Inputs: grimble-model.md (sections 1-5 and the post-model revision in
section 9: binding as a relation 9.1, identity 9.2, .grmb as an F4
language 9.3, capability cells 9.6), universal-model.md (sections 2, 3
and 5: operators, locations, symrefs, fidelity), exceptions.md (the four
kinds), code-model.md section 4 (the directive grammar),
notes/v1/strata.md (what v1 actually did), notes/review/grimble-review.md
(findings H1, M1, M2, M12) and notes/research/paradigms.md section 6
(the features a language must declare).

## 1. Purpose and scope

A `.grmb` file declares a MODEL: a typed architecture graph of nodes,
flows, contracts, claims and V-model links, each of which binds to code
identities in any language (grimble-model.md 9.1). The language exists
for three jobs and nothing else:

1. Declare intent and ceilings: what owns which code, what each owner
   may do, which data may move where, what is claimed about the system
   and what evidence backs it.
2. Give the kernel (grimble-model.md section 3) a closed, typed input:
   label closure over flows, claim verdicts, V-model closure.
3. Give frob and the editor a file in which a `frob:doc` or
   `frob:ticket` directive binds to an entity exactly as it binds to a
   function (grimble-model.md 9.3).

Design stance, kept from v1 and the owner's direction: the grammar holds
only what v1 consumers measurably used (node, flow, boundary, claims, the
V-model, capability grants, matrix-build templates, exceptions). Everything else is a
DATA PACK.

What is a data pack. A pack is a versioned, digest-pinned bundle of
data (TOML under `packs/`, enabled in `grimble.toml`) that contributes
capability atoms, detectors, obligations, node kinds, units of
measure aliases and rule parameters. A pack NEVER contributes grammar:
no keyword, clause or operator. A model refers to a pack with a `pack`
entity (section 4.6) so that pack-qualified names (`threat::injection.sql`)
resolve and so that the pinned version is part of the model's digest.
The consequence is that the keyword table of section 2.6 is the
complete input of the editor grammar generator
(`editors/grimble.tmLanguage.json`, documentation.md section 3) and of
the parser: adding a pack never changes either.

Non-goals. `.grmb` is not a programming language: no expressions beyond
selectors, no functions, no loops, no conditionals, no macros (so the
U encoding of section 9 never needs `phase`). It does not describe
runtime behaviour (the six-phase boundary blocks, sagas, crash and
breach scenarios, hosts, Kerberos, `refine`, `entity/architecture`,
`policy` and `scenario` of v1 are not in the language; section 14).
The one exception is the planning layer, grmb-planning.md: typed step
outcomes with exhaustive handling, the only behaviour the checker can
verify (D124).

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
           | "." | "=" | "->" | "<=" | "&" | "|" | "!" | "~" | "!=" ;
```

grmb-planning.md 2.2 adds `=>`, `-|>`, `-?>` and `*` by maximal munch;
each was a lexical error before, so the addition is valid within major 2.

- A string contains no raw newline; a multi-line text is written as
  adjacent strings joined by the parser (`"a" "b"` is `"ab"`) only in
  value position, never in a selector. There are no raw strings.
- `date` is an ISO calendar date, UTC, validated (month 01-12, day valid
  for the month). It is the only date form (`until=`, `review=`).
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
  `<namespace>:<verb>`, exactly the rule of code-model.md section 4:
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

Reserved in every position (an identifier equal to a keyword is
MDL000; there are no contextual keywords except the three selector
predicates noted below and `outside`, recognized only after an include
path, 3.2):

```
accept age allocates alias as assumed at attr blocked_by bound boundary
claim clearance condition consumer contract declassify decides defer
digest endorse evidence excuse extend fanout flow for growth hotfix include
kind label latency level may module namespace node noflow of on owns pack part
producer proof reach ref refines renamed_from rate runnable satisfies
shape size supersedes surface template tests transport utilization verifies
version versioning vmodel when
```

`lang`, `kind` and `attr` are valid heads of a selector predicate
(`lang(rust)`); in clause position `kind` and `attr` are the clause
keywords. The parser decides by position (a clause starts a statement; a
predicate occurs inside a selector). `noflow` and `reach` are claim
verbs, reserved as well. Metric names after `bound` are `age`, `rate`,
`latency`, `size` and `utilization`.

Contextual planning words (grmb-planning.md 2.1, D125), recognized only
at item position (the first line) or inside a planning item (the rest),
identifiers everywhere else:

```
actor goal impl page scenario step system
_ else end entry err fails from handle in max ok realizes requires retry
title verified_by with
```

The keyword table is the single source for the generated editor grammar:
`cargo dev gen editors` reads the table from the `Keyword` derive in
grimble-model and nothing else.

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
by a pack-generated `attr id` on an identifier-named claim (section 14).

## 3. Files and includes

The model follows the Rust crate model (owner decision D77): a crate root
by convention that `Cargo.toml` can override, modules reachable only
through `mod` declarations from the root, `mod foo;` resolving to a file
next to the declaring file, and `#[path]` as the explicit escape hatch.
Here the root is listed in `grimble.toml`, files join the model only
through `include`, an include resolves at or below the including file's
directory, and the `outside` marker is the `#[path]` analogue. Where
rustc silently ignores an unreachable file, grimble fails loudly (3.1).

### 3.1 Roots: one model from one declared entry

A MODEL is the set of files reachable from one ROOT file through
`include`. Roots are declared by the materialized enforcement knob

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
  the three remedies: include it from a root, list it as a root, or
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

### 3.2 Include semantics

```
include "gob.grmb";                       // one file, at or below this directory
include "services/*.grmb";                // a glob (path glob of section 6.2)
include "api.grmb" as api;                // mount under the prefix api
include "../shared/x.grmb" outside;       // explicitly climbing out (below)
include "../shared/*.grmb" as s outside;  // marker comes last, after `as`
```

Grammar: `include STRING [ "as" REFPATH ] [ "outside" ] ";"`. `outside` is
the only word recognized after the path and is not otherwise reserved
(it stays a valid identifier elsewhere).

- LOCATION MIRRORS HIERARCHY. An include may name only files at or below
  the directory of the including file (the way `mod foo;` finds `foo.rs`
  next to the declaring file). An include that climbs out is MDL020 and is
  skipped, unless it carries `outside`. Climbing means any `..` segment in
  the written path, or a resulting path (a leading `/` anchors the path at
  the repository root) that is not at or below the including directory.
  Globs follow the same rule: the pattern is checked as written and every
  file it matches must be at or below the including directory. `outside`
  on an include that does not climb is accepted and does nothing.
- Paths are POSIX, resolved relative to the directory of the including
  file (a leading `/` is relative to the repository root, never to the
  file system), and must stay inside the repository (a path that leaves it
  is MDL002 even with `outside`; so is a backslash). A glob expands to its
  files in byte-wise lexicographic order; a glob that matches nothing is
  MDL002 (an include that names a file that is missing is an error, a
  selector that matches nothing is a warning: includes are structural,
  selectors are intent).
- A file is read once per model however many times it is included
  (identity by normalized path). The same file included under two
  different `as` prefixes is MDL001 on the first duplicate entity.
- `include ... as P` MOUNTS the file: every top-level entity and
  namespace the file declares gets the prefix `P.` (section 5.2). `as`
  is not allowed on a glob that matches more than one file.
- CYCLES ARE REFUSED. The include graph is walked depth first with the
  active stack; reaching a file on the stack is MDL003 naming the cycle,
  and the offending include is skipped so the rest of the model still
  loads. A diamond (two files including a third) is not a cycle.
- Include is the only cross-file mechanism; there is no `import`,
  `export` or `layer` (v1 parse-only forms, dropped). A file that is
  included is a file of the model; one that is not reached is an orphan
  (3.1).

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
  change that would alter the meaning of valid text bumps the major.
- The header is part of the language parameter of the U terms (the
  "edition" of universal-model.md 2.2 item 5) and of the digest scheme
  input: a major bump makes every entity's digests stale with the reason
  recorded, exactly as a digest-scheme change does (grimble-model.md
  9.2).

## 4. Entities

An ENTITY is a named, declared thing; it is a `unit` in U. There are
eight kinds: `node`, `flow`, `contract`, `claim`, `vmodel`, `boundary`,
`pack` and `template`. (grimble-model.md 9.3 lists six; `boundary` is kept
because D6 keeps it and `template` is added by D75; section 14.) grmb-planning.md 4
adds seven planning kinds (`system`, `actor`, `goal`, `step`, `scenario`,
`impl`, `page`) in the same namespace. Every statement inside an
entity body is a CLAUSE; a clause is an `attr` in U. A clause key may be
repeated only where the table says "list".

Common clauses, valid on every entity:

| Clause | Syntax | Meaning |
|---|---|---|
| `alias` | `alias old_name;` | an additional permanent name (list); resolves like the real name, no warning |
| `renamed_from` | `renamed_from old_name;` | transitional name after a rename (list); resolves with MDL012 Warn, and lets the ack planner carry lock entries to the new identity (5.5) |
| `attr` | `attr KEY [= VALUE];` | typed user attribute (list by distinct KEY); VALUE is a string, number, quantity, date, ident or a bracketed list of those |
| exception clauses | section 7 | `accept`, `defer`, `hotfix` (list) |

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
| may | `may ATOM [ "(" ARGS ")" ] [ at SELECTOR ];` | grant | list | capability grant. ARGS is a comma list of strings constraining the atom (host names, env names, paths); the grant applies at SELECTOR, default the node's whole `owns` set. This replaces v1's `of CONSTRAINT` and the colon form `net.connect:host` |
| surface | `surface SELECTOR;` | selector | list (union) | the intended public API; SYS014 (reserved by binding.md 11.3) compares it with observed public symbols |
| attrs | `attr` | typed value | list | markers and magnitudes (`attr timeout = 30 s;`, `attr idempotency_key;`) |

A node without a `trust` is MDL008. A node carries NO excuse clause:
capabilities are denied by default (binding.md 7.2), so a node never
needs to say "not this atom"; a not-granted atom is simply denied, and
observed use of it is CAP001. A node-level `excuses ...` clause (the
D5-era spelling) is MDL018 (4.8). Capability atoms are resolved against
the one registry (grimble-model.md 9.6); an atom that is in no registry
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
| growth | `growth Q;` | rate of ratio per time (`15 %/d`) | no | growth of the flow's rate over time; see open question 8 |
| transport | `transport ATOM, ATOM;` | list of atoms | no | the atoms `in_process`, `http`, `ipc`, `ffi`, `file` (`in-process` is not lexable as an atom, 2.2); pack-extensible |
| condition | `condition on_ok;` or `condition on_err;` | ident | no | v1 `on Ok/Err` |
| producer | `producer SELECTOR;` | selector | no (SYS004 or SYS009 report absence of symbols, binding.md 6.4 and 6.9) | the code unit(s) that emit; may be any language |
| consumer | `consumer SELECTOR;` | selector | no | the code unit(s) that read |
| contract | `contract NAME;` | ref to a `contract` entity | no | the agreed data shape (4.3) |

Flows may form cycles (request and response, retry loops, feedback);
cyclic flows are legal and the kernel's longest-path age uses SCC
condensation (grimble-model.md section 3). v1's `utility` (non-transitive
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
| shape | `shape SELECTOR;` | selector | yes | the language-neutral shape: ONE unit whose Contract facet (universal-model.md 7.1) is the shape. A selector that does not resolve to exactly one identity is SYS003 kind `ambiguous-singleton` (binding.md 2.5 item 4, G02); here only the grammar is fixed |
| versioning | `versioning scheme=S current="V" compat=C;` | attrs | no | `scheme` one of `semver`, `date`, `integer`, `none`; `current` a string in that scheme; `compat` one of `backward`, `forward`, `full`, `none`. Informational for SYS006: skew is detected from digests, versioning says what skew is allowed to be |

Contracts exist as entities (not as an inline selector in the flow)
because a contract is shared by flows, versioned, and is the subject of
the typed lock entries of grimble-model.md 9.2: the flow lock entry
records the `contract` facet digest of each end against this entity.

### 4.4 claim

```
claim no_frob_to_grimble {
  noflow frob -> grimble;
  proof L2;
  evidence tests "crates/frob/tests/wiring.rs";
}
```

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `claim NAME` | name | yes | |
| what | `noflow A -> B;` or `reach A -> B;` or `bound METRIC TARGET <= Q;` | exactly one | yes | the proposition. `noflow` and `reach` take node refs; `bound` takes a metric (`age`, `rate`, `latency`, `size`, `utilization`), a node or flow ref and a quantity of the metric's dimension. `independent` and `readers(x) == S` of v1 had no surface and stay out |
| proof | `proof LEVEL;` | `L1`..`L5` | no, default from `[grimble] default_proof` | the required rung. The rung ladder is an ordered label to the kernel; its meaning is G03 |
| assumed | `assumed owner=IDENT review=DATE because="...";` | attrs, all three required | no | the claim is an assumption: named, owned, expiring (v1 `assume`); overdue is REFUTED, as in v1 |
| evidence | `evidence tests SELECTOR;` or `evidence ref "SYMREF";` | list | no | what discharges the claim above L1: test units (bound also from the test side by `frob:tests`, 8.3) or a document anchor |

Verdicts (PROVED, REFUTED with witness, UNPROVABLE, and the three-way
closure) are computed by the kernel and are not part of the language.

### 4.5 vmodel

```
vmodel req_gate_exit {
  kind artifact;
  level requirements;
  ref "docs/design/cli.md#2-output-contract";
}
vmodel t_gate_exit {
  kind test;
  level customer_test;
  runnable "crates/frob/tests/check_verb.rs::error_finding_exits_1_and_fail_on_none_exits_0";
  verifies req_gate_exit;
}
```

| Field | Clause | Type | Required | Meaning |
|---|---|---|---|---|
| name | `vmodel NAME` | name | yes | |
| kind | `kind K;` | `artifact`, `test`, `decision` | yes | v1 node kinds |
| level | `level L;` | a level of the table below | yes | |
| ref | `ref "SYMREF";` | symref of a document anchor or code unit | artifact: yes | the spec artifact |
| runnable | `runnable SELECTOR;` | selector resolving to one test unit | test: yes | the test |
| links | `satisfies X;` `verifies X;` `refines X;` `allocates X;` `decides X;` `supersedes X because="...";` `blocked_by X;` | ref to a vmodel | list | edges from THIS entity to X; v1 `vmodel_edge`, with `supersedes` requiring `because` |

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

Construction errors are model-load errors (MDL014): a link whose
endpoints are of the wrong kind, a `verifies` between unpaired levels,
a missing `ref` or `runnable`, a duplicate link. A link target that
resolves to nothing is MDL006; one that resolves to an entity that is not
a vmodel is MDL014. The five structural
closure rules (orphan requirement, unjustified design, untested artifact,
orphan test, trace cycle) and milestone known gaps belong to the kernel
(G03); their rule ids are open question 4.

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
selection reaches. Templates live in two places only: in packs (packs.md
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
tclause   = excuse | common ;                   (* common: alias, doc, exceptions *)
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
  `fs.read` and `fs.write` (hierarchy, grimble-model.md 9.6). An excuse
  with ARGS is not expressible: an excuse never narrows by argument.
- An excuse never hides an observed use. If detectors observe the excused
  atom in covered code, the result is CAP004 (binding.md 7.2), evaluated
  before the excuse; an uncertain detection is Unresolved, never a pass.
- An excuse that overlaps a grant `may A` of the model for the same atom
  (or an ancestor or descendant) is SYS012 (binding.md 6.12): the model
  both permits and declares not-applicable.
- Every template excuse is listed and counted in `grimble check --json`
  (sibling-contract.md): a `template_excuses` array of
  `{template, atom, selector, because, source}` and a `template_excuses`
  total in the summary, so a reviewer sees the full set at a glance.
- Not-applicable is unchanged: it remains declared only by detector data
  (packs.md 6.5), never by a template. A template excuse is `excused`, a
  different cell.

### 4.8 Removed: the node-level `excuses` clause (MDL018)

Before D75 a node could write `excuses ATOM because="..."` and the matrix
cell for that atom was `excused`. That clause is removed. Writing it on a
`node` (or in an `extend node`) is MDL018 (Error). The remedy is one of:
grant the atom (`may ATOM at SELECTOR`) if the node is meant to use it;
leave it ungranted if the node is meant not to (capabilities are denied
by default, so that is the whole statement); or, when the reasoning is
about how the atom applies to a kind of code across languages (generated
code, a language with no meaningful form of the atom), move it into a
matrix-build template (4.7).

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
`unit` part with role `extension` of the same identity (universal-model.md
2.6): one entity, many parts.

`namespace NAME { items }` groups items under a prefix. It is a
containment node, not an entity: it cannot have clauses.

## 5. Names and scoping

### 5.1 One namespace per model

All entities of all eight kinds, all packs and all namespaces share ONE
flat-with-prefixes namespace per model. A flow and a node cannot share a
name. Capability atoms, lattice elements, rule ids, units and metric
names live in their own registries and never collide with entity names.

### 5.2 Qualified names

The full name of an entity is its declared name prefixed by the
enclosing `namespace` names and the `as` prefix of the include that
brought its file in, joined with `.`. `api.handlers` is the entity
`handlers` in `namespace api` or in a file included `as api`; both
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
or which `include` order produced them; the first in canonical (path,
byte) order is kept so that downstream rules still see one entity. The
`extend` form is the only legal way to add to an existing name. Aliases
and `renamed_from` names occupy the namespace too (an alias equal to
another entity's name is MDL001).

### 5.5 Identity and renames

The identity of an entity (universal-model.md 2.2, grimble-model.md 9.2)
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
`surface`, `may ... at`, `producer`, `consumer`, `shape`, `runnable`,
`evidence tests` and the CLI (`grimble select EXPR`). The grammar and the
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
  code-model.md section 2: `.` separates segments, `*` matches one
  segment, `**` any depth, `[...]` is the opaque bracket of a symref
  segment (`Type[Trait].method`). Literal text matches literally.
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
status per identity, in the answer lattice of universal-model.md 4.1.

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
   through the symref resolution order of code-model.md section 2
   (exact, unique qualname, unique suffix); a unique resolution is Must,
   candidates are May, and no resolution in a file with no unseen
   remainder is `Exact(empty)`.
6. Boolean combinators use Kleene logic on membership (Yes, No, Unknown):
   `&` is the three-valued meet, `|` the join, `!` the complement
   (`Unknown` stays `Unknown`). `lo(!e)` is the walked universe minus
   `hi(e)` and `hi(!e)` the universe minus `lo(e)`, and an unseen
   placeholder is never in `lo`.

Reading of grimble-model.md 9.1 ("Must for literal paths, May for globs
that match units with Unknown edges"): a glob is Must exactly where a
literal path would be, and degrades to May only along an Unknown or May
fact; the rule above is the same statement made total.

Polarity consequences (the framework applies universal-model.md 4.2; this
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

The four exception kinds of exceptions.md replace v1's `waive`. In a
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
| accept | `accept RULE [on REF] because="..."` | `because` | | permanent; REATTEST compares the entity's Body digest with the attested one (exceptions.md section 1) |
| defer | `defer RULE [on REF] ticket="ULID" because="..."` | `ticket`, `because` | `until=DATE` | the `ticket` value is an opaque string to grimble (a full ULID; an abbreviation is DSL002); standalone grimble reports UnresolvedExit |
| hotfix | `hotfix RULE [on REF] ticket="ULID" because="..."` | `ticket`, `because` | | expiry from `[exceptions] hotfix_days`, evaluated by date from the creation event |
| baseline | none | | | never written in a .grmb file: pools live in `<product>-ratchet.lock.json` (exceptions.md section 2). `grimble graph` synthesizes an `attr(baseline)` node on each entity that a pool key names, for display and for suppressed-finding accounting only; a hand-written `baseline` is MDL000 |

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
  matching the `because=` spelling of the shared directive parser; this
  also changes the `because "..."` of grimble-model.md section 2 to
  `because="..."`.
- Reasons are judged by EXC rules (reason quality, budgets, STALE,
  EXPIRED; exceptions.md section 6), not by MDL rules; MDL013 only
  checks structure (kind and attribute combination, position, known
  rule id, `ticket` and `until` shape).
- An accept cannot park an Unresolved finding (EXC016); that is checked
  at evaluation, not at parse.
- Matching: an exception on entity E suppresses findings of RULE whose
  logical location is `E` or lies inside E's clauses (for example
  `node/cli` and `node/cli/owns`). Rule id equality is exact.

In U each exception clause is an `attr(name=accept|defer|hotfix)` on the
entity unit (section 9), so it is in the Attr facet and does not change
the Body digest: adding an accept never makes its own entity "changed".

## 8. Directives inside .grmb

### 8.1 Where a directive binds

Directives are parsed from comments by the shared parser (2.3) and bind
to ITEMS: an entity, a namespace, an include, a clause or the file.

1. A directive comment binds to the first item whose first token follows
   it, skipping other comments (a blank line does not detach it).
2. A comment that follows an item on the same line (after its `;` or its
   opening `{`) binds to that item.
3. A comment immediately before a closing `}` with no following item
   binds to the enclosing entity.
4. A comment before the `grimble = "2";` header or with no item after it
   binds to the file's module unit.

This is the same rule as for code units (code-model.md section 4),
applied to the U term of section 9, so the directive's target is a `unit`
or an `attr` node and every downstream query (`attachments`,
`directives_for`) works unchanged.

### 8.2 Verbs accepted

| Verb | Binds to | Effect inside a .grmb file |
|---|---|---|
| `frob:doc PATH#anchor` | entity or file | the design doc for this entity; DRIFT is evaluated between the doc's digest and the entity's Body and Doc facets through `grimble graph --json` (grimble-model.md 9.3) |
| `frob:ticket ULID` | entity or clause | the work item that changed this hunk; REF check by frob from the JSON |
| `frob:todo ULID` | entity or clause | deferred work marker |
| `frob:invariant`, `frob:decision`, `frob:deprecated`, `frob:until` | entity or clause | as in code-model.md section 4, bound to a unit |
| `grimble:binds SYMREF [via="manual"]` | entity (node, flow end, contract, claim, vmodel) | explicit binding, source rank 1 of 10.3: the entity is bound to the identity SYMREF at Must. For a node it adds SYMREF to the node's ownership regardless of `owns`; on a flow it is accepted before a `producer`, `consumer` or `contract` clause to bind that end |
| `frob:tests SYMREF` | claim or vmodel test | reverse evidence binding: the target entity's evidence includes this test (also written in test code, 8.3) |
| claim verbs `frob:effects`, `frob:pure`, `frob:honest`, `frob:core`, `frob:shell`, `frob:hook`, `frob:dispatcher`, `frob:idempotent` | entity | parsed and bound (a `unit` is a legal target); the NEAT rules answer NotApplicable on `grmb` units (no effects), so they never produce findings here; reserved so a future claim about a model entity has a place (open question 9) |
| `grimble:accept`, `grimble:defer`, `grimble:hotfix` | none | MDL013: use the clause (section 7) |
| `grimble:node`, `grimble:channel`, `grimble:boundary`, `grimble:effect` | none | these are code-side attestations naming an entity; written in a .grmb file they are MDL013 |

A `frob:` directive evaluated by frob needs `grimble graph --json`; a
frob without grimble reports it Unresolved (grimble-model.md 9.3). The
directive grammar, the verb registry and the typed validators are the
shared ones of code-model.md section 4; this file adds no verb.

### 8.3 What a claim's evidence binds to

`evidence tests SEL;` in a claim and `frob:tests <claim symref>` on a
test are the same relation: `Evidence(claim, test-unit)`. The relation is
the union of both spellings, each with its own status from 6.4 (a
`runnable` literal is Must; a glob is as in 6.4). A claim above L1 with
an empty Evidence set that is not `assumed` is UNPROVABLE (kernel, G03),
and a `frob:tests` that names a claim that does not exist is MDL006
reported from the .grmb side by `grimble graph`.

## 9. The U encoding

`grimble-model` owns the adapter A_grmb = (parse, rho, bind, cap) with
the fidelity F4 (universal-model.md 3.3): units and roles, a scope graph
with Must edges for every reference, attributes, comments bound to
targets. It is total (Theorem 1): invalid input yields `hole` and
`opaque`, never a refusal.

### 9.1 Locations

A location is `text(artifact, byte range)` with an ANCHOR: the logical
location `kind/full-name` for entities (`node/cli`), and
`kind/full-name/clause-key[i]` for the i-th clause of that key
(`node/cli/owns[0]`). The anchors are the stable addresses findings,
`design:` ticket links and the sibling JSON use; byte ranges are the
spans (every construct has one: the v1 regex-located spans are gone).
The artifact is the repo-relative path of the file.

### 9.2 Encoding table

Language tag `grmb`; language parameter `grimble="2"` (the edition) on
every node. S = sort of the produced node.

Placement inside an entity unit (this fixes which facet a clause lands
in; the facet table below is derived from it, and gob-ir classifies a
child by this placement alone):

- Sig parts are direct children of the unit marked `ir.facet = "sig"`:
  the trust attr, the flow `connect` apply, the boundary `endorse` or
  `declassify` apply, the vmodel `kind` and `level` attrs, and the
  `label`, `producer`, `consumer`, `contract`, `shape` and `versioning`
  clauses.
- Body parts are every other clause (`owns`, `surface`, `may`,
  `clearance`, the other flow fields, claim and vmodel
  clauses, links, pack clauses, `alias`, `renamed_from`), all inside one
  `group(unordered)` child of the unit. `attr(name=owns)` and its
  siblings therefore sit in that group, not directly under the unit.
- Attr parts are the `attr K` clauses and the exception clauses
  (`accept`, `defer`, `hotfix`), left as direct children of the unit;
  gob-ir classifies every `attr` child that is not `doc` and not a sig
  part as Attr.
- Doc is the `attr(name=doc)` child; comments are trivia.
- The Contract facet is not a separate placement: it is the Sig parts
  with names erased.

| Construct | U term | Sort | Notes |
|---|---|---|---|
| file | `unit(kind=module)` with body `group(unordered)(items)` | decl | the file-level Module unit every file has |
| `grimble = "2";` | `attr(name=grimble-version)(file unit; lit(string, "2"))` | decl | also the language parameter |
| `module X;` / `part of X;` | `attr(name=module)(file unit; lit(ident, X))` | decl | the model name; a pack's `module` and `part of` attrs use the same `attr(name=module)` (D73) |
| `include "p" ...;` | `apply(kind=include)(ref("p"))` | exp | Must edge to the included file's module unit; a glob gives May edges to each match (Must when exactly one); unresolved is an Unknown edge and MDL002 |
| `... as P` | `bind(kind=mount, mode=prefix)(P . scope; rhs=apply(include))` | exp | P binds the prefix over the included file's entities (the one non-unit binder) |
| `namespace N { }` | `unit(kind=namespace)` | decl | containment only |
| `node` | `unit(kind=node, role=declaration)`, body `group(unordered)(clauses)` | decl | one per entity |
| `extend node X { }` | `unit(kind=node, role=extension)` | decl | same identity as X (universal-model.md 2.6 multi-part) |
| `flow` `contract` `claim` `vmodel` `boundary` `pack` | `unit(kind=flow/contract/claim/vmodel/boundary/pack, role=declaration or extension)` | decl | |
| `: trusted` | `ref(trusted)` as `attr(name=trust)(unit; ref)` | decl | Must edge to the trust-lattice element in the builtin scope |
| `clearance L` | `attr(name=clearance)(unit; ref(L))` | decl | label lattice element |
| `kind K` | `attr(name=kind)(unit; lit(ident, K))` | decl | |
| `owns SEL` | `attr(name=owns)(unit; apply(kind=select)(...))` | decl | selector terms below; May edges from the `select` node to every unit it matches (6.4 status); the edges are the binding relation of section 10 |
| `surface SEL` | `attr(name=surface)(unit; apply(kind=select))` | decl | |
| `may A(args) at SEL` | `attr(name=may)(unit; apply(kind=grant)(ref(A); group(unordered)(lit(string)...); apply(kind=select)))` | decl | `ref(A)` is a Must edge to the registry atom (`ref(pack::A)` through the pack); unknown atom is an Unknown edge and MDL016 |
| `template N { }` | `unit(kind=template, role=declaration)`, body `group(unordered)(excuse clauses)` | decl | one per entity; no `extend` of a template (a template is replaced whole) |
| `excuse A for SEL because=".."` | `attr(name=excuse)(template unit; group(unordered)(ref(A); apply(kind=select); attr(name=because)(.; lit(string))))` | decl | `ref(A)` is a Must edge to the registry atom (unknown is an Unknown edge and MDL016); the `select` is the units the excuse covers (May edges, 6.4); a Body part of the template, listed in `check --json` |
| flow `: A -> B` | `apply(kind=connect)(ref(A); ref(B))` in the flow body | exp | two Must edges to the nodes |
| `label`, `rate`, `age`, `size`, `fanout`, `growth`, `condition`, `transport` | `attr(name=<key>)(unit; lit or ref)` | decl | quantities are `lit(quantity, "100 req/s")` |
| `producer SEL` `consumer SEL` | `attr(name=producer\|consumer)(unit; apply(kind=select))` | decl | |
| `contract NAME;` (in a flow) | `attr(name=contract)(unit; ref(NAME))` | decl | Must edge to the contract entity |
| `shape SEL` | `attr(name=shape)(unit; apply(kind=select))` | decl | |
| `versioning k=v ...` | `attr(name=versioning)(unit; group(unordered)(attr(name=k)(.; lit)...))` | decl | |
| `noflow A -> B` `reach A -> B` | `apply(kind=noflow\|reach)(ref(A); ref(B))` in the claim body | exp | |
| `bound M T <= Q` | `apply(kind=bound)(lit(ident, M); ref(T); lit(quantity, Q))` | exp | |
| `proof L` | `attr(name=proof)(unit; lit(ident, L))` | decl | |
| `assumed owner=.. review=.. because=..` | `attr(name=assumed)(unit; group(unordered)(attr(owner), attr(review), attr(because)))` | decl | |
| `evidence tests SEL` / `evidence ref "S"` | `attr(name=evidence)(unit; apply(kind=select) or ref(S))` | decl | `ref(S)` has a Must edge to the markdown or code unit when it exists |
| vmodel `kind`, `level` | `attr(name=kind)`, `attr(name=level)` with `lit(ident)` | decl | alias levels print canonical |
| `ref "S"` | `attr(name=ref)(unit; ref(S))` | decl | |
| `runnable SEL` | `attr(name=runnable)(unit; apply(kind=select))` | decl | |
| `verifies X` etc. | `apply(kind=verifies\|satisfies\|refines\|allocates\|decides\|supersedes\|blocked_by)(ref(X))` in the body | exp | one Must edge each; `because=` is an `attr` on the apply's enclosing clause |
| `boundary b endorse f : A -> B when ".."` | `unit(kind=boundary)` with body `apply(kind=endorse\|declassify)(ref(f); ref(A); ref(B); lit(string))` | decl, exp | |
| `pack` clauses | `attr(name=ref\|version\|digest)(unit; lit(string))` | decl | |
| `attr K = V` | `attr(name=attr:K)(unit; lit or group(ordered)(lit...))` | decl | a bracketed list is `group(ordered)`; a bare marker has an empty `group(unordered)` payload |
| `alias`, `renamed_from` | `attr(name=alias\|renamed_from)(unit; lit(ident))` | decl | the name is also an alias declaration in the scope graph |
| `accept\|defer\|hotfix RULE ...` | `attr(name=accept\|defer\|hotfix)(unit; group(unordered)(ref(RULE); attr(because); attr(ticket); attr(until)))` | decl | `ref(RULE)` is a Must edge to the rule registry; a top-level `accept ... on REF` hangs on the file unit (a direct child of it, outside the item group) with a `ref(on)` payload child, which is the Must edge to the resolved unit (D71) |
| selector `"glob"` | `lit(glob, lexeme)` | exp | the lexeme is the unescaped string |
| selector `lang(l)`, `kind(..)`, `attr(..)` | `apply(kind=pred)(ref(lang\|kind\|attr); lit...)` | exp | `ref` resolves into the predicate registry (Must) |
| selector `a & b`, `a \| b`, `!a` | `apply(kind=and\|or\|not)(group(unordered)(operands))` | exp | operands unordered: `a & b` and `b & a` have one digest |
| `//` `/* */` | `comment(text)` | trivia | attached to the item per 8.1; comments never merge or drop (D72) |
| `///` | `attr(name=doc)(unit or attr; lit(prose))` | decl | the Doc facet; a `///` comment is never trivia and never a `comment` node (D72) |
| directive in a comment | `attr(name="<ns>:<verb>")(target; payload)` | decl | exactly as for code units (code-model.md section 4) |
| syntax error | `hole(kind=parse-error)` | any | resynchronizes at the next `;` or at the `}` closing the current block; the rest of the file still parses |
| not UTF-8, or a file the lexer cannot start | `opaque(reason=not-utf8\|binary, payload)` | any | the whole file; all queries Unknown on it |
| (not produced) `anon`, `region`, `phase` | none | | the language has no anonymous entities (every entity is named), no embedded-language islands (a selector is a string literal parsed by gob-walk, not an island) and no macros; `include` is an `apply`, not a `phase`, because an included file is its own artifact with its own units, whereas a `phase` rewrites text in place |

Scope graph. Entity declarations (names, aliases, `renamed_from`, packs)
are declarations in the model's root scope (nested by namespace and mount
prefix); every `ref` in the table is a reference with the resolution of
5.3, status Must; every `select` node has May edges to the identities it
matches (status per 6.4). Lattice elements, atoms, rules, units and
predicates are declarations in a builtin scope that every file's scope
inherits.

Facets (universal-model.md 7.1, computed over the canonical facet
stream; trivia and directives excluded, literals exact):

| Facet | Content for a .grmb entity |
|---|---|
| Sig | kind, full name, plus the sig parts of the placement above: trust, flow endpoints `: A -> B`, boundary direction and endpoints, `level` and `kind` of a vmodel, and for flow and contract entities `label`, `producer`, `consumer`, `contract`, `shape`, `versioning` (D74: a superset of the list the first draft gave) |
| Body | every clause that is not a sig part and not an `attr K` or exception clause, in canonical order |
| Doc | the `///` text |
| Attr | `attr K` clauses and the exception clauses |
| Contract | the Sig parts with names erased: on a `contract` entity `shape` and `versioning`; on a `flow` the canonical `(from, to, label, producer, consumer, contract)`; on other entities whatever sig parts they have (trust, vmodel `kind` and `level`, the boundary apply) |

### 9.3 What `grimble fmt` guarantees

`grimble fmt` is the alpha-normal printer for `grmb`: a fixed point of
parse then print, defined on the canonical facet stream.

1. Idempotent: `fmt(fmt(x)) = fmt(x)`.
2. Digest-preserving: for every entity and facet, the digest of
   `fmt(x)` equals that of `x`. Reformatting never changes a digest
   (universal-model.md 7.1); a semantic edit always does.
3. Canonical order: items of a file in the order module/part, includes
   (by path), packs, namespaces, entities by (kind order node, flow,
   contract, claim, vmodel, boundary, template; then name, a declaration before
   its `extend`), then top-level exceptions (D70); clauses of an entity
   in a fixed order (kind, clearance, owns, may, surface,
   producer, consumer, contract, flow fields, what, proof, assumed,
   evidence, links, attrs by key, exceptions by (kind, rule), aliases);
   operands of `&` and `|` sorted by their printed form; list-valued
   clauses sorted by printed form and de-duplicated (a duplicate is
   MDL017 Advisory before printing); a duplicate is removed only when
   it carries no comments or docs (D72).
4. Canonical spelling: one space around `:`, `->`, `=`; quantities as
   `N unit` with `%` attached; level and unit aliases replaced by the
   canonical names; keywords lowercase; strings with minimal escapes;
   dates as written.
5. Comments and directives travel with their item and keep their text;
   a comment is never deleted, merged or reflowed; doc comments stay
   directly above the item.
6. A file that contains a `hole` or an `opaque` is not rewritten
   (`fmt` exits 1 naming the hole) so that a syntax error is never
   "formatted away".
7. Multi-file: fmt formats each file in place and never moves an item
   to another file (item order is a per-file concern, 3.3).

## 10. The formal relation to code

### 10.1 Sets

- E: the set of entities of a model (the units of kinds node, flow,
  contract, claim, vmodel, boundary, pack of the U term of 9.2), each
  with a full name and an identity (5.5).
- I: the identities of the code term (universal-model.md 2.2): every
  `unit` of every artifact in the snapshot, including the units of the
  model's own .grmb files (the model is part of the code it describes).
- S = {Must, May, Unknown}, ordered Must > May > Unknown.

### 10.2 Binding

Binding is a relation

```
B  subset of  E x I x S
```

where `(e, i, s) in B` means entity e is bound to identity i with status
s, and `Unknown` is represented by a residual pair `(e, hidden(r), Unknown)`
for each unseen remainder r of 6.4 step 4, never by a missing row. For
each e the set `B(e)` is the union over the entity's binding clauses:
`owns` of a node, `producer` and `consumer` of a flow (to the nodes'
code), `shape` of a contract, `runnable` and `ref` of a vmodel, and
`evidence tests` of a claim; `may ... at` and `surface` bind capability
and surface sets and are queried, not stored in B.

### 10.3 The four ranked sources and conflict rules

| Rank | Source | Contributes | Status |
|---|---|---|---|
| 1 | `grimble:binds` directives (in code or in .grmb, 8.2) | `(e, i)` for the named entity and symref | Must |
| 2 | model selectors (`owns`, `producer`, ...) through `sel` (6.4) | `(e, i)` for every identity in `lo` (Must) and `hi \ lo` (May) | Must or May |
| 3 | pack inference from names and attributes (declared by a data pack) | `(e, i)` | May |
| 4 | nothing | the residual `(e, hidden(r), Unknown)`; an empty selector is reported (MDL005, SYS004), never clean | Unknown |

Conflict rules, applied per identity i and per binding KIND (ownership,
producer, consumer, shape, evidence):

1. HIGHER RANK WINS. If a pair at rank r exists for i, lower ranks are not
   consulted for that kind, except that a lower-rank pair for a DIFFERENT
   entity is kept as an advisory "overridden" fact (shown by
   `grimble explain`, not a finding).
2. WITHIN RANK 2, MOST SPECIFIC WINS by the total order of 6.5; a tie is
   SYS002 and the owner is Unknown. Within rank 1, two entities bound to
   the same identity for ownership is SYS003 (explicit contradiction; binding.md
   2.1 and 2.5 refine this rule, see the note after the conflict rules).
3. WITHIN RANK 3, a tie yields no owner (May on both) and no finding;
   inference never creates SYS002.
4. STATUS COMBINES by maximum over sources of the same rank and entity
   (a pair reached by a Must glob and a May glob is Must).
5. UNOWNED (FOREIGN) is `Exact(None)` only when no source mentions i and i
   has no unseen remainder; otherwise Unknown. A FOREIGN identity is Warn
   until `[grimble] strict = true`, as decided in grimble-model.md
   section 8.
6. ONE OWNER PER IDENTITY: `owner(i)` of 6.5 is a function; B may relate
   an identity to several entities of different kinds (a function is
   owned by a node and is the producer of a flow), but to one node.

Rules over B are stated with polarity over the `(lo, hi)` of `B(e)` in
G02; this file fixes only the relation, the sources and the conflict
rules.

G02 (binding.md) landed after this section and refines it: the relation gains
a role, rank 1 against a different Must at rank 2 is the finding SYS003
`directive-selector` (rule 1 above kept it advisory), two rank 1 nodes on one
identity are SYS003 (rule 2), and the owner function has the possible-worlds
reading of binding.md 2.2. Where they differ, binding.md wins (its 11.3).

## 11. Well-formedness rules (MDL)

`grimble check` runs these on the model itself, before and independent of
any code rule. They are the `MDL` family of crate grimble-model
(boundaries.md owner), each derived once with the `Rule` derive; the
documentation page is generated (documentation.md section 3). They are
P+ (presence) over the exact model term; a rule whose subject sits inside
a `hole` or an `opaque` reports one Unresolved for that subject instead
of an Error (the model must fail loudly, not quietly pass).

| Id | Alias | Severity | Condition |
|---|---|---|---|
| MDL000 | MDL-SYNTAX | Error | lexical or syntax error, bad encoding, forbidden construct (a hand-written `baseline`, a bare `because "..."`, a slug rule alias) |
| MDL001 | MDL-DUPLICATE-ENTITY | Error | two declarations of one full name (including alias and `renamed_from` collisions) |
| MDL002 | MDL-UNRESOLVED-INCLUDE | Error | included file or glob matches nothing, escapes the repo, is not readable |
| MDL003 | MDL-INCLUDE-CYCLE | Error | the include graph has a cycle (the offending include is skipped) |
| MDL004 | MDL-UNKNOWN-PACK | Error | pack not in `packs/`, not enabled in `grimble.toml`, or version or digest differs from the pin |
| MDL005 | MDL-SELECTOR-NO-FILE | Warn | a selector's PATH matches no file in the walk. A WARNING by design: a model may legitimately describe code that does not exist yet. It suppresses SYS001 for the same selector so one root cause is one finding; a selector whose file matches but whose units do not is SYS001 |
| MDL006 | MDL-UNRESOLVED-REF | Error | a reference (flow endpoint, claim operand, link, exception target, `frob:tests` target) resolves to no entity, or to an entity of the wrong kind (except a V-model link target that is not a vmodel, which is MDL014) |
| MDL007 | MDL-VERSION | Error | missing header, unsupported major, or files of one model with different majors |
| MDL008 | MDL-FIELD | Error | a required field is missing (`trust`, flow `label`, contract `shape`, claim `what`, vmodel `kind` and `level`, a template's `excuse` clause, an excuse's `for` or non-empty `because`), a scalar clause appears twice, or an `extend` sets a scalar |
| MDL009 | MDL-TYPE | Error | an ill-typed value: unit outside the table, comparing dimensions, a path with `..` or empty, a boundary pair on the wrong lattice, a malformed date |
| MDL010 | MDL-SELECTOR-EMPTY-BY-CONSTRUCTION | Warn | a selector that cannot match anything whatever the repository holds (`lang(rust) & lang(python)`, `a & !a`) |
| MDL011 | MDL-MODULE | Error | `part of` name differs from the root `module`, or two roots declare the same module name, or an included file declares `module` |
| MDL012 | MDL-DEPRECATED-NAME | Warn | a reference by a `renamed_from` name, or a `renamed_from` clause that nothing needs any more (this second half needs lock data and is deferred to G12; grimble-model reports only the reference half) |
| MDL013 | MDL-EXCEPTION | Error | malformed exception clause: wrong attribute set for the kind, `on` inside a body, missing `on` at top level, unknown rule id, malformed `ticket` or `until`, a `grimble:accept` style directive in a .grmb comment |
| MDL014 | MDL-VMODEL | Error | V-model construction error (wrong endpoint kinds, including a link target that resolves to an entity that is not a vmodel; an unresolved link target is MDL006, including a link target that resolves to an entity that is not a vmodel; an unresolved link target is MDL006, unpaired levels on `verifies`, missing `ref` or `runnable`, duplicate link, `supersedes` without `because`) |
| MDL015 | MDL-SHADOW | Advisory | the resolved entity shadows a different entity of the same name at an outer level |
| MDL016 | MDL-UNKNOWN-ATOM | Error | a capability atom in no registry and no enabled pack |
| MDL017 | MDL-DUPLICATE-CLAUSE | Advisory | a list clause repeated with identical content |
| MDL018 | MDL-NODE-EXCUSE | Error | an `excuses` clause on a `node` or in an `extend node` (removed by D75). Remedy: move the reasoning into a matrix-build template (4.7) or grant the atom with `may`; ungranted already means denied |
| MDL019 | MDL-ORPHAN-FILE | Warn | a `.grmb` file of the walk that no declared root reaches through `include` and that is not excluded (3.1). Remedy: include it from a root, list it under `[grimble] models`, or exclude it in `[check] exclude` |
| MDL020 | MDL-INCLUDE-OUTSIDE | Error | an include (or glob) names a file above the including file's directory without the `outside` marker (3.2); the include is skipped |
| MDL021 | MDL-NO-ROOT | Unresolved (required) | no model root is declared (`[grimble] models` empty) while `.grmb` files exist, or a declared root is not a `.grmb` file of the walk (3.1) |

MDL022-MDL031 (exhaustiveness, error sets, retry bounds, scenario
start, goal `requires` cycles, planning placement) are defined in
grmb-planning.md 7.1.

Cyclic flows are allowed and are not an MDL rule: a cycle is a legal
model and the kernel's age and demand computations handle it by SCC
condensation. What the kernel does with a rate-fed cycle (+infinity with a
witness, grimble-model.md section 3) is a kernel verdict. Include cycles
(MDL003) and V-model trace cycles (a kernel closure rule) are refused;
flow cycles are not.

Ids are `FAMILYNNN`, new family MDL registered in rules.md by the
implementation ticket (G08); the aliases above are the slug aliases.

## 12. Conformance corpus outline

Location `crates/grimble-model/tests/corpus/`, run by gob-mdtest (one
case per directory; a block without `expect=` is documentation, D51).
Each directory holds the `.grmb` inputs and an `expect` file; those that
test the U adapter hold the expected U term and scope graph per construct
(the F4 corpus of universal-model.md 3.3).

| Directory or file | What it proves |
|---|---|
| `lex/idents.grmb` | identifier charset, keyword collision is MDL000, no string entity names |
| `lex/strings.grmb` | escapes, `\u{..}`, adjacent-string join in value position, no raw newline |
| `lex/quantities.grmb` | the unit table, attached and separated units, MDL009 on unknown unit and cross-dimension compare |
| `lex/dates.grmb` | date validity, `until=` and `review=` |
| `lex/encoding/` | not-UTF-8, BOM, NUL give `opaque(reason=not-utf8)` and a bare CR gives `opaque(reason=binary)`, each with MDL000; CRLF accepted |
| `lex/comments.grmb` | line, block (nested) and doc comments; none in the token stream |
| `directive/binding.grmb` | the four binding rules of 8.1 (next item, trailing, before `}`, file) |
| `directive/verbs.grmb` | accepted verbs; `grimble:accept` and `grimble:node` in a .grmb comment are MDL013 |
| `directive/malformed.grmb` | a malformed directive is reported, never dropped |
| `include/basic/` | include, read-once, diamond is not a cycle |
| `include/glob/` | glob expansion order, glob matching nothing is MDL002 |
| `include/cycle/` | MDL003 and the rest of the model still loads |
| `include/escape/` | path leaving the repository is MDL002 |
| `include/roots/` | only the declared root's include tree is the model; an extra unreachable file is MDL019 |
| `include/no-root/` | files but no declared root is the required Unresolved MDL021 |
| `include/climb/` | an include above the including directory without `outside` is MDL020, the include is skipped (its target is then an MDL019 orphan) |
| `include/climb-marker/` | the same include with the `outside` marker loads clean |
| `include/climb-glob/` | a glob that climbs out follows the same rule (MDL020 without `outside`) |
| `include/mount/` | `as P` prefixes entities, resolution inside the mounted file, root-anchored `::` |
| `version/header/` | a directory (multi-file): missing header and unsupported major (MDL007); mismatched majors are unreachable while only major 2 is read, so that half is untested until a second major exists |
| `entity/node.grmb` | every node clause and its U term; missing `trust` is MDL008 |
| `entity/flow.grmb` | flow fields, producer in another language, cyclic flows accepted |
| `entity/contract.grmb` | shape and versioning, shared contract |
| `entity/claim.grmb` | the three claim forms, `assumed`, both evidence spellings give one relation |
| `entity/vmodel.grmb` | levels and aliases, link kinds, MDL014 cases |
| `entity/boundary.grmb` | endorse and declassify, lattice mismatch is MDL009 |
| `entity/template.grmb` | the excuse grammar, selection over lang, kind and attr, missing `for` or `because` is MDL008, unknown atom is MDL016, `check --json` lists and counts each excuse |
| `entity/node-excuse.grmb` | a node-level `excuses` clause is MDL018 and the file otherwise loads |
| `entity/pack.grmb` | pin, digest mismatch and missing pack (MDL004), pack-qualified atom |
| `scope/unique/` | a directory (multi-file): MDL001 independent of include order |
| `scope/resolve.grmb` | nearest-first resolution, MDL006, shadow Advisory MDL015 |
| `scope/rename.grmb` | `renamed_from` keeps identity, warns MDL012, `alias` does not |
| `scope/extend.grmb` | additive `extend`, scalar `extend` is MDL008, extension is one identity |
| `selector/grammar.grmb` | precedence of `!`, `&`, `|`; parenthesized forms; predicates |
| `selector/glob.grmb` | `*`, `**`, `?`, classes, alternation, trailing `/`, qualname globs |
| `selector/status.grmb` | Must for literal, May under an unexpanded phase and an Unknown attribute, hidden placeholder in `hi` |
| `selector/specificity.grmb` | the total order, including the `src/**` against `src/*/mod.rs` example, ties give SYS002 |
| `selector/owner.grmb` | `owner` with explicit bind, owns, inference, FOREIGN and Unknown |
| `selector/empty.grmb` | MDL005 versus SYS004 versus MDL010 |
| `exception/kinds.grmb` | accept, defer, hotfix clauses; top-level `on`; baseline rejected |
| `exception/targets.grmb` | position rules and MDL013 |
| `u/encoding/` | one directory per row of 9.2: expected term, sorts, locations and the scope graph |
| `u/facets.grmb` | the five facets, and that an exception edit changes only Attr |
| `fmt/idempotent/` | fmt is a fixed point and preserves every digest |
| `fmt/order/` | canonical item, clause and operand order |
| `fmt/comments/` | comments and directives travel; a file with a hole is not rewritten |
| `recovery/holes.grmb` | resynchronization at `;` and `}`, rest of file still parsed, Unresolved for subjects in a hole |
| `plan/` | the planning layer: one directory per construct and per MDL022-MDL031 rule, plus the two worked examples of grmb-planning.md 12 and 13 (P1) |
| `example/frob.grmb` | the worked model of section 13 (with its include) loads with zero Errors and the documented warnings |

## 13. Worked example: this repository

Two files. The root declares the architecture; the fragment holds the
V-model. They obey every rule above: names are unique, every reference
resolves, every required field is present, no keyword is used as a name.
Paths, symbols and tests named here exist in the repository today except
the grimble crates, which do not exist yet (see the expected warnings below).

`design/frob.grmb`:

```
grimble = "2";
module frob;

include "vmodel.grmb";

/// The ticket goblin: accounts for work. Never links grimble (D28).
node frob : trusted {
  kind component;
  clearance Internal;
  owns "crates/frob/**";
  owns "crates/frob-*/**";
  may fs.read at "crates/frob*/**";
  may fs.write at "crates/frob-ledger/**";
  may exec at "crates/gob-exec/**";
}

/// The design goblin. Crates are created by G08 onward.
node grimble : trusted {
  kind component;
  clearance Internal;
  owns "crates/grimble-*/**";
  may fs.read at "crates/grimble-*/**";
}

/// The shared substrate: no product knowledge.
node gob : trusted {
  kind component;
  clearance Internal;
  owns "crates/gob-*/**";
  may fs.read at "crates/gob-walk/**";
  may exec at "crates/gob-exec/**";
  may net.connect("github.com") at "crates/gob-git/**";
}

flow f_walk : gob -> frob {
  label Internal;
  rate 100 req/s;
  producer "crates/gob-walk/src/lib.rs::walk";
  consumer "crates/frob-check/src/snapshot.rs";
  contract walk_result;
}

flow f_symref : gob -> grimble {
  label Internal;
  producer "crates/gob-symbols/src/symref.rs::Symref.parse";
  consumer "crates/grimble-model/src/**";
  contract symref;
}

contract walk_result {
  shape "crates/gob-walk/src/lib.rs::WalkResult";
  versioning scheme=semver current="0.1.0" compat=backward;
}

contract symref {
  shape "crates/gob-symbols/src/symref.rs::Symref";
  versioning scheme=none;
}

claim no_frob_to_grimble {
  noflow frob -> grimble;
  proof L2;
  evidence tests "crates/frob/tests/wiring.rs";
}
```

`design/vmodel.grmb`:

```
grimble = "2";
part of frob;

// frob:doc docs/design/cli.md#2-output-contract
vmodel req_gate_exit {
  kind artifact;
  level requirements;
  ref "docs/design/cli.md#2-output-contract";
}

vmodel t_gate_exit {
  kind test;
  level customer_test;
  runnable "crates/frob/tests/check_verb.rs::error_finding_exits_1_and_fail_on_none_exits_0";
  verifies req_gate_exit;
}
```

Why the rules accept it:

- MDL007 and MDL011: both files carry `grimble = "2"` and `part of frob`
  matches `module frob`; MDL002 and MDL003: one include of an existing
  file, no cycle.
- MDL001: `frob`, `grimble`, `gob`, `f_walk`, `f_symref`, `walk_result`,
  `symref`, `no_frob_to_grimble`, `req_gate_exit`, `t_gate_exit` are
  distinct (the node `frob` and the module `frob` are different
  namespaces); the contract `symref` and the flow `f_symref` differ.
- MDL008 and MDL009: every node has `trust`; every flow has `label`;
  quantities use table units; both vmodels have `kind` and `level`.
- MDL006: `walk_result`, `symref`, `frob`, `gob`, `grimble` and
  `req_gate_exit` all resolve. MDL014: `verifies` joins a test at
  `customer_test` to an artifact at `requirements`, a pair of 4.5.
- No node carries an excuse (MDL018 would fire). `frob` is not granted
  `net.listen`, and that is the whole statement: capabilities are denied
  by default (binding.md 7.2), so an observed `net.listen` in
  `crates/frob/**` is CAP001 and a blank cell is "denied", not
  "unconsidered". The earlier draft wrote `excuses net.listen because=...`
  here; it is rewritten as a grant decision (no grant) because the
  reasoning ("a CLI never serves") is about this node, not about how an
  atom applies to a kind of code. A template excuse (4.7) is the right
  tool only for the latter, for example generated stubs.
- `grimble check` reports zero Errors and MDL005 Warn for the three
  selectors that name crates not yet created (`crates/grimble-*/**` twice
  and `crates/grimble-model/src/**`); these are warnings by design and
  disappear when G08 creates the crates. SYS004 is suppressed for them.
- Capability atoms `fs.read`, `fs.write`, `exec`, `net.listen` and
  `net.connect` are registry atoms (grimble-model.md 9.6).
- Binding: `owner` of `crates/gob-walk/src/lib.rs::walk` is `gob` at
  Must from `crates/gob-*/**`; `owner` of `crates/frob-ledger/src/lib.rs`
  is `frob` at Must from `crates/frob-*/**`, specificity
  `(1, 1, -1, -1, 0, 0)`; `crates/frob/**` does not match it and no other
  node's selector does, so no tie (SYS002) arises.

## 14. Open questions, and what this specification drops or changes

### 14.1 Cross-check against grimble-model.md sections 1-3

Every construct of sections 1-3 has a place in this specification
(section 9.2 gives each its U term). Dropped or changed relative to those
sections:

1. `store` keyword: dropped; a store is `node ... { kind store; }` with
   typed attrs (`attr engine = git_tracked; attr append_only;`).
2. `module X` root and `part of X` fragments: kept; fragments may now
   declare any entity (as 2 stated), and the new `extend KIND REF` is
   restricted to list clauses (v1's `extend node` widened `may` only).
3. `may ATOM at SELECTOR of CONSTRAINT`: `of CONSTRAINT` and the colon
   atom argument (`net.connect:api.github.com`) are replaced by one form,
   `ATOM("arg", ...)`. v1's `exclusive` and `via` are gone.
4. `because "..."` of every exception: the bare string after
   `because` becomes `because="..."` (`key=value` everywhere, matching the
   shared directive parser). `defer ... ticket ID` becomes
   `ticket="ULID"`.
5. `surface pub fn *, "Cli"`: replaced by a selector expression
   (`kind(function) & attr(vis = "pub") & "..."`); there is no unquoted kind
   list. Multiple `surface` clauses union.
6. `flow ... via producer P consumer C contract K;`: `via` is dropped;
   `producer`, `consumer` and `contract` are three clauses. `contract`
   now names a `contract` ENTITY (new, 4.3) rather than a selector, so a
   shape is shared and versioned.
7. `boundary`: kept (D6) and made the seventh entity kind; 9.3 listed six. D75 adds `template` as the eighth (4.7); the node-level `excuses` clause of grimble-model.md section 2 is removed (MDL018).
   The six-phase block remains dropped; the example's undeclared
   `f_install`, `foreign`/`trusted` levels and the other undeclared names
   of section 2 (`symbols`, `registry`, `vet`) are why that example was
   ill-formed and why section 13 here is a complete one.
8. `assert noflow ...` and `assume "weakness:CWE-78:vet" ... owner ... review ...`:
   both become `claim` entities (`what`, `proof`, `assumed owner= review=
   because=`). Claim ids are identifiers; a string id from a pack is the
   `attr id`. The `assume ... owner logan review 2026-10-15` spelling
   becomes `assumed owner=logan review=2026-10-15 because="..."` with a
   mandatory reason.
9. `vmodel req_1 kind artifact level requirements ref "..."` is kept as a
   block; the one-line `vmodel t_1 verifies req_1;` becomes a link clause
   inside the source entity's body, and v1's separate `vmodel_edge`
   statement is not in the language. The level name `unit` is an alias of
   `component_unit_test`.
10. "Most specific selector wins; equal specificity on one symbol is an
    error; unclaimed symbols are FOREIGN": kept, but "most specific" is
    now a total order (6.5, review M12) and a tie yields an Unknown owner
    plus SYS002, never an arbitrary winner. `owns "path::qualname-glob"`
    with "optional kind filter" is now the `kind(...)` predicate.
11. "Every construct has a stable id": identity is `(module, full name)`,
    independent of the file (5.5), with `renamed_from` for renames.
12. `waive` replaced by the exception kinds: kept; `baseline` is not a
    clause (exceptions.md: pools are files); `grimble graph` synthesizes
    the baseline attribute that grimble-model.md 9.3 lists among the
    `attr` nodes.
13. 9.1 "May for globs that match units with Unknown edges": kept and made
    total (6.4): a glob is Must where a literal is, May along a May or
    Unknown fact; the placeholder in `hi` is the Unknown.
14. SYS001 "selector matches zero symbols" (renumbered SYS004 by binding.md
    11.3): kept as the unit-level rule;
    MDL005 is the new file-level warning and suppresses SYS004 for the
    same selector.
15. The directive table row `grimble:node N`, `grimble:channel F`,
    `grimble:boundary B`, `grimble:effect`: code-side only; written in a
    .grmb comment they are MDL013 (they name an entity from outside it).
16. Dropped from the grammar and not carried: `host`, `krb`, `deploy`,
    cdn/balancer/queue/cache/secret/resource as keywords (kinds now),
    `operation`, `saga`, `crash`, `breach`, `policy`, `scenario`,
    `refine`, `entity`/`architecture`/`configuration`, `carries` (a PII
    pack), `import`/`export`/`layer`, `managed` and `abstract` (attrs),
    `capacity`, `skew`, `users`, `observe`, `on deploy` (attrs or a pack),
    `waive`. This agrees with grimble-model.md section 2's own dropped list.
17. Section 3's kernel and section 4's drift table are untouched; only
    the polarity statements (G02) and kernel verdict ids (G03/G04) are
    left to later tickets.

### 14.2 Open questions

1. Trust and label lattices. Fixed as the two builtin lattices with pack
   extension (4.1). v1 let a model extend them; is a pack the right owner
   for a project that needs a fifth trust level, or should a model file
   have a `lattice` item?
2. Cross-model references. Roots are isolated models (3.1). A monorepo
   with two models that share a contract needs either a qualified
   cross-root reference or one root; the current stance forces one root
   with includes.
3. Selector text across crates. The grammar is owned by gob-walk (G07) but
   written in .grmb tokens; confirm that slicing a selector's text from the
   .grmb token stream and re-parsing is acceptable for span fidelity, or
   whether gob-walk should expose a token-level parser.
4. Kernel verdict and V-model closure rule ids. The five closure rules
   and claim verdicts have no ids yet (review M3); MDL014 covers only
   construction errors.
5. The proof ladder `L1`..`L5` is an opaque ordered label here; its
   discharge conditions belong to G03.
6. Directive-form exceptions in .grmb are refused (MDL013) to keep one
   spelling; frob-side tooling that writes exceptions (`accept` verb) must
   edit the clause, which means a TOML-free edit of a .grmb file. Is the
   `exceptions.toml` form acceptable for model exceptions to avoid frob
   editing .grmb?
7. `until=` is a date only; a metric target (exceptions.md) is not
   expressible.
8. `growth` period. v1's `growth 15 %/month` needs a period unit; the
   time table stops at `d`. Add `w` and `mo`, or keep `%/d` only?
9. Claim verbs (`frob:effects` and the rest) are accepted but inert on
   .grmb units. Is a claim about a model entity (for example "this node
   has no effects") meaningful, or should they be MDL013 too?
10. Include globs: sorted lexicographic expansion is deterministic, but a
    new file silently joins the model. Should a glob include require an
    explicit marker (for example a count) so an accidental file is
    visible?
11. `pack` pins are exact. A pack security fix then needs a model edit;
    `grimble packs update` could rewrite the pin, which makes grimble
    edit a model (never auto-widen is the v1 lesson); it is shrink-neutral
    but needs a decision.
12. Whether `renamed_from` is enough for the ack planner or whether lock
    entries should additionally be keyed by a generated entity id (ULID)
    stored in the file; that would survive a rename without author effort
    at the price of noise in the model.
