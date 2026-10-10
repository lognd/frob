//! The generic `doctor` verb: the product's environment and config report.

use std::marker::PhantomData;

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, CommandMeta, Context, Described, Outcome};

use crate::Product;

/// The `doctor` verb of product `P`; its data and rows come from [`Product::doctor`].
#[derive(Debug, Clone)]
pub struct Doctor<P: Product> {
    matches: ArgMatches,
    product: PhantomData<fn() -> P>,
}

impl<P: Product> Described for Doctor<P> {
    const META: CommandMeta = CommandMeta {
        verb: "doctor",
        product: P::NAME,
        idempotent: P::DOCTOR_IDEMPOTENT,
        dry_run: false,
        exits: P::DOCTOR_EXITS,
        summary: P::DOCTOR_SUMMARY,
        module: module_path!(),
        deprecated: None,
        markdown: false,
        read_only: true,
    };
}

impl<P: Product> Command for Doctor<P> {
    type Data = P::Doctor;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        P::configure_doctor(cmd)
    }

    fn from_matches(matches: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            matches: matches.clone(),
            product: PhantomData,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<P::Doctor> {
        let root = P::locate_root(&ctx.cwd);
        tracing::debug!(product = P::NAME, root = %root.display(), "doctor started");
        P::doctor(ctx, &root, &self.matches)
    }
}
