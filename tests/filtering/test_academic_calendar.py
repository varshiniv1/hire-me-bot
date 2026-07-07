from hire_me_bot.filtering.academic_calendar import is_summer_locked


def test_summer_year_in_title():
    assert is_summer_locked("Software Engineering Intern - Summer 2026")
    assert is_summer_locked("Software Engineering Intern - Summer 2027")


def test_summer_year_in_description():
    assert is_summer_locked("Software Engineering Intern", "This is a Summer 2026 internship program.")


def test_bare_summer_intern_with_no_year():
    assert is_summer_locked("Summer Intern - Software Engineering")
    assert is_summer_locked("Software Engineering Summer Internship")


def test_off_cycle_and_timing_variants_not_flagged():
    assert not is_summer_locked("Off-Cycle Software Engineering Intern")
    assert not is_summer_locked("Fall 2026 Software Engineering Intern")
    assert not is_summer_locked("Winter Software Engineering Intern")
    assert not is_summer_locked("Software Engineering Intern - Immediate Start")
    assert not is_summer_locked("Rolling Software Engineering Internship")
    assert not is_summer_locked("Year-round Software Engineering Internship")
    assert not is_summer_locked("2026 Software Engineering Internship")


def test_full_time_titles_not_flagged():
    assert not is_summer_locked("Software Engineer II")


def test_none_and_empty_not_flagged():
    assert not is_summer_locked(None)
    assert not is_summer_locked("", "")
