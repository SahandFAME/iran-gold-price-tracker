#!/usr/bin/env python3
"""Package source/context, optional Git history, and a workbook; no secret reads."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from inspect_workbook import inspect


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    "START_HERE.md", "AGENTS.md", "CLAUDE.md", "README.md",
    "docs/PROJECT_HANDOFF.md", "docs/HISTORY_AND_DECISIONS.md",
    "docs/OPERATIONS.md", "docs/ACCESS_AND_RECOVERY.md",
    "docs/STATE_AND_LIMITATIONS.md", "docs/RESTORE.md",
    "docs/RESUME_PROMPT.md", "docs/BACKUP_CONTENTS.md",
]
PATTERNS = {
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    "telegram_token": re.compile(rb"\b[0-9]{7,12}:[A-Za-z0-9_-]{30,}\b"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "jwt": re.compile(rb"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def blocked(name: str) -> bool:
    return any(p in {".git", ".venv", "__pycache__", ".vercel"} for p in Path(name).parts) or (
        Path(name).name.startswith(".env") and Path(name).name != ".env.example"
    )


def scan(files: dict[str, bytes], label: str) -> list[dict[str, str]]:
    return [{"location": f"{label}:{name}", "rule": rule}
            for name, data in files.items() for rule, pattern in PATTERNS.items() if pattern.search(data)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--include-history", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "gold-agent-complete-handoff-2026-11-08.zip"
    if archive.exists():
        raise SystemExit(f"Refusing to overwrite existing archive: {archive}")
    baseline = git("rev-parse", "HEAD").decode().strip()
    tracked = git("ls-files", "-z").decode().split("\0")
    names = {n for n in tracked if n and not blocked(n)}
    names.update(DOCS)
    names.update({".env.example", "tools/inspect_workbook.py", "tools/build_handoff.py"})
    payload = {n: (ROOT / n).read_bytes() for n in sorted(names) if (ROOT / n).is_file()}
    findings = scan(payload, "working-tree")
    history_blobs_checked = 0
    if args.include_history:
        for commit in git("rev-list", "work").decode().splitlines():
            for record in git("ls-tree", "-r", "--long", commit).decode().splitlines():
                _, name = record.split("\t", 1)
                if blocked(name):
                    findings.append({"location": f"{commit}:{name}", "rule": "excluded-path-in-history"})
                elif name.endswith((".py", ".md", ".json", ".txt", ".yml", ".yaml")) or name in {".gitignore", ".env.example"}:
                    findings.extend(scan({name: git("show", f"{commit}:{name}")}, commit))
                    history_blobs_checked += 1
    if findings:
        raise SystemExit("Potential secrets/excluded files; inspect safely before export: " + json.dumps(findings))
    inspection = inspect(args.workbook.resolve())
    payload["backups/Geram18-tahlil-updated.xlsm"] = args.workbook.read_bytes()
    payload["verification/WORKBOOK_INSPECTION.json"] = (json.dumps(inspection, ensure_ascii=False, indent=2) + "\n").encode()
    test_python = ROOT / ".venv/bin/python"
    if not test_python.exists():
        raise SystemExit("Configure .venv/bin/python and test dependencies before packaging")
    tests = subprocess.run([str(test_python), "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True)
    if tests.returncode:
        raise SystemExit("Tests failed: " + tests.stdout + tests.stderr)
    payload["verification/TEST_RESULTS.txt"] = (tests.stdout + tests.stderr).encode()
    payload["verification/SECRET_PATTERN_SCAN.json"] = (json.dumps({
        "rules": sorted(PATTERNS), "history_blobs_checked": history_blobs_checked, "findings": [],
        "scope": "Common credential formats in selected source/history only; no env/credential reads; not a comprehensive secret audit."
    }, indent=2) + "\n").encode()
    payload["history/COMMITS.txt"] = git("log", "--reverse", "--format=%H %cI %s", "work")
    if args.include_history:
        with tempfile.TemporaryDirectory(prefix="gold-handoff-") as temp:
            bundle = Path(temp) / "project-work.bundle"
            subprocess.run(["git", "bundle", "create", str(bundle), "work"], cwd=ROOT, check=True, capture_output=True)
            payload["history/project-work.bundle"] = bundle.read_bytes()
    combined = ["# Complete portable project handoff\n\nPrepared 2026-11-08. Read all sections. Curated context, not a full conversation export. Source and Git history are separate payload files.\n"]
    for name in DOCS:
        combined.append(f"\n\n---\n\n## Source document: {name}\n\n" + payload[name].decode())
    payload["HANDOFF_COMPLETE.md"] = "".join(combined).encode()
    payload["RESTART_PROMPT.md"] = payload["docs/RESUME_PROMPT.md"]
    manifest = {
        "prepared_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "baseline_commit": baseline, "branch": git("branch", "--show-current").decode().strip(),
        "git_status": git("status", "--short").decode(), "history_included": args.include_history,
        "workbook_source": "Owner OneDrive raw download; dated snapshot, not live-file replacement",
        "files": {n: {"bytes": len(d), "sha256": hashlib.sha256(d).hexdigest()} for n, d in sorted(payload.items())},
    }
    payload["verification/PACKAGE_MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    payload["SHA256SUMS.txt"] = "".join(f"{hashlib.sha256(d).hexdigest()}  {n}\n" for n, d in sorted(payload.items())).encode()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name, data in sorted(payload.items()):
            package.writestr(name, data)
    with zipfile.ZipFile(archive) as package:
        if package.testzip():
            raise SystemExit("Archive ZIP integrity failed")
        for line in package.read("SHA256SUMS.txt").decode().splitlines():
            expected, name = line.split("  ", 1)
            if hashlib.sha256(package.read(name)).hexdigest() != expected:
                raise SystemExit(f"Archive checksum mismatch: {name}")
    for name in ("HANDOFF_COMPLETE.md", "RESTART_PROMPT.md"):
        (output / name).write_bytes(payload[name])
    print(json.dumps({
        "archive": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "payload_files": len(payload), "workbook_latest_date": inspection["last_date"],
        "workbook_latest_row": inspection["last_row"], "vba_sha256": inspection["vba_sha256"],
        "history_blobs_scanned": history_blobs_checked, "tests": tests.stdout.strip(),
        "standalone_context": str(output / "HANDOFF_COMPLETE.md")
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
