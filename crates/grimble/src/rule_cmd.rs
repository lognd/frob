//! `rule test`, `rule check`, `rule catalog`, `rule fmt` and `rule new`: thin verbs over `gob_plan::verbs`.

// frob:ticket 01M6EXZE3ARQ1855G1KSNCFGZ5

/// Attach plain pre-rendered rows to a payload.
fn render<T>(payload: gob_cli::Payload<T>, rows: Vec<String>) -> gob_cli::Payload<T> {
    payload.with_rendered(rows)
}

gob_product::rule_verbs!("grimble", render);
