//! The inputs every rule and verb reads: graph, directives and lock.

use std::path::Path;

use gob_cache::{ArtifactKey, Cache};
use gob_directives::frob::{Describes, Doc};
use gob_directives::{Binding, Directive, ScanConfig, Scanner};
use gob_languages::{Language, grammar_identity};
use gob_lock::{LockFile, file_name};
use gob_symbols::{
    Digests, EXTRACTOR_VERSION, FacetDigest, SymbolGraph, Symref, build_graph, extract_file,
};
use gob_text::{FileInterner, Span, TextRange, TextSize};
use gob_walk::{ContentReader, ContentSource, FileEntry, Roles, WalkConfig, walk};
use serde::{Deserialize, Serialize};

use crate::error::AckError;

/// The product this crate acks for; names `frob.lock` and `.frob/`.
pub const PRODUCT: &str = "frob";

/// The verb text that makes a file worth scanning (cheap prefilter).
const DOC_MARKER: &str = "frob:";

/// Bump when the scan or its binding output changes for the same input; part of the cache key.
const SCAN_VERSION: u32 = 3;

/// One cached `frob:doc` directive of a file, free of interner ids.
#[derive(Serialize, Deserialize)]
struct Stored {
    start: u32,
    end: u32,
    symbol: Symref,
    target: Symref,
}

/// The cached directives under `key`, or `fresh()` stored there.
fn cached_scan(
    cache: &Cache,
    key: &ArtifactKey,
    fresh: impl FnOnce() -> Vec<Stored>,
) -> Vec<Stored> {
    if let Some(hit) = cache
        .get_artifact(key)
        .and_then(|b| serde_json::from_slice::<Vec<Stored>>(&b).ok())
    {
        return hit;
    }
    let found = fresh();
    if let Ok(bytes) = serde_json::to_vec(&found) {
        cache.put_artifact(key, &bytes);
    }
    found
}

/// Scans one file for well-formed `frob:doc` directives (uncached).
///
/// Offsets are into the git-normalized text, the same text the symbol graph was built from.
fn scan_file(
    reader: &mut ContentReader<'_, '_>,
    entry: &FileEntry,
    lang: Language,
    scanner: &Scanner,
) -> Vec<Stored> {
    let Ok(text) = reader.read_text(&entry.path) else {
        tracing::debug!(path = %entry.path, "unreadable file not scanned for frob:doc");
        return Vec::new();
    };
    if !text.contains(DOC_MARKER) {
        return Vec::new();
    }
    let symbols = extract_file(entry, &text);
    let mut ids = FileInterner::new();
    let file = ids.intern(&entry.path);
    let mut out = Vec::new();
    for d in scanner.scan_in(file, lang, &text, &symbols).directives {
        let Some((symbol, target)) =
            doc_pair(&d.namespace, &d.verb, &d.args, &d.bound, &entry.path)
        else {
            continue;
        };
        out.push(Stored {
            start: u32::from(d.span.range.start()),
            end: u32::from(d.span.range.end()),
            symbol,
            target,
        });
    }
    out
}

/// The (code symbol, doc section) pair of a `frob:doc` or `frob:describes` directive at `path`.
///
/// `frob:doc` binds the annotated symbol to the named section; `frob:describes`
/// sits in a doc and binds the named symbol to the enclosing section (the file
/// when above any heading). Malformed arguments yield `None` (PARSE001 reports them).
// frob:ticket 01M4FD0TNGWDEYHP9FHH0RPXYR
pub fn doc_pair(
    namespace: &str,
    verb: &str,
    args: &gob_directives::ArgList,
    bound: &Binding,
    path: &str,
) -> Option<(Symref, Symref)> {
    if namespace != "frob" {
        return None;
    }
    let here = match bound {
        Binding::Symbol(s) => s.clone(),
        Binding::File => Symref::file(path),
    };
    match verb {
        "doc" => match Doc::parse_args(args) {
            Ok(doc) => Some((here, doc.target.0)),
            Err(_) => {
                tracing::debug!(path, "malformed frob:doc skipped (PARSE001 reports it)");
                None
            }
        },
        "describes" => match Describes::parse_args(args) {
            Ok(d) => Some((d.symbol.0, here)),
            Err(_) => {
                tracing::debug!(
                    path,
                    "malformed frob:describes skipped (PARSE001 reports it)"
                );
                None
            }
        },
        _ => None,
    }
}

/// One `frob:doc` directive: a symbol bound to a markdown section.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocDirective {
    /// Repo-relative file holding the directive.
    pub file: String,
    /// Where the directive text sits.
    pub span: Span,
    /// The symbol it binds to (the file symref for file-level directives).
    pub symbol: Symref,
    /// The `path#slug` section it names.
    pub target: Symref,
}

/// Graph, directives and lock of one repository state.
pub struct Inputs {
    /// The symbol graph.
    pub graph: SymbolGraph,
    /// The current `frob.lock` (empty when absent).
    pub lock: LockFile,
    /// Every well-formed `frob:doc` directive, in file then source order.
    pub docs: Vec<DocDirective>,
    /// Resolves the `FileId`s inside [`DocDirective::span`].
    pub files: FileInterner,
}

/// The digest recorded for a markdown section: blake3 over its sig and body digests.
pub fn section_digest(d: &Digests) -> FacetDigest {
    let mut h = blake3::Hasher::new();
    h.update(d.sig.as_bytes());
    h.update(d.body.as_bytes());
    FacetDigest::from_bytes(*h.finalize().as_bytes())
}

impl Inputs {
    /// Builds the inputs for the repository rooted at `root`.
    ///
    /// The symbol cache lives in `<root>/.frob/`; `.frob/` and `target/` are
    /// never walked.
    ///
    /// # Errors
    ///
    /// [`AckError::Walk`] when the walk fails and [`AckError::Lock`] when
    /// `frob.lock` is malformed.
    pub fn collect(root: &Path) -> Result<Self, AckError> {
        let config = WalkConfig {
            exclude: vec!["/.frob/".to_owned(), "/target/".to_owned()],
            ..WalkConfig::default()
        };
        let walked = walk(root, &config)?;
        let cache = Cache::open(&root.join(".frob"));
        let graph = build_graph(root, &walked.files, &cache);
        let scanner = Scanner::new(&ScanConfig::default());
        let mut files = FileInterner::new();
        let mut docs = Vec::new();
        let roles = Roles::for_root(root);
        let source = ContentSource::locate(root);
        source.with_reader(|reader| {
            for entry in &walked.files {
                // frob:ticket 01M43KP0RXKB1DJA8KGJTV288R
                if !roles.role(&entry.path).scans_directives() {
                    continue;
                }
                let Some(lang) = Language::detect(&entry.path) else {
                    continue;
                };
                let key = ArtifactKey {
                    content_digest: entry.digest.to_string(),
                    producer_identity: format!(
                        "frob-ack/doc/v{SCAN_VERSION}/{EXTRACTOR_VERSION}/{}",
                        grammar_identity(lang)
                    ),
                };
                let found = cached_scan(&cache, &key, || scan_file(reader, entry, lang, &scanner));
                let file = files.intern(&entry.path);
                docs.extend(found.into_iter().map(|s| DocDirective {
                    file: entry.path.clone(),
                    span: Span::new(
                        file,
                        TextRange::new(TextSize::new(s.start), TextSize::new(s.end)),
                    ),
                    symbol: s.symbol,
                    target: s.target,
                }));
            }
        });
        let lock = LockFile::load(&root.join(file_name(PRODUCT)))?;
        tracing::info!(
            symbols = graph.node_count(),
            docs = docs.len(),
            acks = lock.entries.len(),
            "ack inputs collected"
        );
        Ok(Self {
            graph,
            lock,
            docs,
            files,
        })
    }

    /// Digest of everything the rules read: the repo-rule cache key component.
    ///
    /// `SymbolGraph::graph_digest` covers structure and sig digests only, so
    /// the body and doc facets, the directives and the lock are folded in.
    pub fn digest(&self) -> String {
        let mut h = blake3::Hasher::new();
        h.update(self.graph.graph_digest().as_bytes());
        let mut recs: Vec<_> = self.graph.records().collect();
        recs.sort_by(|a, b| a.symref.cmp(&b.symref));
        for r in recs {
            h.update(r.symref.to_string().as_bytes());
            h.update(r.digests.body.as_bytes());
            h.update(r.digests.doc.as_bytes());
            h.update(r.digests.attr.as_bytes());
            h.update(r.digests.contract.as_bytes());
        }
        for d in &self.docs {
            h.update(format!("{}|{}|{}\n", d.file, d.symbol, d.target).as_bytes());
        }
        // The lock's Debug form is deterministic (sorted maps) and covers header, entries and flows.
        h.update(format!("{:?}", self.lock).as_bytes());
        h.finalize().to_hex().to_string()
    }
}
