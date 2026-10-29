# Grimble capability language v3

Status: draft
Owner: grimble
Decisions: none
Audience: rule author

This file specifies the v3 capability and effect language for .grmb models: typed `may` arguments, symbol-scoped grants, providers, never-claims, taint, expiring exceptions, environment profiles and a versioned core vocabulary.

Provenance: written under ticket ~T35301F, from the pessimistic audit of the grimble capability layer (findings H1-H10, M1-M14, L1-L6). It is a design: nothing here is enforced until the implementation tickets named in section 14 land. Where this file and an older statement disagree, this file wins for v3 models and grmb-spec.md 4.1, binding.md 7.2 and packs.md 8.1 point here.

Related: grmb-spec.md 4.1 (the `node` entity and the `may` clause), 4.4 (claims), 7 (exceptions), binding.md 7 (the capability matrix), packs.md 8.1 (the core-effects pack).

## 1. Principles

1. Deny by default (D75). An atom with no matching grant is denied; the observed use is the finding.
2. Judge per use, never per atom. Each observed use of an atom at a call site is checked on its own against the grants of its owner node. One covered use never masks an uncovered use of the same atom (audit H3). The cell verdict of binding.md 7.2 is the worst per-use verdict.
3. Typed arguments, not strings. Every atom declares an argument schema (section 3). The model parser rejects an argument that does not parse against the schema (MDL016 family, section 13).
4. Unresolved, never pass. When the checker cannot establish what a use does, the verdict is Unresolved with a reason code. It is never an implicit pass and never an implicit fail (the P+/P- discipline of universal-model.md 4.2: only a Must use outside every grant is a P+ finding; an Unresolved use blocks `declared-unused` and is listed). The same holds for a language with no detector for the atom (audit H5) and for unowned code (audit H8).
5. Narrower wins for the checker, wider for the reviewer. A grant constrains; a `forbid` (section 8) overrides every grant. A diagnostic always names the nearest grant and why it did not match.
6. Policy is data. The vocabulary (atoms, argument schemas, severities, detector rows) ships as the versioned core-effects pack (section 12); the grammar here is the only part in the binary.

## 2. Grammar

EBNF over the token set of grmb-spec.md 2. `NAME` is a name (grmb-spec.md 2.7), `STRING` a string literal, `DATE` an ISO date `YYYY-MM-DD`, `SELECTOR` a selector expression (grmb-spec.md 6).

```
grant        = "may" atomref [ at ] [ via ] [ cond ] { keyval } ";"
forbid       = "forbid" atomref [ "except" exceptspec ] [ at ] ";"
provide      = "provides" atomref "via" symsel { keyval } ";"
atomref      = ATOM [ opset ] [ "(" arglist ")" ]
opset        = "(" OPNAME { "," OPNAME } ")"        (* only for atoms with an operation set, section 3.2 *)
arglist      = arg { "," arg }
arg          = value | NAME "=" value
value        = STRING | NUMBER | RANGE | CLASS | ROOTED | "*" | list
list         = "[" [ value { "," value } ] "]"
ROOTED       = ROOTNAME ":" STRING                   (* tmp:"**", home:".config/*" *)
at           = "at" symsel
via          = "via" symsel
symsel       = SELECTOR                              (* may end in "::" SYMPATH *)
cond         = "profile" "=" NAME { "," NAME } | "until" "=" DATE
keyval       = ("because" | "ticket" | "owner") "=" STRING
```

Rules:

- `ATOM` is a registered atom or parent atom; a parent covers its children (`net` covers `net.connect` and `net.listen`).
- A positional argument binds to the atom's first schema slot; `NAME=value` binds the named slot. A grant with no `arglist` means "any argument of this atom" and is the broadest form; `grimble status` ratchets it as the widest (grmb-spec.md 4.1 ratchet) and the diagnostic recommends the narrowest argument that covers the observed uses.
- `*` is "any value of this slot" and is stated explicitly when a slot is deliberately open (`bin=*`); an omitted slot is open too, but `*` documents intent and is not flagged as an omission.
- `at` limits where the grant applies (the calling symbol), section 5. `via` limits how (the use must pass through the named provider), section 5.3.
- Backward compatibility: v2 `may fs.read at "src/**"` and `may net.connect("api.github.com")` parse unchanged. A bare string in a net slot is the host glob slot; a bare string in an fs slot is a repo-relative path glob. A v2 string that does not parse against the v3 schema is MDL016 only in a model that declares `grimble = "3"`; under `"2"` it stays an opaque string and is reported as "argument not enforced" (so existing models never silently change verdict).

## 3. Atom vocabulary and argument types

Per atom: the argument schema, the extraction rule (how a call-site argument becomes a value) and the verdict when extraction fails. The extraction ladder is shared and defined in section 4; "UNRESOLVED" below always means the Unresolved verdict of section 4.4, reason `arg-unresolved` unless stated.

Matching is by slot: a use satisfies a grant when the atom is covered and every slot the grant constrains matches the extracted value. A slot the grant leaves open matches anything, including an unresolvable value. A slot the grant constrains and the use cannot resolve is UNRESOLVED, not a pass.

### 3.1 net

| Atom | Slots (type) | Extraction | Cannot extract |
|---|---|---|---|
| `net.connect` | `target` (URL or `host[:port]` glob), `host` (host glob), `port` (int or `lo-hi` range), `scheme` (`http`, `https`, `ws`, `wss`, `tcp`, `udp`, `unix`), `direction` (`out` fixed for connect), `class` (`loopback`, `private`, `public`, `linklocal`, `any`), `dns` (bool: may resolve names) | URL or host-port literal at the URL/host parameter of the callee row; default port from scheme; class from a literal IP (RFC 1918, 127/8, ::1, 169.254/16, fc00::/7) | non-literal host: UNRESOLVED for `host`/`target`/`class`; a literal hostname has class `unknown-dns` until resolved, so a `class=` constraint over a hostname is UNRESOLVED (a name can resolve anywhere); a `host` constraint over a hostname is decided textually |
| `net.listen` | `bind` (`host:port` glob), `port`, `class` | the bind address literal; `0.0.0.0` / `::` is class `public` | UNRESOLVED |
| `net.resolve` | `host` glob | the name argument | UNRESOLVED |
| `net.tls` | `verify` (`on`, `off`) | the verify/insecure keyword or flag literal | UNRESOLVED; `verify=off` observed is a Must P+ only when the literal is the disabling value |

Notes:

- `net.listen` is never in the `net.connect` class (audit L2): a listener needs a `net.listen` grant, a client needs `net.connect`. A grant on the parent `net` covers both and every net child.
- A connect grant does not imply `net.resolve`; a use that resolves a name carries both atoms unless the grant sets `dns=true`, in which case resolve is covered for the same host glob.
- Host globs: `*.example.com` matches one or more labels left of `example.com`, `api.example.com` exactly one host, `**` any. IPv6 literals are bracketed in `host:port` form.

### 3.2 fs

| Atom | Slots (type) | Extraction | Cannot extract |
|---|---|---|---|
| `fs` | parent; covers every `fs.*` child | | |
| `fs.read` | `path` (path glob, repo-relative or ROOTED), `ops` (subset of `read`, `metadata`, `list`) | path argument at the callee's path parameter; `open` mode literal selects `read` vs `write`/`create` (audit M1); `exists`/`stat` are `metadata`, directory iteration is `list` | path non-literal: UNRESOLVED for `path`; mode non-literal: the use is UNRESOLVED for `ops` and is counted as all of `read`, `write`, `create` for the upper bound only (it never creates a P+ finding on its own) |
| `fs.write` | `path`, `ops` (subset of `write`, `create`, `delete`, `rename`, `chmod`, `symlink`, `truncate`, `append`) | as above; `OpenOptions` builder flags are folded when the chain is a single expression, otherwise UNRESOLVED | as above |
| `fs.exec` | `path` | path of an executed file (`exec` bit set, `chmod +x`) | UNRESOLVED |
| `fs.temp` | `ops` | `tempfile` / `mkstemp` family; implies the `tmp:` root | none: no path argument |
| `stdio.read` | `stream` (`stdin`) | the stdin handle | none |
| `stdio.write` | `stream` (`stdout`, `stderr`, `fd`), `fd` (int) | `println!`/`print`/`console.log` map to `stdout` or `stderr` by callee row; a raw fd write has `fd` the literal int | `fd` non-literal: UNRESOLVED for `fd` only |

Roots (ROOTED paths): `repo` (the default; a bare glob is repo-relative), `tmp` (the platform temp dir), `home`, `cache`, `config`, `data`, `abs` (an absolute path outside any named root). A `tmp:"**"` grant does not cover `/etc/passwd`; a path built from `dirs::home_dir().join(x)` is rooted at `home` when the root call is recognized and UNRESOLVED otherwise. A path containing `..` that escapes its root, or a symlink-creating operation, is evaluated on the lexically normalized path and an escape is a Must violation of any rooted grant; a path that cannot be normalized (non-literal segment) is UNRESOLVED. Path globs use gob-walk glob syntax (grmb-spec.md 6.2).

The `fs.read` / `fs.write` parent-child split of v2 (`fs` covers both) stays; v3 adds the `ops` slot so `may fs(read, create)("data/**")` is the atom `fs` with an operation set (section 2 `opset`) and means `fs.read` with ops `{read}` plus `fs.write` with ops `{create}`.

### 3.3 process

| Atom | Slots (type) | Extraction | Cannot extract |
|---|---|---|---|
| `process.spawn` (alias `exec`) | `bin` (name or path glob, or list), `argv` (shape: list of literal or `*`; the first element after `bin`), `shell` (bool), `env` (`inherit` or list of names) | `bin` is the program literal (`Command::new("git")`, `subprocess.run(["git", ...])`); a string passed to a shell-mode API (`shell=True`, `os.system`, `child_process.exec`) sets `shell=true` and has no separable `bin`; `argv` is the literal prefix; env passthrough from `.env(...)`, `env_clear`, `env=` keyword | `bin` non-literal: UNRESOLVED; `shell=true` with a non-literal string: a Must `shell=true` use whose `bin` and `argv` are UNRESOLVED; a grant that sets `shell=false` is violated by it (a Must P+ finding) |
| `process.signal` | `target` (`self`, `child`, `any`) | the signal API row | UNRESOLVED |
| `exit` | none | the exit/abort callee | none |

A grant `may process.spawn(bin="git", argv=["rev-parse", *], shell=false, env=[])` matches a use when `bin` is exactly `git`, the literal argv prefix is `rev-parse`, no shell is involved and the child gets an empty environment. `argv` shape semantics: `[a, b]` exact, `[a, *]` prefix `a` then anything, `*` anything. `env=[]` means `env_clear` was observed; `env=inherit` (the default for an unconstrained slot) is any.

### 3.4 env

| Atom | Slots (type) | Extraction | Cannot extract |
|---|---|---|---|
| `env.read` | `name` (list of variable-name globs), `secret` (flag) | the name argument; `secret` is a use-side classification: the name matches a secret-name pattern (section 9.2) | whole-environment reads (`env::vars`, `os.environ` iteration) have `name = *` (Must), and a name that is non-literal is UNRESOLVED for `name` |
| `env.write` | `name` | as above | UNRESOLVED |
| `env.cwd` | `op` (`read`, `change`) | `current_dir` / `chdir` | none |

`env.read("PORT", secret)` is a grant for the named variable `PORT` plus any variable classified secret; the flag `secret` in a grant means "reads of secret-class names are allowed here"; absent, a secret-class read is denied even when its name glob matches a broader `name` constraint.

### 3.5 Singletons and the rest of the vocabulary

Each row: atom, slots, extraction, cannot-extract verdict. Atoms without slots are decided by presence of the use only; their verdict on a missing detector is `no-detector` Unresolved (principle 4).

| Atom | Slots | Extraction | Cannot extract |
|---|---|---|---|
| `clock` | `kind` (`wall`, `monotonic`, `sleep`) | callee row selects kind | none (no argument) |
| `rng` | `kind` (`crypto`, `fast`) | callee row (`getrandom`, `secrets` are `crypto`) | none |
| `thread` | `op` (`spawn`, `join`), `count` (int, max) | `spawn` callee row; count only from a literal pool size | count non-literal: UNRESOLVED for `count` only |
| `unsafe` | none | tree-sitter attribute/block query (the Rust `unsafe` node) | none; fidelity below F2 is `no-detector` Unresolved |
| `ffi` | `lib` (name glob) | the loaded library literal (`dlopen`, `ctypes.CDLL`, `extern "C"` block's link name) | non-literal: UNRESOLVED for `lib` |
| `eval` | `kind` (`code`, `import`, `template`) | `eval`, `exec`, `Function(...)`, `importlib.import_module`, `require(expr)`, `import(expr)`; a literal module string is NOT dynamic and is a plain import | `eval` is always a Must use of the atom; its argument is never analysed; `import` with a non-literal module name is a Must `eval(import)` use |
| `deserialize` | `format` (`pickle`, `yaml-unsafe`, `marshal`, `json`, `bincode`, `any`), `trusted` (bool) | callee row selects format; the unsafe loaders (`pickle.loads`, `yaml.load` without `SafeLoader`) are the `unsafe-format` class, safe ones (`json.loads`, `serde_json`) are not capability uses unless a pack lists them | UNRESOLVED when a loader's safe/unsafe mode depends on a non-literal flag |
| `reflect` | `op` (`get`, `set`, `call`) | `getattr`/`setattr`, `Reflect.*`, `Class.forName`, `Method.invoke` | none |
| `db` | `engine` (name), `op` (`query`, `exec`, `ddl`), `table` (glob) | driver callee row; `table` only from a literal SQL string parsed to a single verb and table | SQL non-literal or concatenated: UNRESOLVED for `op` and `table`; the atom use itself stays a Must `db` use |
| `ipc` | `kind` (`pipe`, `shm`, `socket-unix`, `dbus`, `queue`), `name` (glob) | the endpoint name literal | UNRESOLVED for `name` |
| `log` | `sink` (`stdout`, `stderr`, `file`, `syslog`, `net`, `tracing`), `level` (`error`..`trace`) | logging-framework callee row (`tracing::info!`, `logging.info`); the sink is the configured one only when it is a literal in the same file | sink unknown at call site: the use is `log(tracing)` with `sink` UNRESOLVED; sink-aware taint (section 9) treats it as the union of sinks |
| `secret` | `name` (glob) | secret-manager callee rows (`keyring`, `vault`, `os.getenv` of a secret-class name is `env.read(secret)`, not this atom) | UNRESOLVED for `name` |

Output atoms (`stdio.*`, `log.*`) follow the output catalogue (~JXNJRTQ) and are enforced by the logging-routing rules (~JKKJPTT); this spec defines their grant syntax and verdicts and does not duplicate the catalogue.

### 3.6 Atom invariants

Every atom, without exception, has: (a) a slot schema (possibly empty); (b) at least one callee/pattern row in some language, or an explicit `impossible` or `no-detector`; (c) a stated Unresolved reason set. An atom registered without (a) or (c) is a pack-lint error (section 12). An argument slot has exactly one type from the set `glob`, `int`, `range`, `bool`, `enum`, `class`, `name`, `list`, `rooted-glob`, `url`.

## 4. Extracting a call-site argument

### 4.1 The ladder

For each slot of each observed use, the extractor tries in order and stops at the first that yields a value; each rung yields a value with a provenance tag that goes in the diagnostic:

1. `literal`: a string, number, bool or list literal at the argument position.
2. `folded`: constant folding within the symbol and across `const`/`static`/module-level literals resolved through the scope graph (string concatenation, `format!` with all-literal pieces, `Path::join` of literals, f-strings of constants).
3. `config`: a value read from a declared config source whose literal is statically known: a `[config]` file named in the model (`config "app.toml";` entity attribute) and read through a recognized loader. Only literals present in the committed file count. A config-derived value is `May`, not `Must`: it lowers a P+ finding to Unresolved, but still satisfies "all values in the config file match the grant" (the checker checks each possible value the key can take in the file and the declared default).
4. `param`: the value is a parameter of the enclosing symbol. This is not a verdict; it triggers effect polymorphism (section 6) so the caller's argument is judged at each call site.
5. `unknown`: anything else (runtime input, network, a non-const function result, a computed or reassigned variable).

### 4.2 Folding limits

Intra-procedural, bounded (a fixed number of assignments and nodes per symbol; the bound is a pack setting `[compute] fold_budget`). Exceeding the budget yields `unknown` with reason `fold-budget`, never a guess. A variable assigned in more than one branch folds to the set of its literals (a May set). Mutation through aliases or `&mut`, loops that build strings, and any value passing through `eval`/`reflect` are `unknown`.

### 4.3 Matching

A Must value (rungs 1, 2) matches or does not. A May set (rung 3 and branch sets) matches only when every element matches the grant: all-match is a pass, any element outside the grant is a P+ finding at May precision (reported but not an Error until a rule's ratchet raises it), and a mix needs the whole set.

### 4.4 Verdicts

Every observed use yields exactly one of:

| Verdict | Meaning | Finding |
|---|---|---|
| `allowed` | atom covered and every constrained slot matched with a Must value | none |
| `denied` | no grant covers the atom, or a constrained slot has a Must value outside every covering grant, or a `forbid` matches | CAP001 (P+; Error per the pack severity table) |
| `unresolved` | a covering grant exists but a constrained slot is `unknown`, `fold-budget`, May with a non-matching element, the symbol is an unresolvable dynamic call, the language has no detector (`no-detector`), the fidelity is too low (`fidelity`), or the owner is not Must (binding.md 7.2 item 4) | CAP006 (new, Warn by default): "capability use cannot be decided", with the reason code and the slot |
| `deferred` | the value is a `param` and the symbol is subject to effect polymorphism (section 6); the verdict is moved to its call sites | none at the callee; a verdict at each caller |

`unresolved` is never rendered as clean: it appears in the cell as `unknown`, in the summary Unresolved count, and it blocks `declared-unused` (CAP002) for the grant it could use. Raising `unresolved` to an error is a ratchet choice (`[packs.severity]`), not a default relaxation; lowering it below Warn is refused (it would be a pass). The verdict applies per use; the cell takes the worst of its uses in the order `denied` > `unresolved` > `allowed`.

### 4.5 Worked example

```
// grant
may net.connect(host="api.stripe.com", port=443, scheme=https) at "src/payments/stripe.rs::StripeClient.*";
```

| Call site | Extraction | Verdict |
|---|---|---|
| `client.get("https://api.stripe.com/v1/charges")` in `StripeClient::charge` | literal, host `api.stripe.com`, port 443 (default of https), scheme https | allowed |
| `client.get(format!("https://{}/v1", HOST))` with `const HOST: &str = "api.stripe.com"` | folded to the same | allowed |
| `client.get(&cfg.url)` where `app.toml` has `url = "https://api.stripe.com"` and `config "app.toml"` is declared | config, May set `{api.stripe.com}` | allowed (all elements match) |
| `client.get(&url)` where `url` is a function parameter, `fn fetch(url: &str)` | param | deferred to each caller of `fetch` |
| `client.get(&std::env::var("U")?)` | unknown | unresolved, reason `arg-unresolved`, slot `host` |
| `client.get("https://evil.example/")` in the same symbol | literal, host outside the grant | denied (CAP001) |

## 5. Symbol-granular grants: `at`, `via`, `provides`

### 5.1 `at SYMBOL`

`at SELECTOR` already accepts `FILE_GLOB::SYMBOL_PATH` (grmb-spec.md 6). In v2 the selector collapsed to its file set for enforcement (audit H4). In v3 it is enforced at symbol granularity:

- A use is "at" the innermost enclosing named symbol (function, method, closure's enclosing named symbol, module top level `<module>`) of its source location.
- The grant matches when that symbol is in the selector's symbol set. `Store.*` is every member of `Store`; `Store.**` includes nested; a bare file glob is every symbol in the files (the v2 meaning).
- A closure or a nested function belongs to its named outer symbol for `at`, except an `async` task spawned from it, which is attributed through the effect summary of section 6.
- A use in a file that matches the glob but in a symbol that does not match the `::SYMBOL` part is not covered. It is `denied` if no other grant covers it.
- A symbol that no adapter parsed (a syntax-error region recovered by tree-sitter without a symbol) has the file's `<module>` symbol and is judged as such, with the recovery recorded as fidelity `F1`, which yields `unresolved`.

### 5.2 Ownership and `at` together

`at` narrows within the node's owned set (binding.md 7.1). An `at` selector that matches nothing owned by the node is MDL008 at Warn (the grant is dead). It cannot extend authority to code another node owns; a symbol owned by node m is judged against m's grants whatever any other node's `at` says.

### 5.3 `via` and `provides`: sanctioned providers

```
node store : trusted {
  owns "src/store/**";
  may fs(read, write, create)("data/**") at "src/store/fs.rs::Store.*";
  provides fs.write("data/**") via "src/store/fs.rs::Store.put";
}
node api : authenticated {
  owns "src/api/**";
  may fs.write("data/**") via "src/store/fs.rs::Store.put";   // reaches the capability only through Store.put
}
```

- `provides C via S` declares S a capability boundary for C: a call to S performs C for the purposes of its callers, narrowed to C's arguments, and the effect inside S is judged against S's own owner's grants (not the caller's). The caller does not need a direct `C` grant for the effect inside S; it needs `may C via S`, which says the caller is permitted to invoke this boundary (a use of C that is a call to S).
- `may C via S` limits the grant to uses that reach C by a call into S. An effect transitive through anything else (section 6) is not covered.
- A `forbid C except via S` (section 8.1) is the negative form: only through S.
- `provides` in a node requires S to be owned by that node (an unowned or foreign-owned S is MDL008).
- A provider with no matching `provides` declaration is not a boundary: a wrapper function that merely calls `fs::write` exposes its effect to its callers (section 6) and does not launder it (audit H10).

### 5.4 "Only callers of S may do C"

`may C at "A::f"` plus `forbid C` on the rest (or the default deny) states it for direct uses. For transitive callers, `claim never ... uses C except via S` (section 8.2) states it. The two together express "call allowed here but nowhere else".

## 6. Effect transitivity and polymorphism

### 6.1 Per-symbol summaries

For each resolved symbol the checker computes an effect summary: the set of `(atom, slot-values, provenance)` the symbol performs directly or through resolved callees, a least fixpoint over the resolved call graph (cycles converge because the lattice is finite per symbol and atom; widening is the slot value `*`).

- Resolved edges to repo symbols compose the callee's summary into the caller's with call-site argument substitution (a `param` slot becomes the extracted value at the call site, or `unknown`).
- An edge to a repo symbol that is a declared provider boundary (`provides`) contributes the boundary's declared effect, not the interior.
- An edge to an external, unresolved or dynamically dispatched callee contributes a May edge: the caller's summary carries `unresolved(reason = dynamic-call)` for every atom of the callee's declared bound if known, otherwise a single `unresolved(any)` entry. It never contributes silence.
- Unowned code (no node owns the symbol) summarises with its own effects and attributes them to the first owned caller; a call from an owned symbol into unowned code is `unresolved(unowned-callee)` for the call's atoms unless a summary is computed (audit H8).

### 6.2 Attribution across nodes

A transitive effect of a symbol s owned by node a, reached through a call into a symbol t owned by node b (not a boundary), is attributed to both: it is a use of node a at the call site (judged against a's grants, with provenance `via b::t`) and a use of b at its own site (judged against b's grants). Thus a trusted `other` calling `wrap::write_any("/etc/passwd", ..)` is a `fs.write` use of `other` with `path="/etc/passwd"` extracted by substitution through the call, and `denied` unless `other` grants it.

### 6.3 Effect polymorphism

A symbol whose atom slot is a `param` is polymorphic in that slot. Its summary stores the slot as a variable `$p`, and each call site substitutes. This is the Koka effect-row idea restricted to slot values; there are no row variables beyond parameter slots in the first version.

Higher-order and dynamic dispatch:

| Case | Rule |
|---|---|
| Closure/lambda passed to a function | the closure's effects belong to the creating symbol; if the callee calls a function-typed parameter, the call is a May edge to every closure argument seen at the repo's call sites of the callee, else `unresolved(dynamic-call)` |
| Trait/interface/virtual dispatch | edge to every implementation in the repo that the type information allows (May); an external implementor is `unresolved(dynamic-call)` |
| Callback registered and invoked later (event handler) | attributed to the registering symbol (the closure creator) |
| Reflection and dynamic import | `eval`/`reflect` atom use, and the call it makes is `unresolved(dynamic-call)` |
| Macro expansions | calls inside macro arguments are observed (existing behaviour); macro bodies are unexpanded: `unresolved(macro-body)` when the macro is not known |
| async/spawned task | attributed to the spawning symbol |

### 6.4 Cost bounds

Summaries are computed per file group and cached by content digest. Recursion depth through `param` substitution is bounded (`[compute] poly_depth`); beyond it the slot is `unknown`.

## 7. Policies, composition and trust ceilings

```
policy std_service {
  may clock;
  may rng;
  may env.read("LOG_LEVEL", "PORT");
  may stdio.write via "src/log/**" because="all output routes through tracing";
  forbid stdio.write except via "src/log/**";
}
ceiling foreign {
  forbid process.spawn;
  forbid fs.write except fs.write(tmp:"**");
  forbid net.connect(class=public);
}
node payments : trusted { owns "src/payments/**"; use std_service; ... }
```

- `policy NAME { ... }` is a named bundle of `may`, `forbid`, `provides` and exception clauses. `use NAME;` in a node includes it; a policy may `use` another (cycles refused, MDL012 family). A policy has no `owns`, so its `at` selectors are relative to the using node's owned set (a policy `at` is intersected with owns).
- Composition is union for `may`, and `forbid` always wins over `may` (Cedar: forbid overrides permit). A forbid in a used policy applies to the using node.
- `ceiling TRUST { ... }` binds forbids to a trust level: every node of that level or lower inherits them; a node cannot grant past its ceiling (audit M9). A grant that a ceiling forbids is a model error (MDL020, new): the model does not load that grant, rather than loading and ignoring it.
- `extend POLICY { ... }` (grmb-spec.md 4.9) adds clauses to a policy; it may add `forbid`, and may add `may` only within the policy's own ceilings.
- Imported policies come from pack files (`import policy NAME from "pack"`) and are locked by digest like any pack content (packs.md).
- Identity of a grant for ratchet and ack purposes is canonical: atom, canonicalized argument value (normalized globs, sorted lists), `at`/`via` selectors, profile set; the `because`/`ticket` text and clause order do not change it (audit L5).

## 8. Negative guarantees

### 8.1 `forbid`

`forbid ATOMREF [except ...] [at SELECTOR];` removes authority. `except` takes a narrower atomref (`except fs.write(tmp:"**")`) or `except via SYMSEL`. A forbid in a node or policy applies to the node's owned set (narrowed by `at`).

### 8.2 `claim never`

```
claim pure_domain { never "src/domain/**" uses net, fs, process, env.read(secret); }
claim api_no_raw_fs { never node/api uses fs except via store; }
```

Grammar: `"never" SUBJECT "uses" atomref { "," atomref } [ "except" "via" symsel ] ";"`, where SUBJECT is a selector or `node/NAME`.

A never-claim is checked against observed AND transitive uses (section 6) in the subject set, not only against declared flows (the existing `noflow`/`reach` claims keep their flow semantics, grmb-spec.md 4.4). Verdicts:

| Verdict | When |
|---|---|
| Holds | every symbol of the subject set has a complete summary (detector covered, fidelity sufficient, no unresolved edge for those atoms) and no summary contains a match |
| Refuted | some summary contains a Must use matching the atomref (the use and its call chain are the counterexample) |
| Unresolved | no Must match, but some symbol has an unresolved edge or a `no-detector` / `fidelity` gap for a named atom, or the arguments of a candidate match cannot be extracted |

A never-claim never reports Holds on incomplete evidence (Unresolved, never pass). `never ... uses env.read(secret)` is refuted by a Must `env.read` whose name is classified secret.

## 9. Taint

### 9.1 Declaration

```
taint secrets {
  source env.read(secret), fs.read(secret_shaped), flow(label >= Secret);
  sink   stdio.write, log.*, net.connect, fs.write except via store;
  sanitize "src/payments/vault.rs::redact";
}
```

A `taint NAME` entity has `source`, `sink` and `sanitize` clauses. Sources and sinks are atomrefs; `flow(label >= L)` is a source defined by declared flows whose label meets L (the data model already labels flows). A sanitizer is a symbol selector: a value that passes through it is clean for this taint.

### 9.2 Secret classification

- `secret` as a name class: a variable name matching the pack list (`*_KEY`, `*_SECRET`, `*_TOKEN`, `*PASSWORD*`, `AWS_*`, ...), extendable per taint.
- `secret_shaped` as a path class: gob-trust `is_secret_path` (`.env`, `*.pem`, `id_*`, `credentials*`, ...).

### 9.3 Semantics and limits

Taint is symbol-level and flow-insensitive in v3: a taint holds a source in symbol s, and reaches a sink if some symbol s' with a sink atom use is reachable from s by calls (section 6) or if the same symbol both reads the source and performs the sink with no sanitizer on any path between them by call chain. This is an over-approximation of leakage: it never claims a precise data-flow.

| Verdict | When |
|---|---|
| Violation | a Must source and a Must sink exist in a call-connected pair, no sanitizer symbol is on the connecting call chain |
| Unresolved | source or sink arguments cannot be extracted, the chain contains an unresolved edge, or the language has no detector for a sink atom |
| Clean | no source reaches any sink under complete evidence |

A taint is Clean only on complete evidence. A flow-insensitive Violation is reported at May precision (a reviewer prompt, not a gate Error) unless the source and sink are in the same symbol, which is Must.

## 10. Exceptions with expiry

```
accept CAP001 on node/api atom=fs.read at "src/api/legacy.rs::load_cfg"
       owner="lognd" until=2026-12-31 because="moves to config service in ~XXXX";
```

Extends grmb-spec.md 7. An `accept` of a CAP rule must carry:

| Key | Rule |
|---|---|
| `atom=` | required for CAP rules: one atom with optional argument constraints; a bare `accept CAP001` with no atom is MDL021 (new), because it silenced every atom of a node (audit H7) |
| `at` | required (the narrowest symbol selector) |
| `owner=` | required; a person or team id |
| `until=` | required; ISO date; an expired accept is inert (the finding returns) and is itself reported as CAP007 (expired exception) |
| `because=` or `ticket=` | required |

Specificity: an exception matches a finding only when its atom (and argument constraints) cover the finding's atom and arguments and its `at` covers the finding's symbol. The most specific exception wins; an exception for `fs.read` never matches an `fs.write` finding, and `fs.read("config/**")` never matches `fs.read("/etc/**")`.

Gate: an exception on a P+ capability finding is accepted only when an attester has acknowledged it (the CAP005 presence mechanism: a TTY and an attester email, recorded in the ack ledger) and the ledger entry is recorded under the exception's canonical identity. Deleting the ledger does not silently re-enable the exception: CAP005 fires for the unattested exception. An `until=` more than the pack-set maximum horizon (`[exceptions] max_days`, default 365) is MDL022.

## 11. Environments and profiles

```
node api : authenticated {
  may process.spawn(bin="git", argv=["rev-parse", *], shell=false, env=[]) at "src/api/version.rs::git_sha" profile=prod;
  may process.spawn(bin=*) profile=test at "src/api/**/tests/**";
}
```

- `profile=NAME[,NAME]` on a `may`, `forbid`, `provides` or `accept` restricts the clause to the named profiles. A clause with no `profile` applies in all profiles.
- The active profile is chosen by `grimble check --profile NAME` or `[grimble] profile` in the repo config; the default profile is `prod`, so test-only grants never widen the default policy.
- `until=DATE` on a `may` makes the grant expire: a grant past its date is inert (its uses are `denied` again) and is reported as CAP007; a grant expiring within `[exceptions] warn_days` is a Warn on the grant itself. `until=` and `profile=` compose (both must hold).
- `grimble check --all-profiles` checks each declared profile in turn and reports each separately, so prod and test are never merged into one verdict.
- A node may declare `profiles a, b;` to constrain the names (a misspelt profile is MDL016 family).

## 12. Versioning the core vocabulary

- The atom set, parents, slot schemas, extraction rows and severities live in the `core-effects` pack and are versioned as the pack (semver). `grimble.packs.lock` records the pack version and digest like any pack (packs.md 8.1 and the lock rules); the `grimble = "3"` header pins the GRAMMAR version, the lock pins the VOCABULARY.
- A grimble upgrade that changes a verdict through vocabulary changes (a new detector for `net.connect`, a new atom) changes the pack digest, so it is a lock drift signal, not a silent verdict change.
- Compatibility: adding an atom, a slot or a detector row is a minor bump; removing or renaming is a major bump with an `alias` entry (`process.env` -> `env.read`, `exec` -> `process.spawn`) kept for a full major.
- Pack lint rejects an atom lacking a slot schema, an extraction rule or an Unresolved reason set (section 3.6), a detector row naming an unknown atom, and duplicate callee spelling across atoms of the same language (the divergent-vocabularies problem of audit M3).
- A model whose header is `grimble = "2"` is judged by the v2 rules plus a "not enforced" note (section 2 backward compatibility); `grimble migrate` rewrites it.

## 13. New and changed rules

| Id | Meaning | Default |
|---|---|---|
| CAP001 | denied use (extended: argument and symbol mismatch, forbid) | per atom, pack severity table |
| CAP002 | declared-unused grant (only on Exact absence) | warn |
| CAP005 | grant/exception widening or unattested exception | error |
| CAP006 | unresolved use: capability use cannot be decided | warn |
| CAP007 | expired grant or exception | error |
| MDL016 | unknown atom, unknown slot, or an argument not matching its slot type under `grimble = "3"` | error |
| MDL020 | grant exceeds a trust ceiling or conflicts with a forbid | error |
| MDL021 | `accept` of a CAP rule without atom, at, owner, until | error |
| MDL022 | `until=` beyond the maximum horizon | error |

CAP003 stays retired; CAP004 (template excuse) is unchanged. Rule ids CAP006, CAP007 and MDL020-022 are proposed here and are registered by the implementation tickets (section 14).

## 14. Prior art and implementation split

| Feature here | Prior art |
|---|---|
| Typed slots per atom (`host:port`, path, name, binary) | Deno `--allow-net=host:port`, `--allow-read=path`, `--allow-env=NAME`, `--allow-run=bin` |
| `provides ... via`, boundaries as sanctioned providers | cap-std / WASI (authority as a value): a module gets authority only through a provider; Pony/E object capabilities |
| fs operation set, bind/connect split | Landlock / seccomp / Java SecurityManager: operation bitsets, path-beneath rules, bind vs connect |
| `ban X except via Y`, `unsafe` count | cargo-geiger, cargo-deny wrappers |
| Effect summaries and slot polymorphism | Koka / Eff effect rows (restricted to parameter slots) |
| Source / sink / sanitize taint, pattern detectors | CodeQL, semgrep taint mode |
| `forbid` overrides `may`, ceilings, templates (`policy`), explain/test | Cedar, OPA (policies as data, forbid overrides permit) |

Implementation tickets (from the audit; each consumes this spec): ~867GGVJ (core-effects pack and versioning), ~6ZD117V (effect summaries and transitivity), ~NBEC70D (never-claims and taint), ~CT14W34 (expiry, profiles, policies), ~KEM2RHP (listen split), ~JXNJRTQ and ~JKKJPTT (output atoms). Detector recall for non-Rust and non-Python languages and call-site argument extraction per language are implementation work under those tickets; until a language's detector row exists, its verdict for the atom is `no-detector` Unresolved.

## 15. Worked examples index

Each construct above has a worked example in its section: typed arguments (4.5), symbol-scoped grants and providers (5.3), effect transitivity (6.2), policies and ceilings (7), never-claims (8.2), taint (9.1), expiring exceptions (10), profiles (11).

Diagnostic the full model produces for a denied use:

```
src/api/handlers.rs:42:13: error CAP001 `node/api` connects to `https://evil.example:443`
  seen:    reqwest::Client::get("https://evil.example/..") (resolved from `use reqwest::Client as C`)
  allowed: none for node/api (payments has https://api.stripe.com:443 at StripeClient.*)
  fix:     move the call behind a node that grants it, or add
           may net.connect("https://evil.example:443") at "src/api/handlers.rs::fetch_profile" because="...";
  explain: grimble why src/api/handlers.rs:42
```

An unresolved use renders with its reason and slot instead of a pass:

```
src/api/handlers.rs:58:9: warn CAP006 `node/api` net.connect target cannot be decided
  seen:    client.get(&url) where url = std::env::var("U")  (extraction: unknown)
  reason:  arg-unresolved, slot host
  allowed: net.connect(host="api.stripe.com") at StripeClient.* (does not apply at this symbol)
```
