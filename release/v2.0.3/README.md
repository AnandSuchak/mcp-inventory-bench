# LASR-MCP Release v2.0.3 Package

This folder contains release documentation, verification manifests, and data provenance records for **LASR-MCP v2.0.3**.

## Directory Contents

- **[`MANIFEST.sha256`](MANIFEST.sha256):** Complete SHA-256 cryptographic manifest covering all manuscript files, distribution archives, and raw datasets.
- **[`RELEASE_NOTES.md`](RELEASE_NOTES.md):** Detailed release notes documenting v2.0.3 changes, token accounting resolution, and benchmark findings.
- **[`DATA_PROVENANCE.md`](DATA_PROVENANCE.md):** Detailed breakdown of Experimental Scopes 1, 2, and 3, including raw dataset origins, analysis scripts, and paper mappings.

## Canonical Distribution Archives

- **Manuscript PDF:** `zenodo_deposit_v2_0_3/LASR_MCP_v2.0.3_Manuscript.pdf` (SHA-256: `73e1b92e1308b57c5760f3b9ef0a2d82355daa1858227a263eca36c0fcece82d`)
- **Manuscript Source Bundle:** `zenodo_deposit_v2_0_3/lasr_v2_203_manuscript_bundle.zip` (SHA-256: `ae9599564b55a5e19004f32ded7c91fe2b46c480b12914b5343834bcf789044f`)
- **Raw Telemetry Archive:** `zenodo_deposit_v2_0_3/lasr_v2_203_raw_benchmark_telemetry.zip` (SHA-256: `9ee32f32dd332c06b978c4dc37482eebba95216a131961adbbb742b1d1c23b90`)

To verify all files against the manifest:
```powershell
python -c "
import hashlib
from pathlib import Path
manifest = Path('release/v2.0.3/MANIFEST.sha256')
with open(manifest) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'): continue
        h, p = line.split(maxsplit=1)
        path = Path(p.strip())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == h
        print(f'VERIFIED: {path.name}')
"
```
