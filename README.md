# SourceGuard Claim Attestor

SourceGuard Claim Attestor is a reusable GenLayer Intelligent Contract for evidence-backed claim verification. It accepts a factual claim and a small set of allowed source URLs, asks validators to evaluate each source, aggregates their conclusions, and stores a canonical attestation report on-chain.

The primitive is intended for builders who need a reusable way to attach consensus-reviewed evidence to claims, marketplace listings, governance proposals, prediction market outcomes, audit notes, or knowledge-base entries.

## Why GenLayer

The contract uses GenLayer consensus in two stages:

1. Source evaluation: validators fetch each URL with `gl.get_webpage`, extract evidence, and return a structured verdict.
2. Aggregate attestation: validators combine the per-source results into a final verdict with confidence and supporting source references.

Both stages use `gl.eq_principle_prompt_comparative` so validators must agree on the normalized claim and verdict, while still allowing minor wording differences in reasoning and evidence.

## Verdicts

- `SUPPORTED`: at least one allowed source directly supports the claim and no source directly contradicts it.
- `CONTRADICTED`: at least one allowed source directly contradicts the claim.
- `INSUFFICIENT`: relevant sources exist but do not settle the claim.
- `IRRELEVANT`: the submitted sources do not address the claim.

## State Design

- `allowed_domains`: allowlist used to keep attestations scoped to trusted source domains.
- `reports`: append-only canonical JSON attestation history.
- `latest_report`: cached latest report for simple reads.
- `max_sources`: bounded source count to keep validation cost predictable.

Each report stores the submitter, original claim, source URLs, per-source validator outputs, aggregate verdict, confidence, reasoning, and creation timestamp.

## Example

Deploy with an allowlist:

```python
primary_domain = "github.com"
secondary_domain = "docs.genlayer.com"
max_sources = 3
```

Call `attest`:

```python
claim = "The genlayer-py repository supports calldata encoding utilities."
source_url_one = "https://github.com/genlayerlabs/genlayer-py"
source_url_two = ""
source_url_three = ""
```

Read the latest report:

```python
contract.get_latest_report()
```

## Files

- `contracts/sourceguard_claim_attestor.py`: standalone Intelligent Contract source.
- `tests/test_sourceguard_claim_attestor.py`: lightweight regression tests for deterministic helpers and source structure.

## Review Notes

This submission focuses on the contract primitive, not a full frontend product. The contract is useful as a building block for claim registries, source-backed oracle flows, research review tools, governance evidence checks, and provenance systems.
