//! The `grimble` product: a [`gob_product::Product`] impl plus its own verbs.
//!
//! [`cli`] assembles the root; `main` only runs it. The generic `check` (the `gob.sibling/1`
//! document) and `doctor` verbs come from `gob-product`; grimble adds [`ack`] (`grimble.lock`),
//! [`init`], [`fmt_cmd`] and [`exceptions`] and holds its own [`doctor`] rows. The built-in
//! `schema` verb comes from `gob-cli`. The `[compute]`, `[packs]`, `[check]` and `[perf]`
//! config tables register through `grimble-check` and `gob-check`. No frob crate is linked (the
//! boundary test in `tests/boundary.rs`).

// frob:ticket 01M47QSGHYD2EQ4552V1B4EEQZ

pub mod ack;
pub mod compile_cmd;
pub mod doctor;
pub mod exceptions;
pub mod fmt_cmd;
pub mod init;
pub mod rule_cmd;
mod workspace;

use std::path::Path;

use gob_cli::clap::ArgMatches;
use gob_cli::{Cli, Context, Outcome};
use gob_product::{CheckOptions, Product, ProductRun};
use serde_json::Value;

/// Product name, also the config file stem (`grimble.toml`).
pub const PRODUCT: &str = "grimble";

/// grimble as a [`Product`]: the generic verbs plus `ack`, `init`, `fmt` and `exceptions list`.
#[derive(Debug, Clone, Copy, Default)]
pub struct GrimbleProduct;

gob_product::register_commands!(GrimbleProduct);

impl Product for GrimbleProduct {
    const NAME: &'static str = PRODUCT;
    const VERSION: &'static str = env!("CARGO_PKG_VERSION");
    const DOCTOR_SUMMARY: &'static str = "Report adapter fidelity per language, how each model file parses and the state of grimble.toml.";
    const REQUIRES_CONFIG: bool = false;

    type CheckData = Value;
    type Doctor = doctor::DoctorData;

    fn check(
        ctx: &Context,
        root: &Path,
        opts: &CheckOptions,
        _matches: &ArgMatches,
    ) -> Outcome<Value> {
        let run = grimble_check::run(
            root,
            &grimble_check::CheckOptions {
                only: opts.only.clone(),
                fail_on: opts.fail_on,
                base: opts.base.clone(),
                ticket_scope: opts.ticket_scope.clone(),
            },
        )
        .map(|run| {
            let document = grimble_check::sibling_document(&run);
            ProductRun {
                report: run.report,
                document,
                warnings: run.warnings,
            }
        });
        gob_product::sibling_check(Self::NAME, ctx, run)
    }

    fn doctor(_ctx: &Context, root: &Path, _matches: &ArgMatches) -> Outcome<doctor::DoctorData> {
        doctor::report(root)
    }

    fn register(cli: Cli) -> Cli {
        cli.register::<ack::Ack>()
            .register::<init::Init>()
            .register::<fmt_cmd::Fmt>()
            .register::<compile_cmd::Compile>()
            .register::<exceptions::ExceptionsList>()
            .register::<rule_cmd::RuleTest>()
            .register::<rule_cmd::RuleCheck>()
            .register::<rule_cmd::RuleCatalog>()
            .register::<rule_cmd::RuleFmt>()
            // frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W
            .register::<rule_cmd::RuleNew>()
    }
}

/// The fully registered `grimble` command-line root.
pub fn cli() -> Cli {
    gob_product::cli::<GrimbleProduct>()
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

    // frob:tests crates/grimble/src/lib.rs::state_guard_tests::check_refuses_exit_3_when_git_tracks_a_state_file
    #[test]
    fn check_refuses_exit_3_when_git_tracks_a_state_file() {
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(dir.path().join("grimble.toml"), "").expect("config");
        std::fs::create_dir_all(dir.path().join(".grimble")).expect("state dir");
        std::fs::write(dir.path().join(".grimble/cache.json"), b"x").expect("state");
        git(dir.path(), &["init", "-q"]);
        git(dir.path(), &["add", "-f", ".grimble/cache.json"]);
        let (code, out, _) = gob_cli::run_for_test(&cli(), &["check", "--json"], dir.path());
        assert_eq!(code, 3, "{out}");
        let env: Value = serde_json::from_str(&out).expect("json envelope");
        assert_eq!(env["error"]["code"], "E-STATE-TRACKED");
        assert!(
            env["error"]["message"]
                .as_str()
                .is_some_and(|m| m.contains(".grimble/cache.json"))
        );
    }
}
