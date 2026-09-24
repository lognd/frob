"""Plain Python CLI fixture with no web framework and no security surface
(T-5325 ADVISORY negative control)."""


def main() -> None:
    """Do nothing -- this fixture exists to have no header evidence at all."""


if __name__ == "__main__":
    main()
