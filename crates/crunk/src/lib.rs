//! The `crunk` product: a [`gob_product::Product`] impl on the shared goblin CLI root.
//!
//! [`cli`] assembles the root; `main` only runs it. The generic `check` (the `gob.sibling/1`
//! document) and `doctor` verbs come from `gob-product`; [`doctor`] holds crunk's own report
//! rows, [`tokens`] exports and checks the generated token files, and the built-in `schema` verb
//! comes from `gob-cli`. Every verb but `doctor` refuses
//! with `E-NO-CONFIG` (exit 3) when no `crunk.toml` exists. No frob crate is linked (the
//! boundary test in `tests/boundary.rs`).

// frob:ticket 01M43ARVS24254G85TMFYH8FGQ
// frob:ticket 01M47QSGHYD2EQ4552V1B4EEQZ

pub mod doctor;
pub mod tokens;

use std::path::Path;

use gob_cli::clap::ArgMatches;
use gob_cli::{Cli, Context, Outcome};
use gob_product::{CheckOptions, Product, ProductRun};
use serde_json::Value;

/// Product name, also the config file stem (`crunk.toml`).
pub const PRODUCT: &str = crunk_check::PRODUCT;

/// crunk as a [`Product`]: the generic `check` and `doctor` plus [`tokens`].
#[derive(Debug, Clone, Copy, Default)]
pub struct CrunkProduct;

gob_product::register_commands!(CrunkProduct);

// frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
gob_cli::inventory::submit! {
    gob_cli::SchemaExtension::new(crunk_spec::schema::schema)
}

impl Product for CrunkProduct {
    const NAME: &'static str = PRODUCT;
    const VERSION: &'static str = env!("CARGO_PKG_VERSION");
    const DOCTOR_SUMMARY: &'static str =
        "Report the crunk version, the repository root and the state of crunk.toml.";
    const REQUIRES_CONFIG: bool = true;

    type CheckData = Value;
    type Doctor = doctor::DoctorData;

    fn has_config(root: &Path) -> bool {
        crunk_check::has_config(root)
    }

    fn check(
        ctx: &Context,
        root: &Path,
        opts: &CheckOptions,
        _matches: &ArgMatches,
    ) -> Outcome<Value> {
        let run = crunk_check::run(
            root,
            &crunk_check::CheckOptions {
                only: opts.only.clone(),
                fail_on: opts.fail_on,
                base: opts.base.clone(),
                ticket_scope: opts.ticket_scope.clone(),
            },
        )
        .map(|run| {
            let document = crunk_check::sibling_document(&run);
            ProductRun {
                report: run.report,
                document,
                warnings: run.warnings,
            }
        });
        gob_product::sibling_check(Self::NAME, ctx, run)
    }

    fn doctor(_ctx: &Context, root: &Path, _matches: &ArgMatches) -> Outcome<doctor::DoctorData> {
        Ok(doctor::report(root))
    }

    fn register(cli: Cli) -> Cli {
        cli.register::<tokens::Tokens>()
    }
}

/// The fully registered `crunk` command-line root.
pub fn cli() -> Cli {
    gob_product::cli::<CrunkProduct>()
}

// frob:ticket 01M4K8TMXWK93ZKAAFQE9W4M0D
#[cfg(test)]
mod state_guard_tests {
    use std::path::Path;

    use serde_json::Value;

    use super::cli;

    // frob:ticket 01M4K8TMXWK93ZKAAFQE9W4M0D
    /// Run `git` in `dir` and assert it succeeded.
    fn git(dir: &Path, args: &[&str]) {
        let ok = std::process::Command::new("git")
            .args(args)
            .current_dir(dir)
            .status()
            .expect("run git")
            .success();
        assert!(ok, "git {args:?}");
    }

    // frob:tests crates/crunk/src/lib.rs::state_guard_tests::check_refuses_exit_3_when_git_tracks_a_state_file
    #[test]
    fn check_refuses_exit_3_when_git_tracks_a_state_file() {
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(dir.path().join("crunk.toml"), "").expect("config");
        std::fs::create_dir_all(dir.path().join(".crunk")).expect("state dir");
        std::fs::write(dir.path().join(".crunk/cache.json"), b"x").expect("state");
        git(dir.path(), &["init", "-q"]);
        git(dir.path(), &["add", "-f", ".crunk/cache.json"]);
        let (code, out, _) = gob_cli::run_for_test(&cli(), &["check", "--json"], dir.path());
        assert_eq!(code, 3, "{out}");
        let env: Value = serde_json::from_str(&out).expect("json envelope");
        assert_eq!(env["error"]["code"], "E-STATE-TRACKED");
        assert!(
            env["error"]["message"]
                .as_str()
                .is_some_and(|m| m.contains(".crunk/cache.json"))
        );
    }
}
