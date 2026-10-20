//! `frob tour`: the repository tour in the terminal (`navigation.md` section 5).
//!
//! The stops come from the generated `TOUR.md` on the ticket branch. On a terminal one stop is
//! shown at a time with next and previous controls, and a linked file opens in the pager; anywhere
//! else (a pipe, `--json`) every stop is printed in order.

// frob:ticket 01M3ZX88BP9P0ZWPMJ5J5SBSMN

use gob_path::Shown;
use std::io::{BufRead, IsTerminal, Write};
use std::time::Duration;

use frob_ledger::Ledger;
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_diagnostics::RemedyCommand;
use gob_exec::{Limits, Program, Runner, Spec};
use schemars::JsonSchema;
use serde::Serialize;

/// Branch-relative path of the generated tour.
const TOUR_PATH: &str = "TOUR.md";

/// The heading prefix that starts a stop.
const STOP_PREFIX: &str = "## Stop ";

/// One stop of the tour.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Stop {
    /// 1-based position.
    pub number: usize,
    /// The heading text after `## `.
    pub title: String,
    /// The stop as markdown, heading included.
    pub body: String,
    /// Ticket-branch files the stop links to, in order, for the pager.
    pub links: Vec<String>,
}

/// Output of `frob tour`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TourData {
    /// Every stop, in order.
    pub stops: Vec<Stop>,
    /// True when this run walked the stops interactively.
    pub interactive: bool,
}

/// Show the repository tour: one stop at a time on a terminal, every stop otherwise.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "tour",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct TourVerb {
    all: bool,
}

/// Local file targets of the markdown links in `text`, percent-decoded, without anchors.
fn links_of(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut rest = text;
    while let Some(i) = rest.find("](") {
        rest = &rest[i + 2..];
        let Some(end) = rest.find(')') else { break };
        let target = rest[..end].split('#').next().unwrap_or_default();
        if !target.is_empty() && !target.contains("://") && !out.iter().any(|t| t == target) {
            out.push(target.replace("%20", " "));
        }
        rest = &rest[end..];
    }
    out
}

/// Split the generated tour into its stops; text before the first stop is dropped.
#[must_use]
pub fn split_stops(markdown: &str) -> Vec<Stop> {
    let mut stops: Vec<Stop> = Vec::new();
    for line in markdown.lines() {
        if let Some(title) = line
            .strip_prefix("## ")
            .filter(|_| line.starts_with(STOP_PREFIX))
        {
            stops.push(Stop {
                number: stops.len() + 1,
                title: title.to_owned(),
                body: String::new(),
                links: Vec::new(),
            });
        } else if line.starts_with("## ") {
            // A later section such as `## Notes` is not a stop.
            break;
        }
        if let Some(stop) = stops.last_mut() {
            stop.body.push_str(line);
            stop.body.push('\n');
        }
    }
    for stop in &mut stops {
        stop.body = stop.body.trim_end().to_owned();
        stop.links = links_of(&stop.body);
    }
    stops
}

/// Where a linked file is shown; the terminal session uses the pager.
pub trait Opener {
    /// Show `path` of the ticket branch.
    ///
    /// # Errors
    ///
    /// A message when the file cannot be shown.
    fn open(&mut self, path: &str) -> Result<(), String>;
}

/// Walk `stops` from the first with next and previous controls read from `input`.
///
/// Commands, one per line: empty or `n` next, `p` previous, `o N` open the Nth link of the stop,
/// `q` quit. End of input quits.
///
/// # Errors
///
/// Failures writing to `out` or reading `input`.
pub fn session(
    stops: &[Stop],
    input: &mut impl BufRead,
    out: &mut impl Write,
    opener: &mut dyn Opener,
) -> std::io::Result<()> {
    let total = stops.len();
    if total == 0 {
        return Ok(());
    }
    let mut at = 0;
    let mut show = true;
    loop {
        if show {
            let s = &stops[at];
            writeln!(out, "\n[{}/{total}]\n{}\n", s.number, s.body)?;
            for (i, l) in s.links.iter().enumerate() {
                writeln!(out, "  o {} opens {l}", i + 1)?;
            }
        }
        show = true;
        write!(out, "(n)ext, (p)revious, (o)pen N, (q)uit: ")?;
        out.flush()?;
        let mut line = String::new();
        if input.read_line(&mut line)? == 0 {
            writeln!(out)?;
            return Ok(());
        }
        let cmd = line.trim();
        match cmd {
            "" | "n" | "next" if at + 1 < total => at += 1,
            "" | "n" | "next" => {
                writeln!(out, "This is the last stop.")?;
                show = false;
            }
            "p" | "previous" if at > 0 => at -= 1,
            "p" | "previous" => {
                writeln!(out, "This is the first stop.")?;
                show = false;
            }
            "q" | "quit" => return Ok(()),
            _ => {
                let n = cmd
                    .strip_prefix('o')
                    .map(str::trim)
                    .and_then(|n| n.parse::<usize>().ok());
                let target = n
                    .and_then(|n| n.checked_sub(1))
                    .and_then(|i| stops[at].links.get(i));
                match target {
                    Some(path) => {
                        if let Err(e) = opener.open(path) {
                            writeln!(out, "cannot open {path}: {e}")?;
                        }
                    }
                    None => writeln!(out, "unknown command `{cmd}`")?,
                }
                show = false;
            }
        }
    }
}

/// Opens a ticket-branch file in `$PAGER` (`less` by default) through [`Runner`], or prints it when no pager starts.
struct PagerOpener<'a> {
    ledger: &'a Ledger,
    tip: String,
}

impl Opener for PagerOpener<'_> {
    fn open(&mut self, path: &str) -> Result<(), String> {
        let full = format!("{}{path}", self.ledger.tree_prefix());
        let bytes = self
            .ledger
            .repo()
            .read_blob_at(&self.tip, &full)
            .map_err(|e| e.to_string())?
            .ok_or_else(|| "not on the ticket branch".to_owned())?;
        let pager = std::env::var("PAGER").unwrap_or_else(|_| "less".to_owned());
        let mut words = pager.split_whitespace().map(str::to_owned);
        let name = words.next().unwrap_or_else(|| "less".to_owned());
        let name_of_file = path.rsplit('/').next().unwrap_or("page");
        let tmp =
            std::env::temp_dir().join(format!("frob-tour-{}-{name_of_file}", std::process::id()));
        std::fs::write(&tmp, &bytes).map_err(|e| e.to_string())?;
        let mut args: Vec<String> = words.collect();
        args.push(Shown::with_home(&tmp, None).to_string());
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
        let _ = std::fs::remove_file(&tmp);
        if let Err(e) = ran {
            tracing::debug!(error = %e, "no pager; printing");
            std::io::stdout()
                .write_all(&bytes)
                .map_err(|e| e.to_string())?;
        }
        Ok(())
    }
}

/// `TourVerb` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct TourArgs {
    #[arg(long, help = "Print every stop in order even on a terminal")]
    all: bool,
}

impl Command for TourVerb {
    type Data = TourData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<TourArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<TourArgs>(m)?;
        Ok(Self { all: a.all })
    }

    fn run(&self, ctx: &Context) -> Outcome<TourData> {
        let ledger = crate::ticket::open(ctx)?;
        let tip = ledger.ledger_ref().map_err(CliError::internal)?;
        let path = format!("{}{TOUR_PATH}", ledger.tree_prefix());
        let bytes = ledger
            .repo()
            .read_blob_at(&tip, &path)
            .map_err(CliError::internal)?;
        let text = bytes
            .map(String::from_utf8)
            .transpose()
            .map_err(CliError::internal)?;
        let stops = text.as_deref().map(split_stops).unwrap_or_default();
        if stops.is_empty() {
            return Err(Refusal::new(
                "E-TOUR-MISSING",
                RefusalClass::GuardNeedsAction,
                "the ticket branch has no generated tour yet",
            )
            .with_command(RemedyCommand::new("frob", "ticket reindex"))
            .into());
        }
        let interactive = !self.all
            && !ctx.json
            && !ctx.markdown()
            && std::io::stdin().is_terminal()
            && std::io::stdout().is_terminal();
        tracing::info!(stops = stops.len(), interactive, "tour");
        if interactive {
            let mut opener = PagerOpener {
                ledger: &ledger,
                tip,
            };
            session(
                &stops,
                &mut std::io::stdin().lock(),
                &mut std::io::stdout().lock(),
                &mut opener,
            )
            .map_err(CliError::internal)?;
            return Ok(Payload::new(TourData { stops, interactive }).with_rendered(Vec::new()));
        }
        let rows = stops
            .iter()
            .flat_map(|s| s.body.lines().map(str::to_owned).chain([String::new()]))
            .collect();
        Ok(Payload::new(TourData { stops, interactive }).with_rendered(rows))
    }
}

/// Register the tour verb.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<TourVerb>()
}
