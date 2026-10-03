# Fidelity accounting

`frob check` never skips a file silently. Every walked file is classified per
rule by `gob_check::subject_status_for` (design: `docs/design/universal-model.md`
sections 4.1, 4.2 and 4.6).

| File state | Rule needs a capability (DOC001, DOC002, INV002, COV001) | Rule reads every text artifact (TODO001, REF001, TEST001, INV001, DRIFT*) |
|---|---|---|
| Opaque F0 (no adapter), text, comments scanned (TOML) | NotApplicable | examined |
| Opaque F0, text, not scanned (for example `.py`, `.json`) | NotApplicable | one Unresolved per rule naming the file count |
| Opaque F0, binary (NUL byte or known extension) | NotApplicable | NotApplicable |
| Parse failed | Unresolved | Unresolved |
| Partial parse (holes) | examined, plus an Unresolved for symbol rules | examined |
| Fidelity below the rule's minimum (COV001 and AFFECT001 need F2) | Unresolved | Unresolved |

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

## Test selection

`frob test` reports changed files without an adapter in
`touched.unresolved_files` and as a warning (an Unresolved `TEST001`
finding): selection is undecided for them instead of ignoring them.

## The report

`frob check --timing --text` lists, per language (`opaque` for adapter-less
files): files, files examined, partial parses, files NotApplicable per rule
family and Unresolved counts per rule, under `fidelity`.
