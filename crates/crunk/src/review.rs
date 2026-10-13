//! `review` and `ack`: the human review queue and its person-only acknowledgement (crunk.md 4.1).
//!
//! `review` lists every screen state that needs a human review with where it stands and which
//! inputs changed since the last ack. `ack` records the current content digest into `crunk.lock`
//! as a `[[review]]` entry; it needs a terminal (a person at the keyboard) unless the caller
//! passes `--non-interactive`, which is recorded in the entry so a reviewer can see it.

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4

use std::io::IsTerminal;
use std::path::Path;

use crunk_check::review::{self as gather, AckRefusal, AckRequest, GitSignatures};
use crunk_rules::review::{ReviewFacts, ReviewStatus, Subject};
use gob_cli::clap::{Arg, ArgAction, ArgMatches, builder::PossibleValuesParser};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// One screen state's review standing.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct SubjectRow {
    /// The lock key, `screen/<id>/<state>`.
    pub subject: String,
    /// The screen id.
    pub screen: String,
    /// `current`, `missing`, `stale`, `unlisted`, `unsigned` or `rejected`.
    pub status: String,
    /// Input names that changed since the last ack (stale only).
    pub changed: Vec<String>,
    /// The sentence that explains the standing; empty when current.
    pub detail: String,
}

/// Output of `review`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ReviewData {
    /// Every subject that needs a human review.
    pub subjects: Vec<SubjectRow>,
    /// How many are not current.
    pub pending: usize,
}

/// Output of `ack`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AckData {
    /// The subjects recorded.
    pub acked: Vec<String>,
    /// `approved` or `rejected`.
    pub verdict: String,
    /// Who the entries name.
    pub reviewer: String,
    /// True when recorded without a terminal.
    pub non_interactive: bool,
}

fn refusal(code: &str, message: &str) -> Refusal {
    Refusal::new(code, RefusalClass::GuardNeedsAction, message)
}

fn word(status: &ReviewStatus) -> &'static str {
    match status {
        ReviewStatus::Current => "current",
        ReviewStatus::Missing => "missing",
        ReviewStatus::Stale(_) => "stale",
        ReviewStatus::Unlisted(_) => "unlisted",
        ReviewStatus::Unsigned(_) => "unsigned",
        ReviewStatus::Rejected(_) => "rejected",
    }
}

/// The loaded spec and its reviewable subjects, or a refusal.
fn load(root: &Path) -> Result<(crunk_spec::DesignSpec, Vec<Subject>), CliError> {
    let spec = crunk_spec::load_spec(root).map_err(|e| {
        refusal(
            "E-SPEC",
            &format!("crunk.toml is not a valid design spec: {e}"),
        )
        .with_remedy("fix crunk.toml as described, then rerun")
    })?;
    let subjects = gather::subjects(&spec).map_err(|why| refusal("E-REVIEW-TOKENS", &why))?;
    Ok((spec, subjects))
}

fn rows(facts: &ReviewFacts) -> Vec<SubjectRow> {
    facts
        .findings
        .iter()
        .map(|f| SubjectRow {
            subject: f.subject.clone(),
            screen: f.screen.clone(),
            status: word(&f.status).to_owned(),
            changed: match &f.status {
                ReviewStatus::Stale(c) => c.clone(),
                _ => Vec::new(),
            },
            detail: if f.status == ReviewStatus::Current {
                String::new()
            } else {
                f.message.clone()
            },
        })
        .collect()
}

/// List the screen states that need a human review and what changed since the last ack.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "review",
    product = "crunk",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Review;

impl Command for Review {
    type Data = ReviewData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd
    }

    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<ReviewData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let (spec, _) = load(&root)?;
        let facts = gather::gather(&spec, &GitSignatures::new(&root));
        if let Some(why) = &facts.unreadable {
            return Err(refusal("E-REVIEW-LOCK", why).into());
        }
        let subjects = rows(&facts);
        let pending = subjects.iter().filter(|s| s.status != "current").count();
        tracing::info!(subjects = subjects.len(), pending, "review queue built");
        let mut lines: Vec<String> = subjects
            .iter()
            .map(|s| format!("{:<9} {}  {}", s.status, s.subject, s.changed.join(", ")))
            .collect();
        if lines.is_empty() {
            lines.push("no screen needs a human review".to_owned());
        }
        Ok(Payload::new(ReviewData { subjects, pending }).with_rendered(lines))
    }
}

/// Record a human review of screen states into crunk.lock; needs a terminal unless --non-interactive.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "ack",
    product = "crunk",
    idempotent = false,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct Ack {
    subjects: Vec<String>,
    all_stale: bool,
    rejected: bool,
    note: Option<String>,
    non_interactive: bool,
}

impl Ack {
    /// True when the caller may record: a terminal on stdin and stdout, or an explicit opt-out.
    fn attended(&self, tty: bool) -> bool {
        tty || self.non_interactive
    }
}

impl Command for Ack {
    type Data = AckData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("subjects")
                .value_name("SUBJECT")
                .num_args(0..)
                .help("Subjects (screen/<id>/<state>) or screen ids to record"),
        )
        .arg(
            Arg::new("all_stale")
                .long("all-stale")
                .action(ArgAction::SetTrue)
                .help("Also record every subject whose review is missing or stale"),
        )
        .arg(
            Arg::new("verdict")
                .long("verdict")
                .value_name("VERDICT")
                .value_parser(PossibleValuesParser::new(["approved", "rejected"]))
                .default_value("approved")
                .help("The verdict to record; a rejection needs --note"),
        )
        .arg(
            Arg::new("note")
                .long("note")
                .value_name("TEXT")
                .help("A note stored with the entry"),
        )
        .arg(
            Arg::new("non_interactive")
                .long("non-interactive")
                .action(ArgAction::SetTrue)
                .help("Record without a terminal; the entry says so"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            subjects: m
                .get_many::<String>("subjects")
                .map(|v| v.cloned().collect())
                .unwrap_or_default(),
            all_stale: m.get_flag("all_stale"),
            rejected: m
                .get_one::<String>("verdict")
                .is_some_and(|v| v == "rejected"),
            note: m.get_one::<String>("note").cloned(),
            non_interactive: m.get_flag("non_interactive"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<AckData> {
        let tty = std::io::stdin().is_terminal() && std::io::stdout().is_terminal();
        if !self.attended(tty) {
            tracing::info!("ack refused: no terminal and no --non-interactive");
            return Err(refusal(
                "E-ACK-NO-TTY",
                "crunk ack records a human review and needs a terminal",
            )
            .with_remedy(
                "run it from a terminal, or pass --non-interactive to record it unattended",
            )
            .into());
        }
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let (spec, subjects) = load(&root)?;
        let path = gather::lock_path(&root);
        let mut lock = gob_lock::LockFile::load(&path)
            .map_err(|e| refusal("E-REVIEW-LOCK", &e.to_string()))?;
        let req = AckRequest {
            subjects: self.subjects.clone(),
            all_stale: self.all_stale,
            verdict: if self.rejected {
                gob_lock::ReviewVerdict::Rejected
            } else {
                gob_lock::ReviewVerdict::Approved
            },
            reviewer: gather::current_identity(&root),
            at: ctx.clock.now().to_string(),
            note: self.note.clone(),
            non_interactive: self.non_interactive && !tty,
        };
        let acked =
            gather::record(&mut lock, &spec, &subjects, &req).map_err(|e: AckRefusal| {
                let code = match e {
                    AckRefusal::UnknownSubject(_) => "E-ACK-SUBJECT",
                    AckRefusal::NotAReviewer(_) => "E-ACK-REVIEWER",
                    AckRefusal::NoteRequired => "E-ACK-NOTE",
                    AckRefusal::Nothing => "E-ACK-NOTHING",
                };
                refusal(code, &e.to_string())
            })?;
        if !ctx.dry_run {
            lock.save(&path)
                .map_err(|e| refusal("E-REVIEW-LOCK", &e.to_string()))?;
        }
        let lines = acked
            .iter()
            .map(|s| {
                format!(
                    "{} {s}",
                    if ctx.dry_run {
                        "would record"
                    } else {
                        "recorded"
                    }
                )
            })
            .collect();
        Ok(Payload::new(AckData {
            acked,
            verdict: if self.rejected {
                "rejected"
            } else {
                "approved"
            }
            .to_owned(),
            reviewer: req.reviewer,
            non_interactive: req.non_interactive,
        })
        .with_rendered(lines))
    }
}
