import json

from anthropic import Anthropic

from hire_me_bot import settings

_client: Anthropic | None = None

_SCORE_TOOL = {
    "name": "record_score",
    "description": "Record a 1-5 fit score for a single job posting.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["score"],
    },
}

_BATCH_SCORE_TOOL = {
    "name": "record_scores",
    "description": "Record a 1-5 fit score for every posting in the batch.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "posting_id": {"type": "integer"},
                        "score": {"type": "integer", "minimum": 1, "maximum": 5},
                    },
                    "required": ["posting_id", "score"],
                },
            }
        },
        "required": ["scores"],
    },
}


def get_client() -> Anthropic:
    global _client
    if _client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY must be set to use Claude scoring.")
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def score_posting(profile: dict, company: str, title: str, jd_snippet: str) -> int:
    prompt = (
        f"Candidate profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Job posting:\nCompany: {company}\nTitle: {title}\nRequirements: {jd_snippet}\n\n"
        "Rate how well this posting fits the candidate's profile on a 1-5 scale "
        "(1 = poor fit, 5 = excellent fit). Call record_score with your rating."
    )
    resp = get_client().messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=200,
        tools=[_SCORE_TOOL],
        tool_choice={"type": "tool", "name": "record_score"},
        messages=[{"role": "user", "content": prompt}],
    )
    tool_use = next(block for block in resp.content if block.type == "tool_use")
    return int(tool_use.input["score"])


def score_batch(profile: dict, items: list[dict]) -> dict[int, int]:
    postings_block = "\n\n".join(
        f"posting_id: {item['posting_id']}\n"
        f"Company: {item['company']}\n"
        f"Title: {item['title']}\n"
        f"Requirements: {item['jd_snippet']}"
        for item in items
    )
    prompt = (
        f"Candidate profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Job postings:\n{postings_block}\n\n"
        "Rate how well EACH posting fits the candidate's profile on a 1-5 scale "
        "(1 = poor fit, 5 = excellent fit). Call record_scores with exactly one "
        "entry per posting_id listed above."
    )
    resp = get_client().messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=200 * len(items) + 200,
        tools=[_BATCH_SCORE_TOOL],
        tool_choice={"type": "tool", "name": "record_scores"},
        messages=[{"role": "user", "content": prompt}],
    )
    tool_use = next(block for block in resp.content if block.type == "tool_use")
    return {int(entry["posting_id"]): int(entry["score"]) for entry in tool_use.input["scores"]}
