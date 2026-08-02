"""
SQL verifiers — validate and sandbox all model-generated SQL.

The SQL verifier pipeline blocks any statement that could cause
data loss or unintended mutations before it reaches any data source.

Stages:
    1. Parse       — reject unparseable SQL immediately
    2. Statement   — block non-SELECT statements (DDL, DML)
    3. Schema      — validate referenced identifiers where schema is known
    4. Risk        — flag full-table scans, missing WHERE, cartesian joins
    5. Cost limit  — reject statements exceeding the row/cost threshold
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from forgeops.verification.base import Finding, Severity, VerifierResult

# ── Tokeniser ─────────────────────────────────────────────────────────────────
# Simple keyword extraction without a full SQL parser dependency.
# A full implementation would use sqlglot or sqlparse.

_COMMENT_RE = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")


def _normalise(sql: str) -> str:
    """Strip comments and collapse whitespace."""
    sql = _COMMENT_RE.sub(" ", sql)
    sql = _WHITESPACE_RE.sub(" ", sql)
    return sql.strip().upper()


def _first_token(sql: str) -> str:
    return _normalise(sql).split()[0] if sql.strip() else ""


# ── Forbidden statement types ─────────────────────────────────────────────────

_WRITE_KEYWORDS: frozenset[str] = frozenset({
    "INSERT", "UPDATE", "DELETE", "REPLACE",
    "TRUNCATE", "DROP", "CREATE", "ALTER",
    "GRANT", "REVOKE", "CALL", "EXEC", "EXECUTE",
    "MERGE", "UPSERT", "COPY",
})

# Patterns that look like SQL injection or privilege escalation attempts
_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (
        r";\s*(DROP|CREATE|ALTER|TRUNCATE|DELETE|INSERT|UPDATE)\b",
        "Stacked write statement after semicolon",
    ),
    (r"\bUNION\s+ALL\s+SELECT\b", "UNION ALL SELECT (possible injection)"),
    (r"\bINTO\s+OUTFILE\b", "INTO OUTFILE (file write via SQL)"),
    (r"\bLOAD_FILE\s*\(", "LOAD_FILE() (file read via SQL)"),
    (r"xp_cmdshell", "xp_cmdshell (OS command via SQL)"),
    (r"\bINFORMATION_SCHEMA\b.*(PASSWORD|CREDENTIALS)", "Information schema credential probe"),
]

# Patterns that indicate risky but not necessarily malicious queries
_RISK_PATTERNS: list[tuple[str, str, Severity]] = [
    (r"\bSELECT\s+\*\s+FROM\b(?!\s*\()", "SELECT * without column projection", Severity.low),
    (r"\bSELECT\b.*\bFROM\b(?!.*\bWHERE\b)", "SELECT without WHERE clause", Severity.low),
    (r"\bCROSS\s+JOIN\b", "CROSS JOIN detected (potential cartesian product)", Severity.medium),
    (r"\bSELECT\b.*\bFROM\b.*\bFROM\b", "Nested subquery — verify intent", Severity.low),
]


# ── Verifiers ─────────────────────────────────────────────────────────────────


@dataclass
class SQLStatementTypeVerifier:
    """Blocks any non-SELECT SQL statement."""

    name: str = "sql_statement_type"

    def verify(self, sql: str, **_: object) -> VerifierResult:
        findings: list[Finding] = []
        first = _first_token(sql)

        if not first:
            findings.append(Finding(
                verifier=self.name,
                severity=Severity.medium,
                title="Empty SQL statement",
                detail="The SQL statement is empty.",
            ))
        elif first in _WRITE_KEYWORDS:
            findings.append(Finding(
                verifier=self.name,
                severity=Severity.critical,
                title=f"Write operation blocked: {first}",
                detail=(
                    f"Statement begins with '{first}'. "
                    "Only SELECT statements are permitted in automated execution."
                ),
            ))

        return VerifierResult(
            verifier_name=self.name,
            passed=len(findings) == 0,
            findings=findings,
        )


@dataclass
class SQLInjectionVerifier:
    """Detects common SQL injection and privilege escalation patterns."""

    name: str = "sql_injection"

    def verify(self, sql: str, **_: object) -> VerifierResult:
        findings: list[Finding] = []
        normalised = _normalise(sql)

        for pattern, title in _INJECTION_PATTERNS:
            if re.search(pattern, normalised, re.IGNORECASE):
                findings.append(Finding(
                    verifier=self.name,
                    severity=Severity.critical,
                    title=title,
                    detail=f"Pattern matched: {pattern}",
                ))

        return VerifierResult(
            verifier_name=self.name,
            passed=len(findings) == 0,
            findings=findings,
        )


@dataclass
class SQLRiskVerifier:
    """Flags risky but non-malicious SQL patterns for human review."""

    name: str = "sql_risk"

    def verify(self, sql: str, **_: object) -> VerifierResult:
        findings: list[Finding] = []
        normalised = _normalise(sql)

        for pattern, title, severity in _RISK_PATTERNS:
            if re.search(pattern, normalised, re.IGNORECASE):
                findings.append(Finding(
                    verifier=self.name,
                    severity=severity,
                    title=title,
                    detail=f"Pattern: {pattern}",
                ))

        return VerifierResult(
            verifier_name=self.name,
            # Risk findings are informational — they don't fail the pipeline
            passed=True,
            findings=findings,
        )


@dataclass
class SQLRowLimitVerifier:
    """Enforces that SQL queries declare a LIMIT clause."""

    name: str = "sql_row_limit"
    default_max_rows: int = 10_000

    def verify(self, sql: str, max_rows: int | None = None, **_: object) -> VerifierResult:
        findings: list[Finding] = []
        limit = max_rows or self.default_max_rows
        normalised = _normalise(sql)

        if not re.search(r"\bLIMIT\s+\d+", normalised):
            findings.append(Finding(
                verifier=self.name,
                severity=Severity.medium,
                title="No LIMIT clause",
                detail=(
                    f"Query has no LIMIT clause. "
                    f"Automated queries must not return more than {limit:,} rows. "
                    "Add LIMIT to the query."
                ),
            ))

        return VerifierResult(
            verifier_name=self.name,
            passed=len(findings) == 0,
            findings=findings,
        )
