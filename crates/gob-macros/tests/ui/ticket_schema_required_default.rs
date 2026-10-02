use frob_ledger::schema::TicketSchema;

/// A schema.
#[derive(TicketSchema)]
struct S {
    /// The title.
    #[ticket(required, default = "x")]
    title: String,
}

fn main() {}
