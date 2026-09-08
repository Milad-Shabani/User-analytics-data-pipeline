"""Command-line entry point.

python -m analytics_pipeline.cli run
python -m analytics_pipeline.cli run --config config/config.yaml --log-level DEBUG
"""

from __future__ import annotations

import argparse
import sys

from .logging_config import setup_logging
from .pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analytics-pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run the full ETL pipeline once.")
    run_parser.add_argument("--config", default="config/config.yaml")
    run_parser.add_argument("--log-level", default="INFO")
    run_parser.add_argument(
        "--no-fail-on-quality",
        action="store_true",
        help="Log quality failures instead of raising (useful for exploratory runs).",
    )

    args = parser.parse_args(argv)
    setup_logging(args.log_level)

    if args.command == "run":
        result = run_pipeline(
            config_path=args.config,
            fail_on_quality=not args.no_fail_on_quality,
        )
        print(
            f"\nDone: {result.profiles_loaded} profiles, "
            f"{result.events_extracted} events -> {result.fact_rows} fact rows "
            f"in {result.duration_seconds:.2f}s "
            f"(quality {'PASSED' if result.quality.passed else 'FAILED'})"
        )
        return 0 if result.quality.passed else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
