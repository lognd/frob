//! The definition of done as close guards: every entry of `[pm] done_requires` is enforced (pm-enforcement.md section 3).
// frob:ticket 01M40WS6200M99J09D5XGAS05X

use std::path::Path;

use frob_ledger::event::{ChangelogExemptData, EventBody};
use frob_ledger::guards::{CloseContext, CloseGuard, GuardFailure};
use frob_ledger::model::{Category, Outcome, Ticket};
use frob_ledger::{EventId, Ledger, TicketId};
use frob_pm::{DoneRequirement, PmConfig};

use crate::error::{EvidenceError, Result as EvResult};

/// Stable code of a criterion that has no passing evidence or attestation bound to it.
pub const CODE_CRITERIA: &str = "E-DONE-CRITERIA-UNBOUND";
/// Stable code of a ticket that still has open children.
pub const CODE_CHILDREN: &str = "E-DONE-OPEN-CHILDREN";
/// Stable code of a requirement that cannot be evaluated yet (Unresolved, never a silent pass).
pub const CODE_UNRESOLVED: &str = "E-DONE-UNRESOLVED";
/// Stable code of a missing changelog fragment (REL003).
pub const CODE_FRAGMENT: &str = "E-DONE-CHANGELOG-FRAGMENT";

/// Flavour of a ticket that carries a measured target (pm-enforcement.md section 2a).
const OBJECTIVE_FLAVOUR: &str = "quality_objective";

// frob:ticket 01M41KT4RMYMMP9SSFN8RZK7QV
/// Whether the done guards (evidence, criteria, children, fragment) apply to a close with `outcome`.
///
/// Only `done` and `fixed` claim a change was made; `invalid`, `duplicate` and `wont-fix` close on a reason alone. A missing outcome is judged strictly (the outcome guard refuses it anyway). `ticket close`, `land` and both guards read this one answer.
pub fn guards_apply(outcome: Option<Outcome>) -> bool {
    let applies = !matches!(
        outcome,
        Some(Outcome::Invalid | Outcome::Duplicate | Outcome::WontFix)
    );
    tracing::debug!(?outcome, applies, "done guards applicability");
    applies
}

/// The usage message when a close with `outcome` needs a `--reason` and `reason` is missing or blank; `None` when nothing is wrong.
///
/// Shared by `ticket close` and `land` so both demand the same thing of `invalid`, `duplicate` and `wont-fix`.
// frob:ticket 01M41KT4RMYMMP9SSFN8RZK7QV
pub fn missing_reason(outcome: Option<Outcome>, reason: Option<&str>) -> Option<String> {
    if guards_apply(outcome) || reason.is_some_and(|r| !r.trim().is_empty()) {
        return None;
    }
    Some(format!(
        "closing as {} needs --reason <text> saying why (no evidence or changelog is asked for)",
        outcome.map_or("this outcome", Outcome::as_str)
    ))
}

/// What the ticket's changelog fragment looks like on disk, judged by the compile's own validator.
#[derive(Debug, Clone, PartialEq, Eq)]
enum FragmentState {
    /// No `changelog.d/<ULID>.*.md` file.
    Missing,
    /// Every fragment of the ticket validates.
    Valid,
    /// At least one fragment fails validation; the messages name the file and the problem.
    Invalid(Vec<String>),
}

/// Enforces `[pm] done_requires` when a ticket would be closed as completed work.
#[derive(Debug, Clone)]
pub struct DoneGuard {
    requires: Vec<DoneRequirement>,
    open_children: Vec<String>,
    fragment: FragmentState,
    bypass: Option<String>,
    /// A `changelog-exempt` event already on the ticket.
    recorded_exemption: bool,
    /// The reason of this close's `--no-changelog --reason`.
    no_changelog: Option<String>,
}

impl DoneGuard {
    /// A guard for ticket `id` with the requirements of `<root>/frob.toml`, its open children read from `ledger` and its fragment looked up under `<root>/changelog.d`.
    ///
    /// # Errors
    ///
    /// [`EvidenceError::Config`] for an unreadable `[pm]` table, ledger failures reading the children.
    pub fn for_ticket(ledger: &Ledger, id: TicketId, root: &Path) -> EvResult<Self> {
        let pm = PmConfig::load(root).map_err(|e| EvidenceError::Config(e.to_string()))?;
        let view = ledger.show(id)?;
        let open_children = view
            .children
            .iter()
            .filter(|c| c.category != Category::Done)
            .map(|c| format!("{} ({})", c.handle, c.title))
            .collect();
        let fragment = fragment_state(root, id, &view.summary.handle);
        let recorded_exemption =
            frob_ledger::event::changelog_exemption(&ledger.events(id)?).is_some();
        tracing::debug!(requires = ?pm.pm.done_requires, ?fragment, recorded_exemption, "done guard loaded");
        Ok(Self {
            requires: pm.pm.done_requires,
            open_children,
            fragment,
            bypass: None,
            recorded_exemption,
            no_changelog: None,
        })
    }

    /// Satisfy `changelog_fragment` without a fragment (`--no-changelog --reason <why>`); [`Self::record_exemption`] audits it.
    #[must_use]
    pub fn allow_no_changelog(mut self, reason: impl Into<String>) -> Self {
        let reason = reason.into();
        tracing::warn!(%reason, "changelog exemption requested");
        self.no_changelog = Some(reason);
        self
    }

    /// The reason of the exemption this guard was given, when there is one.
    pub fn exemption_reason(&self) -> Option<&str> {
        self.no_changelog.as_deref()
    }

    /// Write the exemption as a `changelog-exempt` event on `id`; `None` when none was requested or the ticket already carries one with this reason.
    ///
    /// Call it before the close so a crash cannot leave a closed ticket without its record; an event on a ticket whose close is then refused is harmless, and a retry with the same reason reuses it.
    ///
    /// # Errors
    ///
    /// Ledger, git or format failures.
    pub fn record_exemption(&self, ledger: &Ledger, id: TicketId) -> EvResult<Option<EventId>> {
        let Some(reason) = self.no_changelog.as_deref() else {
            return Ok(None);
        };
        let existing = frob_ledger::event::changelog_exemption(&ledger.events(id)?);
        if existing.is_some_and(|x| x.reason == reason) {
            tracing::debug!(ticket = %id, "changelog exemption already recorded; not repeated");
            return Ok(None);
        }
        let body = EventBody::ChangelogExempt(ChangelogExemptData {
            reason: reason.to_owned(),
        });
        let applied = ledger.append(id, body)?;
        let event = applied.events.first().copied().ok_or_else(|| {
            EvidenceError::Malformed("the changelog-exempt event was not written".to_owned())
        })?;
        tracing::info!(ticket = %id, event = %event, "changelog exemption audited");
        Ok(Some(event))
    }

    /// Let `criteria_evidenced` through (`--no-evidence --reason <why>`); no other requirement has a bypass.
    #[must_use]
    pub fn allow_bypass(mut self, reason: impl Into<String>) -> Self {
        self.bypass = Some(reason.into());
        self
    }

    /// Notices a successful close carries: a ticket without criteria passed `criteria_evidenced` vacuously.
    pub fn warnings(&self, ticket: &Ticket) -> Vec<String> {
        let mut out = Vec::new();
        if self.requires.contains(&DoneRequirement::CriteriaEvidenced)
            && matches!(ticket.front.outcome, Some(Outcome::Done | Outcome::Fixed))
            && ticket.front.acceptance.is_empty()
        {
            out.push(
                "criteria_evidenced passed vacuously: the ticket has no acceptance criteria"
                    .to_owned(),
            );
        }
        out
    }

    fn criteria(&self, cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        if self.bypass.is_some() {
            return Ok(());
        }
        let acceptance = &cx.ticket.front.acceptance;
        let unbound: Vec<String> = acceptance
            .iter()
            .enumerate()
            .filter(|(_, a)| !a.bound)
            .map(|(i, a)| format!("{}. {}", i + 1, a.text))
            .collect();
        if unbound.is_empty() {
            return Ok(());
        }
        Err(GuardFailure {
            code: CODE_CRITERIA.to_owned(),
            message: format!(
                "closing {} needs every acceptance criterion bound to passing evidence \
                 (criteria_evidenced); unbound: {}",
                cx.handle,
                unbound.join("; ")
            ),
            remedy: Some(format!(
                "frob ticket evidence add {} --provider <nextest|command|file> --ref <ref> --accepts <N>; \
                 or, audited, frob ticket close {} --outcome done --no-evidence --reason <why>",
                cx.handle, cx.handle
            )),
        })
    }

    fn children(&self, cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        if self.open_children.is_empty() {
            return Ok(());
        }
        Err(GuardFailure {
            code: CODE_CHILDREN.to_owned(),
            message: format!(
                "closing {} needs every child closed (no_open_children); open: {}",
                cx.handle,
                self.open_children.join("; ")
            ),
            remedy: Some("close or drop each open child, then retry".to_owned()),
        })
    }

    fn objective(cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        if cx.ticket.front.flavour.as_deref() != Some(OBJECTIVE_FLAVOUR) {
            return Ok(());
        }
        Err(unresolved(
            cx,
            "objective_target_met",
            "a quality objective's target and its measured value are not stored on tickets yet (pm-enforcement.md section 2a)",
        ))
    }

    fn docs(cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        Err(unresolved(
            cx,
            "docs_touched_or_excepted",
            "no docs exception record exists yet and the close sees no diff to judge whether docs were touched",
        ))
    }

    // frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
    fn fragment(&self, cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        if self.no_changelog.is_some() || self.recorded_exemption {
            return Ok(());
        }
        match &self.fragment {
            FragmentState::Valid => Ok(()),
            FragmentState::Missing => Err(GuardFailure {
                code: CODE_FRAGMENT.to_owned(),
                message: format!(
                    "closing {} needs a changelog fragment (changelog_fragment, REL003, ~HE2EX99): \
                     changelog.d/{}.<type>.md must exist",
                    cx.handle, cx.ticket.front.id
                ),
                // frob:ticket 01M4069WHH6KXYWDAJD3TXB8SR
                remedy: Some(format!(
                    "run `frob ticket fragment {h}` in the ticket's worktree (writes changelog.d/<ULID>.<type>.md from the title; \
                     add --type added|changed|fixed|removed|deprecated|security and --sentence \"<one user-facing sentence>\" to set them), \
                     edit the sentence, and commit it; \
                     or, when the change has no user-visible effect, close with `--no-changelog --reason <why>` (audited as a changelog-exempt event)",
                    h = cx.handle
                )),
            }),
            FragmentState::Invalid(problems) => Err(GuardFailure {
                code: CODE_FRAGMENT.to_owned(),
                message: format!(
                    "closing {} has an invalid changelog fragment (changelog_fragment, REL003): {}",
                    cx.handle,
                    problems.join("; ")
                ),
                remedy: Some(format!(
                    "fix what the message names, or replace the fragment with `frob ticket fragment {h} --force`, then commit it",
                    h = cx.handle
                )),
            }),
        }
    }
}

/// The refusal for a requirement that cannot be evaluated: Unresolved, never a pass.
fn unresolved(cx: &CloseContext<'_>, name: &str, why: &str) -> GuardFailure {
    GuardFailure {
        code: CODE_UNRESOLVED.to_owned(),
        message: format!(
            "Unresolved: {name} cannot be evaluated for {} yet: {why}",
            cx.handle
        ),
        remedy: Some(format!(
            "remove {name} from [pm] done_requires in frob.toml until it can be evaluated"
        )),
    }
}

/// Validate the fragments of ticket `id` (handle `handle`) under `<root>/changelog.d` with `frob-release`'s validator.
fn fragment_state(root: &Path, id: TicketId, handle: &str) -> FragmentState {
    let ulid = id.to_string();
    let resolver = |u: &str| u.eq_ignore_ascii_case(&ulid).then(|| handle.to_owned());
    match frob_release::fragment::validate_ticket(&root.join("changelog.d"), &ulid, &resolver) {
        Ok(found) if found.is_empty() => FragmentState::Missing,
        Ok(_) => FragmentState::Valid,
        Err(errs) => FragmentState::Invalid(errs.iter().map(ToString::to_string).collect()),
    }
}

impl CloseGuard for DoneGuard {
    fn name(&self) -> &'static str {
        "done_requires"
    }

    fn check(&self, cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        if !guards_apply(cx.outcome) {
            return Ok(());
        }
        for req in &self.requires {
            let verdict = match req {
                DoneRequirement::CriteriaEvidenced => self.criteria(cx),
                DoneRequirement::NoOpenChildren => self.children(cx),
                DoneRequirement::ObjectiveTargetMet => Self::objective(cx),
                DoneRequirement::DocsTouchedOrExcepted => Self::docs(cx),
                DoneRequirement::ChangelogFragment => self.fragment(cx),
            };
            if let Err(f) = &verdict {
                tracing::info!(requirement = ?req, code = %f.code, "done requirement refused");
            }
            verdict?;
        }
        Ok(())
    }
}
