from hire_me_bot.filtering.location import is_usa_location


def test_workday_us_prefix_passes():
    assert is_usa_location("US-TX-RICHARDSON-206 ~ 1717 Cityline Dr ~ CITYLINE C17")


def test_workday_non_us_prefix_excluded():
    assert not is_usa_location("GB-PLY-PLYMOUTH-C ~ Clittaford Rd Southway ~ BLDG C")
    assert not is_usa_location("SG-01-SINGAPORE-039 CARE ~ 39 Changi N Cres")
    assert not is_usa_location("CA-QC-LONGUEUIL-J01 ~ 1000 Blvd Marie-Victorin")


def test_state_abbreviation_suffix_passes():
    assert is_usa_location("New York, NY (HQ)")
    assert is_usa_location("Austin, TX")


def test_explicit_united_states_passes():
    assert is_usa_location("Remote - United States")
    assert is_usa_location("Remote (USA)")
    assert is_usa_location("US")


def test_foreign_city_without_country_excluded():
    assert not is_usa_location("Dublin")
    assert not is_usa_location("Toronto, Canada")
    assert not is_usa_location("Singapore")


def test_missing_or_placeholder_location_excluded():
    assert not is_usa_location(None)
    assert not is_usa_location("")
    assert not is_usa_location("N/A")


def test_non_us_two_letter_code_not_mistaken_for_state():
    # QC = Quebec, not a US state -- must not match just because it's two
    # uppercase letters after a hyphen.
    assert not is_usa_location("CA-QC-Montreal")


def test_smartrecruiters_trailing_country_code_disambiguates_state_collision():
    # SmartRecruiters format "City, Region, country_code" -- the region code
    # can collide with a US state abbreviation (India's Tamil Nadu "TN" vs
    # Tennessee, Brazil's Santa Catarina "SC" vs South Carolina, Spain's
    # Madrid "MD" vs Maryland, Spain's Cataluña "CT" vs Connecticut,
    # Netherlands' Utrecht "UT" vs Utah). The lowercase trailing country
    # code must win over the state-abbreviation guess.
    assert not is_usa_location("Chennai, TN, in")
    assert not is_usa_location("Pomerode, SC, br")
    assert not is_usa_location("Madrid, MD, es")
    assert not is_usa_location("Barcelona, CT, es")
    assert not is_usa_location("Nieuwegein, UT, nl")


def test_smartrecruiters_trailing_us_country_code_still_passes():
    assert is_usa_location("Cincinnati, OH, us")
    assert is_usa_location("Des Moines, IA, us")
