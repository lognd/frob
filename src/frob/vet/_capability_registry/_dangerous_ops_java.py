"""`_JAVA_OPERATIONS`: the java slice of `DANGEROUS_OPERATIONS` (T-3492,
mirrors `_dangerous_ops_bash_csharp.py`'s T-2906 precedent -- java gets
its own file rather than folding into `_dangerous_ops_other.py`, the
same LARGE001-threshold reasoning that split bash/csharp out).

Java is the same JDK/JVM runtime kotlin already patterns in
`_dangerous_ops_other.py` (`java.net`/`java.lang.Runtime`/
`ProcessBuilder`/`System.getenv` are plain Java APIs, not kotlin
syntax), so the highest-value idioms below intentionally mirror
kotlin's own needles -- these are the same library calls, just matched
against `.java` source text instead of `.kt`. `client_storage` has no
plain-Java equivalent (kotlin's own client_storage patterns are
Android-specific: `SharedPreferences`/`Room`, neither a plain-JVM API),
so java gets an excuse there instead of a pattern -- see `_matrix.py`'s
`_new_adapter_matrix_excuses`/`_NEW_ADAPTER_SUBSTANTIVE_EXCUSES` for
every other (kind, "java") cell."""

from __future__ import annotations

from frob.vet._capability_registry._schemas import _DangerousOperation, _op

_JAVA_OPERATIONS: tuple[_DangerousOperation, ...] = (
    # -- java: net -----------------------------------------------------------
    _op(
        "java",
        "java.net",
        "HttpURLConnection",
        "net-connect",
        "the JDK's built-in HTTP client, opening an outbound connection",
        "prefer java.net.http.HttpClient (Java 11+) with explicit TLS verification",
        "medium",
        ("HttpURLConnection",),
        (),
    ),
    _op(
        "java",
        "java.net.http",
        "HttpClient",
        "net-connect",
        "the JDK 11+ HTTP client, opening an outbound connection",
        "pin a timeout; validate SSRF-sensitive URLs",
        "medium",
        ("HttpClient.newHttpClient(", "HttpClient.newBuilder("),
        (),
    ),
    _op(
        "java",
        "java.net",
        "ServerSocket",
        "net-listen",
        "binds a socket to a local address and accepts inbound connections",
        "bind only to a trusted interface",
        "medium",
        ("ServerSocket(",),
        (),
    ),
    # -- java: env -------------------------------------------------------------
    # T-3492 (mirrors kotlin's own T-0771 reasoning exactly -- same JDK,
    # same API): System.getenv() returns an unmodifiable view; the JVM has
    # no supported process-environment MUTATION API of its own, so java's
    # env-write is excused in _matrix.py, not patterned with a misleading
    # needle.
    _op(
        "java",
        "java.lang",
        "System.getenv",
        "env-read",
        "reads process environment variables, which may carry secrets",
        "scope secret access through a config loader with an explicit allowlist",
        "low",
        ("System.getenv(",),
        (),
    ),
    # -- java: exec --------------------------------------------------------
    _op(
        "java",
        "java.lang",
        "Runtime.getRuntime().exec",
        "exec",
        "spawns an external process with the current process's privileges",
        "validate the program/args come from a trusted, fixed set",
        "high",
        ("Runtime.getRuntime().exec(",),
        ("CWE-78",),
    ),
    _op(
        "java",
        "java.lang",
        "ProcessBuilder",
        "exec",
        "spawns an external process with the current process's privileges",
        "validate the program/args come from a trusted, fixed set",
        "high",
        ("ProcessBuilder(",),
        ("CWE-78",),
    ),
    # -- java: deserialize ---------------------------------------------------
    # T-3492: java.io.ObjectInputStream deserializing an untrusted stream
    # is the JDK's own canonical deserialization-RCE gadget chain surface
    # (CVE-2015-4852 and the wider "Java deserialization" CVE family) --
    # unlike bash/csharp (both excused for deserialize, no per-language
    # survey done), this is a well-known, high-value plain-Java idiom
    # worth a real pattern rather than an excuse.
    _op(
        "java",
        "java.io",
        "ObjectInputStream.readObject",
        "deserialize",
        "deserializes an object graph from a byte stream; an untrusted "
        "stream can trigger arbitrary gadget-chain code execution during "
        "readObject (the JDK's own long-running deserialization-RCE class)",
        "never deserialize untrusted data with ObjectInputStream; use a "
        "safe, schema-validated format (JSON/protobuf) or an allowlist filter",
        "critical",
        ("ObjectInputStream", "readObject("),
        ("CWE-502",),
    ),
)
