from hire_me_bot.filtering.citizenship import requires_citizenship


def test_us_citizenship_required_phrase():
    assert requires_citizenship("US Citizenship Required.")


def test_must_be_a_us_citizen():
    assert requires_citizenship("Must be a US Citizen to apply.")


def test_real_rtx_style_language():
    text = (
        "U.S. Citizen, U.S. Person, or Immigration Status Requirements: "
        "U.S. citizenship is required, as only U.S. citizens are eligible for a security clearance"
    )
    assert requires_citizenship(text)


def test_authorized_to_work_not_flagged():
    # Much weaker/more common requirement -- visa holders/international
    # students can satisfy this, unlike an actual citizenship requirement.
    assert not requires_citizenship("Must be authorized to work in the United States.")


def test_visa_sponsorship_language_not_flagged():
    assert not requires_citizenship("We are unable to sponsor visas at this time.")
    assert not requires_citizenship("Candidates must be eligible to work in the US without sponsorship.")


def test_regular_title_not_flagged():
    assert not requires_citizenship("Software Engineer II")


def test_none_and_empty_not_flagged():
    assert not requires_citizenship(None)
    assert not requires_citizenship("")


def test_no_citizenship_required_is_not_flagged():
    assert not requires_citizenship("No U.S. citizenship required for this role.")
    assert not requires_citizenship("This position does not require citizenship.")


def test_uscis_agency_name_reference_not_flagged():
    # E-Verify boilerplate names the agency "U.S. Citizenship and Immigration
    # Services" -- that's not a citizenship requirement, just a reference to
    # who runs E-Verify.
    assert not requires_citizenship(
        "E-Verify is an internet-based employment eligibility verification "
        "system operated by the U.S. Citizenship and Immigration Services."
    )
