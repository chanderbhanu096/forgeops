"""Tests for the verifier pipeline."""
from __future__ import annotations

import pytest

from forgeops.verification.base import Severity
from forgeops.verification.code_verifiers import (
    DangerousPatternVerifier,
    ImportVerifier,
    PatchSizeVerifier,
    PatchSyntaxVerifier,
)
from forgeops.verification.sql_verifiers import (
    SQLInjectionVerifier,
    SQLRiskVerifier,
    SQLRowLimitVerifier,
    SQLStatementTypeVerifier,
)
from forgeops.verification.infra_verifiers import (
    TerraformDestructiveChangeVerifier,
    TerraformSecurityVerifier,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_patch(filename: str, content: str) -> str:
    """Build a minimal unified diff with a single added file."""
    lines = [f"+++ b/{filename}"]
    for line in content.splitlines():
        lines.append(f"+{line}")
    return "\n".join(lines)


# ── PatchSyntaxVerifier ───────────────────────────────────────────────────────


def test_syntax_passes_valid_python():
    patch = _make_patch("models/revenue.py", "def transform(x):\n    return x * 100\n")
    result = PatchSyntaxVerifier().verify(patch=patch)
    assert result.passed
    assert result.findings == []


def test_syntax_fails_invalid_python():
    patch = _make_patch("models/revenue.py", "def transform(x\n    return x")
    result = PatchSyntaxVerifier().verify(patch=patch)
    assert not result.passed
    assert any(f.severity == Severity.critical for f in result.findings)


def test_syntax_passes_non_python_files():
    patch = _make_patch("models/revenue.sql", "SELECT * FROM revenue")
    result = PatchSyntaxVerifier().verify(patch=patch)
    assert result.passed
    assert result.metadata["python_files_found"] == 0


# ── DangerousPatternVerifier ──────────────────────────────────────────────────


def test_dangerous_blocks_os_system():
    patch = _make_patch("fix.py", "import os\nos.system('rm -rf /tmp/data')\n")
    result = DangerousPatternVerifier().verify(patch=patch)
    assert not result.passed
    assert any("os.system" in f.title for f in result.findings)


def test_dangerous_blocks_eval():
    patch = _make_patch("fix.py", "result = eval(user_input)\n")
    result = DangerousPatternVerifier().verify(patch=patch)
    assert not result.passed
    assert any(f.severity == Severity.critical for f in result.findings)


def test_dangerous_blocks_hardcoded_api_key():
    patch = _make_patch("config.py", 'API_KEY = "sk-abc123def456ghi789jkl012"\n')
    result = DangerousPatternVerifier().verify(patch=patch)
    assert not result.passed
    assert any("secret leakage" in f.title.lower() for f in result.findings)


def test_dangerous_passes_clean_patch():
    patch = _make_patch(
        "models/daily_revenue.py",
        "def calculate_revenue(amount_cents: int) -> float:\n"
        "    return amount_cents / 100.0\n",
    )
    result = DangerousPatternVerifier().verify(patch=patch)
    assert result.passed


# ── ImportVerifier ────────────────────────────────────────────────────────────


def test_import_blocks_subprocess():
    patch = _make_patch("fix.py", "import subprocess\nsubprocess.run(['ls'])\n")
    result = ImportVerifier().verify(patch=patch)
    assert not result.passed
    assert any("subprocess" in f.title for f in result.findings)


def test_import_flags_requests_as_suspicious():
    patch = _make_patch("fix.py", "import requests\nresponse = requests.get('https://example.com')\n")
    result = ImportVerifier().verify(patch=patch)
    # Suspicious but not critical — pipeline still passes
    assert result.passed
    assert any(f.severity == Severity.medium for f in result.findings)


def test_import_passes_standard_library():
    patch = _make_patch("fix.py", "import json\nimport datetime\nfrom typing import Any\n")
    result = ImportVerifier().verify(patch=patch)
    assert result.passed
    assert result.findings == []


# ── PatchSizeVerifier ─────────────────────────────────────────────────────────


def test_patch_size_passes_small_patch():
    content = "\n".join(f"    x_{i} = {i}" for i in range(10))
    patch = _make_patch("fix.py", content)
    result = PatchSizeVerifier().verify(patch=patch, changed_files=["fix.py"])
    assert result.passed


def test_patch_size_flags_large_patch():
    content = "\n".join(f"    line_{i} = {i}" for i in range(600))
    patch = _make_patch("fix.py", content)
    result = PatchSizeVerifier().verify(patch=patch, changed_files=["fix.py"])
    assert any("line limit" in f.title.lower() for f in result.findings)


# ── SQLStatementTypeVerifier ──────────────────────────────────────────────────


def test_sql_type_allows_select():
    result = SQLStatementTypeVerifier().verify(sql="SELECT id, revenue FROM orders LIMIT 100")
    assert result.passed


def test_sql_type_blocks_delete():
    result = SQLStatementTypeVerifier().verify(sql="DELETE FROM orders WHERE id = 1")
    assert not result.passed
    assert any(f.severity == Severity.critical for f in result.findings)


def test_sql_type_blocks_drop():
    result = SQLStatementTypeVerifier().verify(sql="DROP TABLE revenue")
    assert not result.passed


def test_sql_type_blocks_truncate():
    result = SQLStatementTypeVerifier().verify(sql="TRUNCATE TABLE staging_orders")
    assert not result.passed


def test_sql_type_blocks_insert():
    result = SQLStatementTypeVerifier().verify(sql="INSERT INTO orders VALUES (1, 100)")
    assert not result.passed


# ── SQLInjectionVerifier ──────────────────────────────────────────────────────


def test_sql_injection_blocks_stacked_write():
    result = SQLInjectionVerifier().verify(
        sql="SELECT * FROM users; DROP TABLE users--"
    )
    assert not result.passed
    assert any(f.severity == Severity.critical for f in result.findings)


def test_sql_injection_blocks_load_file():
    result = SQLInjectionVerifier().verify(sql="SELECT LOAD_FILE('/etc/passwd')")
    assert not result.passed


def test_sql_injection_passes_clean_select():
    result = SQLInjectionVerifier().verify(
        sql="SELECT user_id, SUM(revenue) FROM orders GROUP BY user_id LIMIT 1000"
    )
    assert result.passed


# ── SQLRowLimitVerifier ───────────────────────────────────────────────────────


def test_sql_limit_passes_with_limit():
    result = SQLRowLimitVerifier().verify(sql="SELECT * FROM orders LIMIT 500")
    assert result.passed


def test_sql_limit_fails_without_limit():
    result = SQLRowLimitVerifier().verify(sql="SELECT * FROM orders")
    assert not result.passed
    assert any("LIMIT" in f.title for f in result.findings)


# ── SQLRiskVerifier ───────────────────────────────────────────────────────────


def test_sql_risk_flags_select_star():
    result = SQLRiskVerifier().verify(sql="SELECT * FROM orders LIMIT 100")
    # Risk findings don't fail the pipeline
    assert result.passed
    assert any("SELECT *" in f.title for f in result.findings)


def test_sql_risk_flags_cross_join():
    result = SQLRiskVerifier().verify(
        sql="SELECT a.id, b.id FROM orders a CROSS JOIN customers b LIMIT 100"
    )
    assert result.passed  # warning only
    assert any("CROSS JOIN" in f.title for f in result.findings)


# ── TerraformDestructiveChangeVerifier ───────────────────────────────────────


def test_terraform_blocks_force_destroy():
    tf = 'resource "aws_s3_bucket" "data" {\n  force_destroy = true\n}'
    result = TerraformDestructiveChangeVerifier().verify(terraform_content=tf)
    assert not result.passed
    assert any("force_destroy" in f.title for f in result.findings)


def test_terraform_passes_safe_bucket():
    tf = 'resource "aws_s3_bucket" "data" {\n  bucket = "my-data-bucket"\n  tags = { Env = "prod" }\n}'
    result = TerraformDestructiveChangeVerifier().verify(terraform_content=tf)
    assert result.passed


# ── TerraformSecurityVerifier ─────────────────────────────────────────────────


def test_terraform_security_blocks_open_sg():
    tf = (
        'resource "aws_security_group_rule" "allow_all" {\n'
        '  type        = "ingress"\n'
        '  cidr_blocks = ["0.0.0.0/0"]\n'
        '  from_port   = 0\n'
        '  to_port     = 65535\n'
        '}'
    )
    result = TerraformSecurityVerifier().verify(terraform_content=tf)
    assert not result.passed
    assert any("open to all" in f.title.lower() for f in result.findings)


def test_terraform_security_blocks_iam_wildcard():
    tf = '{\n  "Action": "*",\n  "Resource": "*"\n}'
    result = TerraformSecurityVerifier().verify(terraform_content=tf)
    assert not result.passed
    assert any("wildcard" in f.title.lower() for f in result.findings)


# ── Pipeline integration ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_clean_patch_passes():
    from forgeops.verification.pipeline import VerificationPipeline

    pipeline = VerificationPipeline()
    patch = _make_patch(
        "models/daily_revenue.py",
        "def transform(amount_cents: int) -> float:\n"
        "    return amount_cents / 100.0\n",
    )
    result = await pipeline.verify_patch(patch, changed_files=["models/daily_revenue.py"])
    assert result.passed
    assert result.critical_count == 0


@pytest.mark.asyncio
async def test_pipeline_dangerous_patch_fails():
    from forgeops.verification.pipeline import VerificationPipeline

    pipeline = VerificationPipeline()
    patch = _make_patch(
        "fix.py",
        "import os\nos.system('rm -rf /')\n",
    )
    result = await pipeline.verify_patch(patch)
    assert not result.passed
    assert result.critical_count > 0


@pytest.mark.asyncio
async def test_pipeline_sql_select_passes():
    from forgeops.verification.pipeline import VerificationPipeline

    pipeline = VerificationPipeline()
    result = await pipeline.verify_sql(
        "SELECT order_id, SUM(revenue_eur) FROM orders GROUP BY order_id LIMIT 1000"
    )
    assert result.passed


@pytest.mark.asyncio
async def test_pipeline_sql_delete_fails():
    from forgeops.verification.pipeline import VerificationPipeline

    pipeline = VerificationPipeline()
    result = await pipeline.verify_sql("DELETE FROM orders")
    assert not result.passed
    assert result.critical_count > 0


@pytest.mark.asyncio
async def test_pipeline_terraform_open_sg_fails():
    from forgeops.verification.pipeline import VerificationPipeline

    pipeline = VerificationPipeline()
    tf = 'resource "aws_security_group_rule" "bad" {\n  cidr_blocks = ["0.0.0.0/0"]\n}'
    result = await pipeline.verify_terraform(tf)
    assert not result.passed
