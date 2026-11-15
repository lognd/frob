//! Collecting the Tailwind facts the TW rules judge: the project's theme and the CSS its own
//! Tailwind compiles each scanned utility to, through the node runtime (`crunk-tailwind`).
//!
//! Nothing here is guessed. Without node or an install the facts carry the runtime's verdict and the
//! rules report every utility Unresolved; the theme falls back to the static readers.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use std::collections::BTreeSet;
use std::path::Path;

use crunk_ingest::ProjectStyles;
use crunk_ingest::tailwind::{Engine, ingest_tailwind, runtime_sources};
use crunk_rules::tailwind::TailwindFacts;
use crunk_spec::DesignSpec;
use crunk_spec::table::TailwindEngine;
use crunk_tailwind::runtime::{DoctorReport, Evaluation, Options, Runtime, Sources};
use gob_cache::Cache;

/// The Tailwind facts of the project: the theme (node-resolved, else static) and the compiled
/// utilities of every class the ingest scanned, with the reason when Tailwind could not answer.
///
/// Static mode (`static_flag`, or `[tailwind] engine = "static"`) never spawns node, so no
/// repository JavaScript runs; every utility is then Unresolved.
// frob:ticket 01M7AV37ZMX53C3NNTGFA8TB2V
pub fn collect(
    spec: &DesignSpec,
    styles: &ProjectStyles,
    state_dir: &str,
    static_flag: bool,
) -> TailwindFacts {
    let static_mode = static_flag || spec.tailwind.engine == TailwindEngine::Static;
    tracing::info!(static_mode, static_flag, "tailwind facts: engine chosen");
    let runtime = Runtime::new(
        &spec.root,
        Options {
            static_mode,
            ..Options::default()
        },
        Cache::open_shared(&spec.root, state_dir),
    );
    let engine = if static_mode {
        Engine::Static
    } else {
        Engine::Node(&runtime)
    };
    let theme = ingest_tailwind(spec, engine);
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

/// The Tailwind runtime presence table for the project at `root` (what `crunk doctor` prints).
///
/// A project without a loadable `crunk.toml` is probed with no sources, so node and the project's
/// tailwindcss are still reported. The probe never evaluates utilities.
// frob:ticket 01M4DVX1K76X876W0YPB5EX3F9
pub fn doctor(root: &Path) -> DoctorReport {
    let sources = match crunk_spec::load_spec(root) {
        Ok(spec) => runtime_sources(&spec),
        Err(err) => {
            tracing::debug!(%err, "tailwind doctor: no usable spec; probing without sources");
            Sources::default()
        }
    };
    let state_dir = format!(".{}", crate::PRODUCT);
    let runtime = Runtime::new(
        root,
        Options::default(),
        Cache::open_shared(root, &state_dir),
    );
    let report = runtime.doctor(&sources);
    tracing::info!(
        rows = report.rows.len(),
        issues = report.issues.len(),
        "tailwind doctor finished"
    );
    report
}
