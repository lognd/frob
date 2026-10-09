//! The sibling stage: run `grimble check --json` beside frob's own rules and merge it.
//!
//! The contract is `docs/design/sibling-contract.md` (decision D67). frob talks to
//! a sibling only through the process and the JSON document: no crate of the
//! sibling is a dependency. A configured sibling (its `<product>.toml` exists at
//! the repository root) is spawned concurrently at the start of the pipeline and
//! joined after the per-file and repo rules; any way of not getting a usable
//! document is one required Unresolved `SIB001` per product.
//!
//! - [`spawn`]: invocation, the failure taxonomy and document validation;
//! - [`merge`]: the document into namespaced findings, suppressed pairs, fidelity
//!   rows and the ticket-bound exception exits.

mod doc;
mod merge;
mod spawn;

use std::collections::BTreeSet;
use std::path::Path;
use std::sync::Mutex;
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use frob_obligations::sibling_exception_findings;
use gob_check::{CheckTable, External, SiblingRow, Timing};
use gob_exec::{Program, find_sibling};
use gob_rules::{Finding, RequiredReason, Rule, Severity};
use gob_text::FileInterner;

use crate::options::CheckOptions;
pub use spawn::ACCEPTED_SIBLING_MAJORS;
use spawn::{Failure, Reason, Run, Spawned};

/// A sibling product's `check --json` could not be used: unavailable, incompatible, failed, late or malformed.
///
/// One finding per configured product, never one per symptom. The message names the
/// reason code (`absent`, `incompatible`, `failed`, `timeout`, `malformed`) and an
/// exact remedy command. It is a required Unresolved of kind `sibling_missing` while
/// `[check] require_siblings` is true (the default), so the default gate fails; with
/// the knob off it still prints and fails only under `fail_on_unresolved = "all"`.
#[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
#[rule(
    id = "SIB001",
    slug = "sibling-unavailable",
    family = "SIB",
    severity = Unresolved,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pminus,
    version = 1
)]
pub struct Sib001;

/// The configured siblings: product name and the config file that makes it configured.
///
/// `crunk` is registered ahead of its release: it is spawned only when `crunk.toml`
/// exists, so a repository without one sees no change.
const SIBLINGS: &[(&str, &str)] = &[("grimble", "grimble.toml"), ("crunk", "crunk.toml")];

/// A started sibling run: the product and the thread driving its process.
struct Pending {
    product: &'static str,
    require: bool,
    /// Where discovery found the binary; `None` for a configured override.
    row: Option<SiblingRow>,
    handle: JoinHandle<Spawned>,
}

/// The sibling runs of one pipeline pass, started early and joined late.
#[derive(Default)]
pub(crate) struct Siblings {
    pending: Mutex<Vec<Pending>>,
    /// One note per configured sibling this pass did not run, for the report's warnings.
    skipped: Mutex<Vec<String>>,
}

/// The paths a sibling reads beyond its own source files: its config, its pack lock and, for grimble, model files.
fn is_sibling_input(product: &str, config: &str, models: &[String], path: &str) -> bool {
    let path = path.strip_prefix("./").unwrap_or(path);
    path == config
        || path == format!("{product}.packs.lock")
        || (product == "grimble"
            && (Path::new(path)
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("grmb"))
                || models.iter().any(|m| m == path)))
}

/// Why `product` can be skipped for a ticket touching `scope`, or `None` when it must run.
///
/// A sibling reads its config, its model files and the code its bindings select. Which code
/// that is needs the sibling's own evaluation, so any file of a known code language counts
/// (Markdown does not): a docs-only scope skips, a code scope runs.
fn skip_reason(
    product: &str,
    config: &str,
    models: &[String],
    scope: Option<&BTreeSet<String>>,
) -> Option<String> {
    let files = scope?;
    let touched = files.iter().any(|f| {
        is_sibling_input(product, config, models, f)
            || gob_languages::Language::detect(f)
                .is_some_and(|l| l != gob_languages::Language::Markdown)
    });
    (!touched).then(|| {
        format!(
            "{product} not evaluated: the ticket scope ({} files) touches none of its inputs ({config}, its models and pack lock, code files)",
            files.len()
        )
    })
}

/// The root model files declared in `grimble.toml` `[grimble] models`; empty when unreadable.
fn grimble_models(root: &Path) -> Vec<String> {
    let text = std::fs::read_to_string(root.join("grimble.toml")).unwrap_or_default();
    let doc: toml::Table = text.parse().unwrap_or_default();
    doc.get("grimble")
        .and_then(|g| g.get("models"))
        .and_then(toml::Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str())
                .map(|m| m.strip_prefix("./").unwrap_or(m).to_owned())
                .collect()
        })
        .unwrap_or_default()
}

/// True when `--only` leaves the sibling stage on: no filter, or one naming `SIB`.
fn wanted(only: &[String]) -> bool {
    only.is_empty()
        || only.iter().any(|o| {
            let o = o.trim().to_ascii_uppercase();
            o == "SIB" || o == "SIB001"
        })
}

impl Siblings {
    /// Spawn every configured sibling; `scope` is the ticket scope's paths, passed through.
    pub(crate) fn start(
        &self,
        root: &Path,
        table: &CheckTable,
        base: &str,
        scope: Option<&BTreeSet<String>>,
        opts: &CheckOptions,
    ) {
        let mut pending = self
            .pending
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        pending.clear();
        let mut skipped = self
            .skipped
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        skipped.clear();
        if !wanted(&opts.only) {
            tracing::info!("sibling stage skipped by --only");
            return;
        }
        for (product, config) in SIBLINGS {
            if !root.join(config).is_file() {
                tracing::debug!(product, "sibling not configured");
                continue;
            }
            let models = if *product == "grimble" {
                grimble_models(root)
            } else {
                Vec::new()
            };
            if let Some(note) = skip_reason(product, config, &models, scope) {
                tracing::info!(product, "{note}");
                skipped.push(note);
                continue;
            }
            let (program, row) = match opts.sibling_programs.iter().find(|(p, _)| p == product) {
                Some((_, path)) => (Program::Hook { path: path.clone() }, None),
                None => match find_sibling(product) {
                    Ok(found) => {
                        tracing::info!(product, origin = found.origin.label(), "sibling located");
                        let row = sibling_row(product, found.origin.label(), Some(&found.path));
                        (Program::Hook { path: found.path }, Some(row))
                    }
                    // Not found: the sibling program fails the same way and yields the SIB001.
                    Err(_) => (
                        Program::Sibling {
                            name: (*product).to_owned(),
                        },
                        Some(sibling_row(product, "absent", None)),
                    ),
                },
            };
            let compute_digest = match gob_config::ComputeTable::load_for_product(root, product) {
                Ok((table, _)) => Some(gob_config::compute_digest(&table)),
                Err(e) => {
                    tracing::error!(product, error = %e, "compute knobs unreadable; digest not compared");
                    None
                }
            };
            let run = Run {
                program,
                root: root.to_path_buf(),
                product,
                base: base.to_owned(),
                scope: scope.map(|s| s.iter().cloned().collect()),
                timeout: Duration::from_secs(table.sibling_timeout_secs),
                compute_digest,
                output_cap: usize::try_from(table.output_cap_bytes).unwrap_or(usize::MAX),
            };
            tracing::info!(
                product,
                timeout_secs = table.sibling_timeout_secs,
                scoped = scope.is_some(),
                "starting sibling"
            );
            let handle = std::thread::spawn(move || spawn::run(&run));
            pending.push(Pending {
                product,
                require: table.require_siblings,
                row,
                handle,
            });
        }
    }

    /// Join the started siblings and merge each into `files`, `timing` and the returned [`External`].
    pub(crate) fn join(
        &self,
        root: &Path,
        ledger: Option<&frob_ledger::Ledger>,
        files: &mut FileInterner,
        timing: &mut Timing,
    ) -> External {
        let pending = std::mem::take(
            &mut *self
                .pending
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
        );
        let mut out = External::default();
        out.warnings.append(
            &mut self
                .skipped
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
        );
        for Pending {
            product,
            require,
            row,
            handle,
        } in pending
        {
            let started = Instant::now();
            let spawned = handle.join().unwrap_or_else(|_| Spawned {
                elapsed: started.elapsed(),
                result: Err(Failure::new(
                    Reason::Failed,
                    "the sibling driver thread panicked",
                )),
            });
            timing.push(format!("sibling:{product}"), spawned.elapsed, false);
            if let Some(mut row) = row {
                // frob:ticket 01M421F7Q66MW38R7J1JS1VMBC
                if let Ok(doc) = &spawned.result {
                    row.version.clone_from(&doc.product_version);
                }
                out.siblings.push(row);
            }
            match spawned.result {
                Ok(doc) => match merge::merge(product, &doc, files, &mut out) {
                    Ok(exceptions) => {
                        out.findings.extend(sibling_exception_findings(
                            root,
                            ledger,
                            &exceptions,
                            files,
                        ));
                        tracing::info!(
                            product,
                            findings = out.findings.len(),
                            suppressed = out.suppressed.len(),
                            ms = u64::try_from(spawned.elapsed.as_millis()).unwrap_or(u64::MAX),
                            "sibling merged"
                        );
                    }
                    Err(failure) => out.findings.push(unavailable(product, &failure, require)),
                },
                Err(failure) => out.findings.push(unavailable(product, &failure, require)),
            }
        }
        out
    }
}

/// The report row of `product` found at `location` (`beside-frob`, `path` or `absent`); version unknown until it answers.
fn sibling_row(product: &str, location: &str, path: Option<&Path>) -> SiblingRow {
    SiblingRow {
        product: product.to_owned(),
        location: location.to_owned(),
        path: path.map(|p| p.display().to_string()),
        version: None,
        other: None,
    }
}

/// The one `SIB001` of `product` for `failure`, required when `require` is set.
fn unavailable(product: &str, failure: &Failure, require: bool) -> Finding {
    tracing::warn!(product, reason = failure.reason.code(), detail = %failure.detail, "sibling unavailable");
    let message = format!(
        "{product} is configured but unusable ({}): {}; remedy: {}",
        failure.reason.code(),
        failure.detail,
        failure.remedy(product)
    );
    let id = Sib001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    let finding = Finding::new(id, Severity::Unresolved, None, message, product);
    if require {
        finding.with_required(RequiredReason::SiblingMissing {
            product: product.to_owned(),
        })
    } else {
        finding
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scope(paths: &[&str]) -> BTreeSet<String> {
        paths.iter().map(|p| (*p).to_owned()).collect()
    }

    // frob:ticket 01M4HDRT4RSDZN3PRJ4CV286BH
    // frob:tests crates/frob-check/src/sibling/mod.rs::skip_reason
    #[test]
    fn a_docs_only_scope_skips_with_a_reason_and_an_unscoped_run_never_does() {
        let docs = scope(&["docs/a.md", "changelog.d/x.md"]);
        let reason = skip_reason("grimble", "grimble.toml", &[], Some(&docs)).unwrap();
        assert!(reason.starts_with("grimble not evaluated"), "{reason}");
        assert!(skip_reason("grimble", "grimble.toml", &[], None).is_none());
    }

    // frob:ticket 01M4HDRT4RSDZN3PRJ4CV286BH
    // frob:tests crates/frob-check/src/sibling/mod.rs::skip_reason
    #[test]
    fn config_models_lock_and_code_files_keep_a_sibling_running() {
        let models = vec!["design/model.grmb".to_owned()];
        for touched in [
            "grimble.toml",
            "grimble.packs.lock",
            "design/model.grmb",
            "design/other.grmb",
            "crates/x/src/lib.rs",
        ] {
            let files = scope(&[touched]);
            assert!(
                skip_reason("grimble", "grimble.toml", &models, Some(&files)).is_none(),
                "{touched}"
            );
        }
        let files = scope(&["grimble.toml"]);
        assert!(skip_reason("crunk", "crunk.toml", &[], Some(&files)).is_some());
    }
}
