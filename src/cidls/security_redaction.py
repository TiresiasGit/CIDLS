"""Redaction helpers for CIDLS reports and public-facing artifacts."""

from pathlib import Path
import re


TOKEN_PATTERNS = [
    (re.compile(r"AI" r"za[0-9A-Za-z_\-]{20,}"), "<REDACTED_GOOGLE_API_KEY>"),
    (re.compile(r"QU" r"FFLU[A-Za-z0-9_\-\\u003d%]{20,}"), "<REDACTED_YOUTUBE_TOKEN>"),
    (re.compile(r"\bsk-(?:ant|live|test|proj)?[A-Za-z0-9_\-]{6,}\b"), "<REDACTED_SECRET_KEY>"),
    (re.compile(r"\bwhsec_[A-Za-z0-9_\-]{8,}\b"), "<REDACTED_WEBHOOK_SECRET>"),
    (re.compile(r"S-1-5-" r"21(?:-\d+){3,}"), "<WINDOWS_SID>"),
]


def redact_sensitive_text(text: str, repo_root: Path | str = "", codex_home: Path | str = "") -> str:
    """Generalize local paths, account names, SIDs, and token-like values."""
    redacted = str(text)

    if codex_home:
        redacted = _replace_path(redacted, Path(codex_home), "%CODEX_HOME%")
        user_home = Path(codex_home).parent
        redacted = _replace_path(redacted, user_home, "%USERPROFILE%")

    if repo_root:
        redacted = _replace_path(redacted, Path(repo_root), "<CIDLS_REPO>")

    redacted = re.sub(
        r"C:(?:\\\\)+Users(?:\\\\)+[^\\\\\s\"']+",
        r"%USERPROFILE%",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:\\\\Users\\\\[^\\\\\s\"']+",
        r"%USERPROFILE%",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:\\Users\\[^\\\s\"']+",
        r"%USERPROFILE%",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:/Users/[^/\s\"']+",
        r"%USERPROFILE%",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:(?:\\\\)+Github(?:\\\\)+CIDLS",
        r"<CIDLS_REPO>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:\\\\Github\\\\CIDLS",
        r"<CIDLS_REPO>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:\\Github\\CIDLS",
        r"<CIDLS_REPO>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:/Github/CIDLS",
        r"<CIDLS_REPO>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"D:(?:\\\\)+CIDLS",
        r"<CIDLS_REPO>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"D:\\\\CIDLS",
        r"<CIDLS_REPO>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"D:\\CIDLS",
        r"<CIDLS_REPO>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"D:" r"/CIDLS",
        r"<CIDLS_REPO>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:(?:\\\\)+Github(?:\\\\)+[^\\\\\s\"']+",
        r"<LOCAL_DEV_ROOT>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:\\\\Github\\\\[^\\\\\s\"']+",
        r"<LOCAL_DEV_ROOT>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:\\Github\\[^\\\s\"']+",
        r"<LOCAL_DEV_ROOT>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"C:/Github/[^/\s\"']+",
        r"<LOCAL_DEV_ROOT>",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"\b[A-Z]:\\\\[^\\\s\"'<>|]+(?:\\\\[^\\\s\"'<>|]+)*",
        r"<LOCAL_PATH>",
        redacted,
    )
    redacted = re.sub(
        r"\b[A-Z]:\\[^\\\s\"'<>|]+(?:\\[^\\\s\"'<>|]+)*",
        r"<LOCAL_PATH>",
        redacted,
    )
    redacted = re.sub(
        r"\b[A-Z]:/[^/\s\"'<>|]+(?:/[^/\s\"'<>|]+)*",
        r"<LOCAL_PATH>",
        redacted,
    )
    redacted = re.sub(
        r"\b[A-Za-z0-9_-]+\\\\[A-Za-z0-9_.-]+(?=:\([A-Z,]+\))",
        "<WINDOWS_ACCOUNT>",
        redacted,
    )
    redacted = re.sub(
        r"\b[A-Za-z0-9_-]+\\[A-Za-z0-9_.-]+(?=:\([A-Z,]+\))",
        "<WINDOWS_ACCOUNT>",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b((?:RunAs\s+User|Username|RunAs\s+ユーザー|ユーザー名):\s+)[A-Za-z0-9_-]+\\[A-Za-z0-9_.-]+",
        r"\1<WINDOWS_ACCOUNT>",
        redacted,
    )

    for pattern, replacement in TOKEN_PATTERNS:
        redacted = pattern.sub(replacement, redacted)

    return redacted


def redact_mapping(value, repo_root: Path | str = "", codex_home: Path | str = ""):
    """Recursively redact strings in JSON-like structures."""
    if isinstance(value, str):
        return redact_sensitive_text(value, repo_root=repo_root, codex_home=codex_home)
    if isinstance(value, list):
        return [redact_mapping(item, repo_root=repo_root, codex_home=codex_home) for item in value]
    if isinstance(value, dict):
        return {
            key: redact_mapping(item, repo_root=repo_root, codex_home=codex_home)
            for key, item in value.items()
        }
    return value


def _replace_path(text: str, path: Path, replacement: str) -> str:
    if not path:
        return text
    variants = {
        str(path),
        str(path).replace("\\", "/"),
        str(path).replace("\\", "\\\\"),
    }
    redacted = text
    for variant in variants:
        if variant:
            redacted = redacted.replace(variant, replacement)
    return redacted
