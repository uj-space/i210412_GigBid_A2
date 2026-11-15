# Signature Extension — X2: Proposal Experiments

## Overview
A/B test two proposal strategies in GigSim to measure impact on reply rate.

## Design
- **Strategy A**: Evidence-heavy proposals with detailed case study citations
- **Strategy B**: Concise proposals focused on outcomes and value

## Evaluation
Run both strategies on the same set of dev jobs in GigSim, measure:
- Reply rate per strategy
- Statistical significance (chi-square test)
- Cost per reply (Connects spent)

## Results
Documented in `evals/results/proposal_experiments.json`
