import pytest

from piss import Interpreter, parse, run
from piss.errors import Blocked, Burst, Evaporated, Uphill


def test_hello():
    assert run('puddle x = "hi"\nleak x') == "hi"


def test_arithmetic_precedence():
    assert run("leak 2 + 3 * 4") == "14"


def test_division_by_zero_bursts():
    with pytest.raises(Burst):
        run("leak 1 / 0")


def test_valve_and_flush():
    src = "valve add(a, b) {\n  flush a + b\n}\nleak add(2, 3)"
    assert run(src) == "5"


def test_valve_without_flush_returns_nil():
    src = "valve nothing() {\n  puddle x = 1\n}\nleak nothing()"
    assert run(src) == "nil"


def test_drain_over_range():
    assert run("drain range(3) i {\n  leak i\n}") == "0\n1\n2"


def test_drain_over_string():
    assert run('drain "abc" c {\n  leak c\n}') == "a\nb\nc"


def test_if_else_chain():
    src = 'puddle n = 5\nif n > 10 {\n  leak "big"\n} else if n > 3 {\n  leak "medium"\n} else {\n  leak "small"\n}'
    assert run(src) == "medium"


# --- the one rule ---------------------------------------------------------


def test_binding_survives_inside_the_decay_window():
    src = "puddle x = 1\nleak x"
    assert run(src) == "1"


def test_binding_evaporates_past_the_decay_window():
    src = "\n".join(
        ["puddle x = 1"]
        + [f"puddle filler{i} = {i}" for i in range(6)]
        + ["leak x"]
    )
    with pytest.raises(Evaporated) as info:
        run(src, decay=6)
    assert "x" in str(info.value)


def test_reading_a_binding_rewets_it():
    # x is read every other statement, so it never dries out
    src = "\n".join(
        [
            "puddle x = 1",
            "leak x",
            "puddle a = 0",
            "puddle b = 1",
            "leak x",
            "puddle c = 2",
            "puddle d = 3",
            "leak x",
        ]
    )
    assert run(src, decay=4) == "1\n1\n1"


def test_decay_zero_disables_evaporation():
    src = "\n".join(
        ["puddle x = 7"] + [f"puddle filler{i} = {i}" for i in range(50)] + ["leak x"]
    )
    assert run(src, decay=0) == "7"


def test_using_a_builtin_does_not_evaporate_it():
    assert run("leak len([1, 2, 3])") == "3"


# --- refusal to flow uphill -----------------------------------------------


def test_while_is_refused_with_a_specific_message():
    with pytest.raises(Uphill) as info:
        parse("while true {\n leak 1\n}")
    assert "uphill" in str(info.value)


def test_for_is_refused_with_a_pointer_to_drain():
    with pytest.raises(Uphill) as info:
        parse("for i in [1] {\n leak i\n}")
    assert "drain" in str(info.value)


def test_unterminated_block_is_blocked():
    with pytest.raises(Blocked):
        parse("if true {\n  leak 1\n")


def test_splash_is_raised():
    from piss.errors import Splash

    with pytest.raises(Splash):
        run('splash "no"')


def test_unknown_binding_is_a_burst():
    with pytest.raises(Burst):
        run("leak nope")
