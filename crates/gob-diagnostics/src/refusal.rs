//! Refusal classes (one per row of the cli.md table) and the `Refusal` error.

use crate::envelope::EnvelopeError;
use crate::exit::ExitCode;

/// Class of a non-ok outcome; fixes the exit code and `retryable` flag.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RefusalClass {
    /// Domain negative: the yes/no answer is no.
    DomainNegative,
    /// Usage error: bad flags, unknown verb, schema failure.
    UsageError,
    /// Guard that clears by waiting (lease held, lock held, CAS lost).
    GuardRetryByWaiting,
    /// Guard that needs the caller to act; `remedy` is the exact command.
    GuardNeedsAction,
    /// A `--wait` expired before the lock freed.
    Timeout,
    /// Internal error (a bug).
    Internal,
}

impl RefusalClass {
    /// Every class, in table order.
    pub const ALL: [Self; 6] = [
        Self::DomainNegative,
        Self::UsageError,
        Self::GuardRetryByWaiting,
        Self::GuardNeedsAction,
        Self::Timeout,
        Self::Internal,
    ];

    /// Exit code for this class.
    pub const fn exit_code(self) -> ExitCode {
        match self {
            Self::DomainNegative => ExitCode::Negative,
            Self::UsageError => ExitCode::Usage,
            Self::GuardRetryByWaiting | Self::GuardNeedsAction | Self::Timeout => ExitCode::Refused,
            Self::Internal => ExitCode::Internal,
        }
    }

    /// True when the same argv may succeed later with no caller action.
    pub const fn retryable(self) -> bool {
        matches!(self, Self::GuardRetryByWaiting | Self::Timeout)
    }

    /// One-line description of the class.
    pub const fn doc(self) -> &'static str {
        match self {
            Self::DomainNegative => "the caller asked for a yes/no answer and it is no",
            Self::UsageError => "bad flags, unknown verb, or input that fails its schema",
            Self::GuardRetryByWaiting => "a guard that clears without caller action",
            Self::GuardNeedsAction => "a guard that needs the caller to change something",
            Self::Timeout => "a wait expired before the lock freed",
            Self::Internal => "a bug; a report path is named in the envelope",
        }
    }
}

/// A refused operation: stable code, class, message and the exact remedy.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{code}: {message}")]
pub struct Refusal {
    /// Stable code such as `E-LEASE-HELD`.
    pub code: String,
    /// Class fixing exit code and retryability.
    pub class: RefusalClass,
    /// Human-readable explanation.
    pub message: String,
    /// The exact corrected command, when one exists.
    pub remedy: Option<String>,
    /// True when only a person at a terminal can act; `remedy` is then prose, not a command.
    pub requires_human: bool,
}

impl Refusal {
    /// Build a refusal without a remedy.
    pub fn new(code: impl Into<String>, class: RefusalClass, message: impl Into<String>) -> Self {
        let r = Self {
            code: code.into(),
            class,
            message: message.into(),
            remedy: None,
            requires_human: false,
        };
        tracing::debug!(code = %r.code, ?class, "refusal built");
        r
    }

    // frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
    /// `E-STATE-TRACKED`: git tracks state or cache files; exit 3, names every file.
    pub fn state_tracked(files: &[String]) -> Self {
        Self::new(
            "E-STATE-TRACKED",
            RefusalClass::GuardNeedsAction,
            format!(
                "git tracks state or cache files that must stay untracked: {}",
                files.join(", ")
            ),
        )
        .with_remedy("git rm -r --cached <path> for each listed file, then ignore its directory")
        .requiring_human()
    }

    /// Attach the exact corrected command.
    #[must_use]
    pub fn with_remedy(mut self, remedy: impl Into<String>) -> Self {
        self.remedy = Some(remedy.into());
        self
    }

    /// Mark the remedy as a person's to carry out: an agent must stop and tell the user.
    #[must_use]
    pub const fn requiring_human(mut self) -> Self {
        self.requires_human = true;
        self
    }

    /// Exit code implied by the class.
    pub const fn exit_code(&self) -> ExitCode {
        self.class.exit_code()
    }
}

impl From<&Refusal> for EnvelopeError {
    fn from(r: &Refusal) -> Self {
        Self {
            code: r.code.clone(),
            message: r.message.clone(),
            remedy: r.remedy.clone(),
            retryable: r.class.retryable(),
            requires_human: r.requires_human,
        }
    }
}
