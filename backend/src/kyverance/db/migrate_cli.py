from __future__ import annotations

import argparse
import sys

from alembic import command
from alembic.config import Config


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="kyverance-migrate")
    parser.add_argument("action", choices=["upgrade", "downgrade", "current", "history"])
    parser.add_argument("revision", nargs="?", default="head")
    args = parser.parse_args(argv)

    cfg = Config("alembic.ini")
    if args.action == "upgrade":
        command.upgrade(cfg, args.revision)
    elif args.action == "downgrade":
        command.downgrade(cfg, args.revision)
    elif args.action == "current":
        command.current(cfg)
    elif args.action == "history":
        command.history(cfg)


if __name__ == "__main__":
    main(sys.argv[1:])
