A check run without --fix now fails with E-CHECK-READONLY if it modified a file a fix would edit, and a fixture proves a read-only check leaves a fixable tree untouched.
