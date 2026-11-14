//! `guidelines`: the agent-guidelines file for the project's design system.
//!
//! Returns `design/guidelines.md` when the project has one, else the built-in default that tells
//! an agent how to use the read verbs (`outline`, `query find`, `map`) before writing styles.
//! The verb is `read_only`, so `crunk serve` lists it as an MCP tool.

// frob:ticket 01M5XCW9WCHSZBR5F29VKYBM25

use std::path::Path;

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// The project's own guidelines file, relative to the root.
pub const GUIDELINES_FILE: &str = "design/guidelines.md";

/// The guidelines returned when the project has no file of its own.
pub const DEFAULT_GUIDELINES: &str = "\
# Design system guidelines for agents

Use the design system before writing new styles.

1. Run `crunk outline` first: a sparse list of tokens, components, screens and flows.
2. Drill into one node with `crunk outline --node ID`; do not read whole files.
3. Search before you create: `crunk query find NAME` for tokens and components, `crunk map` for
   where styles live.
4. Use a token for every colour, space, size, radius and layer; never a raw value.
5. Reuse a component before adding one; add a state for every state the spec requires.
6. Run `crunk check` after every change and fix findings before moving on.
";

/// Where the returned guidelines came from.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Source {
    /// The project's `design/guidelines.md`.
    Project,
    /// The built-in default.
    Builtin,
}

/// Return the agent-guidelines file: the project's own, else the built-in default.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "guidelines",
    product = "crunk",
    idempotent = true,
    read_only,
    exits(ok, refused, usage, internal)
)]
pub struct Guidelines;

/// Output of `guidelines`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct GuidelinesData {
    /// Where the text came from.
    pub source: Source,
    /// The file path relative to the root, for a project file.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
    /// The guidelines text (Markdown).
    pub text: String,
}

/// The guidelines of the project at `root`: its file when readable, else the default.
pub fn read_guidelines(root: &Path) -> GuidelinesData {
    let file = root.join(GUIDELINES_FILE);
    match std::fs::read_to_string(&file) {
        Ok(text) => {
            tracing::info!(path = %file.display(), "project guidelines read");
            GuidelinesData {
                source: Source::Project,
                path: Some(GUIDELINES_FILE.to_owned()),
                text,
            }
        }
        Err(err) => {
            tracing::debug!(path = %file.display(), %err, "no project guidelines; built-in used");
            GuidelinesData {
                source: Source::Builtin,
                path: None,
                text: DEFAULT_GUIDELINES.to_owned(),
            }
        }
    }
}

impl Command for Guidelines {
    type Data = GuidelinesData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd
    }

    fn from_matches(_m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<GuidelinesData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let data = read_guidelines(&root);
        let lines: Vec<String> = data.text.lines().map(str::to_owned).collect();
        Ok(Payload::new(data).with_rendered(lines))
    }
}
