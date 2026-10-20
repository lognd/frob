//! `explain RULE`: the full rule page, offline, from pages embedded in the binary.

// frob:ticket 01M3ZX7ZD77ZW385N5B992NX3A

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, ExplainArgs, ExplainData, Outcome, Page};

/// Every `frob` rule page (`docs/reference/rules/<ID>.md`), embedded at build time.
static PAGES: &[Page] = gob_cli::rule_pages![
    "AFFECT001",
    "CI014",
    "CI010",
    "DOC001",
    "DRIFT003",
    "EXC005",
    "DOC002",
    "DRIFT001",
    "EXC007",
    "EXC017",
    "DRIFT002",
    "EXC014",
    "DRIFT004",
    "CI003",
    "EXC016",
    "INV002",
    "PM002",
    "INV001",
    "PM013",
    "CFG001",
    "REL001",
    "COV003",
    "CI001",
    "CI007",
    "COV001",
    "DSL002",
    "EXC003",
    "GRL016",
    "PM004",
    "PM009",
    "PM001",
    "TEST001",
    "PM012",
    "PM003",
    "REF001",
    "PM032",
    "DSL003",
    "DSL001",
    "REL003",
    "PARSE001",
    "PARSE002",
    "TICK004",
    "PM031",
    "TICK003",
    "REL002",
    "PM005",
    "PM007",
    "PM036",
    "PM033",
    "PM010",
    "TICK006",
    "PM008",
    "EXC001",
    "SIB001",
    "TICK005",
    "PROC001",
    "READ001",
    "PERF001",
    "TICK009",
    "TICK010",
    "TICK011",
    "TODO001",
    "TICK001",
    "SCOPE001",
    "TODO002",
    "TOOL001",
    "CI006",
    "PM034",
    "PM006",
    "TICK008",
    "TICK002",
    "TOOL002",
    "TICK007",
    "PM011",
];

/// Print the full page of one rule offline; an unknown id exits 2 with the closest ids.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "explain",
    product = "frob",
    idempotent = true,
    read_only,
    exits(ok, usage, internal)
)]
pub struct Explain {
    rule: String,
}

impl Command for Explain {
    type Data = ExplainData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<ExplainArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ExplainArgs>(m)?;
        Ok(Self { rule: a.rule })
    }

    fn run(&self, ctx: &Context) -> Outcome<ExplainData> {
        gob_cli::explain(ctx, PAGES, &self.rule)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob/src/explain_cmd.rs::PAGES
    #[test]
    fn the_table_covers_every_generated_page_of_the_product() {
        let dir =
            std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../docs/reference/rules");
        let mut on_disk = Vec::new();
        for entry in std::fs::read_dir(&dir).expect("rules dir") {
            let path = entry.expect("entry").path();
            let text = std::fs::read_to_string(&path).expect("page");
            if text.contains("| product | frob |") {
                on_disk.push(
                    path.file_stem()
                        .expect("stem")
                        .to_string_lossy()
                        .into_owned(),
                );
            }
        }
        on_disk.sort();
        let mut embedded: Vec<&str> = PAGES.iter().map(|(id, _)| *id).collect();
        embedded.sort_unstable();
        assert_eq!(
            on_disk, embedded,
            "regenerate the page list of explain_cmd.rs"
        );
    }
}
