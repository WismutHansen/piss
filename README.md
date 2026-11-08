# piss

The world's most fluid programming language.

```piss
puddle greeting = "hello, world"
leak greeting
```

> Someone said "show me the GitHub or it's not real". So this is real: there is an
> interpreter, a test suite, and a semantic rule that no other toy language has.

## What this is

A small, complete, working language. Not a README with a name — the interpreter is
`piss/interp.py`, the grammar is `piss/parser.py`, and `uv run pytest` proves it runs.

It is also a joke, and the joke is load-bearing: **bindings evaporate.**

## The one rule that makes it a language

Every binding has a wetness. If nothing reads it within `decay` statements, it dries
out, and reading it afterwards is a fault:

```
piss: evaporated: `forgotten` (last touched at statement 1, read at 9, decay is 6)
```

Reading a binding re-wets it, so a value you actually use never dies. A value you hoard
— declared "just in case", referenced once at the end — evaporates before you can get
back to it.

This is a real design position wearing a joke's clothes:

- **No variable hoarding.** A binding that nothing reads is dead weight, and the runtime
  says so instead of silently carrying it.
- **Locality is enforced, not encouraged.** You cannot declare everything at the top and
  then write the program. You declare where the value is needed, because that is the only
  place it survives.
- **The clock is statements executed**, so the rule is observable and testable, which is
  why it is in the test suite rather than in the marketing.

`--decay N` sets the window (default 6). `--decay 0` turns evaporation off, if you want
a normal language.

## The vocabulary

| keyword | meaning | note |
| --- | --- | --- |
| `puddle` | bind a name | `puddle x = 1` |
| `leak` | print | `leak x` |
| `valve` | define a function | `valve f(a) { flush a }` |
| `flush` | return | `flush value` |
| `drain` | iterate | `drain items x { ... }` |
| `splash` | raise | `splash "no"` |
| `if` / `else` | branch | `else if` chains work |

**There is no `while`.** Water does not flow uphill:

```
$ piss check uphill.piss
piss: uphill: water does not flow uphill: there is no `while`. Use `drain`.
```

Recursion is allowed. It is a drain, not a pump, and eventually it overflows — which the
interpreter reports as `the drain overflowed (deep recursion)` rather than a traceback.

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/WismutHansen/piss
cd piss
uv sync
uv run piss run examples/hello.piss
```

Or install the command globally:

```sh
uv tool install --from git+https://github.com/WismutHansen/piss piss-lang
piss run examples/valves.piss
```

## Use

```sh
piss run program.piss              # execute
piss run program.piss --decay 20   # a longer memory
piss run program.piss --decay 0    # no evaporation at all
piss check program.piss            # parse only, execute nothing
piss --version
```

Read a program from stdin with `-`:

```sh
printf 'puddle x = 41\nleak x + 1\n' | piss run -
```

## The language

Numbers (`1`, `2.5`), strings (`"double"` or `'single'`), booleans, `nil`, and lists.
Operators: `+ - * / %`, comparisons, `== !=`, `and or not`. Comments are `#`.
Braces only, no semicolons required (they are allowed).

Builtins: `len`, `str`, `num`, `range`, `push`.

```piss
valve double(n) {
    flush n * 2
}

puddle nums = [1, 2, 3]
drain nums n {
    leak double(n)
}
```

## Faults

Everything that goes wrong is a leak of some kind.

| fault | when |
| --- | --- |
| `blocked` | the source could not be lexed or parsed |
| `uphill` | you asked water to flow upwards (`while`, `for`) |
| `evaporated` | you read a binding that dried out |
| `burst` | a pipe gave way: type error, division by zero, bad call |
| `splash` | the program raised one deliberately |

## Develop

```sh
just test       # uv run pytest
just examples   # run every example
just check      # parse every example
```

The test suite covers arithmetic, valves, `drain`, `if`/`else`, every fault kind, and
the evaporation rule in both directions: a hoarded binding dies, a re-read binding
survives, and `--decay 0` disables the clock.

## Why does this exist

Because a challenge was issued in public and the honest answer to "show me the GitHub or
it's not real" is a repository that runs. The vocabulary is a pun. The semantics are not:
evaporation is a real, enforced, tested rule about variable lifetime, and the language is
more interesting for having exactly one opinion than it would be as a complete one.

## Licence

MIT. See `LICENSE`.
