# { "Depends": "py-genlayer:test" }

import json
import typing
from datetime import datetime
from urllib.parse import urlparse

from genlayer import *

SUPPORTED = "SUPPORTED"
CONTRADICTED = "CONTRADICTED"
INSUFFICIENT = "INSUFFICIENT"
IRRELEVANT = "IRRELEVANT"
VALID_VERDICTS = [SUPPORTED, CONTRADICTED, INSUFFICIENT, IRRELEVANT]


class SourceGuardClaimAttestor(gl.Contract):
    allowed_domains: DynArray[str]
    reports: DynArray[str]
    latest_report: str
    max_sources: u256

    def __init__(self, allowed_domains: list[str], max_sources: int):
        if not allowed_domains:
            raise ValueError("At least one allowed source domain is required.")
        if max_sources < 1 or max_sources > 5:
            raise ValueError("max_sources must be between 1 and 5.")

        seen_domains = []
        for domain in allowed_domains:
            normalized = _normalize_domain(domain)
            if not normalized:
                raise ValueError("Allowed domains must be valid.")
            if normalized not in seen_domains:
                seen_domains.append(normalized)
                self.allowed_domains.append(normalized)

        self.max_sources = u256(max_sources)
        self.latest_report = ""

    @gl.public.write
    def attest(self, claim: str, source_urls: list[str]) -> dict[str, typing.Any]:
        claim = claim.strip()
        if not claim:
            raise ValueError("Claim is required.")
        if len(source_urls) == 0:
            raise ValueError("At least one source URL is required.")
        if len(source_urls) > self.max_sources:
            raise ValueError("Too many source URLs.")

        normalized_sources = []
        for source_url in source_urls:
            normalized_url = source_url.strip()
            if not normalized_url:
                raise ValueError("Source URL is required.")
            source_domain = _normalize_domain(normalized_url)
            if not _domain_allowed(source_domain, list(self.allowed_domains)):
                raise ValueError("Source URL domain is not allowed.")
            if normalized_url not in normalized_sources:
                normalized_sources.append(normalized_url)

        source_evaluations = []
        for source_url in normalized_sources:

            def evaluate_source() -> str:
                webpage_text = gl.get_webpage(source_url, mode="text")
                task = f"""
You are validating whether a public source supports a factual claim.

Claim:
{claim}

Source URL:
{source_url}

Source text:
{webpage_text}

Return only valid JSON with this schema:
{{
  "source_url": "{source_url}",
  "normalized_claim": "one concise factual claim",
  "verdict": "SUPPORTED | CONTRADICTED | INSUFFICIENT | IRRELEVANT",
  "confidence": 0,
  "evidence": ["up to three short exact excerpts from the source"],
  "reasoning": "brief reason for the verdict"
}}

Rules:
- Use SUPPORTED only when the source directly supports the claim.
- Use CONTRADICTED only when the source directly contradicts the claim.
- Use INSUFFICIENT when the source is relevant but does not settle the claim.
- Use IRRELEVANT when the source is unrelated to the claim.
- Confidence must be an integer from 0 to 100.
- Do not include markdown, prose, or extra keys.
                """
                result = gl.exec_prompt(task)
                result_dict = _parse_json_dict(result)
                result_dict["source_url"] = source_url
                _validate_source_evaluation(result_dict)
                return _canonical_json(result_dict)

            agreed_result = gl.eq_principle_prompt_comparative(
                evaluate_source,
                principle=(
                    "The `verdict` and `normalized_claim` fields must match. "
                    "Evidence and reasoning must support the same conclusion."
                ),
            )
            source_evaluations.append(_parse_json_dict(agreed_result))

        def aggregate_sources() -> str:
            task = f"""
You are aggregating validator-reviewed source evaluations for a factual claim.

Claim:
{claim}

Source evaluations:
{json.dumps(source_evaluations, sort_keys=True)}

Return only valid JSON with this schema:
{{
  "normalized_claim": "one concise factual claim",
  "final_verdict": "SUPPORTED | CONTRADICTED | INSUFFICIENT | IRRELEVANT",
  "confidence": 0,
  "supporting_sources": ["URLs that support the final verdict"],
  "reasoning": "brief aggregate reason"
}}

Rules:
- SUPPORTED requires at least one directly supportive source and no direct contradiction.
- CONTRADICTED requires at least one directly contradictory source.
- INSUFFICIENT is for relevant evidence that does not settle the claim.
- IRRELEVANT is for sources that do not address the claim.
- Confidence must be an integer from 0 to 100.
- Do not include markdown, prose, or extra keys.
            """
            result = gl.exec_prompt(task)
            result_dict = _parse_json_dict(result)
            _validate_aggregate(result_dict)
            return _canonical_json(result_dict)

        aggregate_result = gl.eq_principle_prompt_comparative(
            aggregate_sources,
            principle=(
                "The `final_verdict` and `normalized_claim` fields must match. "
                "Supporting sources must be consistent with the source evaluations."
            ),
        )
        aggregate = _parse_json_dict(aggregate_result)

        report = {
            "id": len(self.reports) + 1,
            "submitter": gl.message.sender_address.as_hex,
            "claim": claim,
            "source_urls": normalized_sources,
            "source_evaluations": source_evaluations,
            "aggregate": aggregate,
            "created_at": datetime.now().astimezone().isoformat(),
        }
        report_json = _canonical_json(report)
        self.reports.append(report_json)
        self.latest_report = report_json
        return report

    @gl.public.view
    def get_allowed_domains(self) -> list[str]:
        return list(self.allowed_domains)

    @gl.public.view
    def get_report_count(self) -> int:
        return len(self.reports)

    @gl.public.view
    def get_latest_report(self) -> dict[str, typing.Any]:
        if not self.latest_report:
            return {}
        return json.loads(self.latest_report)

    @gl.public.view
    def get_report(self, report_id: int) -> dict[str, typing.Any]:
        if report_id < 1 or report_id > len(self.reports):
            raise ValueError("Report not found.")
        return json.loads(self.reports[report_id - 1])


def _normalize_domain(value: str) -> str:
    value = value.strip().lower()
    if not value:
        return ""
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    return parsed.netloc.replace("www.", "").split(":")[0]


def _domain_allowed(domain: str, allowed_domains: list[str]) -> bool:
    return domain in allowed_domains


def _parse_json_dict(json_str: str) -> dict:
    first_brace = json_str.find("{")
    last_brace = json_str.rfind("}")
    if first_brace == -1 or last_brace == -1 or last_brace < first_brace:
        raise ValueError("No JSON object found.")
    return json.loads(json_str[first_brace : last_brace + 1])


def _canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _validate_source_evaluation(value: dict) -> None:
    if value.get("verdict") not in VALID_VERDICTS:
        raise ValueError("Invalid source verdict.")
    confidence = value.get("confidence")
    if not isinstance(confidence, int) or confidence < 0 or confidence > 100:
        raise ValueError("Invalid confidence.")
    if not isinstance(value.get("evidence"), list):
        raise ValueError("Evidence must be a list.")


def _validate_aggregate(value: dict) -> None:
    if value.get("final_verdict") not in VALID_VERDICTS:
        raise ValueError("Invalid aggregate verdict.")
    confidence = value.get("confidence")
    if not isinstance(confidence, int) or confidence < 0 or confidence > 100:
        raise ValueError("Invalid confidence.")
    if not isinstance(value.get("supporting_sources"), list):
        raise ValueError("supporting_sources must be a list.")
