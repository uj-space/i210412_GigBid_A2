# Data Card — GigBid AI-4016

## Overview
Synthetic portfolio corpora and job data used for training, evaluation, and
demonstration of the GigBid multi-agent freelancer copilot.

## Data Sources

### Persona Corpora (Synthetic)
Three freelancer personas provided by the instructor:
- AI/ML Engineer: CV, 15-25 case studies, repo READMEs, code, client reviews,
  ~150 past proposals labelled won/replied/ignored
- Full-stack Web Developer: same structure
- Data Analyst: same structure

### Job Data (Synthetic)
- GigSim marketplace simulator: ~1,500 historical jobs + live stream
- Dev evaluation set: ~200 jobs per persona with gold labels
- Hidden test set: new jobs and clients (not in repo)

## Fields
| Field | Type | Description |
|-------|------|-------------|
| job_id | string | Unique job identifier |
| title | string | Job title |
| description | string | Full job post text |
| required_skills | list[string] | Required skills |
| budget | object | min/max/currency |
| connects_cost | integer | Connects required to bid |
| client_id | string | Client identifier |
| warning_signals | list[string] | Risk flags in job post |
| posted_at | datetime | Job posting time |

## Licensing
All data is synthetic, created for this assignment. No real client or
freelancer data is used.

## Limitations
- Synthetic data may not reflect real marketplace distributions
- Persona corpora are illustrative, not exhaustive
- Hidden test set is never committed to the repo
