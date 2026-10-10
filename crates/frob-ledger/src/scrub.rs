//! The `TICK004` and `TICK005` repair: scrub absolute home paths and private terms out of committed ledger files in one forward commit.
//!
//! History is never rewritten. Every file below the tickets directory that holds an absolute
//! home path is rewritten in place through a caller-supplied text rewrite (the evidence crate's
//! `PathScrub`; this crate cannot depend on it). The rewrite is applied to the raw file text,
//! which is valid for TOML and Markdown alike because placeholders hold no quote or escape.
//!
//! Integrity rules, so a scrubbed ledger folds exactly as before:
//!
//! - An `evidence` event whose `digest` covered its inline text (or an attestation statement)
//!   gets the digest, and `size`, recomputed over the scrubbed text. A record whose digest did
//!   not match its text before is left alone: the repair never masks existing damage. A record
//!   with a `dir:` URI keeps its digest, because the artifact outside the ledger is untouched.
//! - Each affected ticket gets one audit-only `scrub` event naming the files and digests changed.
//!   The fold ignores it, including for `updated`.
//! - `ticket.md` is checked against the fold of the scrubbed events and re-rendered from the
//!   fold if the text rewrite alone left them apart.
//! - A file the rewrite cannot clear (a foreign home path it does not know) is reported, never guessed.

use std::collections::BTreeMap;

use gob_git::{CommitOptions, RelPath};

use crate::doc;
use crate::error::Result;
use crate::event::{DigestChange, Event, EventBody, ScrubData};
use crate::fold::fold;
use crate::id::TicketId;
use crate::ledger::Ledger;
use crate::redact::{Hit, RuleSet};

// frob:ticket 01M41RHBJ03PGD6JY0J6JTAH9Q

/// Why the audit event says files were rewritten.
pub const SCRUB_REASON: &str =
    "TICK004: absolute home paths replaced by placeholders (forward commit, history untouched)";

/// Why the audit event says private terms were replaced (the rules are named after it, by label and pattern hash).
pub const REDACT_REASON: &str =
    "TICK005: private terms replaced by their rule labels (forward commit, history untouched)";

/// The two text functions a scrub needs from the layers above this crate.
#[derive(Clone, Copy)]
pub struct ScrubTools<'a> {
    /// Rewrite absolute paths in a text (the built-in home-path rule); identity when there is nothing to do.
    pub rewrite: &'a dyn Fn(&str) -> String,
    /// Hex digest of bytes, the same function evidence records use.
    pub digest: &'a dyn Fn(&[u8]) -> String,
}

/// What [`Ledger::scrub`] did.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ScrubReport {
    /// Repo-relative paths of the files rewritten.
    pub files: Vec<String>,
    /// Tickets that received a `scrub` audit event.
    pub tickets: Vec<TicketId>,
    /// Evidence digests recomputed.
    pub digests: usize,
    /// Files that still hold a home path after the rewrite (not guessed at).
    pub unresolved: Vec<String>,
    /// The commit made, or `None` when nothing changed.
    pub commit: Option<String>,
}

/// Per-ticket bookkeeping while the scan runs.
#[derive(Default)]
struct Touched {
    files: Vec<String>,
    digests: Vec<DigestChange>,
    /// Rules that fired in this ticket's files (labels and hashes, never terms).
    rules: std::collections::BTreeSet<Hit>,
    /// New text by path relative to the tickets directory.
    new_text: BTreeMap<String, String>,
}

impl Ledger {
    /// Scrub every ledger file at the tip that holds an absolute home path or a local private term, in one commit.
    ///
    /// One engine: detection and the audit come from the local [`RuleSet`] plus the built-in home-path
    /// rule; the home-path rewrite is `tools.rewrite`, private terms become their rule labels.
    /// Idempotent: a clean ledger yields an empty report and no commit.
    ///
    /// # Errors
    ///
    /// Git read or commit failures, or a ticket whose scrubbed events no longer fold.
    pub fn scrub(&self, tools: &ScrubTools<'_>) -> Result<ScrubReport> {
        self.require_dir_layout("ticket scrub")?;
        let rules = self.redaction()?.clone().with_home_path();
        let mut report = ScrubReport::default();
        let ref_name = self.ledger_ref()?;
        let Some(tip) = self.tip_of(&ref_name)? else {
            return Ok(report);
        };
        let hex = tip.to_string();
        let dir = self.config().dir.clone();
        let mut changes: Vec<(RelPath, Option<Vec<u8>>)> = Vec::new();
        let mut touched: BTreeMap<TicketId, Touched> = BTreeMap::new();
        let mut others: Vec<String> = Vec::new();
        for (rel, oid) in self.list_blobs(&format!("{hex}:{dir}"))? {
            let path = format!("{dir}/{rel}");
            let bytes = self.repo().read_blob(&oid)?;
            let fired = rules.hits(&bytes);
            if fired.is_empty() {
                continue;
            }
            let Ok(old) = String::from_utf8(bytes) else {
                tracing::warn!(
                    path,
                    "ledger file with a redaction hit is not UTF-8; left alone"
                );
                report.unresolved.push(path);
                continue;
            };
            let Some((new, digests)) = rewrite_file(&path, &old, tools, &rules) else {
                tracing::warn!(
                    path,
                    "a redaction hit survives the rewrite; reported, not guessed"
                );
                report.unresolved.push(path);
                continue;
            };
            report.digests += digests.len();
            match ticket_of(&rel) {
                Some(id) => {
                    let t = touched.entry(id).or_default();
                    t.files.push(path.clone());
                    t.digests.extend(digests);
                    t.rules.extend(fired);
                    t.new_text.insert(rel.clone(), new.clone());
                }
                None => others.push(path.clone()),
            }
            changes.push((RelPath::new(path.clone())?, Some(new.into_bytes())));
            report.files.push(path);
        }
        if changes.is_empty() {
            tracing::info!(
                unresolved = report.unresolved.len(),
                "ledger scrub: nothing to change"
            );
            return Ok(report);
        }
        let actor = self.actor()?;
        for (id, t) in &touched {
            self.settle_ticket(&hex, *id, t, &mut changes)?;
            let ev = Event::new(
                self.now(),
                &actor,
                EventBody::Scrub(ScrubData {
                    reason: reason_of(&t.rules),
                    files: t.files.clone(),
                    digests: t.digests.clone(),
                }),
            );
            changes.push((
                RelPath::new(format!("{dir}/{id}/events/{}", ev.file_name()))?,
                Some(ev.to_toml()?.into_bytes()),
            ));
            report.tickets.push(*id);
        }
        let message = format!(
            "tickets(scrub): home paths and private terms removed from {} files ({} tickets, {} digests recomputed)",
            report.files.len(),
            report.tickets.len(),
            report.digests
        );
        let opts = CommitOptions {
            cas_retries: self.config().cas_retries,
            author: None,
        };
        let out = self
            .repo()
            .commit_paths(&ref_name, &changes, &message, &opts)?;
        tracing::info!(
            commit = %out.oid,
            files = report.files.len(),
            tickets = report.tickets.len(),
            digests = report.digests,
            others = others.len(),
            unresolved = report.unresolved.len(),
            "ledger scrubbed in one commit"
        );
        report.commit = Some(out.oid.to_string());
        Ok(report)
    }

    /// Make `ticket.md` of `id` agree with the fold of its scrubbed events, when it agreed with the unscrubbed fold.
    fn settle_ticket(
        &self,
        hex: &str,
        id: TicketId,
        touched: &Touched,
        changes: &mut Vec<(RelPath, Option<Vec<u8>>)>,
    ) -> Result<()> {
        let dir = &self.config().dir;
        let old_events = self.read_events_at(hex, id)?;
        let was_clean =
            self.read_ticket_at(hex, id)?.as_ref() == Some(&fold(id, &old_events)?.ticket);
        let events_dir = format!("{id}/events");
        let mut events = Vec::with_capacity(old_events.len());
        for ev in old_events {
            let rel = format!("{events_dir}/{}", ev.file_name());
            events.push(match touched.new_text.get(&rel) {
                Some(text) => Event::parse(ev.id, text)?,
                None => ev,
            });
        }
        let folded = fold(id, &events)?.ticket;
        let card = format!("{id}/ticket.md");
        let text = match touched.new_text.get(&card) {
            Some(t) => t.clone(),
            None => match self.text(hex, &format!("{dir}/{card}"))? {
                Some(t) => t,
                None => return Ok(()),
            },
        };
        let label = format!("{dir}/{card}");
        let agrees = doc::parse(&label, &text).is_ok_and(|t| t == folded);
        if was_clean && !agrees {
            tracing::info!(ticket = %id, "scrubbed ticket.md re-rendered from the fold of its scrubbed events");
            changes.retain(|(p, _)| p.as_str() != label);
            changes.push((
                RelPath::new(label)?,
                Some(doc::render(&folded)?.into_bytes()),
            ));
        }
        Ok(())
    }
}

/// The audit reason for a ticket: the home-path text, the private-term text, and the rules by label and hash.
fn reason_of(rules: &std::collections::BTreeSet<Hit>) -> String {
    let home = rules.iter().any(|h| h.builtin);
    let private: Vec<String> = rules
        .iter()
        .filter(|h| !h.builtin)
        .map(Hit::to_string)
        .collect();
    match (home, private.is_empty()) {
        (_, true) => SCRUB_REASON.to_owned(),
        (false, false) => format!("{REDACT_REASON}: {}", private.join(", ")),
        (true, false) => format!("{SCRUB_REASON}; {REDACT_REASON}: {}", private.join(", ")),
    }
}

/// The ticket directory a path (relative to the tickets directory) belongs to.
fn ticket_of(rel: &str) -> Option<TicketId> {
    rel.split('/').next()?.parse().ok()
}

/// The rewritten text of one file and the digests recomputed in it; `None` when a home path survives.
fn rewrite_file(
    path: &str,
    old: &str,
    tools: &ScrubTools<'_>,
    rules: &RuleSet,
) -> Option<(String, Vec<DigestChange>)> {
    let mut new = rules.apply_private(&(tools.rewrite)(old));
    if new == old || !rules.hits(new.as_bytes()).is_empty() {
        return None;
    }
    let mut digests = Vec::new();
    if path.contains("/events/")
        && let Some(change) = recompute_digest(path, old, &mut new, tools)
    {
        digests.push(change);
    }
    Some((new, digests))
}

/// For an evidence event whose digest covered its text, edit `new` so the digest and size cover the scrubbed text.
fn recompute_digest(
    path: &str,
    old: &str,
    new: &mut String,
    tools: &ScrubTools<'_>,
) -> Option<DigestChange> {
    let before: toml::Table = old.parse().ok()?;
    let after: toml::Table = new.parse().ok()?;
    if before.get("kind")?.as_str()? != "evidence" {
        return None;
    }
    let old_digest = before.get("digest")?.as_str()?.to_owned();
    let (was, now) = covered_text(&before, &after)?;
    if (tools.digest)(was.as_bytes()) != old_digest || was == now {
        return None;
    }
    let new_digest = (tools.digest)(now.as_bytes());
    let size_was = i64::try_from(was.len()).ok()?;
    let resize = before.get("size").and_then(toml::Value::as_integer) == Some(size_was);
    let edited = edit_top_level(
        new,
        &old_digest,
        &new_digest,
        resize.then_some((was.len(), now.len())),
    );
    let check: toml::Table = edited.parse().ok()?;
    let sized = !resize
        || check.get("size").and_then(toml::Value::as_integer) == i64::try_from(now.len()).ok();
    if check.get("digest")?.as_str()? != new_digest || !sized {
        tracing::warn!(path, "digest edit did not verify; digest left as it was");
        return None;
    }
    *new = edited;
    tracing::info!(path, old = %old_digest, new = %new_digest, "evidence digest recomputed over scrubbed text");
    Some(DigestChange {
        file: path.to_owned(),
        old: old_digest,
        new: new_digest,
    })
}

/// The text a record's digest covers, before and after: the inline transcript or the attestation statement.
fn covered_text(before: &toml::Table, after: &toml::Table) -> Option<(String, String)> {
    let get = |t: &toml::Table| -> Option<String> {
        if let Some(s) = t.get("inline").and_then(toml::Value::as_str) {
            return Some(s.to_owned());
        }
        t.get("attestation")?
            .get("statement")?
            .as_str()
            .map(str::to_owned)
    };
    Some((get(before)?, get(after)?))
}

/// Replace the top-level `digest = "<old>"` line (and `size = N` when asked), skipping multi-line string bodies.
fn edit_top_level(
    text: &str,
    old_digest: &str,
    new_digest: &str,
    size: Option<(usize, usize)>,
) -> String {
    let mut out = String::with_capacity(text.len());
    let mut in_string = false;
    for line in text.split_inclusive('\n') {
        let quotes = line.matches("\"\"\"").count();
        let mut line_out = line.to_owned();
        if !in_string {
            if line.trim_end() == format!("digest = \"{old_digest}\"") {
                line_out = format!("digest = \"{new_digest}\"\n");
            } else if let Some((was, now)) = size
                && line.trim_end() == format!("size = {was}")
            {
                line_out = format!("size = {now}\n");
            }
        }
        if quotes % 2 == 1 {
            in_string = !in_string;
        }
        out.push_str(&line_out);
    }
    out
}
