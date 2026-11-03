"""One LLM call per filing: read the retrieved statement chunks, return the six figures with evidence."""

from __future__ import annotations

import json
import os
import re

import httpx

DEFAULT_MODELS = "nvidia/nemotron-3-ultra-550b-a55b:free, google/gemma-4-31b-it:free"

FIELD_HELP = {
    "revenue": "total revenue (total net sales / total revenues) for the latest fiscal year",
    "net_income": "net income attributable to the company for the latest fiscal year",
    "diluted_eps": "diluted earnings per share for the latest fiscal year",
    "total_assets": "total assets at the end of the latest fiscal year",
    "cash": "cash and cash equivalents at the end of the latest fiscal year",
    "equity": "total stockholders' (shareholders') equity attributable to the company at the end of the latest fiscal year",
}

SYSTEM = """You extract figures from excerpts of a company's annual report (Form 10-K).
Rules:
- Use only the excerpts. If a figure is not in them, return null for it.
- "value" is the number exactly as printed in the excerpt, without currency signs.
  Losses shown in parentheses are negative.
- "scale" is the unit the table states: "units", "thousands", "millions", or "billions".
  Per-share figures use "units".
- "evidence" is a short exact copy of the line the value comes from, for example
  "Total net sales | $ | 416,161 | $ | 391,035".
Reply with JSON only."""


def build_messages(company: str, fiscal_year_end: str, excerpts: list[str]) -> list[dict]:
    fields = "\n".join(f'- "{name}": {help_}' for name, help_ in FIELD_HELP.items())
    shape = ", ".join(f'"{name}": {{"value": ..., "scale": ..., "evidence": ...}}' for name in FIELD_HELP)
    body = "\n\n---\n\n".join(excerpts)
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Company: {company}. Fiscal year ended {fiscal_year_end}.\n\nFigures:\n{fields}\n\n"
                                    f"Return: {{{shape}}}\n\nExcerpts:\n\n{body}"},
    ]


def parse_json(text: str) -> dict:
    """The first {...} object in a reply, tolerating code fences and chatter around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in model reply")
    return json.loads(text[start:end + 1])


class OpenRouter:
    url = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, models: str | None = None, timeout: float = 120):
        self.models = [m.strip() for m in (models or os.getenv("OPENROUTER_MODEL") or DEFAULT_MODELS).split(",")]
        self.key = os.environ["OPENROUTER_API_KEY"]
        self.timeout = timeout

    def complete(self, messages: list[dict]) -> tuple[str, str]:
        """Returns (reply text, model that answered)."""
        payload = {"models": self.models, "messages": messages, "temperature": 0}
        response = httpx.post(self.url, json=payload, timeout=self.timeout,
                              headers={"Authorization": f"Bearer {self.key}", "X-Title": "10-K extraction eval"})
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise httpx.HTTPError(str(data["error"]))
        content = data["choices"][0]["message"].get("content") or ""
        return re.sub(r"<think>.*?</think>", "", content, flags=re.S), data.get("model", "")
