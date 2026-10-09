# Fidelity accounting

Status: current
Owner: frob
Decisions: none
Audience: user

`frob check` never skips a file silently. Every walked file is classified per
rule by `gob_check::subject_status_for` (design: `docs/design/universal-model.md`
sections 4.1, 4.2 and 4.6).

| File state | Rule needs a capability (DOC001, DOC002, INV002, COV001) | Rule reads every text artifact (TODO001, REF001, TEST001, INV001, DRIFT*) |
|---|---|---|
| Opaque F0 (no adapter), text, comments scanned (TOML) | NotApplicable | examined |
| YAML F1 (`.yml`, `.yaml`: block-mapping keys as nested units `path::outer.inner`), comments scanned | NotApplicable | examined |
| Python F2 (`.py`, `.pyi`: modules, classes, functions, methods, imports, calls, decorators, docstrings), comments scanned | NotApplicable for DOC001 and DOC002 (Rust only for now); COV001 examined | examined |
| C# F1 (`.cs`; `.csx` is not C#: namespaces, types, members, attributes, preprocessor conditions; imports and calls land next), comments scanned | NotApplicable for DOC001 and DOC002 (Rust only for now); COV001 examined | examined |
| TypeScript and JavaScript F2 (`.ts`, `.tsx`, `.mts`, `.cts`, `.js`, `.jsx`, `.mjs`, `.cjs`: functions, classes, methods, interfaces, types, enums, namespaces, constants, ESM and CJS imports, exports, calls, JSX elements and attributes as terms, test runner calls), comments scanned | NotApplicable for DOC001 and DOC002 (Rust only for now); COV001 examined | examined |
| CSS F2 (`.css`: style rules, at-rules, declarations and custom properties as `gob_ir::style` terms, `var()` uses linked to definitions at May; SCSS and Less not yet), comments scanned | NotApplicable | examined |
| Opaque F0, text, not scanned (for example `.json`) | NotApplicable | one Unresolved per rule naming the file count |
| Opaque F0, binary (NUL byte or known extension) | NotApplicable | NotApplicable |
| Parse failed | Unresolved | Unresolved |
| Partial parse (holes) | examined, plus an Unresolved for symbol rules | examined |
| Fidelity below the rule's minimum (COV001 and AFFECT001 need F2) | Unresolved | Unresolved |

A `#` directive comment in a YAML file binds to the key on the next line (stacked
comments share it; a blank line ends the block; a trailing comment binds to its
own line's key), so `frob:accept CI006` above `on:` suppresses a tool finding
inside that key.

`NotApplicable` is a query answer only: it is counted, never a finding. A rule
outside the table is always examined. The minimum fidelity lives in
`gob_check::need_of` because `RuleMeta` is declared in `gob-rules`.

## Reach poison

`COV001` treats a callable reached only through May edges, or named by an
unresolved call in a test's reach, as Unresolved: neither covered nor
uncovered. `AFFECT001` does the same for dependents reached through May
edges or behind unresolved calls naming the changed symbol. A file that
parsed partially adds one Unresolved to each of these rules.

### What narrows a call

A call is Must only when the syntax proves one target; anything else stays May
(several candidates) or Unknown (none found), and Unknown calls poison by
`(qualifier, name)` only. These facts narrow a call and never guess:

- **Path calls through `use`.** `use frob_ack::Inputs;` then `Inputs::collect(..)`
  resolves into the crate named by the importing crate's `Cargo.toml`
  dependencies (package names with dashes mapped to underscores, an
  integration test also naming its own crate), following `pub use` re-exports
  across modules and crates. A single concrete target is Must; an inherent and
  a trait method of one name, a trait method, or a glob import when the file
  has more than one glob stay May.
- **Typed receivers.** `self`, annotated locals and parameters, struct
  literals, `Type::new`, declared return types (through `?`, `unwrap` and
  `expect`), tuple returns and struct fields (`self.field.m()`, only when the
  struct name is unique in its crate and the field type is a concrete path
  type) type a method call. Wrappers (`Box`, `Rc`, ...) outside `dyn`, generics, type
  aliases and types with a `Deref` impl drop the typing. A typed receiver without such a
  method of its own can only reach trait-provided methods.
- **Element and variant types.** A `for` variable, a closure parameter and a
  pattern binding take the type their source proves: `Vec`, slice, array, set
  and map element types (`iter`, `into_iter`, `keys`, `values`, `get`, `first`,
  `pop`, `enumerate`, `filter`, `rev`, `chain`, `cloned`, indexing and slicing),
  `Option`/`Result` payloads (`Some(x)`, `Ok(x)`, `ok`, `unwrap_or*`, `map`,
  `and_then`), the closure parameters of `map`, `filter`, `any`, `fold`, `sort_by`
  and `retain` (one parameter), `collect` into a `Vec<_>`, a tuple (`let (a, b)`,
  wildcards keep their position) and the declared fields of an enum variant
  (`Kind::A(x)`, `Kind::B { f }`, unit variants and constants as `Type::NAME`).
  Only the first generic argument or tuple element is kept (`Vec<Vec<T>>` types
  the outer `Vec`); an or-pattern, `Err(e)`, a range `get`, `zip`, a `map` whose
  closure result is unknown, an alias or a generic leaves the value untyped and
  every method of that name stays possible. Bindings end with their `match` arm,
  closure, loop or `if let` body.
- **Standard return types.** A small table types the results of `str`, `String`,
  `Path`, `Vec`, map, set, `Option`, `Result`, iterator, `RefCell`/`Mutex` and
  JSON-value methods (`trim`, `lines`, `parent`, `join`, `get`, `as_array`, `borrow`,
  `lock`, ...), `fs::read_to_string`, `String::from_utf8`, `Path::new`,
  `Clone::clone`, `Type::from(..)`, `Self::default()` and `to_string` (unless
  the repository declares a method of that name). A standard receiver cannot
  reach a repository method, so `s.trim().len()` is not a call of `Relation::len`;
  a repository type named like a standard one (`Vec`) vetoes the table.
- **Derives.** A call a standard derive generates (`T::default()`, `x.clone()`)
  has no repository callee and poisons nothing. `#[derive(D)]` on a type with
  one repository trait named `D` that declares `m` makes `T::m(..)` and `x.m(..)`
  Must to that declaration.
- **`crate::` paths.** `crate::a::f(..)` and `crate::Type::f(..)` in a source
  file resolve inside the crate (following `pub use`); `self::` and `super::` do
  not, because an inline `mod` changes their meaning.
- **A type declared once in the calling file** (an integration test's `Fixture`)
  is that type even when other files declare the same name.
- **Trait bounds.** `&dyn T`, `impl T` and a generic `P: T` receiver or path
  qualifier (`P::make()`) reach the trait's method (Must) and its
  implementations (May); inherent methods of concrete types are ruled out. The
  same holds for `Box<dyn T>` and `Arc<dyn T>` elements and fields.
- **Signatures.** Each function records its `self` kind, arity and return type;
  an unknown-receiver `x.m(args)` admits only methods that take `self` and match
  the argument count.
- **Std macros.** The arguments of `assert!`, `assert_eq!`, `format!`,
  `write!`, `println!`, `tracing::info!`, `vec!` (the `;` of `vec![x; n]` read as
  a comma), `matches!` (read as `match E { P if G => .. }`) and the like are
  re-parsed as expressions and resolve like any other call, unless the
  repository declares a macro of that name or the arguments are not plain
  expressions. Closure parameters and patterns inside them are scoped and typed
  like those outside.

## Python

The Python adapter (F2) reads units (`path::Class.method`, nested `outer.inner`),
imports (plain, from, relative, star), decorators as attributes, docstrings as
the doc facet and calls with qualifiers. Binders follow Python scoping
(parameters and every name assigned in a function). Calls resolve as follows:

- Must: a name defined in an enclosing scope or the module, a `from ... import`
  name (re-exports through `__init__.py` followed), a module attribute reached
  through `import`, a `self.m()` the enclosing class defines, a class call to its
  `__init__`.
- May: a module matched only by path suffix, several definitions of a name, an
  inherited method, a star import, and any call on a value of unknown type
  (`obj.m()` names every repository method `m`).
- Unknown (never clean): a parameter or assigned name called as a function, an
  expression callee (`fns[0]()`), and names no repository file defines.
- Not modelled, reported as a partial parse (Unresolved for symbol rules): `match`
  statements. Calls inside decorators and parameter defaults are attributed to the
  enclosing scope. Dynamic features (`getattr`, `exec`, metaclasses, monkey patching)
  are invisible except as Unknown callees.

A test is a module-level `test*` function or a `test*` method of a class in a
`test*.py`, `*_test.py` or `*_tests.py` module (pytest and unittest naming).
`frob test` still lists changed Python files as unresolved until pytest selection lands.

## TypeScript and JavaScript

The adapter (F2, one adapter for the TypeScript, TSX, JavaScript and JSX grammars, chosen by extension)
reads units as `path::Class.method` (nested functions `outer.inner`, a namespace `A.B` as one unit per
component): functions (declarations, and module-level `const f = () => ..`), classes, methods (constructors,
accessors, `handle = () => ..` fields), interfaces, type aliases, enums, namespaces, and `const` or `static`
for other module-level declarators. An anonymous `export default` function or class is the unit `default`.
A declaration is public when exported (`export`, `export { a as b }`, `export default a`,
`module.exports = ..`, `exports.x = a`); a class member is private for `private` and `#name`, crate-level
for `protected`. A `/** */` comment before a declaration is its doc facet; decorators are attributes.
Binders are function-level (every `let`, `const`, `var`, catch name and parameter of the function body):
a block-scoped name that shadows an outer one hides it for the whole function, so such a call is Unknown,
never a wrong target.

Imports and the module graph:

- Must: a static `import`, `export .. from`, `import x = require()`, and a `require` at the top level of the
  file; a relative specifier that names one file, tried in TypeScript's order (the `.js` family mapped to its
  source extension, the path, the path plus `.ts .tsx .d.ts .js .jsx .mts .cts .mjs .cjs`, then `index` in
  the directory); a named import followed through `export *`, `export { a as b }` and `export * as ns`.
- May: a literal `import("m")`, a `require` under a condition or inside a function, a name exported by
  several files, a method call on a value of unknown type (`obj.m()` names every repository method `m`),
  an inherited method.
- Unknown (kept as an edge with no target, never dropped): a computed specifier (`import(name)`,
  `require(name)`, a template literal with substitutions), a relative specifier that names no file, and every bare specifier (a package, a
  tsconfig `paths` alias, a workspace package, a `#` import) until the project model answers them
  (~C3DEAQX); a local value called, an expression callee, and names no repository file defines.
- Not modelled: `with` statements (reported as a partial parse); type-directed resolution (a method on a
  typed receiver is May by name); CJS exports other than `module.exports = a`, `module.exports = { a }`
  and `exports.x = a` (function expressions assigned to `exports` are not units); constant evaluation of
  class-name strings (~C2F4ZMQ).

JSX lowers to the `gob_ir::markup` forms: an element is `apply(element)` (a `lit(tag)` head for an intrinsic tag, a
`ref` head for a component, which is also a call edge from the using unit), attributes are `markup.attribute` with a
`const_value`-form value, spreads `markup.spread` (May), fragments, conditional and mapped children `group`s.
`style={{..}}` objects add a `region(css)` of `style.declaration` nodes (Known literals tokenised, computed values one
`lit(unknown)`), and `css` tagged templates are `region(css)` islands. `gob_symbols::jsx_elements` lists elements with
tag, kind, attribute names and line.

A test item is a `describe`, `suite`, `it`, `test` or `test.describe` call (modifiers such as `only`, `skip`,
`fixme`) with a literal title and a function argument, when the name is imported from vitest,
`@jest/globals`, `@playwright/test`, `bun:test` or `node:test`, or the file is a test file (`*.test.*`,
`*.spec.*`, under `__tests__`, `tests`, `e2e`); `gob_symbols::test_items` lists them (framework `globals` when
not imported).

`frob test` runs TypeScript tests (~RNQ92ZK). A runner call is a unit (`test$<title>`, `suite$<title>`), and a
selected one maps to the test file's member (the nearest `package.json`) and runner: vitest when the package lists
`vitest`, has a `vitest.config.*` or the file imports `vitest`; jest likewise (`jest`, `@jest/globals`, `ts-jest`,
`jest.config.*`). It runs `vitest run` or `jest --ci` in the member directory on the files of the selected tests
(their siblings run too; `--all` runs each member whole that declares its runner by dependency or config, not only by an import) and reads the runner's JSON report. Evidence names every
executed test as its unit (`src/a.test.ts::suite$math::test$adds`, `[dupN]` for a repeated title in a suite;
two `describe` blocks of one title are not told apart; a dynamic title is recorded under its slug and maps to no unit). `node` or
the runner missing is a refusal (`E-EVIDENCE-RUNNER-MISSING`), never a skip, and the runner must be listed in
`[evidence] allowed_tools` (vitest and jest are by default). A member with neither runner evident (playwright,
`node:test`) selects nothing and is logged. Tests that run real node tooling skip with a named message when
`node` is absent unless `FROB_REQUIRE_NODE_TESTS` is set.

## CSS

The adapter (F2, `.css`, tree-sitter css grammar) lowers a stylesheet to the `gob_ir::style` forms: a rule set is
`unit(style-rule)` named by its selector text, an at-rule (`@media`, `@supports`, `@layer`, `@keyframes`,
`@font-face`, `@import`, ...) is `unit(at-rule)` named without the `@` with its prelude text, a keyframe block is a
style rule named by its selector, a declaration is the `style.declaration` operator (property, raw value text,
`important`, component values as children, the declaration's byte span), and `--x: value` is
`unit(custom-property)`. A declaration's selector and at-rule chain is its ancestor chain. Symrefs nest the same way
(`site.css::media.[.card,_.tile].--gap`: whitespace becomes `_`, a name with a dot is bracketed, repeats get `[dupN]`). A `var(--x)` is a
`ref`; the scope graph holds every custom property of the file at May in one cascade scope, so a use with
several definitions resolves to a May set and a use with none has no definition edge (D100).

A syntax error is a `hole(parse-error)`: the file is a partial parse and other files are unaffected.
`crunk:waive` comments are bound by the directive scanner. Component values are tokenised by
`css/tokens.rs`, shared with the TypeScript inline-style lowering. Not modelled: SCSS and Less (variables and
mixins are `phase` per D96), `@import` resolution, selector structure.

## C# symbols

The C# adapter (F1) reads units as `path::Ns.Type.member`: a namespace is one unit per dotted
component (a file-scoped `namespace A;` owns the rest of the file), types are class, struct,
interface, record, enum and delegate units, enum members are variants, and members are methods,
constructors (named like the type, `$cctor` for a static one), finalizers (`~T`), properties,
indexers (`this`), events, fields and constants (one unit per declarator, spanning the whole
declaration), operators (`operator+`, `operator-implicit[Type]`) and local functions nested in the
member that declares them. Overloads and explicit interface implementations are told apart by
the `[dupN]` mark and the `implements` text, as in Rust. Accessibility follows the keywords
(`internal` and `private protected` read as crate-private) with the language defaults.

- Attributes are kept on the unit with their type name, argument text and target
  (`[field: SerializeField]`) for later vocabulary matching (`SymbolGraph::extras`, `facts`).
  A change to an attribute changes the unit's `attr` and `sig` digests.
- Base types (`: MonoBehaviour, IFoo`) are facts on the type unit.
- Preprocessor: every `#if`, `#elif` and `#else` branch is scanned and each unit under a branch
  carries its condition stack (`UNITY_EDITOR`; `!(UNITY_EDITOR)` in the `#else`), so editor-only
  code is neither dead in player builds nor the reverse. The branch of a duplicated declaration
  gets the `[dupN]` mark. No condition is evaluated.
- A `partial` type is one unit per part in a file; the graph merges the parts, by namespace-qualified
  name across the repository (until the project model maps files to assemblies), into the first part
  in path order: its `facts.spans` list every part, attributes and base types are the union, the digests
  cover all parts and members of later parts are re-parented onto the merged unit.
- Not modelled, reported as a partial parse (Unresolved for symbol rules): top-level statements,
  a conditional inside a member body or around an attribute list or other part of a declaration
  header (the enclosing member's digests are unknown), unrecognized member kinds, syntax errors,
  and declarations below the depth cap. `using` imports, references and calls are tokens only.

## Test selection

`frob test` reports changed files without an adapter in
`touched.unresolved_files` and as a warning (an Unresolved `TEST001`
finding): selection is undecided for them instead of ignoring them.

## The report

`frob check --timing --text` lists, per language (`opaque` for adapter-less
files): files, files examined, partial parses, files NotApplicable per rule
family and Unresolved counts per rule, under `fidelity`.

## C# comments

`gob_languages::comment_spans` is the one owner of C# comment discovery: `//`, `///` XML doc
lines and `/* */` (including `/** */`) blocks. Regular, verbatim (`@"..."`), interpolated
(`$"..."`, holes included) and raw (`"""..."""`) string literals and character literals never
yield comments, with or without a syntax tree (the text fallback lexes them too). Preprocessor
lines (`#if`, `#region`) are not comments and do not disturb scanning; a trailing `//` on one is
a comment. A file that parses with syntax errors still yields its partial tree (`has_errors`).
Directives (`frob:...`) and TODO001 therefore read the same spans in C# as in Rust.
