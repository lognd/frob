//! `frob board`: the scrumban board as text columns, or the same data as JSON.
//!
//! The board is built by [`frob_pm::board::build`] from the one WIP count
//! (`frob_pm::rules::wip::read`, shared with `PM013` and `work`), so limits and
//! over-limit marks always agree with them. Text mode hands the rendered rows
//! to [`Payload::with_rendered`] (printed raw, no envelope header or indent)
//! and leaves the structure out; `--json` carries the structure in `board`.

// frob:ticket 01M4069W45P08YPC4YH4XZVMNC

use std::collections::{BTreeMap, BTreeSet};
use std::io::IsTerminal;

use frob_ledger::TicketId;
use frob_ledger::guards::NoLeases;
use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, Stamp};
use frob_pm::board::{self, Board, Input, RenderOptions};
use frob_pm::rules::wip::{self, WipLimits};
use gob_cli::clap::{Arg, ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_diagnostics::ColorChoice;
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
}

/// Show the scrumban board: columns by category with WIP limits, the expedite lane and card ages.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "board",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct BoardVerb {
    width: Option<usize>,
    cards: usize,
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
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            width: m.get_one::<usize>("width").copied(),
            cards: m
                .get_one::<usize>("cards")
                .copied()
                .unwrap_or(board::DEFAULT_SHOWN),
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
        let now = Stamp::now();

        let mut warnings = Vec::new();
        let (holders, live) = match open_lease_store(ctx)
            .and_then(|(s, _)| s.live_snapshot().map_err(CliError::from))
        {
            Ok(leases) => {
                let ids: BTreeSet<TicketId> = leases.iter().map(|l| l.ticket).collect();
                let holders: BTreeMap<TicketId, String> = leases
                    .into_iter()
                    .map(|l| (l.ticket, l.holder.actor))
                    .collect();
                (holders, Some(ids))
            }
            Err(e) => {
                tracing::warn!(error = %e, "leases unreadable; board counts every in-progress ticket");
                warnings.push(format!(
                    "leases unreadable ({e}); every in-progress ticket is counted as live"
                ));
                (BTreeMap::new(), None)
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

        let mut entered = BTreeMap::new();
        for s in &tickets {
            let recent_done = s.category != Category::Done
                || now.unix() - s.updated.unix() <= board::DONE_DAYS * 86_400;
            if recent_done {
                let events = ledger.events(s.id).map_err(cli_err)?;
                entered.insert(s.id, board::entered(&events, s));
            }
        }
        let board = board::build(&Input {
            tickets,
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

        let (data, rows) = if ctx.json {
            (BoardData { board: Some(board) }, None)
        } else {
            let tty = std::io::stdout().is_terminal();
            let width = resolve_width(self.width, std::env::var("COLUMNS").ok().as_deref(), tty);
            let opts = RenderOptions {
                width,
                color: ctx.color == ColorChoice::Always,
            };
            (
                BoardData { board: None },
                Some(board::render(&board, &opts)),
            )
        };
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
