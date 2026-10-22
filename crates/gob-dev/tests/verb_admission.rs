//! Verb admission (cli.md section 4.0, D104): every registered verb of frob, grimble and crunk has
//! a row in the section 4 table naming its justification (effect, policy or object), and every
//! Milestone 1 row names a registered verb, so the implementation and the design cannot drift.
// frob:ticket 01M48Q28JZ3AB6FNJ8H2Y6V4G2

use std::collections::BTreeSet;
use std::path::PathBuf;

/// One verb path of one product, for example `("frob", "ticket show")`.
type VerbKey = (String, String);

/// One table row of cli.md section 4.0.
#[derive(Debug)]
struct Row {
    /// Verb paths the row names, per product (`grimble` rows carry their own product).
    verbs: Vec<VerbKey>,
    /// The raw first cell, for messages.
    cell: String,
    /// The `M` column: the milestone that builds it.
    milestone: String,
    /// The `Justification` column.
    justification: String,
    /// True for the catch-all row of a product whose verbs live in another file (no backticked verb).
    product_wide: Option<String>,
}

/// The section 4.0 body of cli.md.
fn section(doc: &str) -> &str {
    let start = doc.find("### 4.0 ").expect("cli.md has section 4.0");
    let rest = &doc[start..];
    let end = rest.find("### 4.1 ").expect("cli.md has section 4.1");
    &rest[..end]
}

/// Cells of a table line, splitting on `|` that is not escaped as `\|`.
fn cells(line: &str) -> Vec<String> {
    let body = line.trim().trim_start_matches('|').trim_end_matches('|');
    let mut out = vec![String::new()];
    let mut prev = ' ';
    for c in body.chars() {
        if c == '|' && prev != '\\' {
            out.push(String::new());
        } else if let Some(last) = out.last_mut() {
            last.push(c);
        }
        prev = c;
    }
    out.into_iter().map(|c| c.trim().to_string()).collect()
}

/// Verb paths named by one backticked span: leading plain words, the last one may be `a\|b\|c`.
fn expand_span(span: &str, product: &str) -> Vec<VerbKey> {
    let span = span.replace("\\|", "|");
    let mut words: Vec<&str> = Vec::new();
    for w in span.split_whitespace() {
        if w.starts_with(['[', '<', '-', '(']) {
            break;
        }
        words.push(w);
    }
    let mut product = product.to_string();
    if words.len() > 1 && matches!(words[0], "frob" | "grimble" | "crunk") {
        product = words.remove(0).to_string();
    }
    let Some(last) = words.pop() else {
        return Vec::new();
    };
    let head = words.join(" ");
    last.split('|')
        .map(|alt| {
            let path = if head.is_empty() {
                alt.to_string()
            } else {
                format!("{head} {alt}")
            };
            (product.clone(), path)
        })
        .collect()
}

/// Backticked spans of a cell.
fn spans(cell: &str) -> Vec<&str> {
    cell.split('`').skip(1).step_by(2).collect()
}

/// Parse the section 4.0 table; the error names the problem (a missing `Justification` column).
fn parse_rows(doc: &str) -> Result<Vec<Row>, String> {
    let mut lines = section(doc)
        .lines()
        .filter(|l| l.trim_start().starts_with('|'));
    let header = cells(lines.next().ok_or("section 4.0 has no table")?);
    let col = |name: &str| {
        header
            .iter()
            .position(|h| h == name)
            .ok_or(format!("the verb table has no `{name}` column"))
    };
    let (ci_product, ci_m, ci_just) = (col("Product")?, col("M")?, col("Justification")?);
    let mut rows = Vec::new();
    for line in lines.skip(1) {
        let c = cells(line);
        if c.len() != header.len() {
            return Err(format!(
                "row `{}` has {} cells, the header has {}",
                c.first().map_or("", String::as_str),
                c.len(),
                header.len()
            ));
        }
        let products: Vec<&str> = c[ci_product].split(',').map(str::trim).collect();
        let found = spans(&c[0]);
        let mut verbs = Vec::new();
        for p in &products {
            for s in &found {
                verbs.extend(expand_span(s, p));
            }
        }
        let product_wide =
            (found.is_empty() && products.len() == 1).then(|| products[0].to_string());
        verbs.sort();
        verbs.dedup();
        rows.push(Row {
            verbs,
            cell: c[0].clone(),
            milestone: c[ci_m].clone(),
            justification: c[ci_just].clone(),
            product_wide,
        });
    }
    Ok(rows)
}

/// True when one verb path equals the other or is a sub-path of it (`ticket evidence` covers `ticket evidence add`).
fn related(a: &str, b: &str) -> bool {
    a == b || a.starts_with(&format!("{b} ")) || b.starts_with(&format!("{a} "))
}

/// True when `row` names `verb` of `product` (`any` matches every product).
fn names(row: &Row, product: &str, verb: &str) -> bool {
    row.product_wide.as_deref() == Some(product)
        || row
            .verbs
            .iter()
            .any(|(p, v)| (product == "any" || p == product) && related(v, verb))
}

/// Every drift between the registry and the rows, each message naming the verb or row.
fn problems(rows: &[Row], registry: &BTreeSet<VerbKey>) -> Vec<String> {
    let mut out = Vec::new();
    for row in rows {
        let prefix = row.justification.split(':').next().unwrap_or("");
        let body = row
            .justification
            .split_once(':')
            .map_or("", |(_, b)| b.trim());
        if !matches!(prefix, "effect" | "policy" | "object") || body.is_empty() {
            out.push(format!(
                "row {} has no justification of the form `effect|policy|object: why` (found `{}`)",
                row.cell, row.justification
            ));
        }
    }
    for (product, verb) in registry {
        if !rows.iter().any(|r| names(r, product, verb)) {
            out.push(format!(
                "registered verb `{product} {verb}` has no row in docs/design/cli.md section 4.0"
            ));
        }
    }
    for row in rows {
        if row.milestone.trim() != "1" {
            continue;
        }
        for (product, verb) in &row.verbs {
            let registered = registry
                .iter()
                .any(|(p, v)| (p == "any" || p == product) && related(v, verb));
            if !registered {
                out.push(format!(
                    "row names `{product} {verb}` (milestone 1) but no such verb is registered"
                ));
            }
        }
    }
    out
}

/// The live registry of the three products, hidden deprecated aliases excluded.
fn registry() -> BTreeSet<VerbKey> {
    // Linking the product crates registers their verbs with the inventory.
    std::hint::black_box((frob_cli::cli(), grimble::cli(), crunk::cli()));
    gob_cli::all_commands()
        .filter(|m| m.deprecated_form().is_none())
        .map(|m| (m.product.to_string(), m.verb.to_string()))
        .collect()
}

/// The real cli.md.
fn cli_md() -> String {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../docs/design/cli.md");
    std::fs::read_to_string(path).expect("docs/design/cli.md is readable")
}

/// A one-row table for the synthetic cases.
fn doc_with(rows: &[&str]) -> String {
    let mut s = String::from(
        "### 4.0 Verb admission\n\n| Verb | Product | Crate | Idempotent | Exit codes | M | Justification |\n|---|---|---|---|---|---|---|\n",
    );
    for r in rows {
        s.push_str(r);
        s.push('\n');
    }
    s.push_str("\n### 4.1 next\n");
    s
}

fn reg(items: &[(&str, &str)]) -> BTreeSet<VerbKey> {
    items
        .iter()
        .map(|(p, v)| (p.to_string(), v.to_string()))
        .collect()
}

// frob:tests crates/gob-cli/src/meta.rs::all_commands
#[test]
fn a_registered_verb_without_a_row_fails_naming_it() {
    let rows = parse_rows(&doc_with(&[
        "| `ticket show` | frob | c | yes | 0 | 1 | object: a ticket |",
    ]))
    .expect("parses");
    let found = problems(
        &rows,
        &reg(&[("frob", "ticket show"), ("frob", "ticket orphan")]),
    );
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("`frob ticket orphan`"), "{found:?}");
}

// frob:tests crates/gob-cli/src/meta.rs::all_commands
#[test]
fn a_row_without_a_registered_verb_fails_naming_it() {
    let rows = parse_rows(&doc_with(&[
        "| `ticket show` | frob | c | yes | 0 | 1 | object: a ticket |",
        "| `ticket ghost\\|phantom` | frob | c | yes | 0 | 1 | effect: haunts |",
        "| `ticket future` | frob | c | yes | 0 | 2 | effect: later |",
    ]))
    .expect("parses");
    let found = problems(&rows, &reg(&[("frob", "ticket show")]));
    assert_eq!(found.len(), 2, "{found:?}");
    assert!(
        found.iter().any(|f| f.contains("`frob ticket ghost`")),
        "{found:?}"
    );
    assert!(
        found.iter().any(|f| f.contains("`frob ticket phantom`")),
        "{found:?}"
    );
}

// frob:tests crates/gob-cli/src/meta.rs::all_commands
#[test]
fn the_justification_column_exists_for_every_row() {
    let missing = parse_rows(
        "### 4.0 x\n\n| Verb | Product | M |\n|---|---|---|\n| `a` | frob | 1 |\n\n### 4.1 y\n",
    );
    assert!(missing.expect_err("no column").contains("`Justification`"));

    let rows = parse_rows(&doc_with(&[
        "| `ticket show` | frob | c | yes | 0 | 1 | because |",
        "| `ticket list` | frob | c | yes | 0 | 1 | effect: |",
    ]))
    .expect("parses");
    let found = problems(
        &rows,
        &reg(&[("frob", "ticket show"), ("frob", "ticket list")]),
    );
    assert_eq!(found.len(), 2, "{found:?}");
    assert!(
        found[0].contains("`ticket show`") && found[1].contains("`ticket list`"),
        "{found:?}"
    );
}

// frob:tests crates/gob-cli/src/meta.rs::all_commands
#[test]
fn the_shipped_verb_table_matches_the_registry() {
    let rows = parse_rows(&cli_md()).expect("cli.md section 4.0 parses");
    let registry = registry();
    assert!(
        registry.len() > 100,
        "registry walk found {} verbs",
        registry.len()
    );
    let found = problems(&rows, &registry);
    assert!(found.is_empty(), "verb table drift:\n{}", found.join("\n"));
}
