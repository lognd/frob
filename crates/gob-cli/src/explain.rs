//! The shared half of the `explain` verb: look a rule page up, suggest near ids, page it.
//!
//! The pages are the generated `docs/reference/rules/<ID>.md` files, embedded in each product's
//! binary through [`rule_pages!`]; one source feeds the web reference, the terminal and the JSON
//! `data` (diagnostics.md sections 1.2, 5.1 and 6). A product registers a thin verb that calls
//! [`explain`] with its own page table.

// frob:ticket 01M3ZX7ZD77ZW385N5B992NX3A

use std::io::IsTerminal;
use std::time::Duration;

use gob_exec::{Limits, Program, Runner, Spec};
use schemars::JsonSchema;
use serde::Serialize;

use crate::{CliError, Context, FormatChoice, Outcome, Payload};

/// How many near ids an unknown-id error offers.
const SUGGESTIONS: usize = 3;

/// Edit distance at or under which an id counts as a near miss.
const NEAR: usize = 3;

/// One embedded rule page: the rule id and the full generated markdown.
pub type Page = (&'static str, &'static str);

/// Embed the generated rule pages named by id, as a `&'static [Page]` table.
///
/// The paths resolve against the calling crate's manifest directory, so the caller must sit two
/// levels under the workspace root (`crates/<name>`).
#[macro_export]
macro_rules! rule_pages {
    ($($id:literal),* $(,)?) => {
        &[$((
            $id,
            include_str!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../docs/reference/rules/",
                $id,
                ".md"
            )),
        )),*] as &'static [$crate::Page]
    };
}

/// The positional id every product's `explain` verb takes.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
pub struct ExplainArgs {
    /// The rule id to explain, for example `TODO001`.
    #[arg(
        value_name = "RULE",
        help = "The rule id to explain, for example TODO001"
    )]
    pub rule: String,
}

/// Output of `explain`: the rule id and its full page.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ExplainData {
    /// The canonical (upper-case) rule id.
    pub id: String,
    /// The full rule page, markdown.
    pub page: String,
}

/// Levenshtein distance between two strings, by chars.
fn distance(a: &str, b: &str) -> usize {
    let b: Vec<char> = b.chars().collect();
    let mut row: Vec<usize> = (0..=b.len()).collect();
    for (i, ca) in a.chars().enumerate() {
        let mut diag = row[0];
        row[0] = i + 1;
        for (j, cb) in b.iter().enumerate() {
            let above = row[j + 1];
            row[j + 1] = (diag + usize::from(ca != *cb))
                .min(above + 1)
                .min(row[j] + 1);
            diag = above;
        }
    }
    row[b.len()]
}

/// The ids of `pages` closest to `wanted` (upper-case), best first, at most `SUGGESTIONS`.
pub fn closest(pages: &[Page], wanted: &str) -> Vec<&'static str> {
    let mut scored: Vec<(usize, &'static str)> = pages
        .iter()
        .map(|(id, _)| {
            let mut d = distance(id, wanted);
            if id.starts_with(wanted) || wanted.starts_with(id) {
                d = d.min(1);
            }
            (d, *id)
        })
        .filter(|(d, _)| *d <= NEAR)
        .collect();
    scored.sort_unstable();
    scored
        .into_iter()
        .take(SUGGESTIONS)
        .map(|(_, id)| id)
        .collect()
}

/// Find the page for `id` (any case), or the usage error naming the closest ids.
///
/// # Errors
///
/// `CliError::Usage` (exit 2) with a did-you-mean when `id` is not in `pages`.
pub fn find(pages: &[Page], id: &str) -> Result<(&'static str, &'static str), CliError> {
    let wanted = id.trim().to_ascii_uppercase();
    if let Some((found, page)) = pages.iter().find(|(known, _)| *known == wanted) {
        return Ok((found, page));
    }
    let near = closest(pages, &wanted);
    tracing::debug!(id = %wanted, near = near.len(), "explain: unknown rule id");
    let message = if near.is_empty() {
        format!("no rule `{}`; see docs/reference/rules", id.trim())
    } else {
        let list = near
            .iter()
            .map(|n| format!("`{n}`"))
            .collect::<Vec<_>>()
            .join(", ");
        format!("no rule `{}`; did you mean {list}?", id.trim())
    };
    Err(CliError::Usage(message))
}

/// The pager program and its arguments: `$PAGER` when set and non-blank, else `less -R`.
pub fn pager_command(env_pager: Option<&str>) -> (String, Vec<String>) {
    let mut words = env_pager
        .map(str::split_whitespace)
        .into_iter()
        .flatten()
        .map(str::to_owned);
    match words.next() {
        Some(name) => (name, words.collect()),
        None => ("less".to_owned(), vec!["-R".to_owned()]),
    }
}

/// Show `page` in the pager; false when no pager could run (the caller prints plainly).
fn page_it(id: &str, page: &str) -> bool {
    let env = std::env::var("PAGER").ok();
    let (name, mut args) = pager_command(env.as_deref());
    let tmp = std::env::temp_dir().join(format!("explain-{}-{id}.md", std::process::id()));
    if let Err(e) = std::fs::write(&tmp, page) {
        tracing::debug!(error = %e, "explain: cannot stage the page for the pager");
        return false;
    }
    args.push(gob_path::Shown::with_home(&tmp, None).to_string());
    let spec = Spec {
        program: Program::Tool { name },
        args,
        cwd: None,
        env: Vec::new(),
        timeout: Duration::from_secs(3600),
        // Not captured: the pager owns the terminal.
        capture: false,
    };
    let ran = Runner::new(Limits { jobs: 1 }).run(&spec);
    if let Err(e) = std::fs::remove_file(&tmp) {
        tracing::debug!(error = %e, "explain: staged page already gone");
    }
    match ran {
        Ok(_) => true,
        Err(e) => {
            tracing::debug!(error = %e, "explain: no pager; printing");
            false
        }
    }
}

/// Run `explain RULE` against a product's page table.
///
/// JSON carries the page in `data`; text prints it plainly, or through the pager on a terminal.
///
/// # Errors
///
/// `CliError::Usage` (exit 2) when `rule` names no page.
pub fn explain(ctx: &Context, pages: &[Page], rule: &str) -> Outcome<ExplainData> {
    let (id, page) = find(pages, rule)?;
    let data = ExplainData {
        id: id.to_owned(),
        page: page.to_owned(),
    };
    let on_tty = ctx.format == FormatChoice::Text && std::io::stdout().is_terminal();
    if !ctx.json && !ctx.quiet && on_tty && page_it(id, page) {
        tracing::debug!(id, "explain: paged");
        return Ok(Payload::new(data).with_rendered(Vec::new()));
    }
    tracing::debug!(id, "explain: printed");
    let rows = vec![page.trim_end_matches('\n').to_owned()];
    Ok(Payload::new(data).with_rendered(rows))
}

#[cfg(test)]
mod tests {
    use super::*;

    const PAGES: &[Page] = &[
        ("TODO001", "# one\n"),
        ("TODO002", "# two\n"),
        ("SYS001", "# s\n"),
    ];

    // frob:tests crates/gob-cli/src/explain.rs::find
    #[test]
    fn a_known_id_in_any_case_finds_its_page() {
        assert_eq!(find(PAGES, "todo001").map(|p| p.1).ok(), Some("# one\n"));
    }

    // frob:tests crates/gob-cli/src/explain.rs::find
    #[test]
    fn an_unknown_id_is_a_usage_error_naming_the_closest_ids() {
        let err = find(PAGES, "TODO01").expect_err("unknown");
        assert_eq!(err.exit_code(), crate::ExitCode::Usage);
        let text = err.to_string();
        assert!(text.contains("`TODO001`"), "{text}");
        assert!(!text.contains("SYS001"), "{text}");
    }

    // frob:tests crates/gob-cli/src/explain.rs::find
    #[test]
    fn a_far_id_gets_no_suggestion() {
        let text = find(PAGES, "ZZZZZZZZ").expect_err("unknown").to_string();
        assert!(!text.contains("did you mean"), "{text}");
    }

    // frob:tests crates/gob-cli/src/explain.rs::pager_command
    #[test]
    fn the_pager_is_pager_env_then_less_dash_r() {
        assert_eq!(
            pager_command(Some("most -s")),
            ("most".to_owned(), vec!["-s".to_owned()])
        );
        assert_eq!(
            pager_command(Some("  ")),
            ("less".to_owned(), vec!["-R".to_owned()])
        );
        assert_eq!(
            pager_command(None),
            ("less".to_owned(), vec!["-R".to_owned()])
        );
    }
}
