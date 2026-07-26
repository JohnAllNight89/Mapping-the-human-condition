# Blueprint Calculator

A working implementation of *THE HUMAN CONDITION: A BLUEPRINT CALCULATOR
PROCESS MAP* -- the Master Outline that specifies how to turn four raw
inputs (birth name, date, time, place) into a fully cross-referenced
"Soul Blueprint" spanning Numerology, Western Tropical Astrology, Vedic
Sidereal Astrology, Human Design, and Gene Keys.

The outline was a specification, not verified code. This is the code.
Every function here corresponds to a numbered Data Point in the outline
(`P3-4`, `NBD-1`, `HD-10`, `GK-4`, ...) and every value it produces is
recorded in a **provenance ledger** that can be traced, one dependency
at a time, all the way back to the four raw inputs. That traceability
is the actual point: it's the difference between *asserting* that these
systems are internally consistent and *proving* it for a specific
person, in public, in code someone else can re-run.

## Why this matters

The four systems in this pipeline don't cite each other in their
traditional forms -- a Human Design reading doesn't reference a
numerology chart. But they all trace back to the same handful of raw
numbers (a birth moment, a set of ecliptic longitudes, a name). This
codebase makes those shared roots literal: a chart's Human Design
"Type" is not an opinion, it's a deterministic function of the same
Julian Day that produces its Western Sun sign, run through three
coordinate bridges and a graph-theoretic decision tree. Nothing in
Phases 3-9 involves interpretation. **Phase 10 (Synthesis) is the only
layer where meaning is assigned** -- and it's structurally separated
from the rest so that separation stays visible in the output, not just
in the design intent.

## Quick start

```bash
pip install -r requirements.txt

# Reproduce the outline's own worked example
python -m blueprint_calculator.cli --doc-example

# Run your own chart
python -m blueprint_calculator.cli --name "Ada Lovelace" --date 1815-12-10 \
    --time 08:00 --place "London"

# Trace exactly how one data point was derived, back to raw inputs
python -m blueprint_calculator.cli --doc-example --trace HD-10

# Full machine-readable provenance ledger (every data point, every phase)
python -m blueprint_calculator.cli --doc-example --json > blueprint.json

# Run the test suite (reproduces the doc's worked example and checks it)
pytest tests/ -v
```

`--place` accepts either a city name from the small offline gazetteer
(`blueprint_calculator/gazetteer.py`) or raw `"lat,lon"` coordinates,
which work anywhere. Timezone resolution (`timezonefinder`) and
historical DST rules (`zoneinfo`) are fully offline; ephemeris
computation (`pyswisseph`) uses the real Swiss Ephemeris data files
bundled in `blueprint_calculator/ephe/` (1800-2400 AD range, matching
the outline's stated engine), not the lower-precision analytical
fallback.

## Chain of command

```
RAW INPUTS (name, date, time, place)
        |
PREPROCESSING (geocode -> timezone -> UTC -> Julian Day; name normalization)
        |
EPHEMERIS CORE (Swiss Ephemeris: 11 bodies, houses, ayanamsa, nodes,
                Design-moment Newton-Raphson solver)
        |
        +---- three coordinate bridges (longitude -> sign / sidereal / HD gate+line) ----+
        |                                                                                 |
   +----+----+                                                              +-------------+-------------+
   |         |                                                              |                           |
NUMEROLOGY  WESTERN TROPICAL                                          VEDIC SIDEREAL              (independent
(name+date   (sign/house/aspect                                       (ayanamsa subtraction,        of ephemeris
 arithmetic,  layer on tropical                                        rashi/nakshatra/dasha)        entirely)
 zero         longitudes)
 ephemeris)        |
                HUMAN DESIGN (tropical -> gate/line -> channels ->
                               centers -> Type/Authority/Definition)
                        |
                   GENE KEYS (1:1 isomorphic relabeling of HD gates)
        |
CROSS-SYSTEM VALIDATION (15 rules -- proves the branches didn't drift apart)
        |
SYNTHESIS (the only interpretive layer; every sentence cites a specific,
           validated data point)
```

## Module map

| Module | Outline Phase | What it computes |
|---|---|---|
| `preprocessing.py` | 1-2 | Geocode, UTC conversion, Julian Day, name normalization |
| `ephemeris.py` | 3 | Swiss Ephemeris core, the 3 coordinate bridges, Design-moment solver, lunar nodes |
| `numerology.py` | 4 | Life Path, Expression, Soul Urge, Personality, timing cycles, karmic numbers |
| `western.py` | 5 | Sign/house/aspect placements, element/modality balance, chart ruler, lunar phase |
| `vedic.py` | 6 | Rashi, nakshatra, Lagna, dasha balance, charakaraka, dignity, combustion |
| `human_design.py` | 7 | Gate activations, channels, centers, Type, Authority, Definition, Profile |
| `gene_keys.py` | 8 | Isomorphic gate-to-key mapping, programming partners, activation sequence |
| `validation.py` | 9 | The 15 cross-system consistency rules |
| `synthesis.py` | 10 | Headline aggregation, deterministic-vs-narrative relationship table, prose |
| `provenance.py` | -- | The `Ledger`/`DataPoint` machinery every phase records into |
| `pipeline.py` | -- | Orchestrates all of the above in dependency order |

Every module's docstring states, plainly, what it implements vs. what
the outline left as `INVENTORY` (documented but not built -- e.g. full
Vedic yogas/vargas, Human Design Color/Tone/Base, Gene Keys frequency
bands) or `HEURISTIC` (requires interpretive judgment by design, not
math -- e.g. "Prime Gifts"). Nothing is silently stubbed; every
unimplemented data point still appears in the ledger with a `status`
field and a note explaining why.

## Known findings

Building this surfaced two places where the outline's own hand-typed
worked example (Johnathon Anthony Long, 1989-06-23 21:55, Atlanta) is
internally inconsistent with its own stated formulas. Both are
documented in code (search `Known findings` / see the relevant
docstrings) rather than silently "corrected" to match:

1. **Design Sun Gate/Line.** The outline states `10.5`. Running the
   outline's own Newton-Raphson formula (Data Point P3-9, Phase 3 Step
   6b) on this birth data converges cleanly (residual ~1e-9 within 3
   iterations) to a Design Julian Day ~90.9 days before birth -- inside
   the outline's own Rule V-3 tolerance (85-92 days) -- and the
   resulting Design Sun activation is `17.1`, not `10.5`. The number
   `10.5` turns out to be this chart's **Personality Earth** activation
   (Sun + 180 deg), which also happens to equal the outline's own Gene
   Keys "Evolution" value. The most likely explanation: the original
   example reused the Personality Sun/Earth pair for the Design slot
   instead of an actual second ephemeris query. The Design Sun *line*
   (1) does still match the outline's stated Profile, `5/1`.
2. **GK-3 programming-partner inline examples.** The outline's stated
   formula, `((gene_key - 1 + 32) % 64) + 1`, correctly reproduces its
   own "Gate 1 -> Partner 33" example, but not "Gate 15 -> Partner 10",
   "Gate 25 -> Partner 9", or "Gate 41 -> Partner 56" -- none of which
   satisfy that formula (verified: it isn't even a self-consistent
   pairing across those four examples). This build implements the
   formula exactly as the outline states it, verbatim.

Neither finding is a defect in this codebase -- both are reproducible
from the outline's own text and formulas. They're worth keeping visible
because they're exactly the kind of error Phase 9's validation layer
exists to catch, and because "the code disagrees with the doc" is a
more useful signal than quietly picking one.

Everything else -- every numerology figure, the Western Sun/Moon/
Ascendant signs, the Lahiri ayanamsa to sub-arcsecond precision, the
sidereal Moon position, Moon nakshatra + pada, the sidereal Lagna and
its lord, the Personality Sun gate/line, Type, Authority, Definition,
and Profile -- reproduces the outline's worked example exactly or to
within its own stated rounding. All 15 of Phase 9's validation rules
pass for this profile, matching the outline's own claim.

## Extending it

Phase 12 of the outline (Expansion) and the `INVENTORY`-tagged data
points throughout are the natural next build targets: Chinese Bazi,
full Vedic divisional charts, live transits (the ephemeris core and
Newton-Raphson solver already built here are exactly what those reuse),
Arabic Parts, and the Gene Keys Venus/Pearl sequences. None of them
require touching the ephemeris core or the validation layer -- that's
by design, per the outline's own closing principle.
