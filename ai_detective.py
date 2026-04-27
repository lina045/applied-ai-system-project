"""
AI Bug Detective — three-step agentic workflow.

Step 1 (stream_analysis): stream a live bug report
Step 2 (generate_fix):    generate a corrected version of the code
Step 3 (critique_fix):    self-critique — verify every bug was addressed
"""

import logging
import os
import re
from typing import Generator

import anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MAX_CODE_LENGTH = 5_000
MODEL = "claude-opus-4-7"

_SYSTEM_ANALYZE = (
    "You are an expert Python code reviewer. "
    "Analyze the provided code and identify ALL bugs, logic errors, and issues. "
    "Format your response as a numbered list. "
    "For each bug: state where it is, describe the problem, and explain why it breaks the code."
)

_SYSTEM_FIX = (
    "You are an expert Python developer. "
    "Given buggy code and a bug report, produce the fully corrected code. "
    "Return ONLY the fixed Python code inside a ```python code block. No prose, no explanation."
)

_SYSTEM_CRITIQUE = (
    "You are a senior code reviewer doing a final verification pass. "
    "Check whether the proposed fix correctly addresses every identified bug. "
    "Also check if any new bugs were introduced. "
    "Start your response with PASS ✅ or NEEDS REVISION ⚠️, then explain concisely."
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_code(text: str) -> str:
    """Pull code out of a markdown fence if present."""
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def validate_input(code: str) -> str | None:
    """Return an error string if the input is invalid, else None."""
    if not code or not code.strip():
        return "Please paste some Python code to analyze."
    if len(code) > MAX_CODE_LENGTH:
        return (
            f"Code is too long ({len(code):,} chars). "
            f"Maximum is {MAX_CODE_LENGTH:,} characters."
        )
    return None


# ── Agent steps ───────────────────────────────────────────────────────────────

def stream_analysis(code: str) -> Generator[str, None, None]:
    """
    Agent Step 1 — Stream a live bug analysis.

    Yields text chunks as they arrive from the API so the UI can
    display them in real time.  Logs token usage when the stream ends.
    """
    client = anthropic.Anthropic()
    logger.info("Agent Step 1: streaming bug analysis (model=%s)", MODEL)

    with client.messages.stream(
        model=MODEL,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=_SYSTEM_ANALYZE,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Find all bugs in this Python code:\n\n"
                    f"```python\n{code}\n```"
                ),
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            yield text

        final = stream.get_final_message()
        logger.info(
            "Step 1 complete — input: %d tokens, output: %d tokens",
            final.usage.input_tokens,
            final.usage.output_tokens,
        )


def generate_fix(code: str, analysis: str) -> str:
    """
    Agent Step 2 — Generate a corrected version of the code.

    Uses the bug report from Step 1 as context so the model knows
    exactly which issues to address.
    """
    client = anthropic.Anthropic()
    logger.info("Agent Step 2: generating fix (model=%s)", MODEL)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=_SYSTEM_FIX,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Original code:\n```python\n{code}\n```\n\n"
                    f"Bugs identified:\n{analysis}\n\n"
                    "Provide the fixed code:"
                ),
            }
        ],
    )

    text = next(b.text for b in response.content if b.type == "text")
    logger.info(
        "Step 2 complete — input: %d tokens, output: %d tokens",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return _extract_code(text)


def critique_fix(original: str, fixed: str, analysis: str) -> str:
    """
    Agent Step 3 — Self-critique the generated fix.

    The model verifies that every bug from the analysis was resolved
    and checks whether any new issues were introduced.
    """
    client = anthropic.Anthropic()
    logger.info("Agent Step 3: critiquing fix (model=%s)", MODEL)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_SYSTEM_CRITIQUE,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Original code:\n```python\n{original}\n```\n\n"
                    f"Bugs identified:\n{analysis}\n\n"
                    f"Proposed fix:\n```python\n{fixed}\n```\n\n"
                    "Does the fix correctly address all bugs? "
                    "Were any new issues introduced?"
                ),
            }
        ],
    )

    text = next(b.text for b in response.content if b.type == "text")
    logger.info(
        "Step 3 complete — input: %d tokens, output: %d tokens",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return text
