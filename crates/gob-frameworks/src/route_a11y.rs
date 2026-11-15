//! Routes that change the page without telling the user: no document title and no focus move or
//! announcement (the crunk-web A11Y route rule, WCAG 2.4.2 and the client-routing guidance of W3C).
//!
//! The judgement is lexical over the route's page component file and its layouts' files:
//! a title is set when any of them mentions a title API, and the change is announced when any of them
//! moves focus or writes a live region. Next.js announces a route change itself, so only its title is
//! required. A route none of whose sources could be read is left out, never guessed.

// frob:ticket 01M4D95TNEY7MCTS3A4F9HC26C

use tracing::{debug, trace};

use crate::repo::Repo;
use crate::types::Route;

/// Source text that sets the document title (a title element, a head manager, a metadata export).
const TITLE_SIGNALS: [&str; 11] = [
    "document.title",
    "<title",
    "<Helmet",
    "<Head",
    "useDocumentTitle",
    "useTitle(",
    "generateMetadata",
    "export const metadata",
    "export const meta",
    "export function meta",
    "export async function meta",
];

/// Source text that moves focus to the new page or announces it to assistive technology.
const FOCUS_SIGNALS: [&str; 10] = [
    ".focus(",
    "autoFocus",
    "aria-live",
    "role=\"status\"",
    "role=\"alert\"",
    "role='status'",
    "role='alert'",
    "useAnnounce",
    "announce(",
    "RouteAnnouncer",
];

/// The framework that announces its own route changes, so a focus signal is not required of its routes.
const SELF_ANNOUNCING: &str = "nextjs";

/// One route that changes the page silently.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct RouteGap {
    /// The registry name of the framework that declares the route.
    pub framework: &'static str,
    /// The path pattern, or `None` when it is not statically known.
    pub pattern: Option<String>,
    /// Repo-relative path of the file that declares the route.
    pub file: String,
    /// One-based line of the declaration.
    pub line: u32,
    /// True when no source of the route sets a document title.
    pub missing_title: bool,
    /// True when no source of the route moves focus or announces the change.
    pub missing_focus: bool,
}

/// The repo-relative file a symref text names: the part before `::`, or the text itself when it is a path.
fn file_of(symref: &str) -> &str {
    symref.split_once("::").map_or(symref, |(file, _)| file)
}

/// The files whose text decides a route: its component and its layouts. The declaring file is left out
/// because a route table is shared by every route and would excuse them all.
fn sources_of(route: &Route) -> Vec<&str> {
    let mut files: Vec<&str> = route.component.iter().map(|c| file_of(c)).collect();
    files.extend(route.layouts.iter().map(|l| file_of(l)));
    files.dedup();
    files
}

/// True when any of `texts` contains any of `signals`.
fn mentions(texts: &[&str], signals: &[&str]) -> bool {
    texts.iter().any(|t| signals.iter().any(|s| t.contains(s)))
}

/// The gap of one page route, or `None` when it is judged fine or cannot be judged.
fn gap_of(repo: &Repo<'_>, route: &Route) -> Option<RouteGap> {
    route.component.as_ref()?;
    let texts: Vec<&str> = sources_of(route)
        .into_iter()
        .filter_map(|f| repo.text(f))
        .collect();
    if texts.is_empty() {
        debug!(file = %route.file, "route a11y: no source readable, route not judged");
        return None;
    }
    let missing_title = !mentions(&texts, &TITLE_SIGNALS);
    let missing_focus = route.framework != SELF_ANNOUNCING && !mentions(&texts, &FOCUS_SIGNALS);
    trace!(file = %route.file, missing_title, missing_focus, "route a11y judged");
    (missing_title || missing_focus).then(|| RouteGap {
        framework: route.framework,
        pattern: route.pattern.clone(),
        file: route.file.clone(),
        line: route.line,
        missing_title,
        missing_focus,
    })
}

/// The page routes of `routes` that neither set the document title nor move focus or announce the change.
///
/// One entry per route, sorted; handler-only routes (API endpoints) are never judged.
pub fn route_gaps(repo: &Repo<'_>, routes: &[Route]) -> Vec<RouteGap> {
    let mut gaps: Vec<RouteGap> = routes.iter().filter_map(|r| gap_of(repo, r)).collect();
    gaps.sort();
    gaps.dedup();
    debug!(
        routes = routes.len(),
        gaps = gaps.len(),
        "route a11y gaps found"
    );
    gaps
}
