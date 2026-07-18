"""CLI entrypoints for research scheduler and worker."""

from __future__ import annotations

import logging
import sys

from kyverance.config import refresh_settings

# Ensure related ORM mappers are registered before claim/query paths run.
import kyverance.agents.models  # noqa: F401
import kyverance.audit.models  # noqa: F401
import kyverance.identity.models  # noqa: F401
import kyverance.market_data.models  # noqa: F401
import kyverance.portfolios.models  # noqa: F401
import kyverance.research.models  # noqa: F401
import kyverance.simulation.models  # noqa: F401
from kyverance.research.jobs import scheduler as research_scheduler
from kyverance.research.jobs import worker as research_worker

logger = logging.getLogger(__name__)


def scheduler_main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    refresh_settings()
    _ = argv
    result = research_scheduler.schedule_once()
    logger.info("research.scheduler.result %s", result)


def worker_main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    refresh_settings()
    args = list(argv if argv is not None else sys.argv[1:])
    if "--once" not in args:
        args = ["--once", *args]
    research_worker.main(args)


if __name__ == "__main__":
    worker_main(sys.argv[1:])
