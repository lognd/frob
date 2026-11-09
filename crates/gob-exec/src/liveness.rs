//! Process liveness probe shared by the land lock and the check lock.

/// True when process `pid` exists (Linux `/proc`; elsewhere assumed alive, so a lock is never stolen).
#[must_use]
pub fn pid_alive(pid: u32) -> bool {
    let alive = if cfg!(target_os = "linux") {
        std::path::Path::new(&format!("/proc/{pid}")).exists()
    } else {
        true
    };
    tracing::trace!(pid, alive, "probed process liveness");
    alive
}

#[cfg(test)]
mod tests {
    use super::pid_alive;

    #[test]
    fn current_process_is_alive() {
        assert!(pid_alive(std::process::id()));
    }
}
