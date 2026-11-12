#!/usr/bin/env python3
"""Upload staged GA4 parquet files to a Fabric OneLake lakehouse.

Usage:
  python scripts/upload.py --workspace YOUR_WORKSPACE_ID --lakehouse YOUR_LAKEHOUSE_ID
  python scripts/upload.py   # uses FABRIC_WORKSPACE_ID and FABRIC_LAKEHOUSE_ID from the environment / .env

Defaults come from those environment variables (see .env.example). Placeholder
values are rejected. Opens an interactive browser login via
InteractiveBrowserCredential. After each upload, checks that the remote size
matches the local file.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from azure.identity import InteractiveBrowserCredential
from azure.storage.filedatalake import DataLakeServiceClient

STAGING = Path.home() / "fabric-sync/ga4/staging/Files"
PLACEHOLDERS = {
    "YOUR_WORKSPACE_ID",
    "YOUR_LAKEHOUSE_ID",
    "<WORKSPACE_ID>",
    "<LAKEHOUSE_ID>",
    "00000000-0000-0000-0000-000000000000",
    "",
}


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


def lakehouse_path(lh: str) -> str:
    # GUIDs and already-qualified names keep their form; bare names get .Lakehouse
    if "-" in lh or lh.lower().endswith(".lakehouse"):
        return lh
    return lh + ".Lakehouse"


def main() -> int:
    _load_dotenv()
    default_workspace = os.environ.get("FABRIC_WORKSPACE_ID", "YOUR_WORKSPACE_ID")
    default_lakehouse = os.environ.get("FABRIC_LAKEHOUSE_ID", "YOUR_LAKEHOUSE_ID")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--workspace",
        default=default_workspace,
        help="Fabric workspace ID or name (default: FABRIC_WORKSPACE_ID)",
    )
    p.add_argument(
        "--lakehouse",
        default=default_lakehouse,
        help="Fabric lakehouse ID or name (default: FABRIC_LAKEHOUSE_ID)",
    )
    p.add_argument("--staging", default=str(STAGING), help="Local staging Files/ root")
    args = p.parse_args()

    if args.workspace in PLACEHOLDERS or args.lakehouse in PLACEHOLDERS:
        print(
            "Refusing to upload: set FABRIC_WORKSPACE_ID and FABRIC_LAKEHOUSE_ID "
            "or pass --workspace and --lakehouse.",
            file=sys.stderr,
        )
        return 2

    root = Path(args.staging)
    if not root.is_dir():
        print(f"staging folder not found: {root}", file=sys.stderr)
        return 2

    files = sorted(f for f in root.rglob("*") if f.is_file())
    if not files:
        print(f"no files under {root}", file=sys.stderr)
        return 2

    lh = lakehouse_path(args.lakehouse)
    fs = DataLakeServiceClient(
        "https://onelake.dfs.fabric.microsoft.com",
        credential=InteractiveBrowserCredential(),
    ).get_file_system_client(args.workspace)

    uploaded = 0
    mismatches: list[str] = []
    for local in files:
        remote = f"{lh}/Files/{local.relative_to(root).as_posix()}"
        size = local.stat().st_size
        with open(local, "rb") as data:
            fs.get_file_client(remote).upload_data(data, overwrite=True)
        props = fs.get_file_client(remote).get_file_properties()
        remote_size = props.size
        if remote_size != size:
            mismatches.append(f"{local.name} local={size:,} remote={remote_size:,}")
            print(
                f"SIZE MISMATCH {local.name} ({size:,} bytes) -> {remote} remote={remote_size:,}"
            )
        else:
            print(f"uploaded {local.name} ({size:,} bytes) -> {remote}")
        uploaded += 1

    print(f"done: {uploaded} files uploaded, {len(files)} local, {len(mismatches)} size mismatches")
    if mismatches:
        print("mismatches:", *mismatches, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
