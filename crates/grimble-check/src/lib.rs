//! `grimble check`: grimble's driver over the shared [`gob_check`] pipeline and the
//! `gob.sibling/1` document it prints (design: `grimble-model.md` 9.5 and 9.7,
//! `sibling-contract.md`, decisions D28 and D67).
//!
//! This crate supplies what is grimble-specific as the [`Grimble`] product:
//!
//! - inputs: the `.grmb` model files found by the walk ([`GrimbleInputs`]) and the entities,
//!   exceptions and file status derived from them ([`ModelView`]);
//! - rules: the MDL family through one repo group, SYS001-005 and SYS009-011 through another
//!   (`grimble-bind`, which also fills the document's `bindings`); CAP, CYCLE/LARGE/DEAD, PACK, GPOL, NEAT,
//!   CI and DK register their own groups as their tickets land;
//! - exceptions: `accept`, `defer` and `hotfix` clauses in the model, applied through
//!   `gob-rules` (an `accept` never parks an Unresolved finding, EXC016);
//! - config: `[compute]` and `[packs]` in `grimble.toml` ([`config`]); `[check]` and `[perf]` come
//!   from `gob-check`;
//! - the document: [`sibling_document`].
//!
//! # What the document leaves empty for now
//!
//! | Field | Why | Filled by |
//! |---|---|---|
//! | entity `body_digest`, `doc_digest` | the U facet digests are not yet joined to model entities | G11 |
//! | finding `anchor`, `entity`, `remedy` | `check_model` returns findings without them | a `grimble-model` change |
//! | `fidelity[].not_applicable_rules` | lists only the SYS rules the model gives nothing to (the `grmb` row); no CAP rule exists | the CAP rules |
//! | `packs` | packs are accepted in `grimble.toml` but not loaded (packs.md 3) | G14 |
//!
//! # Boundaries
//!
//! No frob crate is a dependency, direct or transitive (a test enforces it with the manifests),
//! so the grimble binary never links frob (boundaries.md).

// frob:ticket 01M41H9Y7TTWDN6DAQ5C06R6B7
// frob:ticket 01M4FGXVQTN5NJ0JBGWAMVHK82

// A rule crate that is a dependency but not in `product_rules!` is an unused dependency (D107).
#![cfg_attr(not(test), deny(unused_crate_dependencies))]

use gob_diagnostics as _; // unused today; removal tracked in ~MKG678C

pub mod bind_cache;
pub mod config;
pub mod fidelity;
pub mod model_view;
pub mod packs;
mod product;
pub mod product_rules;
pub mod sibling;

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, PoisonError};
use std::time::Instant;

pub use gob_check::{CheckError, CheckReport, FailOn};
pub use model_view::ModelView;
pub use product::{
    Grimble, GrimbleInputs, GrimbleShared, MODEL_EXTENSION, binding_rules, model_rules,
};
pub use sibling::{SCHEMA_VERSION, exceptions_json, sibling_document};

use config::{ComputeTable, GrimbleTable, PRODUCT, PacksTable};
use gob_walk::FileEntry;
use grimble_model::ModelFiles;

/// What a `grimble check` run was asked to do.
#[derive(Debug, Clone, Default)]
pub struct CheckOptions {
    /// Rule families or rule ids to keep; empty keeps everything.
    pub only: Vec<String>,
    /// Overrides `[check] fail_on` of `grimble.toml` when deciding the exit code.
    pub fail_on: Option<FailOn>,
    /// `--base`: echoed in the document; no rule diffs against it yet.
    pub base: Option<String>,
    /// `--ticket-scope`: echoed in the document; no per-file rule exists yet to narrow.
    pub ticket_scope: Option<Vec<String>>,
}

/// Everything one run produced, enough to build the document and the verbs' views.
pub struct GrimbleRun {
    /// Repository root.
    pub root: PathBuf,
    /// The pipeline report.
    pub report: CheckReport,
    /// Entities, exceptions and file status of the model.
    pub view: Arc<ModelView>,
    /// Finding key to the id of the exception that suppressed it.
    pub parks: BTreeMap<String, String>,
    /// Files per language tag seen by the walk.
    pub languages: BTreeMap<String, usize>,
    /// The `[compute]` knobs in force.
    pub compute: ComputeTable,
    /// The product file the knobs came from (`frob` or `grimble`).
    pub compute_source: &'static str,
    /// The `[packs]` table.
    pub packs: PacksTable,
    /// True when `grimble.toml` exists (the document then carries `packs`).
    pub has_config: bool,
    /// The repository packs that loaded, as `(id, version, digest)`, for the document's `packs`.
    pub loaded_packs: Vec<(String, String, String)>,
    /// Echo of `--ticket-scope`.
    pub ticket_scope: Option<Vec<String>>,
    /// Echo of `--base`.
    pub base: Option<String>,
    /// The rows of the binding relation B, as sibling `bindings` items.
    pub bindings: Vec<serde_json::Value>,
    /// True when the binding result came from the cache instead of being rebuilt.
    pub bind_cached: bool,
    /// Rules whose whole scope is `NotApplicable` on this model, with the reason (never findings).
    pub not_applicable: BTreeMap<String, String>,
    /// Wall time of the run in milliseconds.
    pub elapsed_ms: u64,
    /// Non-fatal notes: pipeline warnings plus the packs notice.
    pub warnings: Vec<String>,
}

/// Run `grimble check` for the repository at `root`.
///
/// # Errors
///
/// [`CheckError`] for a bad `grimble.toml` or `frob.toml` table, a failed walk or an unknown
/// `--only` name. Findings are never errors.
pub fn run(root: &Path, opts: &CheckOptions) -> Result<GrimbleRun, CheckError> {
    let started = Instant::now();
    let (compute, compute_source) = ComputeTable::load_for_product(root, PRODUCT)?;
    let packs = PacksTable::load(root)?;
    let product = Grimble::new();
    let run_opts = gob_check::RunOptions {
        only: opts.only.clone(),
        fail_on: opts.fail_on,
        ..gob_check::RunOptions::default()
    };
    let report = gob_check::run(&product, root, &run_opts)?;
    let trace = product
        .trace
        .into_inner()
        .unwrap_or_else(PoisonError::into_inner);
    let loaded_packs: Vec<(String, String, String)> = packs::load(root, &packs)
        .pins
        .into_iter()
        .map(|(id, pin)| (id, pin.version, pin.digest.unwrap_or_default()))
        .collect();
    let mut warnings = report.warnings.clone();
    if packs.requests_packs() {
        warnings.push(config::PACKS_NOT_LOADED.to_owned());
    }
    for (rule, why) in &trace.not_applicable {
        tracing::info!(%rule, %why, "rule is not applicable on this model");
    }
    let elapsed_ms = u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX);
    tracing::info!(
        findings = report.findings.len(),
        suppressed = report.suppressed.len(),
        elapsed_ms,
        "grimble check finished"
    );
    Ok(GrimbleRun {
        root: root.to_path_buf(),
        report,
        view: trace.view.unwrap_or_default(),
        parks: trace.parks,
        languages: trace.languages,
        compute,
        compute_source,
        packs,
        loaded_packs,
        has_config: root.join(format!("{PRODUCT}.toml")).is_file(),
        ticket_scope: opts.ticket_scope.clone(),
        base: opts.base.clone(),
        bindings: trace.bindings,
        bind_cached: trace.bind_cached,
        not_applicable: trace.not_applicable,
        elapsed_ms,
        warnings,
    })
}

/// What a walk of the repository found: its model files and its files per language.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Survey {
    /// Repo-relative paths of every `.grmb` file, sorted.
    pub models: Vec<String>,
    /// Files per language tag (`opaque` for unadapted files, `grmb` for models).
    pub languages: BTreeMap<String, usize>,
}

/// Walk `root` honouring `[check] exclude` and `size_cap`: the one walk of grimble's verbs.
///
/// # Errors
///
/// [`CheckError`] for a bad `grimble.toml` table or a failed walk.
pub fn walk_repo(root: &Path) -> Result<Vec<FileEntry>, CheckError> {
    let table = gob_check::CheckTable::load(root, PRODUCT)?;
    let mut exclude = vec![format!("/.{PRODUCT}/"), "/target/".to_owned()];
    exclude.extend(table.exclude.iter().cloned());
    let walked = gob_walk::walk(
        root,
        &gob_walk::WalkConfig {
            exclude,
            size_cap: table.size_cap,
            ..gob_walk::WalkConfig::default()
        },
    )?;
    Ok(walked.files)
}

/// Read the `.grmb` files among `entries` and declare the `[grimble] models` roots.
pub fn read_models(root: &Path, entries: &[FileEntry], table: &GrimbleTable) -> ModelFiles {
    let mut model = ModelFiles::new();
    let mut walk = Vec::with_capacity(entries.len());
    for e in entries {
        walk.push(e.path.clone());
        if !e.path.ends_with(MODEL_EXTENSION) {
            continue;
        }
        match std::fs::read(root.join(&e.path)) {
            Ok(bytes) => {
                tracing::debug!(path = %e.path, bytes = bytes.len(), "model file read");
                model.files.insert(e.path.clone(), bytes);
            }
            Err(err) => tracing::warn!(path = %e.path, %err, "model file unreadable; skipped"),
        }
    }
    model.walk = Some(walk);
    match PacksTable::load(root) {
        Ok(table) => {
            let loaded = packs::load(root, &table);
            model.packs = loaded.pins;
            model.pack_problems = loaded.problems;
        }
        Err(err) => tracing::warn!(%err, "[packs] unreadable; no pack is loaded"),
    }
    tracing::info!(roots = ?table.models, files = model.files.len(), "model roots declared");
    model.with_declared_roots(table.models.clone())
}

/// Build the binding relation over `entries` with the `[grimble]` knobs in force.
///
/// The one bind step of `grimble check` (through the product's collection) and `grimble ack`.
pub fn bind_models(
    root: &Path,
    entries: &[FileEntry],
    model: &ModelFiles,
    table: &GrimbleTable,
) -> grimble_bind::Binding {
    let ledger_dir = config::ledger_dir(root);
    grimble_bind::bind(&grimble_bind::BindInput {
        root,
        entries,
        model,
        modeled: &table.modeled,
        strict: table.strict,
        rename_min_tokens: usize::try_from(table.rename_min_tokens).unwrap_or(usize::MAX),
        ledger_dir: &ledger_dir,
    })
}

/// Walk and bind the repository at `root` exactly as `grimble check` does; what `grimble ack` plans over.
///
/// # Errors
///
/// [`CheckError`] for a bad `grimble.toml` table or a failed walk.
pub fn bind_repo(root: &Path) -> Result<grimble_bind::Binding, CheckError> {
    let entries = walk_repo(root)?;
    let table = GrimbleTable::load(root)?;
    let model = read_models(root, &entries, &table);
    Ok(bind_models(root, &entries, &model, &table))
}

/// Walk `root` honouring `[check] exclude` and `size_cap` and tally models and languages.
///
/// # Errors
///
/// [`CheckError`] for a bad `grimble.toml` table or a failed walk.
pub fn survey(root: &Path) -> Result<Survey, CheckError> {
    let walked = walk_repo(root)?;
    let mut out = Survey::default();
    for f in walked {
        let tag = fidelity::language_tag(&f.path, &f.language);
        *out.languages.entry(tag.to_owned()).or_default() += 1;
        if tag == "grmb" {
            out.models.push(f.path);
        }
    }
    out.models.sort();
    Ok(out)
}
