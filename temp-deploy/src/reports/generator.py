"""Tiered report generation via Amazon Bedrock model routing.

- ``Standard`` tier → ``amazon.nova-lite-v1:0``
- ``Premium``  tier → ``amazon.nova-pro-v1:0`` by default, with optional Claude override
"""
from __future__ import annotations

import json
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

BEDROCK_REGION = os.environ.get(
    "BEDROCK_REGION",
    os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")),
)
STANDARD_MODEL_ID = os.environ.get(
    "STANDARD_MODEL_ID",
    os.environ.get("STANDARD_INFERENCE_PROFILE_ID", os.environ.get("NOVA_LITE_MODEL_ID", "amazon.nova-lite-v1:0")),
)
NOVA_PRO_MODEL_ID = os.environ.get("NOVA_PRO_MODEL_ID", "amazon.nova-pro-v1:0")
CHEAP_CLAUDE_MODEL_ID = os.environ.get(
    "CHEAP_CLAUDE_MODEL_ID",
    os.environ.get("PREMIUM_INFERENCE_PROFILE_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0"),
)
NOVA_LITE_MODEL_ID = os.environ.get("NOVA_LITE_MODEL_ID", STANDARD_MODEL_ID)
PREMIUM_MODEL_ID = os.environ.get(
    "PREMIUM_MODEL_ID",
    os.environ.get("CLAUDE_SONNET_MODEL_ID", NOVA_PRO_MODEL_ID),
)


def _bedrock_runtime():
    import boto3

    return boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def _invoke_nova(prompt: str, model_id: str) -> str:
    client = _bedrock_runtime()
    resp = client.invoke_model(
        modelId=model_id,
        body=json.dumps(
            {
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 4096, "temperature": 0.2},
            }
        ),
    )
    body = json.loads(resp["body"].read())
    return body["output"]["message"]["content"][0]["text"]


def _invoke_claude(prompt: str, model_id: str) -> str:
    client = _bedrock_runtime()
    resp = client.invoke_model(
        modelId=model_id,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )
    body = json.loads(resp["body"].read())
    return body["content"][0]["text"]


def _is_anthropic_model(model_id: str) -> bool:
    return "anthropic." in model_id


def _is_nova_model(model_id: str) -> bool:
    return "amazon.nova" in model_id


def _invoke_model(prompt: str, model_id: str) -> str:
    if _is_anthropic_model(model_id):
        return _invoke_claude(prompt, model_id)
    if _is_nova_model(model_id):
        return _invoke_nova(prompt, model_id)
    raise ValueError(f"Unsupported Bedrock model family for report generation: {model_id}")


def _format_model_error(model_id: str, exc: Exception) -> str:
    message = str(exc)
    if "on-demand throughput isn" in message.lower():
        return (
            f"{model_id}: {message}. Configure an inference profile via "
            "PREMIUM_INFERENCE_PROFILE_ID or STANDARD_INFERENCE_PROFILE_ID."
        )
    return f"{model_id}: {message}"


def _candidate_models(tier: str) -> list[str]:
    if tier == "Premium":
        candidates = [PREMIUM_MODEL_ID, NOVA_PRO_MODEL_ID, STANDARD_MODEL_ID]
    else:
        candidates = [STANDARD_MODEL_ID, NOVA_PRO_MODEL_ID]

    ordered: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _normalize_bullet_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip(" .")
    if not cleaned:
        return ""
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned.endswith((".", "!", "?")):
        return cleaned
    return f"{cleaned}."


def _effect_bullet(text: str, prefix: str) -> str:
    cleaned = _normalize_bullet_text(text)
    if not cleaned:
        return ""
    if cleaned.lower().startswith(prefix.lower()):
        return cleaned
    return f"{prefix} {cleaned[0].lower() + cleaned[1:]}"


def _select_news_bullets(synthesized: dict[str, Any]) -> list[str]:
    news = synthesized.get("news", {}) or {}
    ranked = news.get("ranked_articles", []) or []
    material = [item.get("text", "") for item in ranked if item.get("material")]
    contextual = [item.get("text", "") for item in ranked if not item.get("material")]

    selected: list[str] = []
    for item in material[:3]:
        bullet = _effect_bullet(item, "Material negative or high-impact news:")
        if bullet:
            selected.append(bullet)

    if not selected and contextual:
        fallback = _effect_bullet(contextual[0], "Relevant company development:")
        if fallback:
            selected.append(fallback)

    return selected


def _select_litigation_bullets(synthesized: dict[str, Any]) -> list[str]:
    litigation = synthesized.get("litigation", {}) or {}
    ranked = litigation.get("ranked_cases", []) or []
    material = [item.get("text", "") for item in ranked if item.get("material")]
    contextual = [item.get("text", "") for item in ranked if not item.get("material")]

    selected: list[str] = []
    for item in material[:3]:
        bullet = _effect_bullet(item, "Material litigation or regulatory risk:")
        if bullet:
            selected.append(bullet)

    if not selected and contextual:
        fallback = _effect_bullet(contextual[0], "Relevant legal context:")
        if fallback:
            selected.append(fallback)

    return selected


def _build_reporting_brief(synthesized: dict[str, Any]) -> dict[str, Any]:
    news = synthesized.get("news", {}) or {}
    litigation = synthesized.get("litigation", {}) or {}
    return {
        "profile_summary": synthesized.get("profile", {}).get("summary", ""),
        "material_news": news.get("material_articles", []) or [],
        "contextual_news": news.get("contextual_articles", []) or [],
        "material_litigation": litigation.get("material_cases", []) or [],
        "contextual_litigation": litigation.get("contextual_cases", []) or [],
        "leadership": synthesized.get("leadership", {}),
        "financial": synthesized.get("financial", {}),
        "sentiment_score": news.get("sentiment_score", 0.0),
        "ranked_news": news.get("ranked_articles", []) or [],
        "ranked_litigation": litigation.get("ranked_cases", []) or [],
    }


def _executive_summary_bullets(company: str, synthesized: dict[str, Any]) -> list[str]:
    profile_summary = synthesized.get("profile", {}).get("summary", "No profile summary available.")
    financial_brief = synthesized.get("financial", {}).get("corporate_brief", "")
    news_bullets = _select_news_bullets(synthesized)
    litigation_bullets = _select_litigation_bullets(synthesized)

    risk_bullets = [*litigation_bullets, *news_bullets]
    has_material_risk = bool(
        synthesized.get("news", {}).get("material_articles")
        or synthesized.get("litigation", {}).get("material_cases")
    )

    bullets = [_normalize_bullet_text(profile_summary)]
    if has_material_risk:
        bullets.extend(_normalize_bullet_text(bullet) for bullet in risk_bullets[:2])
        if financial_brief and any(term in financial_brief.lower() for term in ("pressure", "decline", "drop", "risk", "weak", "lower")):
            bullets.append(_normalize_bullet_text(financial_brief))
        return [bullet for bullet in bullets if bullet][:3]

    if news_bullets:
        bullets.append(_normalize_bullet_text(news_bullets[0]))
    elif financial_brief:
        bullets.append(_normalize_bullet_text(financial_brief))

    return [bullet for bullet in bullets if bullet][:3]


def _render_local_report(company: str, country: str, synthesized: dict[str, Any]) -> str:
    profile_summary = synthesized.get("profile", {}).get("summary", "No profile summary available.")
    news_bullets = _select_news_bullets(synthesized)
    litigation_bullets = _select_litigation_bullets(synthesized)
    executives = synthesized.get("leadership", {}).get("executives", []) or []
    product_lines = synthesized.get("leadership", {}).get("product_lines", []) or []
    financial = synthesized.get("financial", {}) or {}
    sentiment_score = synthesized.get("news", {}).get("sentiment_score", 0.0)
    summary_bullets = _executive_summary_bullets(company, synthesized)

    def _bullet_lines(items: list[str], fallback: str) -> str:
        values = items or [fallback]
        return "\n".join(f"- {_normalize_bullet_text(value) or fallback}" for value in values)

    return (
        f"# Company Intelligence Report: {company} ({country})\n\n"
        "## Executive Summary\n"
        f"\n{_bullet_lines(summary_bullets, f'{company} has no clearly material negative developments surfaced in the current news and legal data.')}\n\n"
        "## Profile\n"
        f"\n- {_normalize_bullet_text(profile_summary)}\n\n"
        "## Leadership\n"
        f"\n{_bullet_lines(executives, 'No material executive changes in the current data.')}\n\n"
        "### Product Lines\n"
        f"\n{_bullet_lines(product_lines, 'No major product-line updates in the current data.')}\n\n"
        "## Financial Performance\n"
        f"\n- {_normalize_bullet_text(f"Ticker {financial.get('ticker', 'N/A')} is trading at {financial.get('share_price', 'N/A')}.")}\n"
        f"- {_normalize_bullet_text(f"Five-year CAGR is {financial.get('cagr_5y', 'N/A')}.")}\n"
        f"- {_normalize_bullet_text(financial.get('corporate_brief', 'No additional financial brief available.'))}\n\n"
        "## News & Sentiment\n"
        f"\n- {_normalize_bullet_text(f"Sentiment score is {sentiment_score}.")}\n"
        f"{_bullet_lines(news_bullets, 'No material negative or high-impact news was identified in the current data.')}\n\n"
        "## Litigation\n"
        f"\n{_bullet_lines(litigation_bullets, 'No material litigation or regulatory issues were identified in the current data.')}\n\n"
        "## Risks & Opportunities\n"
        "\n### Risks\n"
        f"- {_normalize_bullet_text((litigation_bullets or ['Litigation and regulatory scrutiny could affect reputation and execution.'])[0])}\n"
        f"- {_normalize_bullet_text((news_bullets or ['Adverse or high-impact news could affect market perception and execution discipline.'])[0])}\n\n"
        "### Opportunities\n"
        "- Product innovation and software-led differentiation remain important growth levers.\n"
        "- Continued demand and market visibility can still support expansion when legal and reputational risks remain contained.\n"
    )


def _build_prompt(company: str, country: str, synthesized: dict[str, Any]) -> str:
    reporting_brief = _build_reporting_brief(synthesized)
    return (
        f"Generate an executive-grade company intelligence report for {company} ({country}).\n"
        "Write polished business-style markdown for an executive audience. "
        "Use clear headings with a blank line after each heading. "
        "Under each major heading, use short bullet points rather than long paragraphs. "
        "Keep bullets concise, informative, and readable, and ensure each bullet is a complete sentence. "
        "Do not mention raw JSON, missing fields, or data-pipeline mechanics. "
        "Synthesize the evidence into readable prose and keep the tone confident, neutral, and analytical. "
        "In the News section, prioritize only negative, adverse, regulatory, reputational, or otherwise high-impact developments first. "
        "Only include other relevant company news when there are no clearly material negative developments or when it adds essential context. "
        "In the Litigation section, focus on active legal, regulatory, enforcement, or settlement risk and explain the business effect when possible. "
        "Avoid generic filler and avoid listing neutral headlines unless they materially change the business outlook. "
        "If there are any material negative news or litigation items, the Executive Summary must not mention positive developments, expansion, launches, or opportunities. "
        "When material risks exist, order the report hierarchy as: litigation risk, negative or high-impact news, financial pressure, then only lower-priority contextual positives if needed outside the Executive Summary. "
        "If the reporting brief contains any material_news items, do not include contextual_news in the Executive Summary, News & Sentiment, or Risks sections. "
        "If the reporting brief contains any material_litigation items, do not dilute them with minor legal context. "
        "Treat the reporting brief below as the authoritative prioritization layer over the raw source JSON.\n"
        "Use this structure exactly:\n"
        "# Executive Intelligence Report: <Company> (<Country>)\n"
        "## Executive Summary\n"
        "- bullet\n"
        "- bullet\n"
        "## Profile\n"
        "- bullet\n"
        "## Leadership\n"
        "- bullet\n"
        "### Product Lines\n"
        "- bullet\n"
        "## Financial Performance\n"
        "- bullet\n"
        "## News & Sentiment\n"
        "- bullet\n"
        "## Litigation\n"
        "- bullet\n"
        "## Risks & Opportunities\n"
        "### Risks\n"
        "- bullet\n"
        "### Opportunities\n"
        "- bullet\n\n"
        f"Reporting brief (authoritative prioritization):\n{json.dumps(reporting_brief, default=str, indent=2)}\n\n"
        f"Source data (JSON):\n{json.dumps(synthesized, default=str, indent=2)}"
    )


def generate_report(
    *, tier: str, company: str, country: str, synthesized: dict[str, Any]
) -> dict[str, Any]:
    prompt = _build_prompt(company, country, synthesized)
    warnings: list[str] = []
    text: str | None = None
    model_used: str | None = None

    for model_id in _candidate_models(tier):
        try:  # pragma: no cover — requires AWS creds
            text = _invoke_model(prompt, model_id)
            model_used = model_id
            break
        except Exception as exc:
            logger.warning("Report generation failed for %s: %s", model_id, exc)
            warnings.append(_format_model_error(model_id, exc))

    if text is None or model_used is None:
        model_used = "local-template"
        text = _render_local_report(company, country, synthesized)

    response = {
        "tier": tier,
        "model": model_used,
        "company": company,
        "country": country,
        "markdown": text,
    }
    if warnings:
        response["warnings"] = warnings
    return response
