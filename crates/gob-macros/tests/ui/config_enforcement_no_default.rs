use gob_config::ConfigTable;

/// A table.
#[derive(ConfigTable)]
#[config(table = "tickets", materialize)]
struct Tickets {
    /// A knob without a default.
    #[config(enforcement)]
    cas_retries: u32,
}

fn main() {}
