from hire_me_bot.connectors.base import strip_html


def test_strips_tags():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_br_becomes_newline():
    assert strip_html("Line one<br/>Line two") == "Line one\nLine two"


def test_decodes_numeric_html_entities():
    # Real live posting (PIMCO, Software Engineer job R106469): the JD's
    # requirement was literally "5&#43; years of ... experience" --
    # requires_too_much_experience's "\d+\+?" never matched against it since
    # there was no literal "+" character to see, and the posting silently
    # passed a filter it should have failed.
    assert strip_html("5&#43; years of experience") == "5+ years of experience"


def test_decodes_named_html_entities():
    assert strip_html("Java &amp; Python, C&#43;&#43;") == "Java & Python, C++"


def test_entity_decoding_does_not_resurrect_stripped_tags():
    # "&lt;div&gt;" must stay as literal text "<div>" after unescaping, not
    # get treated as a real tag -- decoding happens after tag stripping, not
    # before, specifically to avoid this.
    assert strip_html("<p>Use the &lt;div&gt; tag</p>") == "Use the <div> tag"


def test_none_and_empty():
    assert strip_html(None) == ""
    assert strip_html("") == ""
