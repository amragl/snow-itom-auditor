# snow-itom-auditor

ServiceNow ITOM Compliance Auditor -- an MCP server that performs automated compliance auditing of ServiceNow ITOM configurations across CMDB, Discovery, and Asset Management.

## Features

- **CMDB Audit**: Orphan CI detection, stale record identification, duplicate detection, missing field validation
- **Discovery Audit**: Schedule staleness checks, pattern coverage analysis, CI reconciliation
- **Asset Audit**: License over-allocation detection, expired hardware identification, unassigned asset checks
- **Full Audit**: Consolidated cross-domain compliance assessment
- **Compliance Scoring**: Severity-weighted scoring with per-category breakdowns
- **Remediation Plans**: Auto-generated action plans from findings with progress tracking
- **Audit History**: Trend analysis and audit comparison
- **Report Generation**: Structured compliance reports with executive summaries

## MCP Tools

| Tool | Description |
|------|-------------|
| `audit_cmdb` | Run CMDB compliance audit |
| `audit_discovery` | Run Discovery compliance audit |
| `audit_assets` | Run Asset compliance audit |
| `audit_full` | Run full cross-domain audit |
| `compliance_rules` | List all defined compliance rules |
| `compliance_score` | Get latest compliance score |
| `compliance_report` | Generate structured compliance report |
| `audit_history` | Browse past audit results |
| `audit_compare` | Compare two audit runs for trends |
| `remediation_create` | Create remediation plan from findings |
| `remediation_progress` | Track remediation plan progress |
| `remediation_validate` | Re-run check to verify a fix |
| `health_check` | Verify server and ServiceNow connectivity |

## Quick Start

### Prerequisites

- Python 3.11+
- ServiceNow instance with ITOM modules (CMDB, Discovery, SAM/HAM)
- User account with read access to relevant tables

### Installation

```bash
pip install -e .
```

### Configuration

Copy `.env.example` to `.env` and fill in your ServiceNow credentials:

```bash
cp .env.example .env
```

Required environment variables:

| Variable | Description |
|----------|-------------|
| `SERVICENOW_INSTANCE` | Instance URL (e.g., `https://myinstance.service-now.com`) |
| `SERVICENOW_USERNAME` | ServiceNow username |
| `SERVICENOW_PASSWORD` | ServiceNow password |

Optional:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICENOW_TIMEOUT` | `30` | Request timeout in seconds |
| `SERVICENOW_MAX_RETRIES` | `3` | Max retries on transient errors |
| `AUDIT_STORAGE_PATH` | `.snow-audit` | Local storage directory |
| `LOG_LEVEL` | `INFO` | Logging level |

### Running the Server

```bash
snow-itom-auditor
```

### Docker

```bash
docker compose up -d
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ --ignore=tests/integration -q
ruff check src/ tests/
```

### Integration Tests

Integration tests require live ServiceNow credentials and are skipped by default:

```bash
pytest tests/integration -m integration
```

## Architecture

```
src/snow_itom_auditor/
  __init__.py          # Package exports
  config.py            # Pydantic-settings configuration
  exceptions.py        # Typed exception hierarchy
  client.py            # ServiceNow REST client with retry logic
  models.py            # Pydantic v2 data models
  scoring.py           # Compliance scoring engine
  storage.py           # JSON file-based persistence
  engine.py            # Core audit execution engine
  server.py            # FastMCP server and tool registration
  tools/
    cmdb.py            # CMDB audit checks
    discovery.py       # Discovery audit checks
    assets.py          # Asset audit checks
    compliance.py      # Rules listing and score retrieval
    reports.py         # Report generation
    history.py         # Audit history and comparison
    orchestration.py   # Full audit orchestration
    remediation.py     # Remediation plan lifecycle
```

## ServiceNow Tables Accessed

| Table | Purpose |
|-------|---------|
| `cmdb_ci` | CI health checks |
| `cmdb_ci_server` | Server-specific validation |
| `cmdb_rel_ci` | Relationship validation |
| `discovery_schedule` | Schedule compliance |
| `sa_pattern` | Pattern coverage |
| `alm_license` | License compliance |
| `alm_hardware` | Hardware lifecycle |
| `alm_asset` | Asset management |

## License

MIT
