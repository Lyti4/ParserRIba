"""Run guided site onboarding for launcher integration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.site_onboarding import resume_site_onboarding, run_site_onboarding


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run guided site onboarding")
    parser.add_argument("--site-url", default="")
    parser.add_argument("--intent", default="fish_catalog")
    parser.add_argument("--require-operator-confirmation", action="store_true")
    parser.add_argument("--resume-session-id", default="")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    if args.resume_session_id:
        result = resume_site_onboarding(session_id=args.resume_session_id, root_dir=ROOT_DIR)
    else:
        result = run_site_onboarding(
            site_url=args.site_url,
            intent=args.intent,
            root_dir=ROOT_DIR,
            require_operator_confirmation=args.require_operator_confirmation,
        )
    sys.stdout.write(result.model_dump_json(indent=2))
