from hire_me_bot.filtering.enrollment import requires_current_enrollment


def test_currently_enrolled_mention():
    assert requires_current_enrollment("Must be currently enrolled in a degree program.")


def test_must_be_enrolled_mention():
    assert requires_current_enrollment("Candidates must be enrolled full-time.")


def test_enrolled_student_mention():
    assert requires_current_enrollment("Open to enrolled students only.")


def test_returning_to_school_mention():
    assert requires_current_enrollment("You must be returning to school after the internship.")
    assert requires_current_enrollment("Interns are expected to be returning to campus in the fall.")


def test_expected_graduation_mention():
    assert requires_current_enrollment("Expected graduation date: December 2027.")


def test_currently_pursuing_degree_mention():
    assert requires_current_enrollment("Currently pursuing a bachelor's degree in Computer Science.")


def test_regular_posting_not_flagged():
    assert not requires_current_enrollment("Software Engineer II, 0-2 years of experience.")


def test_none_and_empty_not_flagged():
    assert not requires_current_enrollment(None)
    assert not requires_current_enrollment("")
