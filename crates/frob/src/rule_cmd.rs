//! `rule test`, `rule check`, `rule catalog`, `rule fmt` and `rule new`: thin verbs over `gob_plan::verbs`.

// frob:ticket 01M6EXZE3ARQ1855G1KSNCFGZ5
use crate::pretty::PrettyExt;

/// Attach colour-decorated rows to a payload (frob's terminal-aware text view).
fn render<T>(payload: gob_cli::Payload<T>, rows: Vec<String>) -> gob_cli::Payload<T> {
    payload.with_pretty(rows)
}

gob_product::rule_verbs!("frob", render);
