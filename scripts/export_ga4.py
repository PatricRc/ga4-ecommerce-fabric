#!/usr/bin/env python3
"""Export GA4 sample ecommerce events_* tables to local parquet (Storage Read API).

Usage:
  python scripts/export_ga4.py --project YOUR_GCP_PROJECT
  python scripts/export_ga4.py   # uses GCP_PROJECT or GOOGLE_CLOUD_PROJECT from the environment / .env

Reads every events_YYYYMMDD table in
bigquery-public-data.ga4_obfuscated_sample_ecommerce via list_rows().to_arrow()
(BigQuery Storage Read API; not a query job). Writes one snappy parquet per day
under ~/fabric-sync/ga4/staging/Files/raw/ga4/ingest_date=<today>/events/event_date=YYYYMMDD.parquet
and keeps the nested GA4 schema as-is.

A GCP billing/quota project is required. ADC credentials may pin a different
quota project; this script applies with_quota_project() so --project is honored
for both the client and the quota header.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import pyarrow.parquet as pq
from google.api_core.exceptions import Forbidden, GoogleAPICallError, Unauthenticated
from google.auth import default
from google.cloud import bigquery

DATASET = "bigquery-public-data.ga4_obfuscated_sample_ecommerce"
STAGING_ROOT = Path.home() / "fabric-sync/ga4/staging/Files/raw/ga4"
PLACEHOLDER_PROJECTS = {"YOUR_GCP_PROJECT", "your-gcp-project", ""}


def _load_dotenv() -> None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
        break


def _event_date(table_id: str) -> str | None:
    if not table_id.startswith("events_"):
        return None
    suffix = table_id[len("events_") :]
    if len(suffix) == 8 and suffix.isdigit():
        return suffix
    return None


def make_client(project: str) -> bigquery.Client:
    creds, _ = default()
    if hasattr(creds, "with_quota_project"):
        creds = creds.with_quota_project(project)
    return bigquery.Client(project=project, credentials=creds)


def export_table(client: bigquery.Client, table_id: str, dest: Path) -> int:
    table = client.get_table(f"{DATASET}.{table_id}")
    arrow = client.list_rows(table).to_arrow(create_bqstorage_client=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(arrow, dest, compression="snappy")
    return arrow.num_rows


def main() -> int:
    _load_dotenv()
    default_project = (
        os.environ.get("GCP_PROJECT")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or "YOUR_GCP_PROJECT"
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", default=default_project, help="GCP billing/quota project")
    p.add_argument("--ingest-date", default=dt.date.today().isoformat())
    args = p.parse_args()

    if args.project in PLACEHOLDER_PROJECTS:
        print(
            "Refusing to export: set GCP_PROJECT (or GOOGLE_CLOUD_PROJECT) "
            "or pass --project YOUR_GCP_PROJECT.",
            file=sys.stderr,
        )
        return 2

    out = STAGING_ROOT / f"ingest_date={args.ingest_date}" / "events"
    out.mkdir(parents=True, exist_ok=True)

    try:
        client = make_client(args.project)
        table_ids = sorted(
            t.table_id for t in client.list_tables(DATASET) if _event_date(t.table_id)
        )
    except Unauthenticated as e:
        print(
            "ADC auth failed. Run: gcloud auth application-default login\n"
            f"{type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 2
    except Forbidden as e:
        print(
            "Forbidden using quota project "
            f"{args.project}. The ADC account needs "
            "roles/serviceusage.serviceUsageConsumer on that project, "
            "or reauth with the account that owns it:\n"
            "  gcloud auth application-default login\n"
            f"{type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 2
    except GoogleAPICallError as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if not table_ids:
        print(f"no events_* tables in {DATASET}", file=sys.stderr)
        return 2

    print(f"quota_project={args.project}")
    print(f"dataset={DATASET}")
    print(f"days={len(table_ids)} first={table_ids[0]} last={table_ids[-1]}")
    print(f"out={out}")

    total_rows = 0
    total_bytes = 0
    failed: list[str] = []
    for tid in table_ids:
        dest = out / f"event_date={_event_date(tid)}.parquet"
        try:
            n = export_table(client, tid, dest)
            size = dest.stat().st_size
            total_rows += n
            total_bytes += size
            print(f"{tid} rows={n:,} bytes={size:,} -> {dest.name}")
        except Exception as e:
            failed.append(tid)
            print(f"FAIL {tid}: {type(e).__name__}: {e}", file=sys.stderr)

    print(
        f"TOTAL days={len(table_ids) - len(failed)}/{len(table_ids)} "
        f"rows={total_rows:,} bytes={total_bytes:,}"
    )
    if failed:
        print(f"FAILED {len(failed)}: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
