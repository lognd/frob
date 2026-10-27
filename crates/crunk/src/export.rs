//! `export css|tailwind|uss|csharp`: print one token export, or write it to `--out`.
//!
//! A thin verb over [`crunk_tokens::export`]: it renders through the same code path as
//! `tokens --target` (see [`crate::tokens::preview`]) and adds only `--out`. `export dtcg` is the
//! separate [`crate::dtcg::ExportDtcg`], which reads the stored interchange document.

// frob:ticket 01M5XCVMQBQWARH7HT8RYHA0KY

use std::path::PathBuf;

use crunk_tokens::export::{ExportError, Target};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome};

use crate::PRODUCT;
use crate::tokens::{TokensData, export_error, preview, refusal};

/// `export` flags shared by every target.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ExportArgs {
    #[arg(long, value_name = "PATH", help = "Write here instead of printing")]
    out: Option<PathBuf>,
}

/// Render `target` from the project spec; print it, or write it to `out`.
fn run_target(target: Target, out: Option<&PathBuf>, ctx: &Context) -> Outcome<TokensData> {
    let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
    let spec = crunk_spec::load_spec(&root).map_err(|e| {
        tracing::info!(error = %e, "export: spec did not load");
        refusal(
            "E-SPEC",
            &format!("crunk.toml is not a valid design spec: {e}"),
        )
        .with_remedy("fix crunk.toml as described, then rerun")
    })?;
    let payload = preview(&root, &spec, target)?;
    let Some(out) = out else {
        tracing::info!(%target, "export: printed");
        return Ok(payload);
    };
    let path = if out.is_absolute() {
        out.clone()
    } else {
        ctx.cwd.join(out)
    };
    if !ctx.dry_run {
        let text = payload.data.content.clone().unwrap_or_default();
        std::fs::write(&path, text).map_err(|source| {
            export_error(ExportError::Write {
                path: path.clone(),
                source,
            })
        })?;
        tracing::info!(%target, path = %path.to_string_lossy(), "export: written");
    }
    Ok(payload)
}

macro_rules! export_verb {
    ($ty:ident, $verb:literal, $target:expr, $doc:literal) => {
        #[doc = $doc]
        #[derive(Debug, Clone, Default, gob_cli::Command)]
        #[command(
                            verb = $verb,
                            product = "crunk",
                            idempotent = true,
                            dry_run,
                            exits(ok, refused, usage, internal)
                        )]
        pub struct $ty {
            out: Option<PathBuf>,
        }

        impl Command for $ty {
            type Data = TokensData;

            fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
                gob_cli::augment::<ExportArgs>(cmd)
            }

            fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
                Ok(Self {
                    out: gob_cli::parse::<ExportArgs>(m)?.out,
                })
            }

            fn run(&self, ctx: &Context) -> Outcome<TokensData> {
                run_target($target, self.out.as_ref(), ctx)
            }
        }
    };
}

export_verb!(
    ExportCss,
    "export css",
    Target::Css,
    "Print the CSS custom-property export, or write it to `--out`."
);
export_verb!(
    ExportTailwind,
    "export tailwind",
    Target::Tailwind,
    "Print the Tailwind theme export, or write it to `--out`."
);
export_verb!(
    ExportUss,
    "export uss",
    Target::Uss,
    "Print the Unity USS variable sheet, or write it to `--out`."
);
export_verb!(
    ExportCsharp,
    "export csharp",
    Target::Csharp,
    "Print the C# constants export, or write it to `--out`."
);
