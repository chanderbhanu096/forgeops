"""
Demo mission fixture — the revenue pipeline incident.

This module provides deterministic fixture data for the canonical portfolio
demo. It can be used in integration tests and as the seed for live demos.

Scenario:
    Yesterday's deployment caused the executive revenue dashboard to report
    18% lower revenue. Investigation reveals:

    1. Source column changed from euros to cents (revenue_eur → amount_cents)
    2. Schema technically remained valid (both INT columns)
    3. Existing unit tests passed (they only checked column presence)
    4. A dbt transformation applied the old conversion factor (÷ 100)
    5. Error propagated through 3 downstream models
    6. 2 dashboards and 1 ML feature were affected

    ForgeOps should:
    - Find the suspicious commit
    - Generate a lineage impact graph
    - Compare pre/post distributions
    - Create a regression test
    - Correct the transformation
    - Run in sandbox
    - Compare repaired values against historical ranges
    - Produce a backfill plan
    - Open a draft PR
    - Request human approval before touching production
"""
from __future__ import annotations

from typing import Any

# ── Mission payload ───────────────────────────────────────────────────────────

DEMO_MISSION_PAYLOAD: dict[str, Any] = {
    "title": "Revenue dashboard showing 18% lower revenue after yesterday's deployment",
    "description": (
        "Yesterday's deployment caused the executive revenue dashboard to report 18% lower revenue. "
        "Investigate the problem, identify all affected datasets, produce a safe fix and open a pull request. "
        "The pipeline is on dbt/Airflow, warehouse is BigQuery-compatible. "
        "Do not touch production until the fix is validated and approved."
    ),
    "max_steps": 50,
    "max_cost_usd": 3.0,
}

# ── Simulated repository content ──────────────────────────────────────────────

DEMO_REPOSITORY_FILES: dict[str, str] = {
    "models/revenue/daily_revenue.sql": """\
-- daily_revenue.sql
-- Computes daily revenue aggregated from the orders source.
-- NOTE: After the 2024-01-14 deployment, the source column
-- was renamed from revenue_eur to amount_cents and unit changed.

WITH source AS (
    SELECT
        order_date,
        amount_cents,   -- was: revenue_eur (INT, euros)
        customer_id
    FROM {{ source('raw', 'orders') }}
)

SELECT
    order_date,
    customer_id,
    -- BUG: still dividing by 100 assuming old EUR unit
    -- Should now be: amount_cents / 100.0 (convert cents to euros)
    -- But previous logic was: revenue_eur (already in euros, no conversion needed)
    amount_cents / 100.0 AS revenue_eur
FROM source
""",

    "models/revenue/weekly_revenue.sql": """\
-- weekly_revenue.sql — downstream of daily_revenue

SELECT
    DATE_TRUNC('week', order_date) AS week_start,
    SUM(revenue_eur) AS weekly_revenue_eur
FROM {{ ref('daily_revenue') }}
GROUP BY 1
""",

    "models/revenue/executive_dashboard.sql": """\
-- executive_dashboard.sql — upstream of Looker dashboard

SELECT
    DATE_TRUNC('month', order_date) AS month,
    SUM(revenue_eur) AS monthly_revenue_eur,
    COUNT(DISTINCT customer_id) AS unique_customers
FROM {{ ref('daily_revenue') }}
GROUP BY 1
ORDER BY 1 DESC
""",

    "models/ml/revenue_feature.sql": """\
-- revenue_feature.sql — used by churn prediction model

SELECT
    customer_id,
    AVG(revenue_eur) AS avg_daily_revenue_30d
FROM {{ ref('daily_revenue') }}
WHERE order_date >= CURRENT_DATE - 30
GROUP BY 1
""",
}

# ── The fix ───────────────────────────────────────────────────────────────────
# What ForgeOps should generate as the proposed patch

DEMO_EXPECTED_PATCH = """\
--- a/models/revenue/daily_revenue.sql
+++ b/models/revenue/daily_revenue.sql
@@ -1,20 +1,26 @@
 -- daily_revenue.sql
 -- Computes daily revenue aggregated from the orders source.
-
+-- FIXED (2024-01-15): amount_cents column now stores cents, not euros.
+-- Divide by 100.0 to convert back to EUR for downstream consistency.
+
+-- Regression test added: test_revenue_unit_is_eur.sql
+
 WITH source AS (
     SELECT
         order_date,
-        amount_cents,   -- was: revenue_eur (INT, euros)
+        amount_cents,
         customer_id
     FROM {{ source('raw', 'orders') }}
 )
 
 SELECT
     order_date,
     customer_id,
-    -- BUG: still dividing by 100 assuming old EUR unit
-    -- Should now be: amount_cents / 100.0 (convert cents to euros)
-    -- But previous logic was: revenue_eur (already in euros, no conversion needed)
-    amount_cents / 100.0 AS revenue_eur
+    ROUND(amount_cents / 100.0, 2) AS revenue_eur
 FROM source
"""

DEMO_REGRESSION_TEST = """\
-- tests/test_revenue_unit_is_eur.sql
-- Validates that revenue values are in a plausible EUR range.
-- A typical daily revenue per order is between €0.01 and €10,000.

SELECT
    order_date,
    customer_id,
    revenue_eur
FROM {{ ref('daily_revenue') }}
WHERE revenue_eur < 0.01 OR revenue_eur > 10000
"""

# ── Lineage impact graph ──────────────────────────────────────────────────────

DEMO_LINEAGE_IMPACT: dict[str, Any] = {
    "root_model": "daily_revenue",
    "affected_nodes": [
        {"id": "daily_revenue",       "type": "model",     "status": "broken"},
        {"id": "weekly_revenue",      "type": "model",     "status": "stale"},
        {"id": "executive_dashboard", "type": "model",     "status": "stale"},
        {"id": "revenue_feature",     "type": "ml_feature","status": "stale"},
        {"id": "looker_revenue_dash", "type": "dashboard", "status": "stale"},
        {"id": "looker_exec_summary", "type": "dashboard", "status": "stale"},
    ],
    "edges": [
        {"from": "raw.orders",         "to": "daily_revenue"},
        {"from": "daily_revenue",      "to": "weekly_revenue"},
        {"from": "daily_revenue",      "to": "executive_dashboard"},
        {"from": "daily_revenue",      "to": "revenue_feature"},
        {"from": "weekly_revenue",     "to": "looker_revenue_dash"},
        {"from": "executive_dashboard","to": "looker_exec_summary"},
    ],
    "blast_radius": {
        "broken_models": 1,
        "stale_models": 2,
        "stale_dashboards": 2,
        "stale_ml_features": 1,
    },
}

# ── Hypotheses (what ForgeOps should generate) ────────────────────────────────

DEMO_EXPECTED_HYPOTHESES = [
    {
        "id": "h1",
        "description": (
            "The source column 'amount_cents' was renamed from 'revenue_eur' and its unit changed "
            "from euros to cents. The dbt transformation did not account for the unit change, "
            "applying no conversion where it should now divide by 100."
        ),
        "confidence": 0.95,
        "evidence": [
            "Git log shows column rename in commit abc1234",
            "amount_cents values are ~100x larger than historical revenue_eur values",
            "Schema registry shows type is INT in both cases (no type-level change)",
            "dbt tests only checked column existence, not value ranges",
        ],
    },
    {
        "id": "h2",
        "description": "A separate ETL job introduced a currency conversion error upstream.",
        "confidence": 0.05,
        "evidence": [],
    },
]

# ── Sandbox validation ────────────────────────────────────────────────────────

DEMO_SANDBOX_OUTPUT = """\
[SANDBOX] Applying patch to models/revenue/daily_revenue.sql
[SANDBOX] Running: dbt compile
[SANDBOX] ✓ Compilation succeeded
[SANDBOX] Running: dbt test --select daily_revenue
[SANDBOX] 42/42 tests passed
[SANDBOX] Running regression test: test_revenue_unit_is_eur
[SANDBOX] ✓ Regression test passed (0 rows out of range)
[SANDBOX] Comparing post-fix revenue distribution:
[SANDBOX]   Pre-fix  mean: €0.82  (was divided by 100 accidentally)
[SANDBOX]   Post-fix mean: €82.14 (matches historical range €60-€120)
[SANDBOX] ✓ Distribution within expected historical range
"""
