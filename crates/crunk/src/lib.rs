//! The `crunk` product: a [`gob_product::Product`] impl on the shared goblin CLI root.
//!
//! [`cli`] assembles the root; `main` only runs it. The generic `check` (the `gob.sibling/1`
//! document) and `doctor` verbs come from `gob-product`; [`doctor`] holds crunk's own report
//! rows and the built-in `schema` verb comes from `gob-cli`. Every verb but `doctor` refuses
//! with `E-NO-CONFIG` (exit 3) when no `crunk.toml` exists. No frob crate is linked (the
//! boundary test in `tests/boundary.rs`).

// frob:ticket 01M43ARVS24254G85TMFYH8FGQ
// frob:ticket 01M47QSGHYD2EQ4552V1B4EEQZ

pub mod doctor;

use std::path::Path;

use gob_check::CheckError;
use gob_cli::{Cli, Outcome};
use gob_product::{CheckOptions, Product, ProductRun};

/// Product name, also the config file stem (`crunk.toml`).
pub const PRODUCT: &str = crunk_check::PRODUCT;

/// crunk as a [`Product`]: no verbs beyond the generic `check` and `doctor`.
#[derive(Debug, Clone, Copy, Default)]
pub struct CrunkProduct;

gob_product::register_commands!(CrunkProduct);

impl Product for CrunkProduct {
    const NAME: &'static str = PRODUCT;
    const VERSION: &'static str = env!("CARGO_PKG_VERSION");
    const DOCTOR_SUMMARY: &'static str =
        "Report the crunk version, the repository root and the state of crunk.toml.";
    const REQUIRES_CONFIG: bool = true;

    type Doctor = doctor::DoctorData;

    fn has_config(root: &Path) -> bool {
        crunk_check::has_config(root)
    }

    fn check(root: &Path, opts: &CheckOptions) -> Result<ProductRun, CheckError> {
        let run = crunk_check::run(
            root,
            &crunk_check::CheckOptions {
                only: opts.only.clone(),
                fail_on: opts.fail_on,
                base: opts.base.clone(),
                ticket_scope: opts.ticket_scope.clone(),
            },
        )?;
        let document = crunk_check::sibling_document(&run);
        Ok(ProductRun {
            report: run.report,
            document,
            warnings: run.warnings,
        })
    }

    fn doctor(root: &Path) -> Outcome<doctor::DoctorData> {
        Ok(doctor::report(root))
    }

    fn register(cli: Cli) -> Cli {
        cli
    }
}

/// The fully registered `crunk` command-line root.
pub fn cli() -> Cli {
    gob_product::cli::<CrunkProduct>()
}
