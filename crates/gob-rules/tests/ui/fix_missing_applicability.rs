// frob:ticket 01M3ZX7E968R74N08V8DW4RJVG
use gob_rules::{Fix, FixKind};

fn main() {
    let _ = Fix {
        kind: FixKind::Deterministic,
        title: String::new(),
        edits: vec![],
    };
}
