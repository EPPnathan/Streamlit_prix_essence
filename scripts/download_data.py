from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.config import PROCESSED_DIR, YEARS
from utils.io import download_year, parse_year, save_year
from utils.prep import clean_prices, clean_stations


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Download, parse and clean the yearly fuel price archives.")
    parser.add_argument("years", nargs="*", type=int, default=YEARS)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    report_path = PROCESSED_DIR / "quality_report.json"
    reports = json.loads(report_path.read_text()) if report_path.exists() else {}

    for year in args.years:
        if (PROCESSED_DIR / f"prix_{year}.parquet").exists() and not args.force:
            print(f"[{year}] already processed, skipped (use --force to redo)")
            continue
        t0 = time.time()
        print(f"[{year}] downloading...", flush=True)
        zip_path = download_year(year, force=args.force)
        print(f"[{year}] parsing XML...", flush=True)
        df_st, df_px = parse_year(zip_path)
        df_st = clean_stations(df_st)
        df_px, report = clean_prices(df_px)
        report["stations"] = len(df_st)
        save_year(year, df_st, df_px)
        reports[str(year)] = report
        report_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False))
        print(f"[{year}] done: {len(df_st):,} stations, {len(df_px):,} prices "
              f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
