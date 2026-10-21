//! frob as a [`gob_product::Product`]: the generic `check` and `doctor` verbs over frob's own pipeline and survey.
//!
//! frob's `check` and `doctor` keep their own flags and data types ([`frob_check::Check`],
//! [`crate::doctor::Doctor`]); this impl only plugs them into the shared verbs, so the output,
//! JSON envelopes and exit codes are those of the verbs before the move (products.md section 7).

// frob:ticket 01M47QSHBWSGEYXJ56PR6FQBS9

use std::path::{Path, PathBuf};

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{Cli, Command, Context, ExitCode, Outcome};
use gob_product::{CheckOptions, Product};

use crate::doctor::{Doctor, DoctorData};
use crate::workspace::Located;
use crate::{PRODUCT, first_run, init, lease_cmd, ticket};

/// frob as a [`Product`]: `check` and `doctor` are generic, every other verb stays frob's.
#[derive(Debug, Clone, Copy, Default)]
pub struct FrobProduct;

gob_product::register_commands!(FrobProduct);

impl Product for FrobProduct {
    const NAME: &'static str = PRODUCT;
    const VERSION: &'static str = env!("FROB_BUILD_VERSION");
    const DOCTOR_SUMMARY: &'static str = crate::doctor::SUMMARY;
    const CHECK_SUMMARY: &'static str = frob_check::CHECK_SUMMARY;
    const DOCTOR_IDEMPOTENT: bool = true;
    const DOCTOR_EXITS: &'static [ExitCode] = &[ExitCode::Ok, ExitCode::Refused];
    // frob's own guard (the teaching refusal) is installed by `register`.
    const REQUIRES_CONFIG: bool = false;

    type CheckData = frob_check::CheckData;
    type Doctor = DoctorData;

    fn has_config(root: &Path) -> bool {
        root.join("frob.toml").is_file()
    }

    fn locate_root(cwd: &Path) -> PathBuf {
        Located::discover(cwd).root
    }

    fn configure_check(cmd: ClapCommand) -> ClapCommand {
        frob_check::Check::configure(cmd)
    }

    fn configure_doctor(cmd: ClapCommand) -> ClapCommand {
        Doctor::configure(cmd)
    }

    fn check(
        ctx: &Context,
        _root: &Path,
        _opts: &CheckOptions,
        matches: &ArgMatches,
    ) -> Outcome<frob_check::CheckData> {
        tracing::debug!("frob check through the product verb");
        let payload = frob_check::Check::from_matches(matches)?.run(ctx)?;
        let rows = crate::check_view::check_rows(&payload.data, ctx.verbosity > 0);
        Ok(payload.with_rendered(rows))
    }

    fn doctor(ctx: &Context, _root: &Path, matches: &ArgMatches) -> Outcome<DoctorData> {
        tracing::debug!("frob doctor through the product verb");
        Doctor::from_matches(matches)?.run(ctx)
    }

    fn register(cli: Cli) -> Cli {
        let cli = ticket::register(
            cli.register::<init::Init>()
                .register::<crate::config_cmd::ConfigShow>()
                .register::<crate::config_cmd::ConfigSync>()
                .register::<crate::agent_cmd::AgentSync>()
                .register::<crate::agent_cmd::AgentStatus>()
                .register::<crate::agent_cmd::AgentUninstall>()
                .register::<lease_cmd::LeaseWiden>()
                .register::<lease_cmd::LeaseRelease>()
                .register::<lease_cmd::LeaseRekind>()
                .register::<lease_cmd::ClaimTouch>()
                .register::<crate::board_cmd::BoardVerb>(),
        );
        let cli = crate::milestone_cmd::register(cli);
        let cli = crate::cycle_cmd::register(cli);
        let cli = crate::stats_cmd::register(cli);
        // frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2
        let cli = crate::refresh_cmd::register(cli);
        let cli = crate::mirror_cmd::register(cli);
        let cli = crate::profile_cmd::register(cli);
        let cli = crate::tour_cmd::register(cli);
        // frob:ticket 01M3ZX7VDVTM9DJCW5228YRZ8Z
        let cli = cli.register::<crate::trust_cmd::Trust>();
        // frob:ticket 01M3ZX81N4AFEA0W55R756T5RD
        let cli = cli.register::<crate::teach_cmd::Teach>();
        let cli = crate::release_cmd::register(cli);
        let cli = cli
            .register::<crate::rule_cmd::RuleTest>()
            .register::<crate::rule_cmd::RuleCheck>()
            .register::<crate::rule_cmd::RuleCatalog>()
            .register::<crate::rule_cmd::RuleFmt>()
            // frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W
            .register::<crate::rule_cmd::RuleNew>();
        // frob:ticket 01M5ANA1DJ6V3MDF3NJZXAS6JW
        let cli = cli.register::<crate::explain_cmd::Explain>();
        let cli = frob_lease::register(cli);
        let cli = frob_worktree::register(cli);
        let cli = frob_evidence::register(cli);
        let cli = frob_tests::register(cli);
        let cli = frob_ack::register(cli);
        frob_land::register(cli)
            .with_guard(first_run::require_config)
            .with_presenter(crate::profile::PRESENTER)
    }
}

// frob:ticket 01M4K8TMXWK93ZKAAFQE9W4M0D
/// Run `git` in `dir` through the runner and assert it exited 0.
#[cfg(test)]
fn git(dir: &Path, args: &[&str]) {
    let spec = gob_exec::Spec {
        program: gob_exec::Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_owned()),
        env: Vec::new(),
        timeout: std::time::Duration::from_secs(30),
        capture: true,
    };
    let out = gob_exec::Runner::new(gob_exec::Limits { jobs: 1 })
        .run(&spec)
        .expect("run git");
    assert!(
        matches!(out.status, gob_exec::Outcome::Exited(0)),
        "git {args:?}: {}",
        out.stderr
    );
}

// frob:ticket 01M4K8TMXWK93ZKAAFQE9W4M0D
// frob:tests crates/frob/src/product.rs::check_refuses_exit_3_when_git_tracks_a_state_file
#[cfg(test)]
#[test]
fn check_refuses_exit_3_when_git_tracks_a_state_file() {
    let products = [
        ("frob", crate::cli()),
        ("grimble", grimble::cli()),
        ("crunk", crunk::cli()),
    ];
    for (product, cli) in products {
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(dir.path().join(format!("{product}.toml")), "").expect("config");
        let state = format!(".{product}/cache.sqlite");
        std::fs::create_dir_all(dir.path().join(format!(".{product}"))).expect("state dir");
        std::fs::write(dir.path().join(&state), b"x").expect("state");
        git(dir.path(), &["init", "-q"]);
        git(dir.path(), &["add", "-f", &state]);
        let (code, out, _) = gob_cli::run_for_test(&cli, &["check", "--json"], dir.path());
        assert_eq!(code, 3, "{product}: {out}");
        let env: serde_json::Value = serde_json::from_str(&out).expect("json envelope");
        assert_eq!(env["error"]["code"], "E-STATE-TRACKED", "{product}");
        assert!(
            env["error"]["message"]
                .as_str()
                .is_some_and(|m| m.contains(&state)),
            "{product}: {out}"
        );
    }
}
