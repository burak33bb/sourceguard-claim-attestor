# SourceGuard Claim Attestor

## Category

Intelligent Contracts

## Summary

SourceGuard Claim Attestor is a reusable GenLayer Intelligent Contract for source-backed claim verification. It lets a user submit a factual claim and a bounded set of allowed source URLs. Validators fetch each source, evaluate whether the source supports or contradicts the claim, then aggregate those evaluations into a canonical on-chain attestation report.

## Why It Matters

Many apps need a durable evidence layer: governance proposals, prediction market resolution, research review, audit notes, provenance records, and public claim registries. This contract provides a reusable primitive for those flows without requiring a full product frontend.

## How Consensus Is Used

The contract uses GenLayer consensus in two stages:

1. Per-source evaluation with `gl.get_webpage`, `gl.exec_prompt`, and `gl.eq_principle_prompt_comparative`.
2. Aggregate verdict consensus over all source evaluations, again using `gl.eq_principle_prompt_comparative`.

Validators must agree on the normalized claim and verdict while allowing small wording differences in reasoning and evidence excerpts.

## State

- `allowed_domains`: source allowlist.
- `reports`: append-only canonical JSON report history.
- `latest_report`: cached latest report for simple reads.
- `max_sources`: bounded source count for predictable validator work.

## Files

- `contracts/sourceguard_claim_attestor.py`
- `README.md`
- `tests/test_sourceguard_claim_attestor.py`

## Tests

```text
python -m pytest tests
python -m black --check contracts\sourceguard_claim_attestor.py tests\test_sourceguard_claim_attestor.py
```
