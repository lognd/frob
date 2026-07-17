# frob.graph -- obligation graph engine

One sentence: a persistent registry of every symbol's identity and digests,
plus typed edges declared in comments, so that any change to code, docs, or
contracts is detectable statically -- a type checker for obligations.

Built on `frob.lang` (tree-sitter): uniform symbol and comment extraction
for Python, TypeScript, Rust, C, and C++.

## Symbol references

Canonical form everywhere: `path::Qualified.Name`, e.g.
`src/frob/graph/store.py::GraphStore.load`. Paths are repo-root-relative,
POSIX separators. A bare `path` refers to the whole file.

## Public API

<!-- frob:describes src/frob/lang/__init__.py::parse_file -->
<!-- frob:describes src/frob/lang/__init__.py::supported_languages -->
<!-- frob:describes src/frob/graph/__init__.py::build_graph -->
<!-- frob:describes src/frob/graph/__init__.py::load_graph -->
<!-- frob:describes src/frob/graph/__init__.py::resolve -->
<!-- frob:describes src/frob/graph/__init__.py::edges_from -->
<!-- frob:describes src/frob/graph/__init__.py::edges_to -->
<!-- frob:describes src/frob/graph/lock.py::load_lock -->
<!-- frob:describes src/frob/graph/lock.py::acknowledge -->
<!-- frob:describes src/frob/graph/lock.py::drift -->
<!-- frob:describes src/frob/graph/lock.py::write_lock -->

```python
# frob/lang/__init__.py
def parse_file(path: Path) -> Result[ParsedFile, LangError]
    # WHY: single entry point; language dispatch is internal (by extension).
def supported_languages() -> frozenset[str]

# frob/graph/__init__.py
def build_graph(root: Path, cache: Path) -> Result[GraphSnapshot, BuildError]
    # BuildError = GraphError | LangError. Incremental: re-parses only files
    # whose content hash changed in cache (per-file granularity, sqlite-backed).
    # Also walks docs/**/*.md for frob:describes anchors. GraphSnapshot.stats
    # (a BuildStats) reports parsed vs cache_hits for this call.
    # `frob.toml`'s `[graph] exclude = ["glob", ...]` (fnmatch, root-relative
    # POSIX paths) is additive to the built-in dir excludes (.git, .venv,
    # node_modules, target, build, dist, __pycache__, .frob); missing table
    # is `()`. Used by frob's own frob.toml to exclude tests/fixtures/**
    # so fixture symbols never create gate obligations.
def load_graph(cache: Path) -> Result[GraphSnapshot, GraphError]
    # Cache-only load for read paths; Err(CacheStale) if any on-disk file hash
    # moved since the cache was built, Err(CacheCorrupt) if the cache is
    # unreadable or has never been built (including a missing cache file).
def resolve(snapshot: GraphSnapshot, ref: str) -> Result[SymbolRecord, GraphError]
def edges_from(snapshot: GraphSnapshot, ref: str) -> tuple[Edge, ...]
def edges_to(snapshot: GraphSnapshot, target: str) -> tuple[Edge, ...]

# frob/graph/lock.py
def load_lock(path: Path) -> Result[LockFile, LockError]
    # A missing frob.lock is Ok(LockFile()) (empty), not an error -- first ack
    # creates the file. Only malformed JSON/schema is Err(Malformed).
def acknowledge(lock: LockFile, snapshot: GraphSnapshot,
                refs: Sequence[str]) -> Result[LockFile, LockError]
    # Records current digests for refs; each ref must be an edge endpoint AND
    # resolve to a symbol (else Err(UnknownRef)). Facet is looked up from any
    # DESCRIBES edge targeting the ref (attrs["facet"]), default "sig".
def drift(lock: LockFile, snapshot: GraphSnapshot) -> DriftReport
    # Pure comparison; never fails. Dangling edges and stale acks.
def write_lock(lock: LockFile, path: Path) -> Result[Unit, LockError]
    # Atomic (temp + os.replace). Deterministic: entries sorted by (ref,
    # facet), indent=2, trailing newline.
```

## Comment DSL

<!-- frob:describes src/frob/graph/dsl.py::parse_directives -->
<!-- frob:describes src/frob/graph/dsl.py::markdown_anchors -->

- `parse_directives` -- extracts every `frob:` directive comment in a
  parsed file into typed `Edge`s (or `MalformedDirective`s when a line
  fails to parse).
- `markdown_anchors` -- extracts `<!-- frob:describes ... -->` anchors
  from a markdown doc, binding each to the nearest preceding heading slug.

Directives live in ordinary comments in any supported language (`#`, `//`,
`/* */`). Grammar: `frob:<verb> <target> [key="value" ...]`. One directive
per comment line. A directive binds to the innermost enclosing symbol (or
the symbol immediately following it, for preceding-line comments).

| Directive | Meaning (edge created) |
|---|---|
| `frob:doc docs/modules/graph.md#lock` | enclosing symbol is described by that doc anchor |
| `frob:uses-contract <symref>` | enclosing symbol depends on target's signature semantics; target sig change flags this symbol |
| `frob:invariant INV-007` | enclosing symbol is an anchor for that invariant |
| `frob:ticket T-0042` | enclosing symbol (or hunk) satisfies that ticket |
| `frob:todo T-0043 [note]` | deferred work bound to an open ticket |
| `frob:waive RULE-ID reason="..."` | suppress one gate rule here; reason required |
| `frob:tests <symref>` | enclosing test function unit-tests that symbol |
| `frob:tests <pkg-path> kind="integration"` | enclosing test exercises that package's public boundary with real collaborators |
| `frob:tests <system-id> kind="e2e"` | enclosing test drives that declared system end to end |
| `frob:decision AD-###` | enclosing symbol implements that decision record (see docs/modules/decisions.md) |

Markdown side (doc anchors), in HTML comments; applies from the comment to
the next heading of equal or higher level:

```markdown
<!-- frob:describes src/frob/graph/lock.py::acknowledge -->
<!-- frob:describes src/frob/graph/_models.py::LockFile sig -->
```

The optional trailing facet (`sig` | `body` | `doc`) selects which digest the
ack tracks; default is `sig` (docs usually describe contracts, and body-only
changes should not invalidate them).

Targets are stored as opaque strings. Graph does not validate that a ticket
or doc anchor exists -- that join is `frob.gates`' job (prevents a
graph -> tickets dependency cycle).

## Digests

Three per symbol, all sha256 over a normalized rendering of the tree-sitter
subtree (whitespace- and formatting-insensitive):

- `sig`: name, parameters, types, return type, visibility, decorators.
- `body`: implementation subtree, comments and docstrings stripped.
- `doc`: the symbol's own docstring/doc-comment, whitespace-collapsed.

<!-- frob:describes src/frob/graph/digest.py::digest_sig -->
<!-- frob:describes src/frob/graph/digest.py::digest_body -->
<!-- frob:describes src/frob/graph/digest.py::digest_doc -->
<!-- frob:describes src/frob/graph/digest.py::compute_digests -->

- `digest_sig` -- the `sig` facet's hash: hashes a symbol's normalized
  signature token stream.
- `digest_body` -- the `body` facet's hash: hashes a symbol's normalized
  implementation token stream (empty for class/const/type).
- `digest_doc` -- the `doc` facet's hash: hashes a symbol's collapsed
  docstring text.
- `compute_digests` -- convenience wrapper computing all three facets for
  one symbol in a single `Digests` value.

## Data models

All pydantic `BaseModel`, `frozen=True`.

<!-- frob:describes src/frob/graph/_models.py::SymbolId -->
<!-- frob:describes src/frob/graph/_models.py::Digests -->
<!-- frob:describes src/frob/graph/_models.py::SymbolRecord -->
<!-- frob:describes src/frob/graph/_models.py::SymbolRecord.symref -->
<!-- frob:describes src/frob/graph/_models.py::EdgeKind -->
<!-- frob:describes src/frob/graph/_models.py::Edge -->
<!-- frob:describes src/frob/graph/_models.py::MalformedDirective -->
<!-- frob:describes src/frob/graph/_models.py::BuildStats -->
<!-- frob:describes src/frob/graph/_models.py::GraphSnapshot -->
<!-- frob:describes src/frob/graph/_models.py::LockEntry -->
<!-- frob:describes src/frob/graph/_models.py::LockFile -->
<!-- frob:describes src/frob/graph/_models.py::StaleItem -->
<!-- frob:describes src/frob/graph/_models.py::DanglingEdge -->
<!-- frob:describes src/frob/graph/_models.py::DriftReport -->

- `SymbolId` -- a symbol's identity: repo-relative path plus dotted
  qualname, rendered as the canonical `path::qualname` symref.
- `Digests` -- the three independent sha256 digests (`sig`/`body`/`doc`)
  tracked per symbol.
- `SymbolRecord` -- one resolvable symbol: identity, kind, publicness,
  digests, and source span.
- `SymbolRecord.symref` -- the canonical `path::qualname` string key a
  record is stored under in `GraphSnapshot.symbols`.
- `EdgeKind` -- the closed set of typed relationships a `frob:` directive
  or doc anchor can declare (doc, uses-contract, invariant, ticket, todo,
  waive, describes, tests, decision).
- `Edge` -- one directive/anchor's declared obligation between a src
  symbol/doc anchor and an opaque target.
- `MalformedDirective` -- a `frob:` comment line that failed to parse,
  kept as data so nothing is silently dropped.
- `BuildStats` -- per-`build_graph` counters (parsed vs cache-hit files)
  proving incrementality to callers and tests.
- `GraphSnapshot` -- the whole obligation graph at one point in time:
  symbols, edges, malformed directives, and file hashes.
- `LockEntry` -- one acknowledged `(ref, facet)` pair and the digest it
  was acked at.
- `LockFile` -- the full `frob.lock` document: a version tag plus sorted
  entries.
- `StaleItem` -- a locked entry whose current digest no longer matches
  the ack (drift).
- `DanglingEdge` -- an edge whose endpoint no longer resolves in the
  current snapshot, with rename candidates.
- `DriftReport` -- the pure comparison result between a `LockFile` and a
  `GraphSnapshot`: stale acks plus dangling edges.

```python
class SymbolId(BaseModel):      # path + qualname; renders as "path::qualname"
    path: str
    qualname: str

class Digests(BaseModel):
    sig: str
    body: str
    doc: str

class SymbolRecord(BaseModel):
    id: SymbolId
    kind: SymbolKind            # enum: function, method, class, const, type
    public: bool
    digests: Digests
    span: tuple[int, int]       # 1-based start/end lines

class EdgeKind(StrEnum):
    DOC = "doc"; USES_CONTRACT = "uses-contract"; INVARIANT = "invariant"
    TICKET = "ticket"; TODO = "todo"; WAIVE = "waive"; DESCRIBES = "describes"
    TESTS = "tests"             # attrs["kind"]: unit (default) | integration | e2e

class Edge(BaseModel):
    src: str                    # symref or doc anchor ("docs/x.md#h")
    kind: EdgeKind
    target: str                 # opaque: symref, ticket id, rule id, anchor
    origin: str                 # "file:line" of the directive
    attrs: Mapping[str, str]    # reason=..., facet=...

class BuildStats(BaseModel):            # per-build_graph() counters
    parsed: int                          # files re-parsed this call
    cache_hits: int                      # files loaded from cache unchanged

class MalformedDirective(BaseModel):    # a frob: comment line that failed to parse
    file: str
    line: int
    reason: str

class GraphSnapshot(BaseModel):
    root: str
    symbols: Mapping[str, SymbolRecord]   # keyed by symref
    edges: tuple[Edge, ...]
    malformed: tuple[MalformedDirective, ...]  # never silently dropped
    file_hashes: Mapping[str, str]        # incremental rebuild support
    stats: BuildStats                     # parsed/cache_hits for this build_graph() call

class LockEntry(BaseModel):
    ref: str
    facet: str                  # "sig" | "body" | "doc"
    digest: str

class LockFile(BaseModel):
    version: int
    entries: tuple[LockEntry, ...]

class StaleItem(BaseModel):     # digest moved since last ack
    entry: LockEntry
    current: str
    dependents: tuple[str, ...]  # edges whose validity this breaks

class DanglingEdge(BaseModel):  # endpoint no longer resolves
    edge: Edge
    candidates: tuple[str, ...]  # rename suggestions via body-digest match

class DriftReport(BaseModel):
    stale: tuple[StaleItem, ...]
    dangling: tuple[DanglingEdge, ...]

class ParsedFile(BaseModel):    # frob.lang output
    path: str
    language: str
    symbols: tuple[RawSymbol, ...]
    comments: tuple[RawComment, ...]
    content_hash: str
```

## Error types

<!-- frob:describes src/frob/graph/__init__.py::GraphError -->
<!-- frob:describes src/frob/graph/lock.py::LockError -->

- `GraphError` -- failure values graph read paths (`load_graph`,
  `resolve`, `edges_from`/`edges_to`) can return; never a bare exception.
- `LockError` -- failure values `frob.lock` read/write paths (`load_lock`,
  `acknowledge`, `write_lock`) can return.

```python
class LangError(ErrorSet):
    UnsupportedLanguage = "File extension has no registered grammar"
    ParseFailed         = "tree-sitter could not produce a usable tree"
    IoFailed            = "File could not be read"

class GraphError(ErrorSet):
    CacheCorrupt    = "Cache file unreadable; delete .frob/cache.db to rebuild"
    CacheStale      = "Cache does not match working tree; run build_graph"
    UnknownSymbol   = "Symbol reference does not resolve"
    AmbiguousSymbol = "Reference matches more than one symbol"
# plus LangError via composition: BuildError = GraphError | LangError

class LockError(ErrorSet):
    Malformed    = "frob.lock could not be parsed"
    UnknownRef   = "Acknowledged ref is not an edge endpoint in the graph"
    WriteFailed  = "Atomic write of frob.lock failed"
```

## Cache

The SQLite-backed snapshot cache at `.frob/cache.db` (`frob/graph/cache.py`).
Everything stored here is derived and rebuildable from the tracked source
tree -- safe to delete at any time (see Design decisions below).

<!-- frob:describes src/frob/graph/cache.py::connect -->
<!-- frob:describes src/frob/graph/cache.py::set_root -->
<!-- frob:describes src/frob/graph/cache.py::get_root -->
<!-- frob:describes src/frob/graph/cache.py::get_file_hash -->
<!-- frob:describes src/frob/graph/cache.py::store_file_data -->
<!-- frob:describes src/frob/graph/cache.py::load_file_data -->
<!-- frob:describes src/frob/graph/cache.py::load_all -->

```python
def connect(path: Path) -> sqlite3.Connection
    # Opens (creating parent dirs) the cache db; wipes and rebuilds on
    # schema mismatch or on a file that isn't a readable sqlite db at all
    # (T-0019/T-0029) -- the cache is derived state, so delete-and-recreate
    # is the honest recovery.
def set_root(conn: sqlite3.Connection, root: str) -> None
    # Records the snapshot's repo root for a later load_graph.
def get_root(conn: sqlite3.Connection) -> str | None
    # The stored repo root, or None if nothing was ever saved.
def get_file_hash(conn: sqlite3.Connection, file_path: str) -> str | None
    # The cached content hash for one file, or None if never stored --
    # the check build_graph uses to decide whether to re-parse a file.
def store_file_data(conn, *, file_path, content_hash, symbols, edges,
                    malformed) -> None
    # Replaces every row derived from one file (delete-then-insert, one
    # commit) -- the write side of per-file incrementality.
def load_file_data(conn: sqlite3.Connection, file_path: str) -> tuple[...]
    # Reads back everything previously stored for one file -- a cache hit.
def load_all(conn: sqlite3.Connection, *, stats=None) -> GraphSnapshot
    # Reassembles the full GraphSnapshot from every row currently in the db.
```

## Design decisions

- **Lock covers edge endpoints only, not every symbol.** Locking everything
  would churn `frob.lock` on every commit and drown review signal. Coverage
  of unlinked symbols is enforced separately by the coverage gate.
- **Three digests, facet-selectable acks.** A body-only refactor must not
  invalidate contract docs; a signature change must. Alternative (single
  digest) rejected: it makes every ack a rubber stamp.
- **Renames re-link on failure.** Dangling edge -> gate failure listing
  body-digest-matched candidates. Stable IDs in comments rejected as noise.
- **Cache is SQLite in `.frob/cache.db`, always derived.** Fast incremental
  lookups; safe to delete at any time. Tracked-text source of truth.
- **DSL is line-oriented, no expressions.** Grep-able, trivially parseable
  in any language's comments; a real embedded language rejected for alpha.
- **tree-sitter via `tree-sitter-language-pack`.** One dependency for all
  five grammars; hand-rolled parsers rejected (that lesson is the existing
  Python-only `frob.ast`).

## Implementation notes (Phase 2)

- **Source-extension table duplicated from `frob.lang`.** `frob.lang` exposes
  only `supported_languages()` (a label set), not its extension-dispatch
  table, so `frob.graph` walks the tree with its own small, documented copy
  (`.py .ts .tsx .rs .c .h .cpp .hpp .cc .hh`). Adding an extension-listing
  API to `frob.lang` for this one caller was judged out of scope.
- **`ParsedFile.path` is corrected to repo-root-relative.** `frob.lang`
  renders `ParsedFile.path` cwd-relative (or absolute if outside cwd) --
  `frob.graph` always calls with an absolute path and rewrites `.path` to the
  root-relative form before computing symrefs or directive edges, so a
  symref never depends on the caller's working directory.
- **A per-file parse failure does not fail the whole build.** `build_graph`
  logs and skips a file that fails `parse_file` (unsupported extension,
  unreadable, unparseable); the `BuildError = GraphError | LangError` return
  type exists for future callers that need to surface a hard failure (e.g. a
  missing `root`), not for routine per-file skips.
- **Cache deletions are pruned.** Any file present in the cache but no
  longer seen during a `build_graph` walk (deleted or renamed) has its rows
  removed, so `GraphSnapshot` never carries stale symbols/edges for a file
  that no longer exists.

## Dependencies

- `frob.lang` -- ParsedFile (symbols + comments) per source file.
- `tree-sitter`, `tree-sitter-language-pack` -- grammars (new deps).
- `pydantic`, `typani` -- models and Results.
- stdlib `sqlite3`, `hashlib`.

## Integration points

- `frob.gates` consumes `GraphSnapshot`, `DriftReport`, and joins edge
  targets against tickets/docs/invariants.
- CLI: `frob graph build|query|why`, `frob ack <ref...> [--facet]` runners
  under `frob/app/`.
- `frob check` triggers `build_graph` (incremental) at the start of a run.
