from hire_me_bot.scoring.jd_extract import extract_requirements


def test_extracts_section_after_requirements_header():
    description = "About us: we build things.\n\nRequirements:\n- Python\n- SQL"
    result = extract_requirements(description)
    assert result == "- Python\n- SQL"


def test_extracts_section_after_qualifications_header():
    description = "Intro text.\n\nQualifications:\nBachelor's degree in CS."
    result = extract_requirements(description)
    assert "Bachelor's degree" in result


def test_falls_back_to_truncation_when_no_header_found():
    description = "Just a long description with no clear sections at all. " * 50
    result = extract_requirements(description)
    assert result == description[:1500]


def test_empty_description_returns_empty():
    assert extract_requirements("") == ""


def test_result_is_capped_at_fallback_length():
    description = "About us.\n\nRequirements:\n" + ("x" * 5000)
    result = extract_requirements(description)
    assert len(result) == 1500
