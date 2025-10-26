from animesubinfo.utils import normalize


def test_normalize_removes_spaces():
    result = normalize("f o  o 2")

    assert result == "foo2"


def test_normalize_non_alphanum_chars():
    result = normalize("f-o!o&b'a_r.b£a)z")

    assert result == "foobarbaz"


def test_normalize_downcases():
    result = normalize("FOO")

    assert result == "foo"


def test_normalize_trailing_zeros():
    result = normalize("02 03foo 01 bar01 11")

    assert result == "23foo1bar0111"


def test_normalize_roman_numerals():
    result = normalize("Season IV Episode II")

    assert result == "season4episode2"
