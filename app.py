import random
import os

import anthropic
import streamlit as st
from dotenv import load_dotenv

from ai_detective import stream_analysis, generate_fix, critique_fix, validate_input

load_dotenv()


# ── Game logic (module-level so tests can import them) ────────────────────────

def get_range_for_difficulty(difficulty: str):
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 50
    return 1, 100


def parse_guess(raw: str):
    if raw is None:
        return False, None, "Enter a guess."
    if raw == "":
        return False, None, "Enter a guess."
    try:
        if "." in raw:
            value = int(float(raw))
        else:
            value = int(raw)
    except Exception:
        return False, None, "That is not a number."
    return True, value, None


def check_guess(guess, secret):
    if guess == secret:
        return "Win", "🎉 Correct!"
    try:
        if guess > secret:
            return "Too High", "📉 Go LOWER!"
        else:
            return "Too Low", "📈 Go HIGHER!"
    except TypeError:
        g = str(guess)
        if g == secret:
            return "Win", "🎉 Correct!"
        if g > secret:
            return "Too High", "📉 Go LOWER!"
        return "Too Low", "📈 Go HIGHER!"


def update_score(current_score: int, outcome: str, attempt_number: int):
    if outcome == "Win":
        points = 100 - 10 * (attempt_number + 1)
        if points < 10:
            points = 10
        return current_score + points
    if outcome == "Too High":
        if attempt_number % 2 == 0:
            return current_score + 5
        return current_score - 5
    if outcome == "Too Low":
        return current_score - 5
    return current_score


# ── Sample buggy code snippets for the detective tab ─────────────────────────

SAMPLES = {
    "Backwards hints (from this project!)": """\
def check_guess(guess, secret):
    \"\"\"Return (outcome, hint_message) for a number guessing game.\"\"\"
    if guess == secret:
        return "Win", "Correct!"
    if guess > secret:
        return "Too Low", "Go HIGHER!"
    else:
        return "Too High", "Go LOWER!"
""",
    "Broken leaderboard": """\
def add_to_leaderboard(name, score, board):
    \"\"\"Add a score and return the top-5 leaderboard.\"\"\"
    board.append({"name": name, "score": score})
    board.sort(key=lambda x: x["score"])
    return board[:5]

def player_rank(name, board):
    \"\"\"Return the 1-based rank of a player (1 = best).\"\"\"
    for i in range(len(board)):
        if board[i]["name"] == name:
            return i
    return -1
""",
    "Score calculator": """\
def calculate_bonus(attempts, max_attempts):
    \"\"\"Bonus points: more points for fewer attempts.\"\"\"
    if attempts == max_attempts:
        return 0
    ratio = (max_attempts - attempts) / max_attempts
    return ratio * 100

def clamp_score(score):
    \"\"\"Keep score in [0, 1000].\"\"\"
    if score > 1000:
        score == 1000
    if score < 0:
        score == 0
    return score
""",
}


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Code Tools", page_icon="🎮")

tab_game, tab_detective, tab_diagram = st.tabs(
    ["🎮 Glitchy Guesser", "🕵️ AI Bug Detective", "📊 System Diagram"]
)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Guessing Game (original project, preserved)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_game:
    st.title("🎮 Game Glitch Investigator")
    st.caption("An AI-generated guessing game. Something is off.")

    st.sidebar.header("Game Settings")
    difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)

    attempt_limit_map = {"Easy": 6, "Normal": 8, "Hard": 5}
    attempt_limit = attempt_limit_map[difficulty]
    low, high = get_range_for_difficulty(difficulty)

    st.sidebar.caption(f"Range: {low} to {high}")
    st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

    for key, default in [
        ("secret", random.randint(low, high)),
        ("attempts", 1),
        ("score", 0),
        ("status", "playing"),
        ("history", []),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    with st.expander("Developer Debug Info"):
        st.write("Secret:", st.session_state.secret)
        st.write("Attempts:", st.session_state.attempts)
        st.write("Score:", st.session_state.score)
        st.write("Difficulty:", difficulty)
        st.write("History:", st.session_state.history)

    show_hint = st.checkbox("Show hint", value=True)

    if st.session_state.status != "playing":
        if st.session_state.status == "won":
            st.success("You already won. Start a new game to play again.")
        else:
            st.error("Game over. Start a new game to try again.")
        if st.button("New Game 🔁", key="new_game_over"):
            for k, v in [
                ("attempts", 0),
                ("secret", random.randint(1, 100)),
                ("status", "playing"),
                ("history", []),
            ]:
                st.session_state[k] = v
            st.rerun()
    else:
        st.subheader("Make a guess")
        st.info(
            f"Guess a number between 1 and 100. "
            f"Attempts left: {attempt_limit - st.session_state.attempts}"
        )

        with st.form("guess_form"):
            raw_guess = st.text_input(
                "Enter your guess:", key=f"guess_input_{difficulty}"
            )
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Submit Guess 🚀")
            with col2:
                new_game = st.form_submit_button("New Game 🔁")

        if new_game:
            for k, v in [
                ("attempts", 0),
                ("secret", random.randint(1, 100)),
                ("status", "playing"),
                ("history", []),
            ]:
                st.session_state[k] = v
            st.success("New game started.")
            st.rerun()

        if submit:
            st.session_state.attempts += 1
            ok, guess_int, err = parse_guess(raw_guess)

            if not ok:
                st.session_state.history.append(raw_guess)
                st.error(err)
            else:
                st.session_state.history.append(guess_int)
                outcome, message = check_guess(guess_int, st.session_state.secret)

                if show_hint:
                    st.warning(message)

                st.session_state.score = update_score(
                    current_score=st.session_state.score,
                    outcome=outcome,
                    attempt_number=st.session_state.attempts,
                )

                if outcome == "Win":
                    st.balloons()
                    st.session_state.status = "won"
                    st.success(
                        f"You won! The secret was {st.session_state.secret}. "
                        f"Final score: {st.session_state.score}"
                    )
                elif st.session_state.attempts >= attempt_limit:
                    st.session_state.status = "lost"
                    st.error(
                        f"Out of attempts! "
                        f"The secret was {st.session_state.secret}. "
                        f"Score: {st.session_state.score}"
                    )

    st.divider()
    st.caption("Built by an AI that claims this code is production-ready.")


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 2 — AI Bug Detective
# ═══════════════════════════════════════════════════════════════════════════════

with tab_detective:
    st.title("🕵️ AI Bug Detective")
    st.caption(
        "A three-step agentic AI pipeline: **analyze bugs → generate fix → verify the fix.**"
    )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error(
            "**ANTHROPIC_API_KEY is not set.**\n\n"
            "Create a `.env` file in this directory:\n"
            "```\nANTHROPIC_API_KEY=your_key_here\n```\n"
            "Then restart the Streamlit app."
        )
    else:
        with st.expander("How does this work?"):
            st.markdown(
                """
This tool runs **Claude claude-opus-4-7** as a three-step agent:

| Step | What the agent does |
|------|---------------------|
| **1 — Analyze** | Streams a live bug report directly from the model as it reasons |
| **2 — Fix** | Uses the bug report as context to generate a corrected version of the code |
| **3 — Critique** | Reviews its own fix and flags anything still wrong or newly broken |

Each step uses **adaptive thinking** (`thinking: {type: "adaptive"}`), which lets the model
decide how deeply to reason before responding. All three calls are logged to the terminal.
"""
            )

        sample_choice = st.selectbox(
            "Load a sample (or paste your own below):",
            ["— paste your own code —"] + list(SAMPLES.keys()),
        )
        default_code = SAMPLES.get(sample_choice, "")

        code_input = st.text_area(
            "Python code to analyze:",
            value=default_code,
            height=260,
            placeholder="Paste Python code here…",
        )

        analyze_btn = st.button("🔍 Analyze Code", type="primary")

        if analyze_btn:
            input_err = validate_input(code_input)
            if input_err:
                st.error(input_err)
            else:
                # ── Step 1: stream analysis ───────────────────────────────────
                st.subheader("Step 1 — Bug Analysis")
                st.caption("Streaming live from the model…")
                analysis_slot = st.empty()
                analysis_text = ""

                try:
                    for chunk in stream_analysis(code_input):
                        analysis_text += chunk
                        analysis_slot.markdown(analysis_text + "▌")
                    analysis_slot.markdown(analysis_text)
                except anthropic.AuthenticationError:
                    st.error("Invalid API key — double-check your ANTHROPIC_API_KEY.")
                    analysis_text = ""
                except anthropic.RateLimitError:
                    st.error("Rate limit reached. Wait a moment and try again.")
                    analysis_text = ""
                except Exception as exc:
                    st.error(f"Analysis error: {exc}")
                    analysis_text = ""

                if analysis_text:
                    # ── Step 2: generate fix ──────────────────────────────────
                    st.subheader("Step 2 — Fixed Code")
                    fixed_code = None
                    with st.spinner("Generating fix…"):
                        try:
                            fixed_code = generate_fix(code_input, analysis_text)
                        except Exception as exc:
                            st.error(f"Fix generation error: {exc}")

                    if fixed_code:
                        st.code(fixed_code, language="python")

                        # ── Step 3: critique ──────────────────────────────────
                        st.subheader("Step 3 — Quality Check")
                        critique = None
                        with st.spinner("Verifying fix…"):
                            try:
                                critique = critique_fix(
                                    code_input, fixed_code, analysis_text
                                )
                            except Exception as exc:
                                st.error(f"Critique error: {exc}")

                        if critique:
                            st.markdown(critique)
                            st.success("Pipeline complete — all three agent steps finished.")


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 3 — System Diagram
# ═══════════════════════════════════════════════════════════════════════════════

with tab_diagram:
    st.title("📊 System Diagram")
    st.caption("How data flows through the AI Bug Detective pipeline.")

    import streamlit.components.v1 as components

    _DIAGRAM = """
flowchart TD
    User([\"👤 User\\npastes Python code\"])
    Validator[\"🛡️ Input Validator\\nGuardrail: checks length and empty\"]
    Err[\"⚠️ Error message\\nreturned to user\"]

    subgraph Agent [\"Agentic Workflow — claude-opus-4-7 + adaptive thinking\"]
        Step1[\"🔍 Step 1 · Analyzer\\nStreams a live bug report\"]
        Step2[\"🔧 Step 2 · Fixer\\nGenerates corrected code\"]
        Step3[\"🎯 Step 3 · Evaluator\\nSelf-critiques the fix\"]
    end

    Results[\"📋 Results\\nBug list · Fixed code · Verdict\"]
    Human([\"👤 Human Review\\nUser reads output and decides\\nwhether to apply the fix\"])
    Tests[\"🧪 pytest — 26 tests\\nparse_guess · check_guess · update_score · reset_game\\nvalidate_input · _extract_code\"]

    User --> Validator
    Validator -- \"invalid input\" --> Err
    Validator -- \"valid code\" --> Step1
    Step1 -- \"bug report\" --> Step2
    Step2 -- \"fixed code\" --> Step3
    Step3 -- \"verdict\" --> Results
    Results --> Human
    Tests -. \"automated regression\\nchecks on game logic\" .-> Human

    style Step1 fill:#dbeafe
    style Step2 fill:#dbeafe
    style Step3 fill:#dbeafe
    style Tests fill:#fef9c3
    style Human fill:#dcfce7
"""

    components.html(
        f"""
        <script type="module">
          import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
          mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
        </script>
        <div class="mermaid" style="font-size:14px; padding:12px;">
        {_DIAGRAM}
        </div>
        """,
        height=620,
    )

    st.markdown("---")
    st.markdown(
        """
**Component key**

| Component | Role |
|-----------|------|
| 🛡️ Input Validator | Guardrail — rejects empty or oversized input before any API call |
| 🔍 Analyzer (Step 1) | Agent — streams a numbered bug report from the model in real time |
| 🔧 Fixer (Step 2) | Agent — uses the bug report as context to produce corrected code |
| 🎯 Evaluator (Step 3) | Agent — self-critiques the fix; outputs PASS ✅ or NEEDS REVISION ⚠️ |
| 👤 Human Review | Trust layer — the user decides whether to accept and apply the fix |
| 🧪 pytest | Automated testing — 26 tests cover game logic, input validation, and code extraction |
"""
    )
