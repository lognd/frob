"""Sample module fixture for frob.lang python tests."""

MAX_RETRIES = 3


class GraphStore:
    """Holds parsed symbols in memory."""

    def load(self, path: str) -> bool:
        """Load a file from disk."""
        # read the bytes
        data = read_bytes(path)
        return bool(data)

    def _private_helper(self) -> None:
        pass


@decorator
def top_level(x: int, y: int = 2) -> int:
    """Add two numbers."""
    # sum them
    return x + y
