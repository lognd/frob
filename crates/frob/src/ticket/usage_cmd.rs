//! `ticket usage`: record the model tokens a working session spent on a ticket, for `frob stats` cost per token.
// frob:ticket 01M59VC5Y4HWJYV4KWSM02ESM8

use frob_ledger::event::{EventBody, UsageData};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome};

use super::{ChangeData, TicketArg, cli_err, open, payload, resolve};

/// Record token usage on a ticket as an audit event; `frob stats` sums these into cost per token.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket usage",
    product = "frob",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
pub struct Usage {
    ticket: String,
    data: UsageData,
}

/// The flags of `ticket usage`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct UsageArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(long, value_name = "N", help = "Fresh input tokens")]
    input: u64,
    #[arg(long, value_name = "N", help = "Output tokens")]
    output: u64,
    #[arg(
        long,
        value_name = "N",
        default_value_t = 0,
        help = "Input tokens read from the prompt cache"
    )]
    cache_read: u64,
    #[arg(
        long,
        value_name = "N",
        default_value_t = 0,
        help = "Input tokens written to the prompt cache"
    )]
    cache_create: u64,
}

impl Command for Usage {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<UsageArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<UsageArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            data: UsageData {
                input: a.input,
                output: a.output,
                cache_read: a.cache_read,
                cache_create: a.cache_create,
            },
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let applied = ledger
            .append(id, EventBody::Usage(self.data))
            .map_err(cli_err)?;
        tracing::info!(ticket = %id, total = self.data.total(), "ticket usage recorded");
        Ok(payload(&applied))
    }
}

#[cfg(test)]
mod tests {
    use frob_ledger::event::UsageData;

    #[test]
    fn total_sums_every_kind_of_token() {
        // frob:tests crates/frob-ledger/src/event.rs::UsageData::total
        let u = UsageData {
            input: 1,
            output: 2,
            cache_read: 3,
            cache_create: 4,
        };
        assert_eq!(u.total(), 10);
    }
}
