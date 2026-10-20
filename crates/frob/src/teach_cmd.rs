//! `frob teach reset [RULE]`: forget what the repository has been taught (diagnostics.md section 5.1).
//!
//! Teaching state is the local, disposable `.frob/seen.toml`; resetting one rule or all of them
//! makes the next `check` explain again in full, as on a first occurrence.

// frob:ticket 01M3ZX81N4AFEA0W55R756T5RD

use std::path::{Path, PathBuf};

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_diagnostics::{SeenStore, TeachError};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::Located;

/// Where the seen state lives, relative to the repository root.
const SEEN_FILE: &str = ".frob/seen.toml";

/// Output of `frob teach reset`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TeachResetData {
    /// The rule that was reset, or `None` when every rule was.
    pub rule: Option<String>,
    /// The seen file that was rewritten.
    pub path: String,
}

/// The flags of `teach`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct TeachArgs {
    #[arg(value_parser = ["reset"], help = "What to do: `reset` forgets what was taught")]
    action: String,
    #[arg(
        value_name = "RULE",
        help = "Reset only this rule (default: every rule)"
    )]
    rule: Option<String>,
}

/// Forget taught rules (`teach reset`) or one rule (`teach reset RULE`) so the next check explains in full again.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "teach",
    product = "frob",
    idempotent = true,
    exits(ok, usage, refused, internal)
)]
pub struct Teach {
    rule: Option<String>,
}

/// Reset `rule` (or everything) in the seen file under `root`, returning the file written.
///
/// # Errors
/// [`TeachError`] when the seen file cannot be read, parsed or written.
pub fn reset_at(root: &Path, rule: Option<&str>) -> Result<PathBuf, TeachError> {
    let path = root.join(SEEN_FILE);
    let mut store = SeenStore::load(&path)?;
    store.reset(rule);
    store.save(&path)?;
    tracing::info!(?rule, path = %path.display(), "teach state reset");
    Ok(path)
}

impl Command for Teach {
    type Data = TeachResetData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<TeachArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<TeachArgs>(m)?;
        Ok(Self { rule: a.rule })
    }

    fn run(&self, ctx: &Context) -> Outcome<TeachResetData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let path = reset_at(&root, self.rule.as_deref()).map_err(CliError::internal)?;
        let what = self.rule.as_deref().unwrap_or("every rule");
        let rows = vec![format!("reset teaching state for {what}")];
        Ok(Payload::new(TeachResetData {
            rule: self.rule.clone(),
            path: path.display().to_string(),
        })
        .with_rendered(rows))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_diagnostics::{Disclosure, TeachMode};

    // frob:tests crates/frob/src/teach_cmd.rs::reset_at
    #[test]
    fn reset_empties_seen_toml_and_the_next_check_teaches_again() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join(SEEN_FILE);
        let mut s = SeenStore::default();
        s.disclose(TeachMode::First, "SYS003");
        s.disclose(TeachMode::First, "DOC001");
        s.save(&path).unwrap();
        reset_at(dir.path(), None).unwrap();
        let mut after = SeenStore::load(&path).unwrap();
        assert_eq!(after, SeenStore::default());
        assert_eq!(after.disclose(TeachMode::First, "SYS003"), Disclosure::Full);
    }

    // frob:tests crates/frob/src/teach_cmd.rs::reset_at
    #[test]
    fn reset_with_a_rule_keeps_the_others() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join(SEEN_FILE);
        let mut s = SeenStore::default();
        s.disclose(TeachMode::First, "SYS003");
        s.disclose(TeachMode::First, "DOC001");
        s.save(&path).unwrap();
        reset_at(dir.path(), Some("SYS003")).unwrap();
        let after = SeenStore::load(&path).unwrap();
        assert_eq!(after.count("SYS003"), 0);
        assert_eq!(after.count("DOC001"), 1);
    }
}
