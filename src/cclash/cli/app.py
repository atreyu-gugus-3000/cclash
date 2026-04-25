"""Minimal CLI entrypoint for cclash."""

from __future__ import annotations

from cclash import __version__


def main() -> None:
    print(f"cclash {__version__}")
    print("Compile once. Reconfigure three times. Highest output wins.")
    print("MVP engine coming next.")


if __name__ == "__main__":
    main()
