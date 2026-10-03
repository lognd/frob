//! The definition of done as close guards: every entry of `[pm] done_requires` is enforced (pm-enforcement.md section 3).
// frob:ticket 01M40WS6200M99J09D5XGAS05X

use std::path::Path;

use frob_ledger::guards::{CloseContext, CloseGuard, GuardFailure};
use frob_ledger::model::{Category, Outcome, Ticket};
use frob_ledger::{Ledger, TicketId};
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

/// Enforces `[pm] done_requires` when a ticket would be closed as completed work.
#[derive(Debug, Clone)]
pub struct DoneGuard {
    requires: Vec<DoneRequirement>,
    open_children: Vec<String>,
    fragment_present: bool,
    bypass: Option<String>,
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
        let fragment_present = fragment_exists(root, id);
        tracing::debug!(requires = ?pm.pm.done_requires, fragment_present, "done guard loaded");
        Ok(Self {
            requires: pm.pm.done_requires,
            open_children,
            fragment_present,
            bypass: None,
        })
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

    fn fragment(&self, cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        if self.fragment_present {
            return Ok(());
        }
        Err(GuardFailure {
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
                 edit the sentence, and commit it; or remove changelog_fragment from [pm] done_requires",
                h = cx.handle
            )),
        })
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

/// True when `<root>/changelog.d` holds `<ULID>.<type>.md` for ticket `id`.
fn fragment_exists(root: &Path, id: TicketId) -> bool {
    let prefix = format!("{id}.");
    let Ok(rd) = std::fs::read_dir(root.join("changelog.d")) else {
        return false;
    };
    rd.filter_map(std::result::Result::ok).any(|e| {
        let name = e.file_name().to_string_lossy().into_owned();
        name.starts_with(&prefix)
            && Path::new(&name)
                .extension()
                .is_some_and(|x| x.eq_ignore_ascii_case("md"))
    })
}

impl CloseGuard for DoneGuard {
    fn name(&self) -> &'static str {
        "done_requires"
    }

    fn check(&self, cx: &CloseContext<'_>) -> Result<(), GuardFailure> {
        if !matches!(cx.outcome, Some(Outcome::Done | Outcome::Fixed)) {
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
