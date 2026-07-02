from hire_me_bot.filtering.clearance import requires_clearance


def test_title_with_clearance_required_suffix():
    assert requires_clearance("Mid-Level Embedded Software Engineer (Clearance Required)")


def test_security_clearance_mention():
    assert requires_clearance("Must have an active security clearance to be considered.")


def test_ts_sci_mention():
    assert requires_clearance("The ability to obtain and maintain a TS/SCI clearance is required.")


def test_top_secret_mention():
    assert requires_clearance("Must hold a Top Secret clearance.")


def test_dod_clearance_mention():
    assert requires_clearance("Security Clearance Type: DoD Clearance: Secret")


def test_regular_title_not_flagged():
    assert not requires_clearance("Software Engineer II")


def test_none_and_empty_not_flagged():
    assert not requires_clearance(None)
    assert not requires_clearance("")


def test_no_clearance_required_is_not_flagged():
    assert not requires_clearance("No security clearance required for this role.")
    assert not requires_clearance("This position does not require a security clearance.")
