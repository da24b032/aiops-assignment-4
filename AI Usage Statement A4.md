# AI Usage Statement

**Name:** Visaka · **Roll no:** DA24B032 · **Course:** DA3408 Assignment 4

## Collaboration
The base implementation was developed together with a lab partner. As instructed by the TA, I reworked and modified it before submitting (refactoring, renaming, rewording, restructuring the documentation and examples).

## AI tool used
Claude (Anthropic), ChatGPT
## What the AI generated
| Area | Files | AI contribution |
|---|---|---|
| Streamlit app and instrumentation | `app.py`, `pipeline.py`, `captioner.py`, `metrics.py` | Drafted by Claude
| Monitoring config | `prometheus.yml`, `alert_rules.yml`, `alertmanager.yml`, `alert_receiver.py`, `docker-compose.yml`, `grafana/provisioning/*` | Drafted by Claude |
| Grafana dashboard | `gen_dashboard.py`, `grafana/dashboards/captioning_dashboard.json` | Panel layout, styling choices (colour-blind-safe palette, axis labels, units, descriptions) and all PromQL queries were assisted by Claude |
| Test data and docs | `make_test_data.py`, `README.md`, `promql_notes.md`, `.gitignore` | Drafted by Claude |
| Troubleshooting | n/a | Claude diagnosed the disk-space failure (CUDA build of PyTorch), the repeated `torchvision` watcher warning, the misleading `spanNulls` lines in the dashboard |

## AI-generated PromQL and regex (Code of Conduct attribution)
All PromQL in the dashboard and in `alert_rules.yml`  was drafted by Claude. The comments in `alert_rules.yml` and `promql_notes.md` describe the intent of each query; the prompts used are quoted next to each query in `promql_notes.md` and in the comments of `alert_rules.yml`. Regexes used:
- `mode=~"user|system|iowait"` (CPU-by-mode panel)
- `device!~"lo|veth.*|docker.*|br-.*"` (network panels)


