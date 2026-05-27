"""incoming — command-line entry point."""
from __future__ import annotations

import argparse
from pathlib import Path

from incoming import alert as alert_mod
from incoming import recompute as recompute_mod
from incoming import triage as triage_mod
from incoming import warning_time


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="incoming", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ledger = sub.add_parser("ledger", help="build the warning-time ledger (offline)")
    p_ledger.add_argument("--plot", action="store_true", help="also write the warning-time chart")
    p_ledger.add_argument("--out", type=Path, default=None, help="output directory")

    p_rc = sub.add_parser(
        "recompute", help="independently recompute warning time from raw MPC observations"
    )
    p_rc.add_argument(
        "--live", action="store_true", help="fetch missing objects from MPC and update the snapshot"
    )
    p_rc.add_argument("--out", type=Path, default=None, help="output directory")

    p_tri = sub.add_parser(
        "triage", help="flag hyperbolic / interstellar objects by eccentricity (SBDB)"
    )
    p_tri.add_argument("designations", nargs="*", help="objects to classify (default: 1I 2I 3I)")
    p_tri.add_argument("--live", action="store_true", help="fetch from JPL SBDB, update snapshot")

    p_al = sub.add_parser(
        "alert", help="open impact-risk alerts aggregated from JPL CNEOS Sentry"
    )
    p_al.add_argument("--live", action="store_true", help="fetch the live Sentry feed")
    p_al.add_argument("--limit", type=int, default=15, help="rows to print")

    args = ap.parse_args(argv)

    if args.cmd == "ledger":
        kwargs = {"make_plot": args.plot}
        if args.out is not None:
            kwargs["out_dir"] = args.out
        warning_time.build_ledger(**kwargs)
        return 0
    if args.cmd == "recompute":
        recompute_mod.recompute(live=args.live, out_dir=args.out)
        return 0
    if args.cmd == "triage":
        triage_mod.run(args.designations or None, live=args.live)
        return 0
    if args.cmd == "alert":
        alert_mod.build_alerts(live=args.live, limit=args.limit)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
