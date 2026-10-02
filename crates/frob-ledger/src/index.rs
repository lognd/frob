//! The SQLite index: every query verb reads this, never the ledger files.
//!
//! One database per worktree (`.frob/tickets.sqlite`, WAL), keyed by an
//! opaque key the ledger derives from the ledger ref's tickets tree id. When
//! the stored key differs from the ledger's, the index is rebuilt from the
//! ticket documents. The database is a pure cache: deleting it is always safe.

use std::path::Path;
use std::str::FromStr;

use rusqlite::{Connection, OptionalExtension, params, params_from_iter};
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::{Candidate, LedgerError, Result};
use crate::id::{TicketId, compute_handles, display_handle};
use crate::links::{Edge, edges_of};
use crate::model::{Category, LinkKind, Outcome, Priority, Stamp, Ticket, TicketType};

/// Schema version; a mismatch drops and recreates every table.
pub const INDEX_FORMAT: i64 = 1;

const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    handle TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    outcome TEXT,
    priority TEXT NOT NULL,
    points INTEGER,
    parent TEXT,
    created TEXT NOT NULL,
    updated TEXT NOT NULL,
    blocked INTEGER NOT NULL DEFAULT 0,
    idem_key TEXT,
    doc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tickets_category ON tickets(category);
CREATE INDEX IF NOT EXISTS tickets_parent ON tickets(parent);
CREATE INDEX IF NOT EXISTS tickets_idem ON tickets(idem_key);
CREATE TABLE IF NOT EXISTS links (src TEXT NOT NULL, kind TEXT NOT NULL, dst TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS links_src ON links(src);
CREATE INDEX IF NOT EXISTS links_dst ON links(dst);
CREATE TABLE IF NOT EXISTS labels (id TEXT NOT NULL, label TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS labels_label ON labels(label);
CREATE TABLE IF NOT EXISTS aliases (id TEXT NOT NULL, alias TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS aliases_alias ON aliases(alias);
CREATE VIEW IF NOT EXISTS blockers AS
    SELECT dst AS blocker, src AS blocked FROM links WHERE kind = 'blocked-by'
    UNION
    SELECT src AS blocker, dst AS blocked FROM links WHERE kind = 'blocks';
";

const DROP: &str = "
DROP VIEW IF EXISTS blockers;
DROP TABLE IF EXISTS meta; DROP TABLE IF EXISTS tickets; DROP TABLE IF EXISTS links;
DROP TABLE IF EXISTS labels; DROP TABLE IF EXISTS aliases;
";

/// The one-line view of a ticket used by `list`, `doable` and `show`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Summary {
    /// Full ULID.
    pub id: TicketId,
    /// Human handle with its `~`.
    pub handle: String,
    /// Title.
    pub title: String,
    /// Ticket type.
    #[serde(rename = "type")]
    pub ty: TicketType,
    /// Workflow category.
    pub category: Category,
    /// Outcome, when done.
    pub outcome: Option<Outcome>,
    /// Priority.
    pub priority: Priority,
    /// Story points.
    pub points: Option<u8>,
    /// Parent ticket.
    pub parent: Option<TicketId>,
    /// Creation time.
    pub created: Stamp,
    /// Time of the latest event.
    pub updated: Stamp,
    /// True while any blocker is not done (derived).
    pub blocked: bool,
}

/// Filters for [`Index::list`]; all given filters must match.
#[derive(Debug, Clone, Default)]
pub struct ListFilter {
    /// Only this category.
    pub category: Option<Category>,
    /// Only this type.
    pub ty: Option<TicketType>,
    /// Only children of this ticket.
    pub parent: Option<TicketId>,
    /// Only tickets carrying this label.
    pub label: Option<String>,
    /// Only blocked (`true`) or unblocked (`false`) tickets.
    pub blocked: Option<bool>,
}

/// The SQLite-backed index of one worktree.
pub struct Index {
    conn: Connection,
}

impl std::fmt::Debug for Index {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Index").finish_non_exhaustive()
    }
}

fn conv<T: FromStr>(idx: usize, text: &str) -> rusqlite::Result<T>
where
    T::Err: std::error::Error + Send + Sync + 'static,
{
    text.parse().map_err(|e| {
        rusqlite::Error::FromSqlConversionFailure(idx, rusqlite::types::Type::Text, Box::new(e))
    })
}

const SUMMARY_COLS: &str = "id, handle, title, type, category, outcome, priority, points, parent, created, updated, blocked";

fn summary_row(r: &rusqlite::Row<'_>) -> rusqlite::Result<Summary> {
    let outcome: Option<String> = r.get(5)?;
    let parent: Option<String> = r.get(8)?;
    let points: Option<i64> = r.get(7)?;
    Ok(Summary {
        id: conv(0, &r.get::<_, String>(0)?)?,
        handle: display_handle(&r.get::<_, String>(1)?),
        title: r.get(2)?,
        ty: conv(3, &r.get::<_, String>(3)?)?,
        category: conv(4, &r.get::<_, String>(4)?)?,
        outcome: outcome.map(|o| conv(5, &o)).transpose()?,
        priority: conv(6, &r.get::<_, String>(6)?)?,
        points: points.and_then(|p| u8::try_from(p).ok()),
        parent: parent.map(|p| conv(8, &p)).transpose()?,
        created: r.get::<_, String>(9)?.parse().map_err(|e: String| {
            rusqlite::Error::FromSqlConversionFailure(9, rusqlite::types::Type::Text, e.into())
        })?,
        updated: r.get::<_, String>(10)?.parse().map_err(|e: String| {
            rusqlite::Error::FromSqlConversionFailure(10, rusqlite::types::Type::Text, e.into())
        })?,
        blocked: r.get::<_, i64>(11)? != 0,
    })
}

impl Index {
    /// Open (creating if needed) the index database at `path`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Io`] if the directory cannot be created, or a SQLite error.
    pub fn open(path: &Path) -> Result<Self> {
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir)?;
        }
        let conn = Connection::open(path)?;
        conn.busy_timeout(std::time::Duration::from_secs(5))?;
        let _mode: String = conn.query_row("PRAGMA journal_mode=WAL", [], |r| r.get(0))?;
        conn.execute_batch("PRAGMA synchronous=NORMAL;")?;
        let version: i64 = conn.query_row("PRAGMA user_version", [], |r| r.get(0))?;
        if version != INDEX_FORMAT {
            tracing::info!(from = version, to = INDEX_FORMAT, "index schema reset");
            conn.execute_batch(DROP)?;
            conn.execute_batch(&format!("PRAGMA user_version = {INDEX_FORMAT};"))?;
        }
        conn.execute_batch(SCHEMA)?;
        tracing::debug!(path = %path.display(), "index opened");
        Ok(Self { conn })
    }

    /// The key the index currently reflects, if any.
    ///
    /// # Errors
    ///
    /// A SQLite error.
    pub fn key(&self) -> Result<Option<String>> {
        Ok(self
            .conn
            .query_row("SELECT v FROM meta WHERE k = 'key'", [], |r| r.get(0))
            .optional()?)
    }

    /// Replace the whole index with `tickets`, recording `key`.
    ///
    /// # Errors
    ///
    /// A SQLite error; the old contents are kept on failure.
    pub fn rebuild(&mut self, key: &str, tickets: &[Ticket], min_len: usize) -> Result<()> {
        let tx = self
            .conn
            .transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
        for t in ["tickets", "links", "labels", "aliases"] {
            tx.execute(&format!("DELETE FROM {t}"), [])?;
        }
        for t in tickets {
            insert(&tx, t)?;
        }
        finish(&tx, key, min_len)?;
        tx.commit()?;
        tracing::info!(tickets = tickets.len(), key, "index rebuilt");
        Ok(())
    }

    /// Upsert `tickets` if the index still reflects `expect_key`, then record `new_key`.
    ///
    /// Returns `false` (and changes nothing) when the stored key differs, so
    /// the next read rebuilds instead.
    ///
    /// # Errors
    ///
    /// A SQLite error.
    pub fn apply(
        &mut self,
        expect_key: &str,
        new_key: &str,
        tickets: &[Ticket],
        min_len: usize,
    ) -> Result<bool> {
        let tx = self
            .conn
            .transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
        let have: Option<String> = tx
            .query_row("SELECT v FROM meta WHERE k = 'key'", [], |r| r.get(0))
            .optional()?;
        if have.as_deref() != Some(expect_key) {
            tracing::debug!(have = ?have, expect_key, "index stale; incremental update skipped");
            return Ok(false);
        }
        for t in tickets {
            let id = t.front.id.to_string();
            for table in ["links", "labels", "aliases"] {
                let col = if table == "links" { "src" } else { "id" };
                tx.execute(&format!("DELETE FROM {table} WHERE {col} = ?1"), [&id])?;
            }
            insert(&tx, t)?;
        }
        finish(&tx, new_key, min_len)?;
        tx.commit()?;
        tracing::debug!(
            tickets = tickets.len(),
            new_key,
            "index updated incrementally"
        );
        Ok(true)
    }

    /// The full ticket document of `id`.
    ///
    /// # Errors
    ///
    /// A SQLite error or a corrupt stored document.
    pub fn get(&self, id: TicketId) -> Result<Option<Ticket>> {
        let doc: Option<String> = self
            .conn
            .query_row(
                "SELECT doc FROM tickets WHERE id = ?1",
                [id.to_string()],
                |r| r.get(0),
            )
            .optional()?;
        doc.map(|d| {
            serde_json::from_str(&d).map_err(|e| LedgerError::malformed("index.doc", e.to_string()))
        })
        .transpose()
    }

    /// The one-line summary of `id`.
    ///
    /// # Errors
    ///
    /// A SQLite error.
    pub fn summary(&self, id: TicketId) -> Result<Option<Summary>> {
        Ok(self
            .conn
            .query_row(
                &format!("SELECT {SUMMARY_COLS} FROM tickets WHERE id = ?1"),
                [id.to_string()],
                summary_row,
            )
            .optional()?)
    }

    /// Summaries matching `filter`, oldest first (ULID order).
    ///
    /// # Errors
    ///
    /// A SQLite error.
    pub fn list(&self, filter: &ListFilter) -> Result<Vec<Summary>> {
        let mut clauses: Vec<&str> = Vec::new();
        let mut args: Vec<String> = Vec::new();
        if let Some(c) = filter.category {
            clauses.push("category = ?");
            args.push(c.to_string());
        }
        if let Some(t) = filter.ty {
            clauses.push("type = ?");
            args.push(t.to_string());
        }
        if let Some(p) = filter.parent {
            clauses.push("parent = ?");
            args.push(p.to_string());
        }
        if let Some(l) = &filter.label {
            clauses.push("id IN (SELECT id FROM labels WHERE label = ?)");
            args.push(l.clone());
        }
        match filter.blocked {
            Some(true) => clauses.push("blocked = 1"),
            Some(false) => clauses.push("blocked = 0"),
            None => {}
        }
        let wher = if clauses.is_empty() {
            String::new()
        } else {
            format!(" WHERE {}", clauses.join(" AND "))
        };
        let sql = format!("SELECT {SUMMARY_COLS} FROM tickets{wher} ORDER BY id");
        let mut stmt = self.conn.prepare_cached(&sql)?;
        let rows = stmt.query_map(params_from_iter(args.iter()), summary_row)?;
        Ok(rows.collect::<rusqlite::Result<Vec<_>>>()?)
    }

    /// Resolve a full ULID, a `~suffix` handle or an alias to exactly one ticket.
    ///
    /// # Errors
    ///
    /// [`LedgerError::NotFound`] or [`LedgerError::Ambiguous`] (listing every match).
    pub fn resolve(&self, input: &str) -> Result<TicketId> {
        let input = input.trim();
        let not_found = || LedgerError::NotFound {
            input: input.to_owned(),
        };
        let matches: Vec<String> = if let Some(suffix) = input.strip_prefix('~') {
            let suffix = suffix.to_ascii_uppercase();
            if suffix.is_empty() || !suffix.bytes().all(|b| b.is_ascii_alphanumeric()) {
                return Err(not_found());
            }
            self.ids_where(
                "SELECT id FROM tickets WHERE substr(id, -length(?1)) = ?1 ORDER BY id",
                &suffix,
            )?
        } else if let Ok(id) = input.parse::<TicketId>() {
            self.ids_where("SELECT id FROM tickets WHERE id = ?1", &id.to_string())?
        } else {
            self.ids_where(
                "SELECT id FROM aliases WHERE alias = ?1 GROUP BY id ORDER BY id",
                input,
            )?
        };
        match matches.as_slice() {
            [] => Err(not_found()),
            [one] => one.parse().map_err(|_| not_found()),
            many => {
                let mut candidates = Vec::new();
                for id in many {
                    let title: String = self.conn.query_row(
                        "SELECT title FROM tickets WHERE id = ?1",
                        [id],
                        |r| r.get(0),
                    )?;
                    candidates.push(Candidate {
                        id: id.clone(),
                        title,
                    });
                }
                Err(LedgerError::Ambiguous {
                    input: input.to_owned(),
                    candidates,
                })
            }
        }
    }

    fn ids_where(&self, sql: &str, arg: &str) -> Result<Vec<String>> {
        let mut stmt = self.conn.prepare_cached(sql)?;
        let rows = stmt.query_map([arg], |r| r.get::<_, String>(0))?;
        Ok(rows.collect::<rusqlite::Result<Vec<_>>>()?)
    }

    /// Every ticket id, in ULID order.
    ///
    /// # Errors
    ///
    /// A SQLite error.
    pub fn all_ids(&self) -> Result<Vec<TicketId>> {
        let mut stmt = self
            .conn
            .prepare_cached("SELECT id FROM tickets ORDER BY id")?;
        let rows = stmt.query_map([], |r| conv::<TicketId>(0, &r.get::<_, String>(0)?))?;
        Ok(rows.collect::<rusqlite::Result<Vec<_>>>()?)
    }

    /// Every stored link as a normalized edge (dangling targets included).
    ///
    /// # Errors
    ///
    /// A SQLite error.
    pub fn edges(&self) -> Result<Vec<Edge>> {
        let mut stmt = self
            .conn
            .prepare_cached("SELECT src, kind, dst FROM links")?;
        let rows = stmt.query_map([], |r| {
            let src: TicketId = conv(0, &r.get::<_, String>(0)?)?;
            let kind: LinkKind = conv(1, &r.get::<_, String>(1)?)?;
            let dst: TicketId = conv(2, &r.get::<_, String>(2)?)?;
            Ok(Edge::normalize(src, kind, dst))
        })?;
        Ok(rows.collect::<rusqlite::Result<Vec<_>>>()?)
    }

    /// Links stored on other tickets that point at `id`, spelled from `id`'s side.
    ///
    /// # Errors
    ///
    /// A SQLite error.
    pub fn incoming(&self, id: TicketId) -> Result<Vec<(LinkKind, TicketId)>> {
        let mut stmt = self
            .conn
            .prepare_cached("SELECT kind, src FROM links WHERE dst = ?1 ORDER BY src")?;
        let rows = stmt.query_map([id.to_string()], |r| {
            let kind: LinkKind = conv(0, &r.get::<_, String>(0)?)?;
            let src: TicketId = conv(1, &r.get::<_, String>(1)?)?;
            Ok((kind.inverse(), src))
        })?;
        Ok(rows.collect::<rusqlite::Result<Vec<_>>>()?)
    }

    /// The ticket that `new` created under `key`, if any.
    ///
    /// # Errors
    ///
    /// A SQLite error.
    pub fn find_by_key(&self, key: &str) -> Result<Option<TicketId>> {
        let id: Option<String> = self
            .conn
            .query_row("SELECT id FROM tickets WHERE idem_key = ?1", [key], |r| {
                r.get(0)
            })
            .optional()?;
        id.map(|s| s.parse().map_err(|_| LedgerError::malformed("index.id", s)))
            .transpose()
    }

    /// Number of indexed tickets.
    ///
    /// # Errors
    ///
    /// A SQLite error.
    pub fn count(&self) -> Result<usize> {
        let n: i64 = self
            .conn
            .query_row("SELECT count(*) FROM tickets", [], |r| r.get(0))?;
        Ok(usize::try_from(n).unwrap_or(0))
    }
}

fn insert(tx: &rusqlite::Transaction<'_>, t: &Ticket) -> Result<()> {
    let f = &t.front;
    let id = f.id.to_string();
    let doc =
        serde_json::to_string(t).map_err(|e| LedgerError::malformed("index.doc", e.to_string()))?;
    tx.prepare_cached(
        "INSERT OR REPLACE INTO tickets
         (id, title, type, category, outcome, priority, points, parent, created, updated, idem_key, doc)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
    )?
    .execute(params![
        id,
        f.title,
        f.ty.as_str(),
        f.category.as_str(),
        f.outcome.map(Outcome::as_str),
        f.priority.as_str(),
        f.points.map(|p| i64::from(p.get())),
        f.parent.map(|p| p.to_string()),
        f.created.to_string(),
        f.updated.to_string(),
        f.idempotency_key,
        doc,
    ])?;
    let mut link = tx.prepare_cached("INSERT INTO links (src, kind, dst) VALUES (?1, ?2, ?3)")?;
    for l in &f.links {
        link.execute(params![id, l.kind.as_str(), l.target.to_string()])?;
    }
    let mut label = tx.prepare_cached("INSERT INTO labels (id, label) VALUES (?1, ?2)")?;
    for l in &f.labels {
        label.execute(params![id, l])?;
    }
    let mut alias = tx.prepare_cached("INSERT INTO aliases (id, alias) VALUES (?1, ?2)")?;
    for a in &f.aliases {
        alias.execute(params![id, a])?;
    }
    Ok(())
}

/// Recompute handles and the derived `blocked` flag, then record the key.
fn finish(tx: &rusqlite::Transaction<'_>, key: &str, min_len: usize) -> Result<()> {
    let ids: Vec<(String, String)> = {
        let mut stmt = tx.prepare_cached("SELECT id, handle FROM tickets ORDER BY id")?;
        let rows = stmt.query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?)))?;
        rows.collect::<rusqlite::Result<Vec<_>>>()?
    };
    let parsed: Vec<TicketId> = ids.iter().filter_map(|(id, _)| id.parse().ok()).collect();
    let handles = compute_handles(&parsed, min_len);
    let mut set = tx.prepare_cached("UPDATE tickets SET handle = ?2 WHERE id = ?1")?;
    for ((id, old), handle) in ids.iter().zip(&handles) {
        if old != handle {
            set.execute(params![id, handle])?;
        }
    }
    tx.execute(
        "UPDATE tickets SET blocked = CASE
            WHEN category = 'done' THEN 0
            WHEN EXISTS (
                SELECT 1 FROM blockers b JOIN tickets x ON x.id = b.blocker
                WHERE b.blocked = tickets.id AND x.category <> 'done'
            ) THEN 1 ELSE 0 END",
        [],
    )?;
    tx.execute(
        "INSERT OR REPLACE INTO meta (k, v) VALUES ('key', ?1)",
        [key],
    )?;
    Ok(())
}

/// Edges declared by `tickets`, for callers that build a graph without SQLite.
pub fn edges_of_all(tickets: &[Ticket]) -> Vec<Edge> {
    tickets.iter().flat_map(|t| edges_of(&t.front)).collect()
}
