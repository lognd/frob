//! A11Y104: a client route that renders without setting the document title or moving focus or
//! announcing the change (WCAG 2.4.2 and the client-routing guidance). Opt-in through
//! `[packs] crunk_web = true`; the routes come from `gob-frameworks` and the judgement from
//! [`gob_frameworks::route_gaps`], so this module only wires the result into findings.

// frob:ticket 01M4D95TNEY7MCTS3A4F9HC26C

use gob_check::{RepoGroup, Snapshot};
use gob_frameworks::{Repo, RouteGap, analyze, route_gaps};
use gob_rules::{Finding, Rule, Severity};
use gob_symbols::{SymbolGraph, extract_file};
use gob_text::{FileInterner, Span, TextRange, TextSize};
use tracing::debug;

use crate::Crunk;

/// A page route changes the screen without a document title and a focus move or announcement.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "A11Y104",
    slug = "route-change-announced",
    family = "A11Y",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct A11y104;

/// Whether `path` is a script or package manifest the route analysis reads.
fn is_script(path: &str) -> bool {
    let ext = path.rsplit('.').next().unwrap_or_default();
    path.ends_with("package.json")
        || matches!(
            ext,
            "ts" | "tsx" | "js" | "jsx" | "mjs" | "cjs" | "mts" | "cts"
        )
}

/// Bytes that change when any file the route analysis reads changes; empty when the pack is off.
pub fn fingerprint(snap: &Snapshot<Crunk>) -> Vec<u8> {
    if !snap.inputs.spec.as_ref().is_some_and(|s| s.packs.crunk_web) {
        return Vec::new();
    }
    let mut hasher = blake3::Hasher::new();
    for e in snap.core.entries.iter().filter(|e| is_script(&e.path)) {
        hasher.update(e.path.as_bytes());
        hasher.update(e.digest.as_bytes());
    }
    hasher.finalize().as_bytes().to_vec()
}

/// The module graph of the walked source files, read through the snapshot.
fn graph_of(snap: &Snapshot<Crunk>) -> SymbolGraph {
    let symbols = snap
        .core
        .entries
        .iter()
        .filter(|e| is_script(&e.path))
        .filter_map(|e| snap.core.text(&e.path).ok().map(|t| extract_file(e, &t)))
        .collect();
    SymbolGraph::from_files(symbols)
}

/// The gaps of every page route of the project.
fn gaps_of(snap: &Snapshot<Crunk>) -> Vec<RouteGap> {
    let graph = graph_of(snap);
    let analysis = analyze(&snap.core.root, &snap.core.entries, &graph);
    let repo = Repo::load(&snap.core.root, &snap.core.entries, &graph);
    route_gaps(&repo, &analysis.routes)
}

/// What a gap lacks, in words.
fn lacking(gap: &RouteGap) -> &'static str {
    match (gap.missing_title, gap.missing_focus) {
        (true, true) => "sets no document title and moves no focus or announcement",
        (true, false) => "sets no document title",
        _ => "moves no focus and makes no announcement",
    }
}

/// The byte offset where one-based `line` of `text` starts.
fn line_start(text: &str, line: u32) -> u32 {
    let skip = usize::try_from(line.saturating_sub(1)).unwrap_or(0);
    let offset: usize = text.split_inclusive('\n').take(skip).map(str::len).sum();
    u32::try_from(offset).unwrap_or(0)
}

/// The finding of one gap, anchored at the route's declaration.
fn to_finding(snap: &Snapshot<Crunk>, files: &mut FileInterner, gap: &RouteGap) -> Option<Finding> {
    let id = A11y104.meta().rule_id().ok()?;
    let text = snap.core.text(&gap.file).unwrap_or_default();
    let at = TextSize::from(line_start(&text, gap.line));
    let span = Span::new(
        files.intern(&gap.file),
        TextRange::at(at, TextSize::from(0)),
    );
    let route = gap.pattern.as_deref().unwrap_or("(dynamic)");
    let message = format!(
        "route `{route}` {}; a client route change is silent to assistive technology",
        lacking(gap)
    );
    debug!(route, file = %gap.file, line = gap.line, "A11Y104 fires");
    Some(Finding::new(
        id,
        Severity::Error,
        Some(span),
        message,
        &gap.file,
    ))
}

/// The repo group that emits A11Y104.
pub fn group() -> RepoGroup<Crunk> {
    RepoGroup::new(
        "repo:a11y-route",
        vec![A11y104.meta()],
        |snap: &Snapshot<Crunk>, files: &mut FileInterner| {
            let on = snap.inputs.spec.as_ref().is_some_and(|s| s.packs.crunk_web);
            if !on {
                return Vec::new();
            }
            let found = gaps_of(snap);
            debug!(gaps = found.len(), "A11Y104 route gaps");
            found
                .iter()
                .filter_map(|g| to_finding(snap, files, g))
                .collect()
        },
    )
}
