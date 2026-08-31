"""`_CUDA_OPERATIONS`: the cuda slice of `DANGEROUS_OPERATIONS` (T-3493,
mirrors `_dangerous_ops_java.py`'s T-3492 precedent -- cuda gets its own
file rather than folding into `_dangerous_ops_other.py`, the same
LARGE001-threshold reasoning that split bash/csharp/java out).

A `.cu`/`.cuh` file compiles with a HOST C/C++ compiler (nvcc invokes the
platform's own C++ toolchain for everything outside `__global__`/
`__device__` kernel code) -- the same libc/POSIX/Win32 dangerous-operation
surface `_dangerous_ops_other.py`'s c-cpp entries already pattern is
reachable verbatim from cuda host code, so the needles below intentionally
mirror c-cpp's own entries exactly (same functions, same C ABI, just
matched against `.cu`/`.cuh` source text). CUDA's own device-side surface
(`cudaMalloc`/`cudaMemcpy`/kernel launch `<<<...>>>`) is a memory-safety
concern, not a net/fs/exec/eval/deserialize-shaped dangerous capability in
this registry's taxonomy -- no CAPABILITY_KINDS bucket fits it, so it is
deliberately not patterned here (mirrors this registry's own "buffer
overflow != new kind" precedent for c-cpp's strcpy-family entry)."""

from __future__ import annotations

from frob.vet._capability_registry._schemas import _DangerousOperation, _op

_CUDA_OPERATIONS: tuple[_DangerousOperation, ...] = (
    # -- cuda (host C ABI): exec ---------------------------------------------
    _op(
        "cuda",
        "libc",
        "system()",
        "exec",
        "runs a command through the shell with the current process's privileges",
        "use exec* with a fixed argv array, never a shell-interpreted string",
        "critical",
        ("system(",),
        ("CWE-78",),
    ),
    _op(
        "cuda",
        "libc",
        "popen()",
        "exec",
        "opens a shell pipe to/from a command",
        "use posix_spawn/exec* with a fixed argv array",
        "high",
        ("popen(",),
        ("CWE-78",),
    ),
    _op(
        "cuda",
        "libc",
        "exec* family (execl/execv/execve/...)",
        "exec",
        "replaces the process image, running attacker-influenceable input if "
        "the path/argv is untrusted",
        "validate the program path and argv come from a trusted, fixed set",
        "high",
        (
            "execl(",
            "execv(",
            "execve(",
            "execvp(",
            "execle(",
            "execvpe(",
            "posix_spawn(",
            "posix_spawnp(",
            "fexecve(",
        ),
        ("CWE-78",),
    ),
    # -- cuda (host C ABI): fs-read -------------------------------------------
    _op(
        "cuda",
        "libc",
        "fread()/fgets()",
        "fs-read",
        "reads local filesystem state",
        "validate the source path is inside an expected root before reading",
        "low",
        ("fread(", "fgets("),
        (),
    ),
    _op(
        "cuda",
        "libc",
        "open()/read()/mmap()",
        "fs-read",
        "reads local filesystem state via a raw file descriptor",
        "validate the source path is inside an expected root before reading",
        "low",
        ("open(", "read(", "mmap("),
        (),
    ),
    # -- cuda (host C ABI): ffi (dynamic loading) -----------------------------
    _op(
        "cuda",
        "libdl",
        "dlopen()",
        "ffi",
        "loads a shared library at runtime and resolves symbols dynamically",
        "avoid loading libraries from untrusted or writable paths",
        "critical",
        ("dlopen(",),
        (),
    ),
    # -- cuda (host C ABI): fs-write -------------------------------------------
    _op(
        "cuda",
        "libc",
        "strcpy/sprintf/gets family",
        "fs-write",
        "unbounded string copy/format into a fixed buffer, the classic "
        "stack-smashing primitive",
        "use strncpy/snprintf/fgets with an explicit bound",
        "critical",
        ("strcpy(", "sprintf(", "gets("),
        ("CWE-120",),
    ),
    _op(
        "cuda",
        "libc",
        "fopen()/fwrite()/write()/rename()/unlink()/mkdir()",
        "fs-write",
        "creates, overwrites, renames, deletes, or writes local filesystem state",
        "validate the destination path is inside an expected, writable root",
        "high",
        ("fopen(", "fwrite(", "write(", "rename(", "unlink(", "mkdir("),
        (),
    ),
    # -- cuda (host C ABI): net ------------------------------------------------
    _op(
        "cuda",
        "sys/socket.h",
        "socket()/connect()",
        "net-connect",
        "opens a raw network socket and connects out via the BSD sockets API",
        "prefer a higher-level client with TLS verification",
        "medium",
        ("socket(", "connect("),
        (),
    ),
    _op(
        "cuda",
        "sys/socket.h",
        "bind()/listen()",
        "net-listen",
        "binds a socket to a local address and accepts inbound connections "
        "via the BSD sockets API",
        "bind only to a trusted interface",
        "medium",
        ("bind(", "listen("),
        (),
    ),
    _op(
        "cuda",
        "sys/socket.h",
        "send()/recv()/sendto()/recvfrom()/getaddrinfo()",
        "net-connect",
        "sends/receives data or resolves a hostname over a network socket",
        "prefer a higher-level client with TLS verification",
        "medium",
        ("send(", "recv(", "sendto(", "recvfrom(", "getaddrinfo("),
        (),
    ),
)
