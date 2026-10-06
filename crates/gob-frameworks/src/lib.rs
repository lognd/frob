//! Framework discovery above the symbol graph: which frameworks a repository uses, per workspace member,
//! and the facts they declare (routes with path pattern, method, handler unit, page component, layout chain
//! and status; entrypoints) (D96, language-engines.md section 4).
//!
//! # Overview
//!
//! - [`FrameworkEntry`] is the open registry (built-ins plus `inventory::submit!`): a name, [`Detector`]s
//!   (`package.json` dependency, config file, directory convention) and a `discover` function.
//! - [`detect`] evaluates the detectors for every `package.json` of the repository, so a framework in
//!   `apps/web` of a monorepo is found even when the root declares none (~5E0V6W3).
//! - [`analyze`] detects, folds the TypeScript sources over the module graph and runs each detected
//!   framework's discovery; the result is sorted and deterministic.
//! - First adapters: react-router (route objects and `<Route>` elements, paths through `const_value`) and
//!   Next.js (`app` and `pages` directories). A route whose path is not statically known is reported with
//!   status `Unknown` and no pattern, never omitted.
//!
//! The syntactic limits are the adapters' own: a Next.js route handler that re-exports its methods is
//! reported as method `ANY` with status `May`, and react-router framework-mode `routes.ts` helpers are not
//! read yet.

mod nextjs;
mod react_router;
mod registry;
mod repo;
mod terms;
mod types;

use std::path::Path;

use gob_symbols::SymbolGraph;
use gob_walk::FileEntry;
use tracing::info;

pub use registry::{Detector, FrameworkEntry, detect, detect_with, frameworks};
pub use repo::Repo;
pub use types::{
    Analysis, Detection, Discovery, Entrypoint, EntrypointKind, Method, Problem, Route, Status,
};

/// Detects the frameworks of every workspace member under `root` and discovers their routes and entrypoints.
///
/// `graph` is the module graph of `files`; sources are read from disk under `root`.
pub fn analyze(root: &Path, files: &[FileEntry], graph: &SymbolGraph) -> Analysis {
    let (detections, mut problems) = detect(root, files);
    if detections.is_empty() {
        return Analysis {
            detections,
            problems,
            ..Analysis::default()
        };
    }
    let repo = Repo::load(root, files, graph);
    problems.extend(repo.problems().iter().cloned());
    let entries = frameworks();
    let mut routes = Vec::new();
    let mut entrypoints = Vec::new();
    for det in &detections {
        let Some(entry) = entries.iter().find(|e| e.name == det.framework) else {
            continue;
        };
        let found = (entry.discover)(&repo, det);
        info!(
            framework = det.framework,
            member = det.member,
            routes = found.routes.len(),
            entrypoints = found.entrypoints.len(),
            "framework discovered"
        );
        routes.extend(found.routes);
        entrypoints.extend(found.entrypoints);
    }
    routes.sort();
    entrypoints.sort();
    entrypoints.dedup();
    problems.sort();
    Analysis {
        detections,
        routes,
        entrypoints,
        problems,
    }
}
