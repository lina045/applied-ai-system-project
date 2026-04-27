# Model Card: AI Bug Detective

## Model Overview

**System name:** AI Bug Detective  
**Base model:** `claude-opus-4-7` (Anthropic)  
**Interface:** Streamlit web app  
**Pipeline:** Three-step agentic workflow — Analyzer → Fixer → Evaluator

The system takes Python code as input and runs it through three sequential AI calls: the first streams a numbered bug report, the second generates a corrected version using that report as context, and the third self-critiques the fix and returns a PASS ✅ or NEEDS REVISION ⚠️ verdict. A human reviews all output before deciding whether to apply the fix.

---

## Intended Use

This tool is designed to help developers quickly identify and understand bugs in short Python functions. It is intended as a first-pass reviewer, not a replacement for human code review. Output should always be read and verified before use.

---

## Limitations and Biases

The model reasons about code in isolation — it has no knowledge of how a function is called, what data flows through it at runtime, or what the surrounding codebase does. Bugs that only appear under specific runtime conditions (such as race conditions or environment-dependent behavior) are unlikely to be caught.

Because `claude-opus-4-7` was trained on large amounts of public code, it tends to recognize common Python patterns very reliably and less common or domain-specific patterns less so. Niche logic may produce shallower analysis.

The Step 3 Evaluator uses the same underlying model as the Step 2 Fixer. If the model has a systematic blind spot for a particular type of error, the self-critique may not catch it — both calls reason from the same priors.

---

## Misuse Considerations

The clearest risk is submitting code you do not have the rights to share — pasting proprietary or confidential source code sends it to Anthropic's API. The app cannot enforce ownership; this is a social and organizational guardrail, not a technical one.

A secondary risk is using the tool to probe for vulnerabilities in code you intend to exploit rather than fix. The 5,000-character input cap adds friction against bulk automated use, but it is not a security boundary.

The most important mitigation is that the system never applies a fix automatically. Every result requires a human to read and decide — the AI is never the last line of defense.

---

## Testing Results

**26 out of 26 tests pass** across two test files:

- `tests/test_game_logic.py` (15 tests) — covers `reset_game`, `parse_guess`, `check_guess`, `update_score`, and the full submit flow
- `tests/test_ai_detective.py` (11 tests) — covers `validate_input` (6 cases: empty, whitespace, valid, too long, at limit, over limit) and `_extract_code` (5 cases: plain fence, python fence, no fence, multiline, prose outside fence)

The input guardrail rejects all invalid submissions before any API token is spent. All three pipeline steps log their token counts to the terminal. API errors (authentication failures, rate limits) are caught and surfaced to the user without crashing the app.

---

## AI Collaboration

**One helpful suggestion:** The AI fixer kept adding explanation around the corrected code — sentences like "Here is the fixed version:" — even when asked not to. When I described the problem, the AI suggested a two-part fix: be more explicit in the instructions, and also write a backup that strips any extra text automatically. Having that safety net meant the tool worked reliably even when the model didn't follow directions perfectly.

**One flawed suggestion:** Early on, the AI suggested a standard way to stop the game screen from showing after a player won or lost. The suggestion worked fine on its own, but it silently broke the other two tabs — they stopped rendering entirely. The AI gave advice that was correct in the most common situation but didn't account for the specific setup I was using. It was a good reminder that AI suggestions are drawn from patterns; if your situation is slightly different from the usual case, the advice can sound confident and still be wrong.

---

## What Surprised Me During Testing

I expected writing tests to confirm things I already knew were working. Instead, they kept surfacing assumptions I didn't realize I'd made. For example, I assumed that catching an empty text box and catching a box full of spaces were the same check — they're not, and only writing a test for each made that obvious. The other surprise was that the code-extraction logic handled more edge cases correctly than I expected without any extra effort, including the case where the model adds a sentence before or after the code block. Testing revealed both where the code was weaker than I thought and where it was stronger.
