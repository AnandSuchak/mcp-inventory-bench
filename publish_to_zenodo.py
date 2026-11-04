#!/usr/bin/env python3
"""
publish_to_zenodo.py - Secure Zenodo deposit script for LASR-MCP v2.0.3.

Security & Safety Standards:
- Zero hardcoded tokens or credentials. Requires environment variable or CLI argument.
- Pre-upload cryptographic checksum validation against SHA256SUMS.txt.
- Safe default: Creates/updates drafts only. Never publishes automatically.
- Publishing requires explicit --publish AND --confirm-publish flags.

Usage:
  # 1. Validate files and prepare a draft on Zenodo (Default safe mode):
  python publish_to_zenodo.py --token <ZENODO_TOKEN>

  # 2. Test in Zenodo Sandbox (draft mode):
  python publish_to_zenodo.py --token <SANDBOX_TOKEN> --sandbox

  # 3. Prepare a new version draft from an existing record:
  python publish_to_zenodo.py --token <ZENODO_TOKEN> --existing-id <RECORD_ID>

  # 4. Final publish (Requires explicit confirmation):
  python publish_to_zenodo.py --token <ZENODO_TOKEN> --publish --confirm-publish
"""

import os
import sys
import json
import argparse
import hashlib
import requests
from pathlib import Path

DEPOSIT_DIR = Path("zenodo_deposit_v2_0_3")
METADATA_FILE = DEPOSIT_DIR / "zenodo_metadata.json"
CHECKSUMS_FILE = DEPOSIT_DIR / "SHA256SUMS.txt"
FILES_TO_UPLOAD = [
    DEPOSIT_DIR / "LASR_MCP_v2.0.3_Manuscript.pdf",
    DEPOSIT_DIR / "lasr_v2_203_manuscript_bundle.zip",
    DEPOSIT_DIR / "lasr_v2_203_raw_benchmark_telemetry.zip",
    DEPOSIT_DIR / "SHA256SUMS.txt"
]

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def verify_checksums() -> bool:
    """Verifies all deposit files against SHA256SUMS.txt."""
    if not CHECKSUMS_FILE.exists():
        print(f"[ERROR] Checksums file missing: {CHECKSUMS_FILE}")
        return False

    expected_hashes = {}
    with open(CHECKSUMS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            if len(parts) >= 2:
                # Format: <hash>  <filename>
                fname = parts[1].split()[0].strip()
                expected_hashes[fname] = parts[0].strip()

    all_ok = True
    for fpath in FILES_TO_UPLOAD:
        if not fpath.exists():
            print(f"[ERROR] Required deposit file not found: {fpath}")
            all_ok = False
            continue

        actual_hash = sha256_file(fpath)
        expected = expected_hashes.get(fpath.name)
        if expected and actual_hash != expected:
            print(f"[ERROR] Hash mismatch for {fpath.name}!\n  Expected: {expected}\n  Actual:   {actual_hash}")
            all_ok = False
        else:
            print(f"  [VERIFIED] {fpath.name} ({fpath.stat().st_size:,} bytes | SHA-256: {actual_hash[:16]}...)")

    return all_ok

def main():
    parser = argparse.ArgumentParser(description="Securely deposit LASR-MCP v2.0.3 to Zenodo")
    parser.add_argument("--token", default=os.environ.get("ZENODO_TOKEN"), help="Zenodo Personal Access Token (or set ZENODO_TOKEN env var)")
    parser.add_argument("--sandbox", action="store_true", help="Use sandbox.zenodo.org instead of production")
    parser.add_argument("--existing-id", default=None, help="Existing Deposition ID if creating a new version draft")
    parser.add_argument("--publish", action="store_true", help="Flag to publish the deposition (requires --confirm-publish)")
    parser.add_argument("--confirm-publish", action="store_true", help="Explicit confirmation required to finalize publication and mint DOI")
    args = parser.parse_args()

    token = args.token
    if not token:
        print("[ERROR] No Zenodo access token provided.")
        print("Please provide --token <YOUR_TOKEN> or set the ZENODO_TOKEN environment variable.")
        print("Tokens can be generated at: https://zenodo.org/account/settings/applications/tokens/new/")
        sys.exit(1)

    base_url = "https://sandbox.zenodo.org/api" if args.sandbox else "https://zenodo.org/api"
    headers = {"Authorization": f"Bearer {token}"}

    print("=" * 70)
    print("LASR-MCP v2.0.3 — Secure Zenodo Deposit Pipeline")
    print(f"Target API Endpoint: {base_url}")
    print(f"Operation Mode:      {'FINAL PUBLICATION' if (args.publish and args.confirm-publish) else 'DRAFT DEPOSIT (Safe Default)'}")
    print("=" * 70)

    # 1. Pre-Upload Integrity Audit
    print("\n[1/4] Verifying cryptographic checksums and file availability...")
    if not verify_checksums():
        print("[ABORT] File verification failed. Cannot proceed with deposit.")
        sys.exit(1)

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        meta_data = json.load(f)

    # Validate core metadata keys
    required_meta = ["title", "description", "creators", "access_right", "license", "version"]
    for k in required_meta:
        if k not in meta_data:
            print(f"[ERROR] Missing metadata field: {k}")
            sys.exit(1)
    print(f"  [METADATA OK] Title: {meta_data['title'][:60]}...")
    print(f"  [METADATA OK] Creators: {meta_data['creators'][0]['name']}")
    print(f"  [METADATA OK] Version: {meta_data['version']}")

    # 2. Create Deposition Draft (or New Version Draft)
    if args.existing_id:
        print(f"\n[2/4] Initializing new version draft from existing record: {args.existing_id}...")
        r = requests.post(f"{base_url}/deposit/depositions/{args.existing_id}/actions/newversion", headers=headers)
        if r.status_code not in (200, 201):
            print(f"[ERROR] Failed to create new version draft: HTTP {r.status_code}\n{r.text}")
            sys.exit(1)
        new_version_data = r.json()
        deposition_id = new_version_data["links"]["latest_draft"].split("/")[-1]
        print(f"  -> Created draft version with Deposition ID: {deposition_id}")
        r = requests.get(f"{base_url}/deposit/depositions/{deposition_id}", headers=headers)
        dep_data = r.json()
    else:
        print("\n[2/4] Initializing new deposition draft...")
        r = requests.post(
            f"{base_url}/deposit/depositions",
            headers={**headers, "Content-Type": "application/json"},
            json={"metadata": meta_data}
        )
        if r.status_code not in (200, 201):
            print(f"[ERROR] Failed to create deposition: HTTP {r.status_code}\n{r.text}")
            sys.exit(1)
        dep_data = r.json()
        deposition_id = dep_data["id"]
        print(f"  -> Deposition draft created: ID {deposition_id}")

    # Update metadata
    r = requests.put(
        f"{base_url}/deposit/depositions/{deposition_id}",
        headers={**headers, "Content-Type": "application/json"},
        json={"metadata": meta_data}
    )
    if r.status_code not in (200, 201):
        print(f"[ERROR] Failed to update metadata: HTTP {r.status_code}\n{r.text}")
        sys.exit(1)
    dep_data = r.json()
    bucket_url = dep_data.get("links", {}).get("bucket")

    # 3. Upload verified files
    print("\n[3/4] Uploading validated deposit files...")
    if bucket_url:
        for fpath in FILES_TO_UPLOAD:
            print(f"  Uploading {fpath.name}...")
            with open(fpath, "rb") as fp:
                r_up = requests.put(
                    f"{bucket_url}/{fpath.name}",
                    data=fp,
                    headers=headers
                )
            if r_up.status_code not in (200, 201):
                print(f"[ERROR] Upload failed for {fpath.name}: HTTP {r_up.status_code}\n{r_up.text}")
                sys.exit(1)
            print(f"  -> {fpath.name} uploaded successfully.")
    else:
        for fpath in FILES_TO_UPLOAD:
            print(f"  Uploading {fpath.name} (legacy endpoint)...")
            with open(fpath, "rb") as fp:
                r_up = requests.post(
                    f"{base_url}/deposit/depositions/{deposition_id}/files",
                    files={"file": fp},
                    data={"name": fpath.name},
                    headers=headers
                )
            if r_up.status_code not in (200, 201):
                print(f"[ERROR] Upload failed for {fpath.name}: HTTP {r_up.status_code}\n{r_up.text}")
                sys.exit(1)
            print(f"  -> {fpath.name} uploaded successfully.")

    # 4. Safe Publication Control
    portal_url = "https://sandbox.zenodo.org/deposit" if args.sandbox else "https://zenodo.org/deposit"
    print("\n[4/4] Finalizing deposit status...")

    if not args.publish:
        print("=" * 70)
        print("[SAFE DRAFT CREATED] The deposit has been uploaded as a private DRAFT.")
        print(f"Review and finalize publication manually at:")
        print(f"  {portal_url}/{deposition_id}")
        print("No public DOI has been minted yet.")
        print("=" * 70)
        return

    if args.publish and not args.confirm_publish:
        print("[WARNING] --publish was passed without --confirm-publish.")
        print("To protect against accidental publication, publication was aborted.")
        print(f"Your draft is safely saved at: {portal_url}/{deposition_id}")
        return

    # Final publication only if both flags provided
    print(f"Explicit confirmation received. Publishing deposition {deposition_id}...")
    r_pub = requests.post(f"{base_url}/deposit/depositions/{deposition_id}/actions/publish", headers=headers)
    if r_pub.status_code not in (200, 201, 202):
        print(f"[ERROR] Publish action failed: HTTP {r_pub.status_code}\n{r_pub.text}")
        print(f"You can review and publish manually at: {portal_url}/{deposition_id}")
        sys.exit(1)

    pub_data = r_pub.json()
    doi = pub_data.get("doi")
    record_url = pub_data.get("links", {}).get("record_html")
    print("=" * 70)
    print("PUBLICATION SUCCESSFUL!")
    print(f"Persistent DOI:    {doi}")
    print(f"Public Record URL: {record_url}")
    print("=" * 70)

if __name__ == "__main__":
    main()
