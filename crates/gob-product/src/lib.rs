//! One product front end (products.md section 7, D97).
//!
//! A goblin binary is a [`Product`] impl plus [`main`]: this crate provides the generic `check`
//! and `doctor` verbs ([`Check`], [`Doctor`]), workspace discovery ([`workspace`]), the
//! no-config guard and the CLI assembly ([`cli`]). A product adds its own verbs in
//! [`Product::register`] and lists its generic verbs for reference generation with
//! [`register_commands!`].

// frob:ticket 01M47QSGHYD2EQ4552V1B4EEQZ

mod check;
mod doctor;
mod product;
pub mod workspace;

pub use check::Check;
pub use doctor::Doctor;
pub use gob_cli;
pub use product::{CheckOptions, Product, ProductRun};

use gob_cli::Cli;

/// The fully registered command-line root of product `P`: generic verbs, guard, then its own verbs.
pub fn cli<P: Product>() -> Cli {
    let mut cli = Cli::new(P::NAME, P::VERSION);
    if P::REQUIRES_CONFIG {
        cli = cli.with_guard(workspace::require_config::<P>);
    }
    tracing::debug!(product = P::NAME, "generic verbs registered");
    P::register(cli.register::<Check<P>>().register::<Doctor<P>>())
}

/// Run product `P` over the process arguments and return its exit code.
///
/// The binary passes the code to its own process exit, as `frob` does.
pub fn main<P: Product>() -> i32 {
    let cli = cli::<P>();
    match gob_rules::Registry::global().verify_unique() {
        Ok(()) => cli.run(std::env::args_os().skip(1)),
        Err(e) => cli.fail_startup(e),
    }
}

/// Submit the generic verbs of `$product` to the command inventory (reference generation).
#[macro_export]
macro_rules! register_commands {
    ($product:ty) => {
        $crate::gob_cli::inventory::submit! {
            $crate::gob_cli::CommandEntry::new(
                &<$crate::Check<$product> as $crate::gob_cli::Described>::META,
            )
        }
        $crate::gob_cli::inventory::submit! {
            $crate::gob_cli::CommandEntry::new(
                &<$crate::Doctor<$product> as $crate::gob_cli::Described>::META,
            )
        }
    };
}
