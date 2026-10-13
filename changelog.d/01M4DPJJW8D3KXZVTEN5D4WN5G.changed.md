A new worktree seeds the repository-shared check cache from the primary checkout's own cache when no shared cache exists yet, so the first check --ticket there is not a cold whole-repo run.
