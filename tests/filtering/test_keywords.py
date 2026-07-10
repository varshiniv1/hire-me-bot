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


def test_sales_title_naming_a_software_product_excluded():
    # Real live example (Bosch): a sales role, not engineering, but
    # otherwise passes via the bare "software" TECH_TERM because the title
    # names a software product line.
    assert not passes_keyword_filter("Sales Executive - Mobility Software & Services")


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


def test_backend_frontend_fullstack_developer_titles_pass():
    assert passes_keyword_filter("Backend Developer Intern")
    assert passes_keyword_filter("Frontend Developer, New Grad")
    assert passes_keyword_filter("Full Stack Developer")
    assert passes_keyword_filter("Full-Stack Engineer, New Grad")


def test_bare_developer_title_excluded():
    # Narrowed to Software Engineer/SRE/Production Engineer/Backend/
    # Frontend/Full-Stack roles only -- a bare "Developer" title without one
    # of those signals (e.g. tied to a specific non-general-purpose platform)
    # no longer qualifies on its own.
    assert not passes_keyword_filter(".NET Developer New Grad")
    assert not passes_keyword_filter("Salesforce Developer")
    assert not passes_keyword_filter("ServiceNow Developer")
    assert not passes_keyword_filter("React Developer")
    assert not passes_keyword_filter("Database Developer")


def test_sre_and_production_engineer_titles_pass():
    assert passes_keyword_filter("Site Reliability Engineer I")
    assert passes_keyword_filter("SRE, New Grad")
    assert passes_keyword_filter("Production Engineer")
    assert passes_keyword_filter("Production Engineering, Entry Level")


def test_lead_and_leader_titles_excluded():
    assert not passes_keyword_filter("Lead Software Engineer")
    assert not passes_keyword_filter("Software Engineering Technical Leader")
    assert not passes_keyword_filter("Leader, Software Engineering")


def test_embedded_and_firmware_titles_excluded():
    assert not passes_keyword_filter("Embedded Software Engineer")
    assert not passes_keyword_filter("Embedded Software Engineer II")
    assert not passes_keyword_filter("Firmware Engineer, New Grad")
    assert not passes_keyword_filter("Embedded Systems Software Developer")


def test_scientific_software_titles_excluded():
    assert not passes_keyword_filter("Scientific Software Engineer - Compiler")
    assert not passes_keyword_filter("Scientific Software Engineer - Virtual Machine & Emulation")


def test_engineer_level_iii_and_up_excluded():
    assert not passes_keyword_filter("Software Engineer III, Forward Deployed")
    assert not passes_keyword_filter("SDE IV")
    assert not passes_keyword_filter("Software Engineer (L3)")
    assert not passes_keyword_filter("Software Engineer, Level 5")


def test_engineer_level_i_and_ii_still_pass():
    assert passes_keyword_filter("Software Engineer I")
    assert passes_keyword_filter("Software Engineer II - App Core (Remote Eligible)")
    assert passes_keyword_filter("Software Engineer (L1)")


def test_empty_title_fails():
    assert not passes_keyword_filter("")


def test_is_internship_title():
    assert is_internship_title("Software Engineering Intern - Summer 2026")
    assert is_internship_title("Backend Developer Co-op")
    assert is_internship_title("SWE Coop")
    assert not is_internship_title("New Grad Software Engineer")
    assert not is_internship_title("Software Engineer I")
    assert not is_internship_title("")


def test_is_internship_title_recognizes_grad_friendly_synonyms():
    # Apprenticeship/Fellowship/Residency are functional equivalents some
    # companies use instead of "internship" for grad-friendly programs.
    assert is_internship_title("Software Engineering Apprenticeship")
    assert is_internship_title("Software Engineer Apprentice")
    assert is_internship_title("Engineering Fellowship")
    assert is_internship_title("Software Engineering Fellow")
    assert is_internship_title("Software Engineering Residency")
