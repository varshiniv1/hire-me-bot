from hire_me_bot.filtering.keywords import is_internship_title, passes_keyword_filter


def test_internship_title_passes():
    assert passes_keyword_filter("Software Engineering Intern - Summer 2026")


def test_new_grad_title_passes():
    assert passes_keyword_filter("New Grad Software Engineer")


def test_generic_swe_title_passes():
    assert passes_keyword_filter("Software Engineer I")


def test_senior_title_excluded():
    assert not passes_keyword_filter("Senior Software Engineer")


def test_staff_title_excluded_even_with_intern_word():
    assert not passes_keyword_filter("Staff Software Engineer, Internship Program Lead")


def test_unrelated_title_fails():
    assert not passes_keyword_filter("Sales Account Executive")


def test_internal_word_is_not_a_false_positive_for_intern():
    assert not passes_keyword_filter("Internal Auditor - APAC Regulatory")


def test_head_of_exclusion_does_not_false_positive_on_overhead():
    assert not passes_keyword_filter("Overhead Crane Operator")


def test_developer_relations_excluded():
    assert not passes_keyword_filter("Developer Relations")


def test_developer_advocate_excluded():
    assert not passes_keyword_filter("Developer Advocate")


def test_non_tech_internship_excluded():
    # Real example from a live run: CVS Health's pharmacy internships matched
    # the old filter purely on the word "Intern", with zero tech signal.
    assert not passes_keyword_filter("Pharmacy Intern")
    assert not passes_keyword_filter("Foreign Pharmacy Grad - International Pharmacy Intern")


def test_non_tech_new_grad_excluded():
    assert not passes_keyword_filter("Operations Associate, New Grad (Mexico)")


def test_bare_campus_term_excluded():
    assert not passes_keyword_filter("Campus Recruiter")


def test_data_engineer_excluded():
    # Narrowed to SWE/SDE roles only -- Data Engineer no longer qualifies.
    assert not passes_keyword_filter("Data Engineer, New Grad")


def test_machine_learning_engineer_excluded():
    assert not passes_keyword_filter("Machine Learning Engineer, New Grad")


def test_bare_programmer_excluded():
    # Real false positive from a live run: CNC/manufacturing programming,
    # not software.
    assert not passes_keyword_filter("CAM Programmer (Contract)")


def test_sdet_passes():
    assert passes_keyword_filter("SDET Intern")


def test_sde_passes():
    assert passes_keyword_filter("SDE New Grad")


def test_bare_developer_title_passes():
    # Functionally the same job as SWE/SDE at most companies even without
    # the word "software" in the title.
    assert passes_keyword_filter("Backend Developer Intern")
    assert passes_keyword_filter(".NET Developer New Grad")


def test_empty_title_fails():
    assert not passes_keyword_filter("")


def test_is_internship_title():
    assert is_internship_title("Software Engineering Intern - Summer 2026")
    assert is_internship_title("Backend Developer Co-op")
    assert is_internship_title("SWE Coop")
    assert not is_internship_title("New Grad Software Engineer")
    assert not is_internship_title("Software Engineer I")
    assert not is_internship_title("")
