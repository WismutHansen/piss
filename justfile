# piss - the world's most fluid programming language

default:
    @just --list

# install into the local venv
install:
    uv sync

# run the test suite
test:
    uv run pytest

# run every example and show what it leaks
examples:
    @for f in examples/*.piss; do echo "--- $f"; uv run piss run "$f" || exit 1; done

# parse every example without running it
check:
    @for f in examples/*.piss; do uv run piss check "$f" || exit 1; done

# try a one-liner
repl-example:
    @printf 'puddle x = 41\nleak x + 1\n' | uv run piss run -
