//! The closed list of spawn classes from `git-io.md` section 3.

/// Every class of process the design allows frob to spawn.
///
/// The git classes are the closed list; the rest are non-git classes that
/// share the same `gob-exec` runner so `frob --timing` can count them.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SpawnClass {
    /// Three-way merge when gix cannot apply or resolve it; at most 1 per land.
    GitMerge,
    /// `git worktree add` until gix's worktree write path is complete; at most 1 per `work`.
    GitWorktreeAdd,
    /// A repo-configured hook (`pre-commit`, `pre-push`); 1 per commit or push when enabled.
    RepoHook,
    /// `git push` over SSH until gix push is stable; 1 per `--push`.
    GitPush,
    /// The user-invoked `frob git -- ...` escape hatch; explicit only.
    GitEscapeHatch,
    /// Test runners and evidence providers; one per selected runner, within `[perf] jobs`.
    TestRunner,
    /// A configured `[[check.tool]]` external linter; one per tool.
    CheckTool,
    /// A sibling `grimble check --json` or `crunk check --json`; at most 1 per sibling per check.
    Sibling,
    /// `grimble vet --hook` from the pre-tool hook; 1 per guarded call.
    VetHook,
    /// An out-of-process helper (Tailwind runtime, playwright gallery); one per crunk run.
    Helper,
}

impl SpawnClass {
    /// Every class, in `git-io.md` table order.
    pub const ALL: [SpawnClass; 10] = [
        Self::GitMerge,
        Self::GitWorktreeAdd,
        Self::RepoHook,
        Self::GitPush,
        Self::GitEscapeHatch,
        Self::TestRunner,
        Self::CheckTool,
        Self::Sibling,
        Self::VetHook,
        Self::Helper,
    ];

    /// True when the class runs the `git` binary (the closed first table).
    pub fn is_git(self) -> bool {
        matches!(
            self,
            Self::GitMerge | Self::GitWorktreeAdd | Self::GitPush | Self::GitEscapeHatch
        )
    }

    /// Stable lowercase label used in spawn logs and timing output.
    pub fn label(self) -> &'static str {
        match self {
            Self::GitMerge => "git-merge",
            Self::GitWorktreeAdd => "git-worktree-add",
            Self::RepoHook => "repo-hook",
            Self::GitPush => "git-push",
            Self::GitEscapeHatch => "git-escape-hatch",
            Self::TestRunner => "test-runner",
            Self::CheckTool => "check-tool",
            Self::Sibling => "sibling",
            Self::VetHook => "vet-hook",
            Self::Helper => "helper",
        }
    }
}
