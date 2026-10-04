//! The `ticket.md` document: TOML frontmatter between `+++` fences, then markdown.

use crate::error::{LedgerError, Result};
use crate::model::{Frontmatter, Ticket, normalize_body};

const FENCE: &str = "+++";

/// True when some physical line of `text` would close the frontmatter.
fn has_fence_line(text: &str) -> bool {
    text.split_inclusive('\n').any(|l| l.trim_end() == FENCE)
}

/// `s` as a single-line TOML basic string (every control character escaped).
fn basic_string(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c.is_control() => out.push_str(&format!("\\u{:04X}", u32::from(c))),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// Replace every string in `v` that holds a fence line by a unique placeholder, recording the real text.
fn hide_fence_strings(v: &mut toml::Value, prefix: &str, hidden: &mut Vec<(String, String)>) {
    match v {
        toml::Value::String(s) if has_fence_line(s) => {
            let ph = format!("{prefix}{}", hidden.len());
            hidden.push((ph.clone(), std::mem::replace(s, ph)));
        }
        toml::Value::Array(a) => a
            .iter_mut()
            .for_each(|x| hide_fence_strings(x, prefix, hidden)),
        toml::Value::Table(t) => t
            .iter_mut()
            .map(|(_, v)| v)
            .for_each(|x| hide_fence_strings(x, prefix, hidden)),
        _ => {}
    }
}

/// Rewrite `front` so no line equals the fence: strings holding one become single-line escaped strings.
fn escape_fence_lines(front: &str) -> Option<String> {
    let mut table: toml::Table = toml::from_str(front).ok()?;
    let mut prefix = String::from("frob-fence-");
    while front.contains(&prefix) {
        prefix.push('x');
    }
    let mut hidden = Vec::new();
    for (_, v) in table.iter_mut() {
        hide_fence_strings(v, &prefix, &mut hidden);
    }
    let mut out = toml::to_string(&table).ok()?;
    for (ph, real) in hidden {
        out = out.replacen(&format!("\"{ph}\""), &basic_string(&real), 1);
    }
    tracing::debug!("escaped fence-equal lines in ticket frontmatter strings");
    Some(out)
}

/// Join TOML `front` and markdown `body` into a fenced document (the shape of every ledger object file).
///
/// A frontmatter line equal to the fence (inside a multi-line string) is escaped away, so the
/// closing fence is always the first fence line and every field round-trips.
pub fn fenced(front: &str, body: &str) -> String {
    let escaped;
    let front = if has_fence_line(front) {
        match escape_fence_lines(front) {
            Some(e) if !has_fence_line(&e) => {
                escaped = e;
                escaped.as_str()
            }
            _ => {
                tracing::error!("frontmatter holds a fence line that could not be escaped");
                front
            }
        }
    } else {
        front
    };
    let mut out = String::with_capacity(front.len() + body.len() + 16);
    out.push_str(FENCE);
    out.push('\n');
    out.push_str(front);
    if !front.ends_with('\n') {
        out.push('\n');
    }
    out.push_str(FENCE);
    out.push('\n');
    let body = normalize_body(body);
    if !body.is_empty() {
        out.push('\n');
        out.push_str(&body);
        out.push('\n');
    }
    out
}

/// Split a fenced document into its TOML frontmatter text and normalized body; `label` names it in errors.
///
/// # Errors
///
/// [`LedgerError::Malformed`] for a missing opening or closing fence.
pub fn split_fenced<'a>(label: &str, text: &'a str) -> Result<(&'a str, String)> {
    let bad = |m: &str| LedgerError::malformed(label, m);
    let rest = text
        .strip_prefix("+++\n")
        .or_else(|| text.strip_prefix("+++\r\n"))
        .ok_or_else(|| bad("missing opening `+++` fence on the first line"))?;
    let mut offset = 0;
    let mut close = None;
    for line in rest.split_inclusive('\n') {
        if line.trim_end() == FENCE {
            close = Some((offset, offset + line.len()));
            break;
        }
        offset += line.len();
    }
    let (front_end, body_start) = close.ok_or_else(|| bad("missing closing `+++` fence"))?;
    Ok((&rest[..front_end], normalize_body(&rest[body_start..])))
}

/// Render a ticket as the text of `ticket.md`.
///
/// # Errors
///
/// [`LedgerError::Malformed`] when the frontmatter cannot be written as TOML.
pub fn render(ticket: &Ticket) -> Result<String> {
    let front = toml::to_string(&ticket.front).map_err(|e| {
        LedgerError::malformed(format!("{}/ticket.md", ticket.front.id), e.to_string())
    })?;
    Ok(fenced(&front, &ticket.body))
}

/// Parse the text of a `ticket.md`; `label` names it in errors.
///
/// # Errors
///
/// [`LedgerError::Malformed`] for a missing fence, bad TOML or an unknown key.
pub fn parse(label: &str, text: &str) -> Result<Ticket> {
    let (front_text, body) = split_fenced(label, text)?;
    let front: Frontmatter =
        toml::from_str(front_text).map_err(|e| LedgerError::malformed(label, e.to_string()))?;
    Ok(Ticket { front, body })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::id::TicketId;
    use crate::model::{Acceptance, Category, Link, LinkKind, Priority, Stamp, TicketType};

    fn sample() -> Ticket {
        Ticket {
            front: Frontmatter {
                id: TicketId::mint(),
                title: "A \"quoted\" title".into(),
                ty: TicketType::Bug,
                flavour: None,
                category: Category::Todo,
                outcome: None,
                priority: Priority::High,
                class: crate::model::Class::Standard,
                due: None,
                points: None,
                parent: None,
                reporter: "logan".into(),
                assignee: None,
                created: Stamp::from_unix(1_790_000_000),
                updated: Stamp::from_unix(1_790_000_100),
                persona: Some("a\nmultiline persona".into()),
                capability: None,
                outcome_text: None,
                idempotency_key: None,
                aliases: vec![],
                labels: vec!["x".into()],
                scope: vec!["src/**".into()],
                links: vec![Link {
                    kind: LinkKind::Blocks,
                    target: TicketId::mint(),
                }],
                acceptance: vec![Acceptance {
                    text: "works".into(),
                    bound: false,
                }],
            },
            body: "# Heading\n\ntext with +++ inside".into(),
        }
    }

    #[test]
    fn render_parse_round_trip() {
        let t = sample();
        let text = render(&t).expect("render");
        assert!(text.starts_with("+++\n"));
        assert_eq!(parse("t", &text).expect("parse"), t);
    }

    #[test]
    fn fence_lines_in_any_field_round_trip() {
        let mut t = sample();
        t.front.title = "a\n+++\nb".into();
        t.front.persona = Some("+++".into());
        t.front.outcome_text = Some("x\\y\n+++  \r\n\"\"\"\n---".into());
        t.front.acceptance[0].text = "p\n+++\nq".into();
        t.front.labels = vec!["+++".into()];
        let text = render(&t).expect("render");
        assert_eq!(text.lines().filter(|l| l.trim_end() == "+++").count(), 2);
        assert_eq!(parse("t", &text).expect("parse"), t);
    }

    /// Text built from fence-like pieces and arbitrary characters.
    fn nasty() -> impl proptest::strategy::Strategy<Value = String> {
        use proptest::prelude::*;
        let piece = prop_oneof![
            Just("+++".to_owned()),
            Just("\n".to_owned()),
            Just("\r\n".to_owned()),
            Just("---".to_owned()),
            Just("\"\"\"".to_owned()),
            Just("\'\'\'".to_owned()),
            Just("\\".to_owned()),
            Just(" ".to_owned()),
            any::<char>().prop_map(String::from),
        ];
        proptest::collection::vec(piece, 0..12).prop_map(|v| v.concat())
    }

    // frob:tests render
    proptest::proptest! {
        #[test]
        fn arbitrary_field_text_round_trips(
            title in nasty(), persona in nasty(), outcome in nasty(), acc in nasty(), label in nasty(),
        ) {
            let mut t = sample();
            t.front.title = title;
            t.front.persona = Some(persona);
            t.front.outcome_text = Some(outcome);
            t.front.acceptance[0].text = acc;
            t.front.labels = vec![label];
            let text = render(&t).expect("render");
            proptest::prop_assert_eq!(text.lines().filter(|l| l.trim_end() == "+++").count(), 2);
            proptest::prop_assert_eq!(parse("t", &text).expect("parse"), t);
        }
    }

    #[test]
    fn empty_body_has_no_blank_tail() {
        let mut t = sample();
        t.body.clear();
        let text = render(&t).expect("render");
        assert!(text.ends_with("+++\n"));
        assert_eq!(parse("t", &text).expect("parse"), t);
    }

    #[test]
    fn missing_fence_is_malformed() {
        assert!(parse("t", "no fence").is_err());
        assert!(parse("t", "+++\ntitle = 'x'\n").is_err());
    }
}
