#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = REPO_ROOT / "logs" / "distribution_security_audit.json"

FORBIDDEN_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
}
FORBIDDEN_SUFFIXES = {
    ".pem",
    ".p12",
    ".pfx",
}
SECRET_PATTERNS = {
    "stripe_secret_key": re.compile(r"\bsk_(live|test)_[A-Za-z0-9]{12,}\b"),
    "stripe_webhook_secret": re.compile(r"\bwhsec_[A-Za-z0-9]{12,}\b"),
    "private_key_block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "generic_secret_assignment": re.compile(
        r"(?i)\b(secret|api[_-]?key|webhook[_-]?secret|private[_-]?key)\b\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"
    ),
}
PUBLIC_ENV_PATTERN = re.compile(
    r"(?i)\bNEXT_PUBLIC_[A-Z0-9_]*(SECRET|API_KEY|WEBHOOK|PRIVATE)[A-Z0-9_]*\b"
)
PLACEHOLDER_PATTERN = re.compile(r"(?i)\b(TODO|TBD|placeholder)\b|項目1|詳細項目1|証跡1")
TEXT_SUFFIXES = {
    ".bat",
    ".cmd",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".pytest_tmp",
    ".venv",
    "__pycache__",
    "node_modules",
    "reports",
    "logs",
}


@dataclass
class Finding:
    code: str
    path: str
    detail: str

    def to_dict(self):
        return {
            "code": self.code,
            "path": self.path,
            "detail": self.detail,
        }


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def iter_files(roots):
    for root in roots:
        path = Path(root)
        if not path.exists():
            yield Finding("PATH_MISSING", str(path), "scan target does not exist")
            continue
        if path.is_file():
            yield path
            continue
        for child in path.rglob("*"):
            if child.is_dir():
                continue
            relative_parts = child.relative_to(path).parts
            if any(part in EXCLUDED_DIRS for part in relative_parts):
                continue
            yield child


def read_text(path):
    for encoding in ("utf-8", "utf-8-sig", "cp932"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return None


def is_private_key_filename(path):
    name = path.name.lower()
    if name in FORBIDDEN_FILENAMES:
        return True
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return "public" not in name
    if name.endswith(".key"):
        return "public" not in name
    return False


def audit_bat_newlines(path, findings):
    data = path.read_bytes()
    if b"\r\n" not in data and data:
        findings.append(Finding("BAT_CRLF", str(path), ".bat/.cmd file is not CRLF encoded"))
    if b"\x00" in data:
        findings.append(Finding("BAT_BINARY", str(path), ".bat/.cmd file contains NUL bytes"))


def audit_zip(path, findings):
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                lowered = Path(name).name.lower()
                suffix = Path(name).suffix.lower()
                if lowered in FORBIDDEN_FILENAMES or suffix in FORBIDDEN_SUFFIXES:
                    findings.append(Finding("ZIP_SECRET_FILE", f"{path}!{name}", "forbidden secret-like file in distribution archive"))
                if lowered.endswith(".key") and "public" not in lowered:
                    findings.append(Finding("ZIP_PRIVATE_KEY", f"{path}!{name}", "private key-like file in distribution archive"))
    except zipfile.BadZipFile:
        findings.append(Finding("ZIP_INVALID", str(path), "zip file cannot be opened"))


def audit_text(path, text, findings):
    if PUBLIC_ENV_PATTERN.search(text):
        findings.append(Finding("NEXT_PUBLIC_SECRET_NAME", str(path), "public environment variable exposes a secret-like name"))
    for code, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            findings.append(Finding(code.upper(), str(path), "secret-like token or assignment detected"))
    if path.suffix.lower() in {".md", ".html", ".txt"} and PLACEHOLDER_PATTERN.search(text):
        findings.append(Finding("SPEC_PLACEHOLDER", str(path), "release-facing specification placeholder remains"))
    if "public" in [part.lower() for part in path.parts]:
        sensitive_words = ("secret", "private key", "webhook secret", "api key", "customer pii")
        if any(word in text.lower() for word in sensitive_words):
            findings.append(Finding("PUBLIC_SENSITIVE_TEXT", str(path), "public path contains sensitive distribution language"))


def audit_paths(roots):
    findings = []
    scanned_files = 0
    for item in iter_files(roots):
        if isinstance(item, Finding):
            findings.append(item)
            continue
        path = item
        scanned_files += 1
        if is_private_key_filename(path):
            findings.append(Finding("SECRET_FILENAME", str(path), "forbidden secret-like filename"))
        if path.suffix.lower() == ".zip":
            audit_zip(path, findings)
        if path.suffix.lower() in {".bat", ".cmd"}:
            audit_bat_newlines(path, findings)
        if path.suffix.lower() in TEXT_SUFFIXES or path.name.lower() in FORBIDDEN_FILENAMES:
            text = read_text(path)
            if text is not None:
                audit_text(path, text, findings)
    return scanned_files, findings


def build_report(roots):
    scanned_files, findings = audit_paths(roots)
    return {
        "ok": not findings,
        "generated_at_utc": utc_now_iso(),
        "roots": [str(Path(root)) for root in roots],
        "scanned_files": scanned_files,
        "finding_count": len(findings),
        "findings": [finding.to_dict() for finding in findings],
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Audit CIDLS distribution security boundaries.")
    parser.add_argument("paths", nargs="*", help="Files or directories to scan.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="JSON report output path.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    roots = args.paths if args.paths else [REPO_ROOT]
    report = build_report(roots)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
