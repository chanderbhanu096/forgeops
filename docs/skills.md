# Skills Reference

Skills are the unit of capability in ForgeOps. Each skill is a versioned YAML file that declares what tools it needs, what permissions it requires, and what it produces.

---

## Built-in skills

### `dbt_model_repair` v1.0.0

Diagnoses and repairs failing dbt models.

**Required tools**: `repository.read`, `repository.patch`, `dbt.compile`, `dbt.test`

**Permissions**: `filesystem: sandbox_only`, `database: read_only`, `network: restricted`

**Inputs**: `repository_path`, `failing_model`, `error_context`

**Outputs**: `root_cause` (string), `changed_files` (list), `test_results` (object), `confidence` (float)

---

### `log_investigation` v1.0.0

Analyses structured and unstructured log files to identify error patterns, anomalies and root-cause indicators.

**Required tools**: `data.fetch_logs`, `data.search_logs`

**Permissions**: `filesystem: sandbox_only`, `database: read_only`, `network: restricted`

**Inputs**: `log_source`, `time_range`, `error_patterns`

**Outputs**: `findings` (list), `root_cause_hypothesis` (string), `affected_components` (list), `confidence` (float)

---

### `data_lineage_analysis` v1.0.0

Traces the upstream and downstream lineage of a dataset or pipeline component to understand blast radius and data flow.

**Required tools**: `data.get_lineage`, `data.inspect_pipeline_runs`

**Permissions**: `filesystem: sandbox_only`, `database: read_only`, `network: restricted`

**Inputs**: `dataset_name`, `pipeline_name`

**Outputs**: `upstream_dependencies` (list), `downstream_impacts` (list), `lineage_graph` (object), `affected_dashboards` (list)

---

### `pull_request_creation` v1.0.0

Creates a pull request from a prepared patch, adding a structured description with root cause, changes made, tests added and rollback instructions.

**Required tools**: `repository.read`, `repository.patch`, `github.create_branch`, `github.create_pull_request`

**Permissions**: `filesystem: sandbox_only`, `database: read_only`, `network: restricted`

**Inputs**: `repository_path`, `patch`, `title`, `description`, `base_branch`

**Outputs**: `pull_request_url` (string), `branch_name` (string), `files_changed` (list)

---

### `security_review` v1.0.0

Performs a security analysis of a code patch, checking for injection vulnerabilities, secret leakage, unsafe permissions, dependency risks and dangerous operations.

**Required tools**: `repository.read`

**Permissions**: `filesystem: sandbox_only`, `database: read_only`, `network: restricted`

**Inputs**: `patch`, `repository_path`, `context`

**Outputs**: `findings` (list), `risk_level` (string: low/medium/high/critical), `approved` (bool), `recommendations` (list)

---

## Adding a new skill

Create `apps/api/forgeops/skills/definitions/<your_skill>.yaml`:

```yaml
name: your_skill_name      # snake_case, globally unique
version: 1.0.0             # semver

description: >
  One or two sentences describing what this skill does.
  This text is used for skill discovery scoring.

required_tools:
  - server.tool_name       # tools this skill requires

permissions:
  filesystem: sandbox_only   # or: any
  database: read_only        # or: read_write
  network: restricted        # or: any

inputs:
  param_name: type_string    # e.g. repository_path: string

outputs:
  output_name: type_string   # e.g. confidence: float

dependencies: []             # other skill names that must run first
```

Then restart the API or call `POST /api/v1/skills/reload` (if implemented).

---

## Skill versioning

Multiple versions of the same skill can coexist. The registry returns the **highest semver** by default. To pin a specific version, pass `version` to `registry.get(name, version)`.

When updating a skill:
- Increment the patch version for bug fixes: `1.0.0 → 1.0.1`
- Increment the minor version for new outputs or relaxed permissions: `1.0.0 → 1.1.0`
- Increment the major version for breaking input/output changes: `1.0.0 → 2.0.0`

---

## Skill permissions

Permissions gate what an agent using the skill may do:

| Permission | `sandbox_only` | `any` |
|---|---|---|
| `filesystem` | Reads/writes only within the sandbox container | Full filesystem access |

| Permission | `read_only` | `read_write` |
|---|---|---|
| `database` | SELECT only; no mutations | Full DML access |

| Permission | `restricted` | `any` |
|---|---|---|
| `network` | Only MCP servers; no arbitrary HTTP | Unrestricted outbound |

The agent runtime enforces these by checking skill permissions against the tool being called before execution.
