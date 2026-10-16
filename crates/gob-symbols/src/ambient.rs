//! Ambient-source vocabularies: the callee names that read the clock, randomness, the
//! environment, files, the network, stdio or exit the process (the classes NEAT013 sweeps).

// frob:ticket 01M539NQGFCK3VJGRBM3H6CT56

use gob_ir::VocabEntry;

/// The ambient vocabulary classes, in the order the standard `sources` knob names them.
pub const AMBIENT_CLASSES: [&str; 7] = ["clock", "rng", "env", "fs", "net", "stdio", "exit"];

inventory::submit! {
    VocabEntry { lang: "python", kind: "clock", names: &[
        "time.time", "time.time_ns", "time.monotonic", "time.monotonic_ns", "time.perf_counter",
        "time.perf_counter_ns", "time.process_time", "datetime.now", "datetime.utcnow",
        "datetime.datetime.now", "datetime.datetime.utcnow", "datetime.date.today",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "rng", names: &[
        "random.random", "random.randint", "random.randrange", "random.choice", "random.shuffle",
        "random.uniform", "random.sample", "os.urandom", "secrets.token_bytes",
        "secrets.token_hex", "uuid.uuid4",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "env", names: &[
        "os.getenv", "os.putenv", "os.environ.get", "os.getcwd",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "stdio", names: &[
        "input", "sys.stdin.read", "sys.stdin.readline", "sys.stdout.write", "sys.stderr.write",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "exit", names: &["sys.exit", "os._exit", "exit", "quit"] }
}

/// Whether `name` is a registered ambient-source callee of `lang` (any ambient class).
pub fn is_ambient_name(lang: &str, name: &str) -> bool {
    let hit = AMBIENT_CLASSES.iter().any(|class| {
        matches!(
            gob_ir::registry::callee_vocab(lang, class),
            gob_ir::Answer::Exact(set) if set.contains(name)
        )
    });
    tracing::trace!(lang, name, hit, "ambient name lookup");
    hit
}

#[cfg(test)]
mod tests {
    use super::is_ambient_name;

    // frob:tests crates/gob-symbols/src/ambient.rs::is_ambient_name
    #[test]
    fn python_clock_and_rng_names_are_ambient_and_helpers_are_not() {
        assert!(is_ambient_name("python", "time.time"));
        assert!(is_ambient_name("python", "random.randint"));
        assert!(!is_ambient_name("python", "helper"));
        assert!(!is_ambient_name("lua", "time.time"));
    }
}
