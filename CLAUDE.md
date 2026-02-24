# SNOW ITOM Auditor - ServiceNow Compliance Auditor

## Overview
Automated compliance auditing across CMDB, Discovery, and Asset Management domains. Generates compliance scores, remediation plans, trend analysis, and audit history with persistent local storage.

## Core Principles (NON-NEGOTIABLE)
1. **ZERO MOCKS** — Every API call, data point, and integration must be real. No mock data, no hardcoded values, no stub implementations. If the ServiceNow instance isn’t available, STOP and report the blocker.
2. **FAIL-STOP** — If any agent or tool encounters an error, the pipeline halts. No silent failures. No workarounds. Fix the issue, then resume.
3. **READ-ONLY AUDITING** — Audit tools only read from ServiceNow. Remediation tools create plans but do not execute changes without confirmation.
4. **SEVERITY-WEIGHTED SCORING** — Compliance scores weight findings by severity (critical > high > medium > low).

## Architecture
```
FastMCP Server (server.py)
  |
  +-- Audit Tools (audit_cmdb, audit_discovery, audit_assets, audit_full)
  +-- Compliance Tools (compliance_rules, compliance_score, compliance_report)
  +-- History Tools (audit_history, audit_compare)
  +-- Remediation Tools (remediation_create, remediation_progress, remediation_validate)
  +-- Health Check (health_check)
  |
  +-- AuditEngine (engine.py) + ScoringEngine (scoring.py)
  +-- Storage Layer (.snow-audit/) — persistent audit history
  +-- ServiceNowClient (client.py) -> ServiceNow REST API
```

## MCP Tools (13 tools)
| Tool | Purpose |
|------|---------|
| `audit_cmdb` | Audit CMDB data quality and completeness |
| `audit_discovery` | Audit discovery configuration and results |
| `audit_assets` | Audit asset management compliance |
| `audit_full` | Full cross-domain audit |
| `compliance_rules` | Manage compliance rule definitions |
| `compliance_score` | Calculate compliance scores |
| `compliance_report` | Generate compliance reports |
| `audit_history` | View past audit results |
| `audit_compare` | Compare two audit runs |
| `remediation_create` | Create remediation plans |
| `remediation_progress` | Track remediation progress |
| `remediation_validate` | Validate remediation completion |
| `health_check` | System health check |

## ServiceNow Tables
| Table | Purpose |
|-------|---------|
| `cmdb_ci` | Base CI table |
| `cmdb_ci_server` | Server CIs |
| `cmdb_rel_ci` | CI Relationships |
| `discovery_schedule` | Discovery schedules |
| `sa_pattern` | Discovery patterns |
| `alm_license` | Software licenses |
| `alm_hardware` | Hardware assets |
| `alm_asset` | Base asset table |

## Configuration
- **Env prefix:** `SERVICENOW_*`
- **Key variables:** `SERVICENOW_INSTANCE`, `SERVICENOW_USERNAME`, `SERVICENOW_PASSWORD`
- **Additional:** `AUDIT_STORAGE_PATH` (defaults to `.snow-audit/`)

## Key Files
- `src/snow_itom_auditor/server.py` — MCP server entry point
- `src/snow_itom_auditor/engine.py` — Core audit engine
- `src/snow_itom_auditor/scoring.py` — Compliance scoring engine
- `src/snow_itom_auditor/tools/` — Tool modules

## Git Workflow
- All agent work happens on feature branches
- PRs for human review before merging
- Never push directly to main
