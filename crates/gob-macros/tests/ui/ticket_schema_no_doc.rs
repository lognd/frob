use frob_ledger::schema::TicketSchema;

/// A schema.
#[derive(TicketSchema)]
struct S {
    #[ticket(required)]
    title: String,
}

fn main() {}
