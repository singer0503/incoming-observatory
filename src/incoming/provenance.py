"""Provenance for every published number — the 'result -> source' contract.

Carried over (in spirit) from a reproducibility pipeline: any figure this project
publishes must be traceable to (a) the exact data snapshot it came from and (b) the
exact code that produced it. Upstream APIs drift and ESA NEOCC's is explicitly
experimental, so we hash whatever data we read and record the code commit.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def git_commit() -> str:
    return _run(["git", "rev-parse", "HEAD"])


def git_dirty() -> bool:
    return bool(_run(["git", "status", "--porcelain"]))


@dataclass
class Provenance:
    schema_version: str = SCHEMA_VERSION
    created_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tool: str = "incoming-observatory"
    code: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)


def build_provenance(
    *,
    input_hashes: dict[str, str],
    output_hashes: dict[str, str] | None = None,
) -> Provenance:
    """input_hashes / output_hashes: {label -> 'sha256:...'} for each data file."""
    from incoming import __version__

    return Provenance(
        code={
            "version": __version__,
            "git_commit": git_commit(),
            "git_dirty": git_dirty(),
        },
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        inputs=input_hashes,
        outputs=output_hashes or {},
    )


def write(prov: Provenance, out: str | Path = "provenance.json") -> Path:
    out = Path(out)
    out.write_text(json.dumps(asdict(prov), indent=2, sort_keys=True))
    return out
