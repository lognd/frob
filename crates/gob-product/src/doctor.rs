//! The generic `doctor` verb: the product's environment and config report.

use std::marker::PhantomData;

use gob_cli::{CliError, Command, CommandMeta, Context, Described, ExitCode, Outcome};

use crate::Product;
use crate::workspace::locate_root;

/// The `doctor` verb of product `P`; its data and rows come from [`Product::doctor`].
#[derive(Debug, Clone, Copy)]
pub struct Doctor<P: Product>(PhantomData<fn() -> P>);

impl<P: Product> Described for Doctor<P> {
    const META: CommandMeta = CommandMeta {
        verb: "doctor",
        product: P::NAME,
        idempotent: false,
        dry_run: false,
        exits: &[
            ExitCode::Ok,
            ExitCode::Refused,
            ExitCode::Usage,
            ExitCode::Internal,
        ],
        summary: P::DOCTOR_SUMMARY,
        module: module_path!(),
    };
}

impl<P: Product> Command for Doctor<P> {
    type Data = P::Doctor;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self(PhantomData))
    }

    fn run(&self, ctx: &Context) -> Outcome<P::Doctor> {
        let root = locate_root(P::NAME, &ctx.cwd);
        tracing::debug!(product = P::NAME, root = %root.display(), "doctor started");
        P::doctor(&root)
    }
}
