//! The real GitHub `TrackerAdapter` over an injected HTTP transport (mirror.md 2.1, 3.2 to 3.4).
//!
//! [`HttpTransport`] performs one raw REST or GraphQL call (live through `frob-gh`, or recorded
//! offline); nothing here opens a socket. [`GithubRest`] maps the existing `WriteTransport`,
//! `HistorySource` and `ListingSource` contracts onto GitHub endpoints. [`GithubAdapter`] adds
//! the signed creation marker and write spacing and implements `TrackerAdapter`. There is no
//! delete call anywhere, listing never uses search, and label and assignee edits are additive.

// frob:ticket 01M5ASPRW2FYMNRHWQHEVN9W9J

use std::fmt::Write as _;
use std::time::Duration;

use serde_json::{Value, json};
use tracing::{debug, info, trace, warn};

use crate::adapter::{
    AdapterError, AdapterResult, Capabilities, CreateOutcome, EventId, HistoryEntry,
    HistoryRetention, Inventory, IssueRef, IssueState, IssueSummary, MarkdownDialect, StateReasons,
    TrackerAdapter,
};
use crate::github::lookup::{ListingSource, lookup_since};
use crate::github::read::{
    self, BodyRevision, BodyRevisions, HistorySource, RETAINED_BODY_EDITS, TimelineEvent,
};
use crate::github::render::render;
use crate::github::write::{Clock, WRITE_SPACING, WriteTransport, state_reason};
use crate::keyring::{Keyring, MarkerFields};
use crate::marker::format_marker;
use crate::projection::{IssueProjection, Outcome, RelationKind};

/// Items requested per page on list endpoints.
const PER_PAGE: u32 = 100;

/// HTTP verbs the adapter uses; there is deliberately no way to name an unsupported one.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Method {
    /// Read.
    Get,
    /// Create or add.
    Post,
    /// Update.
    Patch,
    /// Remove an association (label, assignee); never an issue.
    Delete,
}

/// One request against the GitHub API, relative to the API root.
#[derive(Debug, Clone, PartialEq)]
pub struct HttpRequest {
    /// The verb.
    pub method: Method,
    /// Path beginning with `/`, for example `/repos/o/r/issues`.
    pub path: String,
    /// Query parameters in order.
    pub query: Vec<(String, String)>,
    /// JSON body, when the call has one.
    pub body: Option<Value>,
}

/// A response: status, optional `Location` header and the body text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HttpResponse {
    /// HTTP status code.
    pub status: u16,
    /// `Location` header, set on redirects.
    pub location: Option<String>,
    /// Response body (JSON, possibly empty).
    pub body: String,
}

/// A failure before any response was read.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum TransportError {
    /// The call timed out; whether the server acted is unknown.
    #[error("timeout")]
    Timeout,
    /// Any other connection failure.
    #[error("transport: {0}")]
    Other(String),
}

/// One raw HTTP exchange with GitHub.
pub trait HttpTransport {
    /// Perform `req` and return the response, whatever its status.
    ///
    /// # Errors
    /// Returns a [`TransportError`] when no response was obtained.
    fn send(&self, req: &HttpRequest) -> Result<HttpResponse, TransportError>;
}

/// Percent-encode one path segment (unreserved characters pass through).
fn encode_segment(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for b in s.bytes() {
        if b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.' | b'~') {
            out.push(char::from(b));
        } else {
            let _ = write!(out, "%{b:02X}");
        }
    }
    out
}

/// Map a non-success status to the adapter error it means.
fn status_error(resp: &HttpResponse) -> AdapterError {
    match resp.status {
        301 | 302 | 307 | 308 => AdapterError::Moved(resp.location.clone().unwrap_or_default()),
        404 => AdapterError::NotFound,
        410 => AdapterError::Gone,
        403 | 429 => AdapterError::RateLimited,
        s => AdapterError::Other(format!("http {s}")),
    }
}

fn transport_error(e: &TransportError) -> AdapterError {
    AdapterError::Other(e.to_string())
}

fn parse_json(body: &str) -> AdapterResult<Value> {
    if body.trim().is_empty() {
        return Ok(Value::Null);
    }
    serde_json::from_str(body).map_err(|e| AdapterError::Other(format!("bad json: {e}")))
}

fn str_of(v: &Value, key: &str) -> String {
    v.get(key)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned()
}

fn names(v: &Value, key: &str, field: &str) -> Vec<String> {
    v.get(key)
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(|x| x.get(field).and_then(Value::as_str).map(str::to_owned))
                .collect()
        })
        .unwrap_or_default()
}

fn issue_state(v: &Value) -> IssueState {
    IssueState {
        issue: IssueRef(
            v.get("number")
                .and_then(Value::as_u64)
                .map(|n| n.to_string())
                .unwrap_or_default(),
        ),
        title: str_of(v, "title"),
        body: str_of(v, "body"),
        labels: names(v, "labels", "name"),
        assignees: names(v, "assignees", "login"),
        closed: v.get("state").and_then(Value::as_str) == Some("closed"),
    }
}

/// GitHub REST and GraphQL calls for one repository, over an [`HttpTransport`].
pub struct GithubRest<H: HttpTransport> {
    http: H,
    owner: String,
    repo: String,
    bot_login: String,
}

impl<H: HttpTransport> GithubRest<H> {
    /// A client for `owner/repo`, listing issues created by `bot_login`.
    pub fn new(http: H, owner: &str, repo: &str, bot_login: &str) -> Self {
        Self {
            http,
            owner: owner.to_owned(),
            repo: repo.to_owned(),
            bot_login: bot_login.to_owned(),
        }
    }

    fn repo_path(&self, tail: &str) -> String {
        format!(
            "/repos/{}/{}{tail}",
            encode_segment(&self.owner),
            encode_segment(&self.repo)
        )
    }

    /// Run one request; any 2xx returns the parsed body, anything else its mapped error.
    fn call(
        &self,
        method: Method,
        path: String,
        query: Vec<(String, String)>,
        body: Option<Value>,
    ) -> AdapterResult<Value> {
        let req = HttpRequest {
            method,
            path,
            query,
            body,
        };
        trace!(?req.method, path = %req.path, "github http: request");
        let resp = self.http.send(&req).map_err(|e| {
            warn!(path = %req.path, error = %e, "github http: transport failure");
            transport_error(&e)
        })?;
        if (200..300).contains(&resp.status) {
            return parse_json(&resp.body);
        }
        let err = status_error(&resp);
        warn!(path = %req.path, status = resp.status, error = %err, "github http: non-success");
        Err(err)
    }

    fn get(&self, path: String, query: Vec<(String, String)>) -> AdapterResult<Value> {
        self.call(Method::Get, path, query, None)
    }

    /// Every page of a list endpoint, concatenated.
    fn get_all(&self, path: &str, extra: &[(&str, &str)]) -> AdapterResult<Vec<Value>> {
        let mut all = Vec::new();
        for page in 1u32.. {
            let mut q: Vec<(String, String)> = extra
                .iter()
                .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
                .collect();
            q.push(("per_page".into(), PER_PAGE.to_string()));
            q.push(("page".into(), page.to_string()));
            let v = self.get(path.to_owned(), q)?;
            let items = v.as_array().cloned().unwrap_or_default();
            let n = items.len();
            all.extend(items);
            if n < PER_PAGE as usize {
                break;
            }
        }
        Ok(all)
    }

    fn issue_path(&self, issue: &IssueRef, tail: &str) -> String {
        self.repo_path(&format!("/issues/{}{tail}", encode_segment(&issue.0)))
    }

    /// The numeric database id of an issue, which sub-issue and dependency calls need.
    fn database_id(&self, issue: &IssueRef) -> AdapterResult<u64> {
        let v = self.get(self.issue_path(issue, ""), vec![])?;
        v.get("id")
            .and_then(Value::as_u64)
            .ok_or_else(|| AdapterError::Other("issue has no id".into()))
    }

    /// POST a create; the outcome distinguishes confirmed, rejected and uncertain.
    fn create_issue(&self, title: &str, body: &str, labels: &[String]) -> CreateOutcome {
        let req = HttpRequest {
            method: Method::Post,
            path: self.repo_path("/issues"),
            query: vec![],
            body: Some(json!({"title": title, "body": body, "labels": labels})),
        };
        match self.http.send(&req) {
            Err(e) => {
                warn!(error = %e, "github create: transport failure, outcome unknown");
                CreateOutcome::Unknown
            }
            Ok(r) if (200..300).contains(&r.status) => {
                let number = parse_json(&r.body)
                    .ok()
                    .and_then(|v| v.get("number").and_then(Value::as_u64));
                match number {
                    Some(n) => {
                        info!(issue = n, "github create: confirmed");
                        CreateOutcome::Created(IssueRef(n.to_string()))
                    }
                    None => CreateOutcome::Unknown,
                }
            }
            Ok(r) if r.status >= 500 || r.status == 429 || r.status == 403 => {
                warn!(
                    status = r.status,
                    "github create: server trouble, outcome unknown"
                );
                CreateOutcome::Unknown
            }
            Ok(r) => {
                warn!(status = r.status, "github create: rejected");
                CreateOutcome::Failed(format!("http {}", r.status))
            }
        }
    }

    fn body_revisions_graphql(&self, issue: &IssueRef) -> AdapterResult<BodyRevisions> {
        let number: u64 = issue
            .0
            .parse()
            .map_err(|_| AdapterError::Other(format!("bad issue number {}", issue.0)))?;
        let query = "query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){\
            issue(number:$n){userContentEdits(first:100){totalCount \
            nodes{id createdAt diff editor{... on User{databaseId}}}}}}}";
        let v = self.call(
            Method::Post,
            "/graphql".into(),
            vec![],
            Some(json!({"query": query,
                "variables": {"o": self.owner, "r": self.repo, "n": number}})),
        )?;
        let edits = v
            .pointer("/data/repository/issue/userContentEdits")
            .ok_or_else(|| AdapterError::Other("graphql: no userContentEdits".into()))?;
        let total = edits.get("totalCount").and_then(Value::as_u64).unwrap_or(0);
        let mut revisions: Vec<BodyRevision> = edits
            .get("nodes")
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .map(|n| BodyRevision {
                        id: str_of(n, "id"),
                        created_at: str_of(n, "createdAt"),
                        editor_id: n.pointer("/editor/databaseId").and_then(Value::as_u64),
                        body: n.get("diff").and_then(Value::as_str).map(str::to_owned),
                    })
                    .collect()
            })
            .unwrap_or_default();
        // GitHub lists newest first; the protocol wants oldest first.
        revisions.reverse();
        let truncated = total > u64::try_from(RETAINED_BODY_EDITS + 1).unwrap_or(u64::MAX);
        debug!(issue = %issue.0, total, truncated, "github read: body revisions");
        Ok(BodyRevisions {
            revisions,
            truncated,
        })
    }
}

impl<H: HttpTransport> WriteTransport for GithubRest<H> {
    fn patch_issue(&mut self, issue: &IssueRef, title: &str, body: &str) -> AdapterResult<()> {
        self.call(
            Method::Patch,
            self.issue_path(issue, ""),
            vec![],
            Some(json!({"title": title, "body": body})),
        )
        .map(drop)
    }

    fn close_issue(
        &mut self,
        issue: &IssueRef,
        state_reason: &str,
        reason: &str,
    ) -> AdapterResult<()> {
        debug!(issue = %issue.0, state_reason, reason, "github: closing issue");
        self.call(
            Method::Patch,
            self.issue_path(issue, ""),
            vec![],
            Some(json!({"state": "closed", "state_reason": state_reason})),
        )
        .map(drop)
    }

    fn add_label(&mut self, issue: &IssueRef, label: &str) -> AdapterResult<()> {
        self.call(
            Method::Post,
            self.issue_path(issue, "/labels"),
            vec![],
            Some(json!({"labels": [label]})),
        )
        .map(drop)
    }

    fn remove_label(&mut self, issue: &IssueRef, label: &str) -> AdapterResult<()> {
        self.call(
            Method::Delete,
            self.issue_path(issue, &format!("/labels/{}", encode_segment(label))),
            vec![],
            None,
        )
        .map(drop)
    }

    fn add_sub_issue(&mut self, parent: &IssueRef, child: &IssueRef) -> AdapterResult<()> {
        let id = self.database_id(child)?;
        self.call(
            Method::Post,
            self.issue_path(parent, "/sub_issues"),
            vec![],
            Some(json!({"sub_issue_id": id})),
        )
        .map(drop)
    }

    fn add_link(
        &mut self,
        issue: &IssueRef,
        kind: RelationKind,
        target: &IssueRef,
    ) -> AdapterResult<()> {
        // GitHub holds only blocked-by edges natively; `blocks` is the reverse edge.
        let (dependent, blocker) = match kind {
            RelationKind::BlockedBy => (issue, target),
            RelationKind::Blocks => (target, issue),
            other => {
                return Err(AdapterError::Other(format!(
                    "no native github link for {other:?}"
                )));
            }
        };
        let id = self.database_id(blocker)?;
        self.call(
            Method::Post,
            self.issue_path(dependent, "/dependencies/blocked_by"),
            vec![],
            Some(json!({"issue_id": id})),
        )
        .map(drop)
    }
}

impl<H: HttpTransport> HistorySource for GithubRest<H> {
    fn issue(&self, issue: &IssueRef) -> AdapterResult<IssueState> {
        let v = self.get(self.issue_path(issue, ""), vec![])?;
        Ok(issue_state(&v))
    }

    fn timeline(&self, issue: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
        let items = self.get_all(&self.issue_path(issue, "/timeline"), &[])?;
        let mut out = Vec::new();
        for e in &items {
            let kind = e.get("event").and_then(Value::as_str).unwrap_or_default();
            let (field, value) = match kind {
                "renamed" => (
                    "title",
                    str_of(e.get("rename").unwrap_or(&Value::Null), "to"),
                ),
                "labeled" => (
                    "labels",
                    format!(
                        "+{}",
                        str_of(e.get("label").unwrap_or(&Value::Null), "name")
                    ),
                ),
                "unlabeled" => (
                    "labels",
                    format!(
                        "-{}",
                        str_of(e.get("label").unwrap_or(&Value::Null), "name")
                    ),
                ),
                "assigned" => (
                    "assignees",
                    format!(
                        "+{}",
                        str_of(e.get("assignee").unwrap_or(&Value::Null), "login")
                    ),
                ),
                "unassigned" => (
                    "assignees",
                    format!(
                        "-{}",
                        str_of(e.get("assignee").unwrap_or(&Value::Null), "login")
                    ),
                ),
                "milestoned" => (
                    "milestone",
                    format!(
                        "+{}",
                        str_of(e.get("milestone").unwrap_or(&Value::Null), "title")
                    ),
                ),
                "demilestoned" => (
                    "milestone",
                    format!(
                        "-{}",
                        str_of(e.get("milestone").unwrap_or(&Value::Null), "title")
                    ),
                ),
                "closed" | "reopened" => ("state", kind.to_owned()),
                _ => continue,
            };
            let Some(id) = e.get("id").and_then(Value::as_u64) else {
                trace!(kind, "github timeline: event without id skipped");
                continue;
            };
            out.push(TimelineEvent {
                id: id.to_string(),
                created_at: str_of(e, "created_at"),
                actor_id: e.pointer("/actor/id").and_then(Value::as_u64).unwrap_or(0),
                field: field.to_owned(),
                value,
            });
        }
        Ok(out)
    }

    fn body_revisions(&self, issue: &IssueRef) -> AdapterResult<BodyRevisions> {
        self.body_revisions_graphql(issue)
    }
}

impl<H: HttpTransport> ListingSource for GithubRest<H> {
    fn page(&self, creator_id: u64, page: u32) -> AdapterResult<Vec<IssueSummary>> {
        let v = self.get(
            self.repo_path("/issues"),
            vec![
                ("creator".into(), self.bot_login.clone()),
                ("state".into(), "all".into()),
                ("sort".into(), "created".into()),
                ("direction".into(), "desc".into()),
                ("per_page".into(), PER_PAGE.to_string()),
                ("page".into(), page.to_string()),
            ],
        )?;
        let items = v.as_array().cloned().unwrap_or_default();
        Ok(items
            .iter()
            .filter(|i| i.get("pull_request").is_none())
            .filter(|i| i.pointer("/user/id").and_then(Value::as_u64) == Some(creator_id))
            .map(|i| IssueSummary {
                issue: issue_state(i).issue,
                title: str_of(i, "title"),
                creator_id,
                created_at: str_of(i, "created_at"),
            })
            .collect())
    }
}

/// The GitHub `TrackerAdapter`: signs the creation marker, spaces mutations, talks HTTP.
pub struct GithubAdapter<'a, H: HttpTransport, C: Clock> {
    rest: GithubRest<H>,
    keyring: &'a Keyring,
    repo_node_id: String,
    clock: &'a C,
    spacing: Duration,
    last_mutation: Option<Duration>,
}

impl<'a, H: HttpTransport, C: Clock> GithubAdapter<'a, H, C> {
    /// An adapter signing markers with `keyring` bound to `repo_node_id`, spacing mutations by
    /// [`WRITE_SPACING`].
    pub fn new(
        rest: GithubRest<H>,
        keyring: &'a Keyring,
        repo_node_id: &str,
        clock: &'a C,
    ) -> Self {
        Self {
            rest,
            keyring,
            repo_node_id: repo_node_id.to_owned(),
            clock,
            spacing: WRITE_SPACING,
            last_mutation: None,
        }
    }

    /// Wait out the spacing since the previous mutation (mirror.md 3.2 serial writes).
    fn space(&mut self) {
        if let Some(last) = self.last_mutation {
            let elapsed = self.clock.now().saturating_sub(last);
            if let Some(wait) = self.spacing.checked_sub(elapsed).filter(|w| !w.is_zero()) {
                trace!(?wait, "github adapter: spacing mutations");
                self.clock.sleep(wait);
            }
        }
    }

    fn mark_mutated(&mut self) {
        self.last_mutation = Some(self.clock.now());
    }

    /// Run a mutation after spacing, noting when it finished.
    fn mutate<T>(
        &mut self,
        f: impl FnOnce(&mut GithubRest<H>) -> AdapterResult<T>,
    ) -> AdapterResult<T> {
        self.space();
        let r = f(&mut self.rest);
        self.mark_mutated();
        r
    }

    /// The hidden creation marker line for `ulid` and `nonce`.
    fn signed_marker(&self, ulid: &str, nonce: &str) -> String {
        let signed = self.keyring.sign(MarkerFields {
            repo_node_id: self.repo_node_id.clone(),
            ulid: ulid.to_owned(),
            nonce: nonce.to_owned(),
        });
        format!("<!-- {} -->", format_marker(&signed))
    }
}

/// The marker line already on `body`, kept verbatim across updates (the marker only counts in
/// the creation revision, so an update must not mint a new one).
fn existing_marker_line(body: &str) -> Option<&str> {
    body.lines().find(|l| l.contains("frob:v1"))
}

impl<H: HttpTransport, C: Clock> TrackerAdapter for GithubAdapter<'_, H, C> {
    fn capabilities(&self) -> Capabilities {
        Capabilities {
            native_sub_issues: true,
            native_links: false,
            custom_fields: false,
            state_reasons: StateReasons::Native,
            history_retention: HistoryRetention::Forever,
            markdown: MarkdownDialect::Github,
        }
    }

    fn create(&mut self, projection: &IssueProjection, nonce: &str) -> CreateOutcome {
        let marker = self.signed_marker(&projection.identity.ulid, nonce);
        let rendered = render(projection, &marker);
        self.space();
        let out = self
            .rest
            .create_issue(&rendered.title, &rendered.body, &rendered.labels);
        self.mark_mutated();
        out
    }

    fn update(&mut self, issue: &IssueRef, projection: &IssueProjection) -> AdapterResult<()> {
        let current = self.rest.issue(issue)?;
        let Some(marker) = existing_marker_line(&current.body) else {
            return Err(AdapterError::Other(format!(
                "issue {} carries no creation marker; refusing to rewrite its body",
                issue.0
            )));
        };
        let rendered = render(projection, marker);
        self.mutate(|r| r.patch_issue(issue, &rendered.title, &rendered.body))
    }

    fn close(&mut self, issue: &IssueRef, reason: Outcome) -> AdapterResult<()> {
        let sr = state_reason(reason);
        self.mutate(|r| r.close_issue(issue, sr, &format!("{reason:?}")))
    }

    fn list_by_creator(&self, creator_id: u64) -> AdapterResult<Vec<IssueSummary>> {
        lookup_since(&self.rest, creator_id, "")
    }

    fn read(&self, issue: &IssueRef) -> AdapterResult<IssueState> {
        read::read_issue(&self.rest, issue)
    }

    fn history_after(
        &self,
        issue: &IssueRef,
        after: Option<&EventId>,
    ) -> AdapterResult<Vec<HistoryEntry>> {
        let h = read::history_after(&self.rest, issue, after)?;
        debug!(issue = %issue.0, fidelity = ?h.fidelity, "github adapter: history read");
        Ok(h.entries)
    }

    fn add_labels(&mut self, issue: &IssueRef, labels: &[String]) -> AdapterResult<()> {
        for l in labels {
            self.mutate(|r| r.add_label(issue, l))?;
        }
        Ok(())
    }

    fn remove_labels(&mut self, issue: &IssueRef, labels: &[String]) -> AdapterResult<()> {
        for l in labels {
            self.mutate(|r| r.remove_label(issue, l))?;
        }
        Ok(())
    }

    fn add_assignees(&mut self, issue: &IssueRef, who: &[String]) -> AdapterResult<()> {
        if who.is_empty() {
            return Ok(());
        }
        self.mutate(|r| {
            r.call(
                Method::Post,
                r.issue_path(issue, "/assignees"),
                vec![],
                Some(json!({"assignees": who})),
            )
            .map(drop)
        })
    }

    fn remove_assignees(&mut self, issue: &IssueRef, who: &[String]) -> AdapterResult<()> {
        if who.is_empty() {
            return Ok(());
        }
        self.mutate(|r| {
            r.call(
                Method::Delete,
                r.issue_path(issue, "/assignees"),
                vec![],
                Some(json!({"assignees": who})),
            )
            .map(drop)
        })
    }

    fn link(
        &mut self,
        issue: &IssueRef,
        kind: RelationKind,
        target: &IssueRef,
    ) -> AdapterResult<()> {
        match kind {
            RelationKind::Parent => self.mutate(|r| r.add_sub_issue(target, issue)),
            RelationKind::Child => self.mutate(|r| r.add_sub_issue(issue, target)),
            kind => self.mutate(|r| r.add_link(issue, kind, target)),
        }
    }

    fn inventory(&self) -> AdapterResult<Inventory> {
        let labels = self
            .rest
            .get_all(&self.rest.repo_path("/labels"), &[])?
            .iter()
            .map(|l| str_of(l, "name"))
            .filter(|n| n.starts_with(crate::fields::MANAGED_LABEL_PREFIX))
            .collect();
        let milestones = self
            .rest
            .get_all(&self.rest.repo_path("/milestones"), &[("state", "all")])?
            .iter()
            .map(|m| str_of(m, "title"))
            .collect();
        // Issue types are an organisation feature; a user-owned repo answers not found.
        let types_path = format!("/orgs/{}/issue-types", encode_segment(&self.rest.owner));
        let issue_types = match self.rest.get(types_path, vec![]) {
            Ok(v) => v
                .as_array()
                .map(|a| a.iter().map(|t| str_of(t, "name")).collect())
                .unwrap_or_default(),
            Err(AdapterError::NotFound) => Vec::new(),
            Err(e) => return Err(e),
        };
        Ok(Inventory {
            labels,
            milestones,
            issue_types,
        })
    }
}

#[cfg(test)]
mod tests {
    use std::cell::{Cell, RefCell};
    use std::collections::{BTreeSet, VecDeque};

    use gob_trust::MachineKey;

    use super::*;
    use crate::projection::{
        Category, Classification, Identity, People, State, TicketFacts, project,
    };

    /// Scripted transport: pops queued responses and records every request.
    #[derive(Default)]
    struct Fake {
        log: RefCell<Vec<HttpRequest>>,
        replies: RefCell<VecDeque<Result<HttpResponse, TransportError>>>,
    }

    impl Fake {
        fn queue(&self, status: u16, body: &str) {
            self.replies.borrow_mut().push_back(Ok(HttpResponse {
                status,
                location: None,
                body: body.into(),
            }));
        }
    }

    impl HttpTransport for &Fake {
        fn send(&self, req: &HttpRequest) -> Result<HttpResponse, TransportError> {
            self.log.borrow_mut().push(req.clone());
            self.replies
                .borrow_mut()
                .pop_front()
                .unwrap_or(Ok(HttpResponse {
                    status: 200,
                    location: None,
                    body: String::new(),
                }))
        }
    }

    #[derive(Default)]
    struct FakeClock(Cell<Duration>);

    impl Clock for FakeClock {
        fn now(&self) -> Duration {
            self.0.get()
        }
        fn sleep(&self, d: Duration) {
            self.0.set(self.0.get() + d);
        }
    }

    fn keyring() -> Keyring {
        Keyring::new("k1", MachineKey::from_bytes([7; 32]), vec![]).expect("keyring")
    }

    fn projection() -> IssueProjection {
        let facts = TicketFacts {
            identity: Identity {
                ulid: "01M5ASPRW2FYMNRHWQHEVN9W9J".into(),
                handle: "~PM742G1".into(),
                aliases: vec![],
                repository: "https://example.invalid/r".into(),
                ledger_path: "tickets/x".into(),
            },
            title: "T".into(),
            summary: "Sum".into(),
            acceptance: vec![],
            scope: vec![],
            evidence: vec![],
            classification: Classification::default(),
            state: State {
                category: Category::Todo,
                outcome: None,
                reason: None,
            },
            relations: vec![],
            people: People::default(),
            last_event: "EV".into(),
        };
        project(&facts, &BTreeSet::new(), "1")
    }

    fn adapter<'a>(
        fake: &'a Fake,
        kr: &'a Keyring,
        clock: &'a FakeClock,
    ) -> GithubAdapter<'a, &'a Fake, FakeClock> {
        GithubAdapter::new(GithubRest::new(fake, "o", "r", "bot"), kr, "R_node", clock)
    }

    // frob:tests GithubAdapter
    // frob:tests crates/frob-mirror/src/github/adapter.rs::HttpTransport.send
    #[test]
    fn create_confirms_rejects_and_flags_unknown() {
        let (fake, kr, clock) = (Fake::default(), keyring(), FakeClock::default());
        let mut a = adapter(&fake, &kr, &clock);
        fake.queue(201, r#"{"number": 7}"#);
        assert_eq!(
            a.create(&projection(), "n1"),
            CreateOutcome::Created(IssueRef("7".into()))
        );
        let body = fake.log.borrow()[0].body.clone().expect("body");
        let text = body["body"].as_str().expect("text");
        assert!(text.contains("frob:v1 kid=k1") && text.contains("nonce=n1"));
        fake.queue(422, "{}");
        assert!(matches!(
            a.create(&projection(), "n2"),
            CreateOutcome::Failed(_)
        ));
        fake.queue(502, "");
        assert_eq!(a.create(&projection(), "n3"), CreateOutcome::Unknown);
        fake.replies
            .borrow_mut()
            .push_back(Err(TransportError::Timeout));
        assert_eq!(a.create(&projection(), "n4"), CreateOutcome::Unknown);
    }

    // frob:tests GithubAdapter
    #[test]
    fn update_keeps_marker_and_close_sends_reason() {
        let (fake, kr, clock) = (Fake::default(), keyring(), FakeClock::default());
        let mut a = adapter(&fake, &kr, &clock);
        let issue = IssueRef("7".into());
        fake.queue(
            200,
            r#"{"number":7,"body":"old\n<!-- frob:v1 kid=k1 ulid=U nonce=n mac=00 -->\n"}"#,
        );
        a.update(&issue, &projection()).expect("update");
        let sent = fake.log.borrow()[1].clone();
        assert_eq!(sent.method, Method::Patch);
        let b = sent.body.expect("body");
        assert!(
            b["body"]
                .as_str()
                .expect("s")
                .contains("kid=k1 ulid=U nonce=n")
        );
        // A body without a marker is never rewritten.
        fake.queue(200, r#"{"number":7,"body":"plain"}"#);
        assert!(a.update(&issue, &projection()).is_err());
        assert_eq!(fake.log.borrow().len(), 3);

        a.close(&issue, Outcome::Duplicate).expect("close");
        let sent = fake.log.borrow()[3].clone();
        assert_eq!(
            sent.body,
            Some(json!({"state": "closed", "state_reason": "duplicate"}))
        );
    }

    // frob:tests GithubAdapter
    #[test]
    fn mutations_are_spaced_and_labels_are_additive() {
        let (fake, kr, clock) = (Fake::default(), keyring(), FakeClock::default());
        let mut a = adapter(&fake, &kr, &clock);
        let issue = IssueRef("7".into());
        a.add_labels(&issue, &["frob:managed".into(), "frob:x y".into()])
            .expect("add");
        a.remove_labels(&issue, &["frob:x y".into()]).expect("rm");
        assert_eq!(clock.now(), WRITE_SPACING * 2);
        let log = fake.log.borrow();
        assert_eq!(log[0].method, Method::Post);
        assert_eq!(log[0].body, Some(json!({"labels": ["frob:managed"]})));
        assert_eq!(log[2].method, Method::Delete);
        assert_eq!(log[2].path, "/repos/o/r/issues/7/labels/frob%3Ax%20y");
    }

    // frob:tests GithubAdapter
    #[test]
    fn read_maps_issue_and_statuses() {
        let (fake, kr, clock) = (Fake::default(), keyring(), FakeClock::default());
        let a = adapter(&fake, &kr, &clock);
        let issue = IssueRef("7".into());
        fake.queue(
            200,
            r#"{"number":7,"title":"T","body":"B","state":"closed",
                "labels":[{"name":"a"}],"assignees":[{"login":"z"}]}"#,
        );
        let s = a.read(&issue).expect("read");
        assert!(s.closed && s.labels == ["a"] && s.assignees == ["z"] && s.body == "B");
        for (code, want) in [
            (404, AdapterError::NotFound),
            (410, AdapterError::Gone),
            (429, AdapterError::RateLimited),
            (500, AdapterError::Other("http 500".into())),
        ] {
            fake.queue(code, "");
            assert_eq!(a.read(&issue).expect_err("err"), want);
        }
        fake.replies.borrow_mut().push_back(Ok(HttpResponse {
            status: 301,
            location: Some("/new".into()),
            body: String::new(),
        }));
        assert_eq!(
            a.read(&issue).expect_err("moved"),
            AdapterError::Moved("/new".into())
        );
    }

    // frob:tests GithubAdapter
    #[test]
    fn list_by_creator_filters_creator_and_pull_requests() {
        let (fake, kr, clock) = (Fake::default(), keyring(), FakeClock::default());
        let a = adapter(&fake, &kr, &clock);
        fake.queue(
            200,
            r#"[{"number":3,"title":"a","created_at":"2026-01-02T00:00:00Z","user":{"id":9}},
                {"number":2,"title":"pr","created_at":"2026-01-01T00:00:00Z","user":{"id":9},"pull_request":{}},
                {"number":1,"title":"other","created_at":"2026-01-01T00:00:00Z","user":{"id":5}}]"#,
        );
        let got = a.list_by_creator(9).expect("list");
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].issue, IssueRef("3".into()));
        assert!(
            fake.log.borrow()[0]
                .query
                .contains(&("creator".into(), "bot".into()))
        );
    }

    // frob:tests GithubAdapter
    #[test]
    fn history_merges_timeline_and_graphql_edits() {
        let (fake, kr, clock) = (Fake::default(), keyring(), FakeClock::default());
        let a = adapter(&fake, &kr, &clock);
        let issue = IssueRef("7".into());
        fake.queue(
            200,
            r#"[{"event":"labeled","id":11,"created_at":"2026-01-02T00:00:00Z",
                 "actor":{"id":9},"label":{"name":"frob:managed"}},
                {"event":"commented","id":12}]"#,
        );
        fake.queue(
            200,
            r#"{"data":{"repository":{"issue":{"userContentEdits":{"totalCount":2,"nodes":[
                {"id":"E2","createdAt":"2026-01-03T00:00:00Z","diff":"v2","editor":{"databaseId":9}},
                {"id":"E1","createdAt":"2026-01-01T00:00:00Z","diff":"v1","editor":{"databaseId":9}}]}}}}}"#,
        );
        let h = a.history_after(&issue, None).expect("history");
        let ids: Vec<_> = h.iter().map(|e| e.event.0.as_str()).collect();
        assert_eq!(ids, ["11", "E2"]);
        assert_eq!(h[0].field, "labels");
    }

    // frob:tests GithubAdapter
    #[test]
    fn links_resolve_database_ids() {
        let (fake, kr, clock) = (Fake::default(), keyring(), FakeClock::default());
        let mut a = adapter(&fake, &kr, &clock);
        let (i, t) = (IssueRef("1".into()), IssueRef("2".into()));
        fake.queue(200, r#"{"id":222}"#);
        a.link(&i, RelationKind::Child, &t).expect("sub");
        {
            let log = fake.log.borrow();
            assert_eq!(log[1].path, "/repos/o/r/issues/1/sub_issues");
            assert_eq!(log[1].body, Some(json!({"sub_issue_id": 222})));
        }
        fake.queue(200, r#"{"id":111}"#);
        a.link(&i, RelationKind::BlockedBy, &t).expect("dep");
        assert_eq!(
            fake.log.borrow()[3].path,
            "/repos/o/r/issues/1/dependencies/blocked_by"
        );
        assert!(a.link(&i, RelationKind::Relates, &t).is_err());
    }

    // frob:tests GithubAdapter
    #[test]
    fn inventory_reads_managed_labels_milestones_and_types() {
        let (fake, kr, clock) = (Fake::default(), keyring(), FakeClock::default());
        let a = adapter(&fake, &kr, &clock);
        fake.queue(200, r#"[{"name":"frob:managed"},{"name":"bug"}]"#);
        fake.queue(200, r#"[{"title":"M1"}]"#);
        fake.queue(404, "");
        let inv = a.inventory().expect("inventory");
        assert_eq!(inv.labels, ["frob:managed"]);
        assert_eq!(inv.milestones, ["M1"]);
        assert!(inv.issue_types.is_empty());
    }
}
