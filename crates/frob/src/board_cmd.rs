//! `frob board`: the scrumban board as text columns, or the same data as JSON.
//!
//! The board is built by [`frob_pm::board::build`] from the one WIP count
//! (`frob_pm::rules::wip::read`, shared with `PM013` and `work`), so limits and
//! over-limit marks always agree with them. Text mode hands the rendered rows
//! to [`Payload::with_rendered`] (printed raw, no envelope header or indent)
//! and leaves the structure out; `--json` carries the structure in `board`.
//!
//! `--brief` (D104/D105: a flag, not a verb) derives the compact view
//! ([`frob_pm::board::Brief`]) from that same board: what is in progress with
//! its last observed signal, what is next and what is blocked. The signal is
//! never declared: it is the newest of the lease heartbeat, a commit on the
//! ticket branch not on the base, and the ticket's evidence, land and
//! category-move events. `--json --brief` carries the structure in `brief`.

// frob:ticket 01M4069W45P08YPC4YH4XZVMNC
// frob:ticket 01M48Q29NESQDWE88YC8HBYT4Z

use std::collections::{BTreeMap, BTreeSet};
use std::io::IsTerminal;
use std::path::Path;
use std::time::Duration;

use frob_ledger::TicketId;
use frob_ledger::guards::NoLeases;
use frob_ledger::index::ListFilter;
use frob_ledger::index::Summary;
use frob_ledger::model::{Category, LinkKind, Stamp};
use frob_pm::board::{self, Board, Brief, BriefInput, Input, RenderOptions, Signal, SignalKind};
use frob_pm::rules::wip::{self, WipLimits};
use gob_cli::clap::{Arg, ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_diagnostics::ColorChoice;
use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::ticket::{cli_err, open, open_lease_store};
use crate::workspace::{Located, config_refusal};

/// Width used when stdout is not a terminal and `--width` is not given.
pub const FALLBACK_WIDTH: usize = 100;

/// Output of `board`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BoardData {
    /// The board, in JSON mode.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub board: Option<Board>,
    /// The compact view, in JSON mode with `--brief`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub brief: Option<Brief>,
}

/// Longest a `git log` for one ticket branch may run.
const GIT_TIMEOUT: Duration = Duration::from_secs(10);

/// Whether the board reads events for `s`: any open ticket, or a done one inside the done window.
fn recent_done(s: &Summary, now: Stamp) -> bool {
    s.category != Category::Done || now.unix() - s.updated.unix() <= board::DONE_DAYS * 86_400
}

/// The `--brief` signals of each in-progress ticket, by handle.
type Signals = BTreeMap<String, Vec<Signal>>;

/// Card entry times and `--brief` signals, from one bulk read of the events of the tickets that need them.
// frob:ticket 01M4BH8WMBDTAT4R0ST9VT321D
fn read_events(
    ledger: &frob_ledger::Ledger,
    tickets: &[Summary],
    brief: bool,
    now: Stamp,
) -> Result<(BTreeMap<TicketId, Stamp>, Signals), CliError> {
    let in_progress = |s: &Summary| brief && s.category == Category::InProgress;
    let wanted: BTreeSet<TicketId> = tickets
        .iter()
        .filter(|s| in_progress(s) || recent_done(s, now))
        .map(|s| s.id)
        .collect();
    let all_events = ledger.events_many(&wanted).map_err(cli_err)?;
    let mut entered = BTreeMap::new();
    let mut signals = Signals::new();
    for s in tickets {
        let Some(events) = all_events.get(&s.id) else {
            continue;
        };
        if in_progress(s) {
            signals.insert(
                s.handle.clone(),
                board::observe(events).into_iter().collect(),
            );
        }
        if recent_done(s, now) {
            entered.insert(s.id, board::entered(events, s));
        }
    }
    Ok((entered, signals))
}

/// Commit time of the newest commit on `branch` that the checked-out base lacks, or `None`.
fn last_commit(runner: &Runner, root: &Path, branch: &str) -> Option<Stamp> {
    let spec = Spec {
        program: Program::Git,
        args: ["log", "-1", "--format=%ct", &format!("HEAD..{branch}")]
            .map(str::to_owned)
            .to_vec(),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: GIT_TIMEOUT,
        capture: true,
    };
    let out = runner.run(&spec).ok()?;
    if out.status != ExecOutcome::Exited(0) {
        tracing::debug!(branch, "no readable branch commits");
        return None;
    }
    out.stdout.trim().parse::<i64>().ok().map(Stamp::from_unix)
}

/// Show the scrumban board: columns by category with WIP limits, the expedite lane and card ages.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "board",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct BoardVerb {
    width: Option<usize>,
    cards: usize,
    brief: bool,
}

/// The line width for text mode: `--width`, else `COLUMNS` on a terminal, else [`FALLBACK_WIDTH`].
pub fn resolve_width(flag: Option<usize>, columns: Option<&str>, tty: bool) -> usize {
    flag.or_else(|| {
        columns
            .filter(|_| tty)
            .and_then(|c| c.trim().parse::<usize>().ok())
    })
    .filter(|w| *w > 0)
    .unwrap_or(FALLBACK_WIDTH)
}

/// What [`brief_input`] reads: the repository, ledger, leases and the ledger signals already observed.
struct BriefSources<'a> {
    root: &'a Path,
    ledger: &'a frob_ledger::Ledger,
    tickets: &'a [frob_ledger::index::Summary],
    leases: &'a [frob_lease::Lease],
    signals: BTreeMap<String, Vec<Signal>>,
    blocked: &'a [(TicketId, String)],
    now: Stamp,
}

/// Gather the brief's extras: worktrees, last signals (ledger, lease heartbeat, branch commits) and open blockers.
fn brief_input(src: BriefSources<'_>) -> Result<BriefInput, CliError> {
    let BriefSources {
        root,
        ledger,
        tickets,
        leases,
        mut signals,
        blocked,
        now,
    } = src;
    let runner = Runner::new(Limits { jobs: 1 });
    let mut worktrees = BTreeMap::new();
    for l in leases {
        let Some(t) = tickets.iter().find(|t| t.id == l.ticket) else {
            continue;
        };
        let Some(list) = signals.get_mut(&t.handle) else {
            continue;
        };
        worktrees.insert(t.handle.clone(), l.holder.worktree.display().to_string());
        list.push(Signal {
            kind: SignalKind::Lease,
            at: l.renewed_at,
        });
        if let Some(dir) = l.holder.worktree.file_name() {
            let branch = format!("ticket/{}", dir.to_string_lossy());
            if let Some(at) = last_commit(&runner, root, &branch) {
                list.push(Signal {
                    kind: SignalKind::Commit,
                    at,
                });
            }
        }
    }
    let mut blockers = BTreeMap::new();
    for (id, handle) in blocked {
        let view = ledger.show(*id).map_err(cli_err)?;
        let open: Vec<String> = view
            .outgoing
            .iter()
            .chain(&view.incoming)
            .filter(|l| l.kind == LinkKind::BlockedBy && l.category != Some(Category::Done))
            .filter_map(|l| l.handle.clone())
            .collect();
        blockers.insert(handle.clone(), open);
    }
    tracing::debug!(
        worktrees = worktrees.len(),
        blocked = blockers.len(),
        "brief inputs gathered"
    );
    Ok(BriefInput {
        worktrees,
        signals: signals
            .into_iter()
            .filter_map(|(h, v)| board::latest(v).map(|s| (h, s)))
            .collect(),
        blockers,
        now: Some(now),
    })
}

/// Pick the payload data and text rows for the chosen view (`--brief`, `--json`, text).
fn present(
    board: Board,
    brief: Option<Brief>,
    ctx: &Context,
    width: usize,
) -> (BoardData, Option<Vec<String>>) {
    let none = BoardData {
        board: None,
        brief: None,
    };
    match (brief, ctx.json) {
        (Some(brief), true) => (
            BoardData {
                brief: Some(brief),
                ..none
            },
            None,
        ),
        (Some(brief), false) => (none, Some(board::render_brief(&brief, width))),
        (None, true) => (
            BoardData {
                board: Some(board),
                ..none
            },
            None,
        ),
        (None, false) => {
            let opts = RenderOptions {
                width,
                color: ctx.color == ColorChoice::Always,
            };
            (none, Some(board::render(&board, &opts)))
        }
    }
}

impl Command for BoardVerb {
    type Data = BoardData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("width")
                .long("width")
                .value_name("COLUMNS")
                .value_parser(gob_cli::clap::value_parser!(usize))
                .help("Text width; default the terminal's COLUMNS, else 100"),
        )
        .arg(
            Arg::new("cards")
                .long("cards")
                .value_name("N")
                .value_parser(gob_cli::clap::value_parser!(usize))
                .help("Most cards per column (0 lists all); in-progress is never cut [default: 8]"),
        )
        .arg(
            Arg::new("brief")
                .long("brief")
                .action(gob_cli::clap::ArgAction::SetTrue)
                .help("Compact view: in progress with last signal, next, blocked"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            width: m.get_one::<usize>("width").copied(),
            cards: m
                .get_one::<usize>("cards")
                .copied()
                .unwrap_or(board::DEFAULT_SHOWN),
            brief: m.get_flag("brief"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<BoardData> {
        let ledger = open(ctx)?;
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let limits = WipLimits {
            in_progress: cfg.pm.wip.in_progress,
            expedite_max: cfg.pm.classes.expedite_max,
        };
        let now = ctx.clock.now();

        let mut warnings = Vec::new();
        let (holders, live, leases) = match open_lease_store(ctx)
            .and_then(|(s, _)| s.live_snapshot().map_err(CliError::from))
        {
            Ok(leases) => {
                let ids: BTreeSet<TicketId> = leases.iter().map(|l| l.ticket).collect();
                let holders: BTreeMap<TicketId, String> = leases
                    .iter()
                    .map(|l| (l.ticket, l.holder.actor.clone()))
                    .collect();
                (holders, Some(ids), leases)
            }
            Err(e) => {
                tracing::warn!(error = %e, "leases unreadable; board counts every in-progress ticket");
                warnings.push(format!(
                    "leases unreadable ({e}); every in-progress ticket is counted as live"
                ));
                (BTreeMap::new(), None, Vec::new())
            }
        };
        let wip = wip::read(&ledger, live.as_ref(), limits.expedite_max).map_err(cli_err)?;
        let tickets = ledger.list(&ListFilter::default()).map_err(cli_err)?;
        let doable_order: Vec<TicketId> = ledger
            .doable(&NoLeases)
            .map_err(cli_err)?
            .into_iter()
            .map(|s| s.id)
            .collect();

        let (entered, signals) = read_events(&ledger, &tickets, self.brief, now)?;
        let blocked_ids: Vec<(TicketId, String)> = tickets
            .iter()
            .filter(|s| s.blocked && s.category == Category::Todo)
            .map(|s| (s.id, s.handle.clone()))
            .collect();
        let board = board::build(&Input {
            tickets: tickets.clone(),
            wip,
            limits,
            entered,
            holders,
            doable_order,
            now,
            show: self.cards,
        });
        tracing::info!(
            columns = board.columns.len(),
            lane = board.expedite.is_some(),
            json = ctx.json,
            "board built"
        );

        let tty = std::io::stdout().is_terminal();
        let width = resolve_width(self.width, std::env::var("COLUMNS").ok().as_deref(), tty);
        let brief = if self.brief {
            let extra = brief_input(BriefSources {
                root: &root,
                ledger: &ledger,
                tickets: &tickets,
                leases: &leases,
                signals,
                blocked: &blocked_ids,
                now,
            })?;
            Some(board::brief(&board, &extra))
        } else {
            None
        };
        let (data, rows) = present(board, brief, ctx, width);
        let mut payload = Payload::new(data);
        if let Some(rows) = rows {
            payload = payload.with_rendered(rows);
        }
        for w in warnings {
            payload = payload.with_warning(w);
        }
        Ok(payload)
    }
}
