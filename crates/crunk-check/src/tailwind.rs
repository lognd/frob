//! Collecting the Tailwind facts the TW rules judge: the project's theme and the CSS its own
//! Tailwind compiles each scanned utility to, through the node runtime (`crunk-tailwind`).
//!
//! Nothing here is guessed. Without node or an install the facts carry the runtime's verdict and the
//! rules report every utility Unresolved; the theme falls back to the static readers.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use std::collections::BTreeSet;

use crunk_ingest::ProjectStyles;
use crunk_ingest::tailwind::{Engine, ingest_tailwind, runtime_sources};
use crunk_rules::tailwind::TailwindFacts;
use crunk_spec::DesignSpec;
use crunk_tailwind::runtime::{Evaluation, Options, Runtime};
use gob_cache::Cache;

/// The Tailwind facts of the project: the theme (node-resolved, else static) and the compiled
/// utilities of every class the ingest scanned, with the reason when Tailwind could not answer.
pub fn collect(spec: &DesignSpec, styles: &ProjectStyles, state_dir: &str) -> TailwindFacts {
    let runtime = Runtime::new(
        &spec.root,
        Options::default(),
        Cache::open_shared(&spec.root, state_dir),
    );
    let theme = ingest_tailwind(spec, Engine::Node(&runtime));
    let candidates: Vec<String> = styles
        .sheets
        .iter()
        .flat_map(|sheet| sheet.utilities.iter().map(|u| u.name.clone()))
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let (results, unresolved) = if candidates.is_empty() {
        (Vec::new(), None)
    } else {
        match runtime.evaluate_candidates(&candidates, &runtime_sources(spec)) {
            Ok(Evaluation::Resolved(run)) => (run.results, None),
            Ok(Evaluation::Unresolved(why)) => {
                tracing::info!(%why, "tailwind facts: the runtime did not run");
                (Vec::new(), Some(format!("{}: {why}", why.code())))
            }
            Err(err) => {
                tracing::warn!(%err, "tailwind facts: the runtime failed");
                (Vec::new(), Some(format!("tailwind runtime failed: {err}")))
            }
        }
    };
    tracing::info!(
        utilities = candidates.len(),
        resolved = results.len(),
        theme = theme.entries.len(),
        "tailwind facts collected"
    );
    TailwindFacts::new(spec, theme.entries, results, unresolved)
}
