//! `explain RULE`: the full rule page, offline, from pages embedded in the binary.

// frob:ticket 01M3ZX7ZD77ZW385N5B992NX3A

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, ExplainArgs, ExplainData, Outcome, Page};

/// Every `grimble` rule page (`docs/reference/rules/<ID>.md`), embedded at build time.
static PAGES: &[Page] = gob_cli::rule_pages![
    "CAP002", "MDL000", "MDL011", "CLAIM001", "CAP001", "CLAIM003", "MDL001", "MDL010", "MDL012",
    "FLOW001", "CYCLE001", "MDL002", "SYS007", "LARGE001", "MDL005", "MDL013", "MDL004", "MDL016",
    "MDL006", "FLOW003", "MDL015", "PATH001", "MDL017", "FLOW002", "MDL008", "PATH002", "SYS009",
    "SYS006", "DEAD001", "MDL007", "MDL020", "SYS008", "SYS001", "MDL019", "MDL014", "MDL003",
    "SYS013", "MDL009", "SYS011", "PATH003", "MDL021", "SYS002", "SYS010", "SYS003", "SYS004",
    "SYS005",
];

/// Print the full page of one rule offline; an unknown id exits 2 with the closest ids.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "explain",
    product = "grimble",
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

    // frob:tests crates/grimble/src/explain_cmd.rs::PAGES
    #[test]
    fn the_table_covers_every_generated_page_of_the_product() {
        let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(2)
            .expect("workspace root")
            .join("docs/reference/rules");
        let mut on_disk = Vec::new();
        for entry in std::fs::read_dir(&dir).expect("rules dir") {
            let path = entry.expect("entry").path();
            let text = std::fs::read_to_string(&path).expect("page");
            if text.contains("| product | grimble |") {
                let rel = gob_path::RelPath::from_host(&dir, &path).expect("under rules dir");
                on_disk.push(rel.as_str().trim_end_matches(".md").to_owned());
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
