//! The read-only lease verbs: `lease list` and `ticket contention`.

use frob_ledger::TicketId;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::overlap_is_lockfiles;
use crate::error::{LeaseError, SAME_TICKET};
use crate::model::Lease;
use crate::open_store_from_file as open_store;
use crate::store::{Contended, CorruptLease};

impl From<LeaseError> for CliError {
    fn from(e: LeaseError) -> Self {
        match e.to_refusal() {
            Some(r) => {
                let r = match &e {
                    LeaseError::Held {
                        ticket, overlap, ..
                    } if overlap == SAME_TICKET => r.with_remedy(format!(
                        "wait and rerun, or take it over with `frob work {ticket} --steal --reason <why>`"
                    )),
                    // frob:ticket 01M418TM2GZ24YPQE7ECTKE1J4
                    LeaseError::Held {
                        ticket, overlap, ..
                    } if overlap_is_lockfiles(overlap) => r.with_remedy(format!(
                        "the overlap is only generated lockfiles: ({overlap}) add them to `[lease] shared_files` in frob.toml, or delete that key to get the default lockfile list, so tickets can run in parallel; or wait until the lease on {ticket} ends"
                    )),
                    LeaseError::Held { ticket, .. } => r.with_remedy(format!(
                        "wait until the lease on {ticket} ends (`frob requeue {ticket} --reason <why>` frees it), then rerun"
                    )),
                    LeaseError::Format { path, .. } => {
                        r.with_remedy(format!(
                            "move {} aside (rename it to <name>.toml.corrupt) and rerun",
                            path.display()
                        ))
                    }
                    _ => r,
                };
                r.into()
            }
            None => CliError::internal(e),
        }
    }
}

/// Output of `lease list`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct LeaseListData {
    /// Live leases ordered by ticket.
    pub leases: Vec<Lease>,
    /// Lease files that could not be read; skipped, not deleted.
    pub corrupt: Vec<CorruptLease>,
}

/// List the live scope leases of this clone.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "lease list",
    product = "frob",
    idempotent = true,
    exits(ok, refused, internal)
)]
pub struct LeaseList;

impl Command for LeaseList {
    type Data = LeaseListData;

    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<LeaseListData> {
        let (store, _) = open_store(&ctx.cwd)?;
        let leases = store.list()?;
        let corrupt = store.corrupt_leases()?;
        let mut payload = Payload::new(LeaseListData { leases, corrupt });
        for c in payload.data.corrupt.clone() {
            payload = payload.with_warning(format!(
                "corrupt lease file {} skipped ({}); move it aside (rename it to <name>.toml.corrupt)",
                c.path.display(),
                c.message
            ));
        }
        Ok(payload)
    }
}

/// Output of `ticket contention`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ContentionData {
    /// Files declared by two or more live leases, most contended first.
    pub files: Vec<ContendedFile>,
}

/// One contended file as reported.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ContendedFile {
    /// Repository-relative path.
    pub file: String,
    /// How many live leases declare it.
    pub holders: usize,
    /// The tickets holding those leases.
    pub tickets: Vec<TicketId>,
}

impl From<Contended> for ContendedFile {
    fn from(c: Contended) -> Self {
        Self {
            holders: c.tickets.len(),
            file: c.file,
            tickets: c.tickets,
        }
    }
}

/// Print the files claimed by more than one live lease, ranked by holder count.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket contention",
    product = "frob",
    idempotent = true,
    exits(ok, refused, internal)
)]
pub struct Contention;

impl Command for Contention {
    type Data = ContentionData;

    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<ContentionData> {
        let (store, _) = open_store(&ctx.cwd)?;
        let files = store.contention()?.into_iter().map(Into::into).collect();
        Ok(Payload::new(ContentionData { files }))
    }
}
