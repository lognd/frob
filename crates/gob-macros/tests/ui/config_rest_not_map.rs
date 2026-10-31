use gob_config::ConfigTable;

/// A rest table whose field is not a map.
#[derive(ConfigTable)]
#[config(table = "x", rest)]
struct Bad {
    /// Entries.
    entries: Vec<String>,
}

fn main() {}
