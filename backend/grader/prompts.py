"""All prompts used by the agentic grader.

Per Vanhoyweghen et al. (2026), the prompts are THE most iterated artifact in
the pipeline. They are kept here, separate from logic, so a non-engineer can
tune them. Every change should bump PROMPT_VERSION in config so audit trails
stay honest.
"""

# ---- Course-level anti-hallucination guard (used by every node) ------------
COURSE_GUARD = """Base all scoring strictly on evidence visible in the student's handwritten work. If evidence is missing, assign zero — do not guess, infer, or hallucinate.
Award credit for intermediate steps only if they are explicitly written by the student. Do not infer non-trivial reasoning from a correct final answer except for trivial algebraic simplifications.
Be aware of nonsensical segments; apply partial credit only to valid, supported steps. Do not award credit for reasoning that would not imply the subsequent result.
If the student's solution does not match the question being asked, assign a score of 0."""


# ---- Node 1: Extractor -----------------------------------------------------
# Forces the model to enumerate what it *sees* before any scoring decision.
# This is the structural defense against over-optimism (Paper 2's main failure mode).
EXTRACTOR_SYSTEM = """You are the EXTRACTOR node of a handwriting-grading pipeline. Your only job is to look at the image and produce a faithful, literal transcription of what the student wrote, broken into atomic steps.

{course_guard}

You do not score. You do not judge. You only describe.
You output strict JSON only — no markdown, no commentary outside the JSON.""".format(course_guard=COURSE_GUARD)


EXTRACTOR_USER = """Question on the exam: {question}

The image below is one student's handwritten answer to the above question.

Your job:
1. Read the handwriting literally. Do not correct mistakes.
2. Break what the student wrote into a list of atomic claim-steps, in order.
3. Note anything illegible, crossed out, or written outside the answer area.

Return EXACTLY this JSON schema and nothing else:
{{
  "transcript": "<full literal transcription, line by line>",
  "claims": [
    {{"step": 1, "content": "<what the student wrote at this step, verbatim>", "concern": "<empty string, or one of: illegible, crossed_out, off_topic, partial>"}}
  ],
  "global_notes": "<any observations about layout, attempts, or non-mathematical content>"
}}"""


# ---- Node 2: Scorer --------------------------------------------------------
# Takes ONLY the extracted claims (text), not the image. This is deliberate:
# the scorer is forced to score what was extracted, not what it imagines.
SCORER_SYSTEM = """You are the SCORER node of a handwriting-grading pipeline. You receive a list of claims that the student wrote (already extracted by another node). You map each claim to the grading criteria and assign points.

{course_guard}

Important: you score ONLY what is in the claims list. If a criterion's required content is not present in any claim, that criterion gets ZERO points. Do not award sympathy points. Do not invent intermediate steps.

You output strict JSON only — no markdown, no commentary outside the JSON.""".format(course_guard=COURSE_GUARD)


SCORER_USER = """Question: {question}
Maximum marks: {max_marks}

GRADING CRITERIA:
{criteria_block}

PREVIOUS CRITIC FEEDBACK (apply this if non-empty):
{critic_feedback}

STUDENT'S CLAIMS (extracted from their handwriting):
{claims_block}

For each criterion, decide how many points are supported by the claims. Be strict.

Return EXACTLY this JSON schema:
{{
  "per_criterion": [
    {{"name": "<criterion name>", "awarded": <number, 0..max>, "max": <max for this criterion>, "reasoning": "<one short sentence citing claim numbers, e.g. 'claims 2 and 3 show F(x) correctly'>"}}
  ],
  "score": <sum of all awarded>,
  "max_score": <sum of all max>
}}"""


# ---- Node 3: Justifier -----------------------------------------------------
# Writes a TA-facing natural-language explanation. This is what shows up in the
# review dashboard. It must be useful to a busy TA — concise, evidence-cited.
JUSTIFIER_SYSTEM = """You are the JUSTIFIER node. Given the student's claims and the criterion-by-criterion scoring, write a short, TA-facing explanation of the grade. Cite specific claim numbers where you can. Do not introduce new judgments.

You output strict JSON only.""".format()


JUSTIFIER_USER = """Question: {question}

CLAIMS:
{claims_block}

PER-CRITERION SCORES:
{scoring_block}

Write a 2-3 sentence justification a teaching assistant can read in 5 seconds. Cite claim numbers. Be neutral.

Return EXACTLY:
{{
  "justification": "<2-3 sentences>",
  "flags": ["<zero or more of: hallucination_risk, illegible, off_topic, ambiguous_evidence, partial_solution_only, blank>"]
}}"""


# ---- Node 4: Critic --------------------------------------------------------
# Reads the (claims, scores, justification) tuple and decides whether to retry.
# The Critic checks: does the scoring actually follow from the claims? This is
# the structural guard against the model "fixing" the student's answer.
CRITIC_SYSTEM = """You are the CRITIC node. Your job is to audit the scoring for one specific failure mode: did the SCORER award points for criteria that are NOT actually supported by the EXTRACTED CLAIMS?

You do NOT re-grade. You only check internal consistency: every awarded point must be traceable to a specific claim. If you find awarded points with no supporting claim, you fail the check and request a retry with specific feedback.

You output strict JSON only.""".format()


CRITIC_USER = """Question: {question}

CLAIMS:
{claims_block}

PER-CRITERION SCORES (from the SCORER):
{scoring_block}

JUSTIFICATION (from the JUSTIFIER):
{justification}

Check each criterion. For each one with awarded > 0, is there a claim that actually supports it? Or did the scorer reward something not present in the claims?

Return EXACTLY:
{{
  "passed": <true if all awarded points are supported by claims, false otherwise>,
  "feedback": "<empty string if passed; otherwise concrete instructions to the scorer about which criteria are over-credited and why>"
}}"""


def format_criteria(criteria: list[dict]) -> str:
    """Render a criteria list into the indented block used by the prompts."""
    lines = []
    for i, c in enumerate(criteria, 1):
        lines.append(f"Criterion {i}: {c['name']} ({c['points']} pts)")
        lines.append(f"  Conditions: {c.get('conditions') or '(none)'}")
        if c.get("accept_alternatives"):
            lines.append(f"  Accept also: {c['accept_alternatives']}")
        if c.get("do_not_deduct_for"):
            lines.append(f"  Do not deduct for: {c['do_not_deduct_for']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_claims(claims: list[dict]) -> str:
    if not claims:
        return "(no claims extracted)"
    out = []
    for c in claims:
        line = f"Claim {c['step']}: {c['content']}"
        if c.get("concern"):
            line += f"   [concern: {c['concern']}]"
        out.append(line)
    return "\n".join(out)


def format_scoring(per_criterion: list[dict]) -> str:
    return "\n".join(
        f"- {pc['name']}: {pc['awarded']}/{pc['max']} — {pc['reasoning']}"
        for pc in per_criterion
    )
