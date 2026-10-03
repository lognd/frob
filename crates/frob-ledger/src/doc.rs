//! The `ticket.md` document: TOML frontmatter between `+++` fences, then markdown.

use crate::error::{LedgerError, Result};
use crate::model::{Frontmatter, Ticket, normalize_body};

const FENCE: &str = "+++";

/// Join TOML `front` and markdown `body` into a fenced document (the shape of every ledger object file).
pub fn fenced(front: &str, body: &str) -> String {
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
