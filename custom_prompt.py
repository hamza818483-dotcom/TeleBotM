from typing import Optional


def build_custom_prompt(user_prompt: str, desired_count: Optional[int] = None) -> str:
    """
    Build a strict prompt for Gemini that instructs it to generate Bengali MCQs
    based on the given user prompt and the attached textbook image.

    Requirements enforced:
    - Output MUST be valid JSON array of question objects (no markdown code fences)
    - Each question in Bangla, 4 options, one correct answer index, and Bengali explanation
    - Preserve structure consistent with existing quiz format used by the bot
    """
    user_prompt = (user_prompt or "").strip()

    count_line = (
        f"Create exactly {desired_count} high-quality questions when content allows; "
        f"if the material is insufficient, return as many as possible without guessing."
        if desired_count
        else "Create 4 to 6 high-quality questions if content allows; fewer is acceptable when material is limited."
    )

    base_instructions = f"""
You are a professional Bengali question setter. Carefully read the provided image
(a textbook page) and generate high‑quality multiple choice questions in Bengali
following the user's intent below. The user's intent can specify style, difficulty,
topic focus, or format hints.

USER INTENT:
{user_prompt}

STRICT OUTPUT RULES:
1) Output ONLY valid JSON (UTF‑8), no backticks, no markdown, no commentary
2) JSON MUST be an array where each element has exactly these fields:
   - "question_description": string (Bengali)
   - "options": array of exactly 4 strings (Bengali)
   - "correct_answer_index": integer 0..3
   - "correct_option": one of "A","B","C","D" (consistent with index)
   - "explanation": short Bengali explanation (≤ 165 chars)
3) Keep questions concise and unambiguous. Avoid copying irrelevant text from the image.
4) {count_line}
5) Never include any external links or metadata in the explanation.

QUALITY NOTES:
- Prefer curriculum‑accurate facts; when uncertain, skip rather than guess.
- If the user intent suggests True/False or other styles, still return 4 options
  where two options act as distractors. Keep correctness unique.
"""
    return base_instructions.strip()


def build_custom_text_prompt(user_prompt: str, source_text: str, desired_count: Optional[int] = None) -> str:
    """
    Build a strict prompt for Gemini that instructs it to generate Bengali MCQs
    directly from user-provided textual material (no images).
    """
    user_prompt = (user_prompt or "").strip()
    source_text = (source_text or "").strip()
    if len(source_text) > 6000:
        source_text = source_text[:6000]
    instructions = user_prompt or "Generate exam-ready Bengali MCQs that cover the provided study text."

    count_line = (
        f"Create exactly {desired_count} uniquely worded MCQs whenever the reference text supports it; "
        f"otherwise return as many as possible without inventing facts."
        if desired_count
        else "Create 4‑6 MCQs when possible; fewer is acceptable if the reference text is limited."
    )

    base_instructions = f"""
You are a professional Bengali question setter. Carefully study the reference
text below and generate high-quality multiple choice questions in Bengali that
capture the most important facts. Follow any stylistic hints in the user intent.

USER INTENT / STYLE GUIDE:
{instructions}

REFERENCE TEXT (ONLY SOURCE OF TRUTH):
<<<TEXT_START
{source_text}
TEXT_END>>>

STRICT OUTPUT RULES:
1) Output ONLY valid JSON (UTF-8). No backticks, markdown, or commentary.
2) JSON MUST be an array where each element has exactly these fields:
   - "question_description": string (Bengali)
   - "options": array of exactly 4 strings (Bengali)
   - "correct_answer_index": integer 0..3
   - "correct_option": one of "A","B","C","D" (consistent with index)
   - "explanation": short Bengali explanation (≤ 165 chars)
3) Never copy the question text verbatim; paraphrase while keeping meaning intact.
4) Only use information that appears inside the reference text.
5) {count_line}
6) Never include URLs or external links in explanations.
"""
    return base_instructions.strip()


