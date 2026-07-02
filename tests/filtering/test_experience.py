from hire_me_bot.filtering.experience import min_years_required, requires_too_much_experience


def test_range_starting_above_threshold_flagged():
    assert requires_too_much_experience("3-5 years of professional experience in software development")


def test_plus_years_flagged():
    assert requires_too_much_experience(
        "8+ years of software development experience, including 3+ years in a technical leadership role."
    )


def test_entry_level_range_not_flagged():
    assert not requires_too_much_experience("0-2 years of experience")
    assert not requires_too_much_experience("1-2 years of relevant experience preferred")


def test_range_upper_bound_above_cap_flagged_even_if_lower_bound_is_within_cap():
    # Strictly up to 2 years -- "1-3 years" must be rejected even though its
    # lower bound (1) is within cap, since the role is openly asking for
    # candidates up to 3 years in, not just 1.
    assert requires_too_much_experience("1-3 years of relevant experience preferred")
    assert requires_too_much_experience("2-4 years of professional experience.")
    assert requires_too_much_experience("0-3 years of experience.")


def test_no_experience_mention_not_flagged():
    assert not requires_too_much_experience("New Grad Software Engineer")
    assert not requires_too_much_experience("")
    assert not requires_too_much_experience(None)


def test_unrelated_years_mention_not_flagged():
    assert not requires_too_much_experience("Our company was founded 10 years ago.")


def test_min_years_required_extracts_all_matches():
    text = "8+ years of software development experience preferred. 2 years of Python experience required."
    assert min_years_required(text) == [8, 2]


def test_custom_max_years_threshold():
    assert not requires_too_much_experience("3-5 years of experience", max_years=5)
    assert requires_too_much_experience("3-5 years of experience", max_years=2)


def test_hyphenated_and_multi_word_phrasing_flagged():
    # Hyphens ("hands-on") and multiple words with punctuation between "of"
    # and "experience" must not break the match.
    assert requires_too_much_experience("5+ years of hands-on experience in software development")
    assert requires_too_much_experience("5+ years of hands-on, professional experience")
    assert requires_too_much_experience("Minimum of 5 years of experience")
