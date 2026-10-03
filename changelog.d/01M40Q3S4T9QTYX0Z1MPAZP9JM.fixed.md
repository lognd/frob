frob: two concurrent `frob work` calls can no longer both take the last repository WIP slot; the count now runs inside the lease-store lock.
