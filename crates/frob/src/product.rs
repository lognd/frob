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
    const VERSION: &'static str = env!("CARGO_PKG_VERSION");
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
        frob_check::Check::from_matches(matches)?.run(ctx)
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
                .register::<lease_cmd::LeaseWiden>()
                .register::<crate::board_cmd::BoardVerb>(),
        );
        let cli = crate::milestone_cmd::register(cli);
        let cli = crate::cycle_cmd::register(cli);
        let cli = crate::release_cmd::register(cli);
        let cli = frob_lease::register(cli);
        let cli = frob_worktree::register(cli);
        let cli = frob_evidence::register(cli);
        let cli = frob_tests::register(cli);
        let cli = frob_ack::register(cli);
        frob_land::register(cli).with_guard(first_run::require_config)
    }
}
