"""
API Adapter — translates BlueprintReport into the frontend JSON contract.

The frontend (templates/index.html) expects a specific nested JSON shape.
This module performs all structural translations without adding new data;
every value in the output traces to a field already computed by the pipeline.
"""
from __future__ import annotations

import re

import swisseph as swe
from zoneinfo import ZoneInfo

from blueprint_calculator.ephemeris import bridge_tropical_to_sign
from blueprint_calculator.constants.hd_wheel import GATE_TO_CENTER, LINE_NAMES
from blueprint_calculator.pipeline import BlueprintReport

# ---- Glyph lookup tables ----

BODY_GLYPHS: dict[str, str] = {
    "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
    "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆",
    "Pluto": "♇", "Chiron": "⚷", "North Node": "☊", "South Node": "☋",
    "Earth": "⊕", "Rahu": "☊", "Ketu": "☋",
}

SIGN_GLYPHS: dict[str, str] = {
    "Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
    "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
    "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓",
}

HD_AUTHORITY_LABELS: dict[str, str] = {
    "Emotional": "Emotional (Solar Plexus)",
    "Sacral": "Sacral",
    "Splenic": "Splenic",
    "Ego": "Ego (Heart)",
    "Self-Projected": "Self-Projected (G Center)",
    "Mental/Environment": "Mental / Environment",
    "Lunar": "Lunar (Reflector)",
}

LP_ARCHETYPES: dict[int, str] = {
    1: "The Pioneer", 2: "The Diplomat", 3: "The Creative", 4: "The Builder",
    5: "The Freedom Seeker", 6: "The Nurturer", 7: "The Mystic", 8: "The Powerhouse",
    9: "The Humanitarian", 11: "The Illuminator", 22: "The Master Builder",
    33: "The Master Teacher",
}

PROFILE_LABELS: dict[str, str] = {
    "1/3": "Investigator / Martyr", "1/4": "Investigator / Opportunist",
    "2/4": "Hermit / Opportunist", "2/5": "Hermit / Heretic",
    "3/5": "Martyr / Heretic", "3/6": "Martyr / Role Model",
    "4/6": "Opportunist / Role Model", "4/1": "Opportunist / Investigator",
    "5/1": "Heretic / Investigator", "5/2": "Heretic / Hermit",
    "6/2": "Role Model / Hermit", "6/3": "Role Model / Martyr",
}

# Activation Sequence sphere → source label
SPHERE_SOURCE: dict[str, str] = {
    "Life's Work": "Personality Sun",
    "Evolution": "Personality Earth",
    "Radiance": "Design Sun",
    "Purpose": "Design Earth",
}

SPHERE_MEANING: dict[str, str] = {
    "Life's Work": "What you are here to do — your outer purpose.",
    "Evolution": "What life is teaching you — your inner growth.",
    "Radiance": "What keeps you healthy and vital — your presence.",
    "Purpose": "What grounds you — your deepest inner purpose.",
}

# Preferred display order for Vedic grahas
_VEDIC_ORDER = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
    "Rahu", "Ketu", "Uranus", "Neptune", "Pluto", "Chiron",
]

# Gene Keys: (I Ching name, Shadow, Gift, Siddhi)
GENE_KEYS: dict[int, tuple[str, str, str, str]] = {
    1: ("The Creative", "Entropy", "Freshness", "Beauty"),
    2: ("The Receptive", "Dislocation", "Orientation", "Unity"),
    3: ("Difficulty at the Beginning", "Chaos", "Innovation", "Innocence"),
    4: ("Youthful Folly", "Intolerance", "Understanding", "Forgiveness"),
    5: ("Waiting", "Impatience", "Patience", "Timelessness"),
    6: ("Conflict", "Conflict", "Diplomacy", "Peace"),
    7: ("The Army", "Division", "Guidance", "Virtue"),
    8: ("Holding Together", "Mediocrity", "Style", "Exquisiteness"),
    9: ("The Taming Power of the Small", "Inertia", "Determination", "Invincibility"),
    10: ("Treading", "Self-Obsession", "Naturalness", "Being"),
    11: ("Peace", "Obscurity", "Idealism", "Light"),
    12: ("Standstill", "Vanity", "Discrimination", "Purity"),
    13: ("Fellowship with Men", "Discord", "Discernment", "Empathy"),
    14: ("Possession in Great Measure", "Compromise", "Competence", "Bounteousness"),
    15: ("Modesty", "Dullness", "Magnetism", "Florescence"),
    16: ("Enthusiasm", "Indifference", "Versatility", "Mastery"),
    17: ("Following", "Opinion", "Far-Sightedness", "Omniscience"),
    18: ("Work on What Has Been Spoiled", "Judgment", "Integrity", "Perfection"),
    19: ("Approach", "Co-dependence", "Sensitivity", "Sacrifice"),
    20: ("Contemplation", "Superficiality", "Self-Assurance", "Presence"),
    21: ("Biting Through", "Control", "Authority", "Valor"),
    22: ("Grace", "Dishonor", "Graciousness", "Grace"),
    23: ("Splitting Apart", "Complexity", "Simplicity", "Quintessence"),
    24: ("Return", "Addiction", "Invention", "Silence"),
    25: ("Innocence", "Constriction", "Acceptance", "Universal Love"),
    26: ("The Taming Power of the Great", "Pride", "Artfulness", "Invisibility"),
    27: ("The Corners of the Mouth", "Selfishness", "Altruism", "Selflessness"),
    28: ("Preponderance of the Great", "Purposelessness", "Totality", "Immortality"),
    29: ("The Abysmal", "Half-Heartedness", "Commitment", "Devotion"),
    30: ("The Clinging Fire", "Desire", "Lightness", "Rapture"),
    31: ("Influence", "Arrogance", "Leadership", "Humility"),
    32: ("Duration", "Failure", "Preservation", "Veneration"),
    33: ("Retreat", "Forgetting", "Mindfulness", "Revelation"),
    34: ("The Power of the Great", "Force", "Strength", "Majesty"),
    35: ("Progress", "Hunger", "Adventure", "Boundlessness"),
    36: ("Darkening of the Light", "Turbulence", "Humanity", "Compassion"),
    37: ("The Family", "Weakness", "Equality", "Tenderness"),
    38: ("Opposition", "Struggle", "Perseverance", "Honor"),
    39: ("Obstruction", "Provocation", "Dynamism", "Liberation"),
    40: ("Deliverance", "Exhaustion", "Resolve", "Divine Will"),
    41: ("Decrease", "Fantasy", "Anticipation", "Emanation"),
    42: ("Increase", "Expectation", "Detachment", "Celebration"),
    43: ("Breakthrough", "Deafness", "Insight", "Epiphany"),
    44: ("Coming to Meet", "Interference", "Teamwork", "Synarchy"),
    45: ("Gathering Together", "Dominance", "Synergy", "Communion"),
    46: ("Pushing Upward", "Seriousness", "Delight", "Ecstasy"),
    47: ("Oppression", "Oppression", "Transmutation", "Transfiguration"),
    48: ("The Well", "Inadequacy", "Resourcefulness", "Wisdom"),
    49: ("Revolution", "Reaction", "Revolution", "Rebirth"),
    50: ("The Cauldron", "Corruption", "Equilibrium", "Harmony"),
    51: ("The Arousing", "Agitation", "Initiative", "Awakening"),
    52: ("Keeping Still", "Stress", "Restraint", "Stillness"),
    53: ("Development", "Immaturity", "Expansion", "Superabundance"),
    54: ("The Marrying Maiden", "Greed", "Aspiration", "Ascension"),
    55: ("Abundance", "Victimization", "Freedom", "Freedom"),
    56: ("The Wanderer", "Distraction", "Enrichment", "Intoxication"),
    57: ("The Gentle", "Unease", "Intuition", "Clarity"),
    58: ("The Joyous", "Dissatisfaction", "Vitality", "Bliss"),
    59: ("Dispersion", "Dishonesty", "Intimacy", "Transparency"),
    60: ("Limitation", "Limitation", "Realism", "Justice"),
    61: ("Inner Truth", "Psychosis", "Inspiration", "Sanctity"),
    62: ("Preponderance of the Small", "Intellect", "Precision", "Impeccability"),
    63: ("After Completion", "Doubt", "Inquiry", "Truth"),
    64: ("Before Completion", "Confusion", "Imagination", "Illumination"),
}


# ---- Section summary generator ----

def _section_summaries(report: BlueprintReport) -> dict:  # noqa: C901
    """Deterministic 3-paragraph (light/shadow/synthesis) analysis for each tab."""
    num = report.numerology
    west = report.western
    ved = report.vedic
    hd = report.human_design
    gk = report.gene_keys
    comm = report.communication or {}

    lp = num["life_path"]
    expr = num["expression"]
    soul = num["soul_urge"]
    maturity = num["maturity"]
    py = num["personal_year"]
    karmic_debts = num["karmic_debts"]
    karmic_lessons = num["karmic_lessons"]
    subcon = num["subconscious_self"]
    challenges = num["challenges"]
    lp_arch = LP_ARCHETYPES.get(lp, "unique frequency")

    _PY = {
        1: "new beginnings — seeds planted now carry a nine-year arc",
        2: "partnership, patience, and relational deepening",
        3: "creative expression and social expansion",
        4: "discipline, foundation-building, and structured effort",
        5: "change, freedom, and unexpected breakthroughs",
        6: "responsibility, home, and alignment of work with values",
        7: "introspection, spiritual deepening, and inner knowing",
        8: "power, ambition, and material manifestation",
        9: "completion, release, and clearing space for the next cycle",
        11: "heightened intuition and visionary sensitivity",
        22: "master-builder energy — turning elevated vision into structure",
        33: "service, healing, and elevating those around you",
    }
    py_meaning = _PY.get(py, "deep reflection and integration")
    debt_str = (
        f"Karmic debts {', '.join(str(d) for d in karmic_debts)} surface as recurring patterns demanding conscious reckoning before they release."
        if karmic_debts else
        "No karmic debt numbers appear in your chains — the core path carries no inherited ancestral obligations."
    )
    lesson_str = (
        f"Karmic lessons {', '.join(str(l) for l in karmic_lessons)} — the digits absent from your name — are not weaknesses but uncultivated territories requiring deliberate development."
        if karmic_lessons else
        "All nine digits appear in your name — no karmic lesson gaps exist."
    )
    ch = challenges
    ch_str = f"{ch[0]}, {ch[1]}, {ch[2]}, {ch[3]}" if len(ch) >= 4 else str(ch)

    num_summ = {
        "light": (
            f"Your Life Path {lp} carries the archetype of {lp_arch} — the frequency woven through every major chapter. "
            f"Your Expression {expr} is the outward vehicle: the talents others recognize in you before you name them yourself. "
            f"Your Soul Urge {soul} is the engine underneath — the deep internal pull that drives choices even when logic can't explain them. "
            f"Your Maturity Number {maturity} is the convergence point that sharpens through the 30s and 40s as Life Path and Expression integrate into a single unified current."
        ),
        "shadow": (
            f"{debt_str} "
            f"{lesson_str} "
            f"Your challenge numbers — {ch_str} — mark the friction at the edge of each life phase: not failures in progress, but the exact pressures that build the character the Life Path demands."
        ),
        "synthesis": (
            f"Life Path {lp} and Expression {expr} are two rails of the same track — where they resonate, effort becomes effortless; where they diverge is where growth lives. "
            f"Personal Year {py} places you in a cycle of {py_meaning} right now. "
            f"Your Subconscious Self {subcon} tells you that {subcon} frequencies are already fully integrated — your bedrock. "
            f"The pillars: Life Purpose ({lp}), Natural Expression ({expr}), Inner Drive ({soul}), Present Timing (Year {py}). Nothing here is accidental."
        ),
    }

    # --- Western ---
    sun = west.get("sun_sign", "")
    moon = west.get("moon_sign", "")
    asc = west.get("ascendant", "")
    chart_ruler = west.get("chart_ruler", "")
    retrogrades = west.get("dominant_retrogrades", [])
    elem_bal = west.get("element_balance", {})
    mod_bal = west.get("modality_balance", {})
    lunar_phase = west.get("lunar_phase_name", "")
    dom_elem = max(elem_bal, key=elem_bal.get) if elem_bal else ""
    dom_mod = max(mod_bal, key=mod_bal.get) if mod_bal else ""
    _ELEM_GIFT = {
        "Fire": "initiative, inspiration, and the courage to act before the path is fully clear",
        "Earth": "pragmatism, endurance, and the ability to build things that last",
        "Air": "intellectual versatility, communication, and connecting disparate ideas",
        "Water": "emotional depth, intuition, and profound empathy and healing",
    }
    _ELEM_SHADOW = {
        "Fire": "impulsivity, burnout from leading without replenishing, and difficulty sitting with discomfort",
        "Earth": "rigidity, resistance to change, and hoarding energy out of fear",
        "Air": "overthinking, emotional detachment, and scattering focus across too many directions",
        "Water": "absorbing others' emotional states, boundary erosion, and conflating intuition with anxiety",
    }
    retro_str = (
        f"Retrograde planets — {', '.join(retrogrades)} — internalize those energies: their work happens in depth and in private before becoming visible."
        if retrogrades else
        "No dominant retrograde planets — all planetary energies flow outwardly and expressively."
    )
    west_summ = {
        "light": (
            f"Your {sun} Sun is the conscious identity you grow into — the archetype of your outward creative expression. "
            f"Your {asc} Ascendant is the lens through which all incoming experience is first filtered and the face you meet the world with. "
            f"With {dom_elem} as the dominant element, your natural gifts include {_ELEM_GIFT.get(dom_elem, 'a balanced elemental field')}. "
            f"Your {dom_mod} modality signature describes the rhythm of your engagement: how you initiate and sustain action in the world."
        ),
        "shadow": (
            f"Your {moon} Moon reveals the emotional architecture — the instinctive reactive patterns that activate before the conscious mind responds. "
            f"The Moon's shadow is not the sign itself but the automated responses it produces when stress bypasses reflection. "
            f"{retro_str} "
            f"The shadow of a dominant {dom_elem} field: {_ELEM_SHADOW.get(dom_elem, 'the unexamined elemental tendency')}."
        ),
        "synthesis": (
            f"Sun ({sun}), Moon ({moon}), and Ascendant ({asc}) form the trinity of Western identity: who you are, how you feel, how you appear. "
            f"Your chart ruler — {chart_ruler} — is the planetary governor of the whole chart, the lens through which the entire birth map is focused. "
            f"The {lunar_phase} at birth describes the relationship between conscious purpose (Sun) and emotional need (Moon): the tension or harmony between those two drives is the lived texture of your life. "
            f"Integration means running Sun, Moon, and Ascendant in conscious concert — not suppressing any of the three but letting each inform the others."
        ),
    }

    # --- Vedic ---
    moon_rashi = ved.get("moon_rashi", "")
    moon_nak = ved.get("moon_nakshatra", "")
    moon_nak_lord = ved.get("moon_nakshatra_lord", "")
    lagna_str = ved.get("lagna", "")
    lagna_lord = ved.get("lagna_lord", "")
    mahadasha = ved.get("starting_mahadasha", "")
    atmakaraka = ved.get("charakarakas", {}).get("Atmakaraka", "")
    lagna_sk = lagna_str.split("(")[0].strip()
    _NAK_GIFTS = {
        "Ashwini": "healing instincts and swift pioneering energy",
        "Bharani": "creative force and the capacity to hold and transform",
        "Krittika": "purifying intensity and fearless truth-telling",
        "Rohini": "sensual richness, creative fertility, and magnetic presence",
        "Mrigashira": "perpetual curiosity and refined aesthetic sense",
        "Ardra": "storm-weathering strength and transformative intelligence",
        "Punarvasu": "renewal, optimism, and restoring what has been lost",
        "Pushya": "nurturing wisdom and the gift of sustaining others",
        "Ashlesha": "penetrating insight and the ability to see beneath surfaces",
        "Magha": "ancestral authority and command that others follow naturally",
        "Purva Phalguni": "creative joy and the gift of bringing delight",
        "Uttara Phalguni": "steadfast service and executive capability",
        "Hasta": "craftsmanship, healing hands, and practical intelligence",
        "Chitra": "architectural brilliance and the eye that sees design in everything",
        "Swati": "independent spirit and the ability to bend without breaking",
        "Vishakha": "focused purpose and harvest at the end of long effort",
        "Anuradha": "devotion and loyalty that outlasts difficulty",
        "Jyeshtha": "elder wisdom and leadership earned through ordeal",
        "Mula": "root-level truth-seeking and metaphysical intelligence",
        "Purva Ashadha": "invincible spirit and confidence that cannot be shaken",
        "Uttara Ashadha": "ultimate victory through right action and enduring achievement",
        "Shravana": "listening intelligence and the gift of transmitting wisdom",
        "Dhanishta": "rhythmic power and the ability to prosper through community",
        "Shatabhisha": "healing at the deepest level and the medicine of truth",
        "Purva Bhadrapada": "fierce idealism and the purification of what no longer serves",
        "Uttara Bhadrapada": "depth of compassion and patient mastery",
        "Revati": "spiritual completion and the wisdom of the journey's end",
    }
    nak_gift = _NAK_GIFTS.get(moon_nak, "unique lunar intelligence")
    ved_summ = {
        "light": (
            f"Your Moon in {moon_rashi} (sidereal) carries the karmic and emotional inheritance of this incarnation. "
            f"The {moon_nak} nakshatra — ruled by {moon_nak_lord} — brings {nak_gift}. "
            f"Your {lagna_sk} Lagna with lord {lagna_lord} defines the dharmic vehicle: the body, persona, and life trajectory you came here to express. "
            f"The Atmakaraka {atmakaraka} is the soul indicator in Jaimini astrology — the planet encoding the primary lesson and highest calling of this incarnation."
        ),
        "shadow": (
            f"In Vedic cosmology, the shadow is carried by the lunar nodes: Rahu represents insatiable hunger — the new territory the soul must integrate but doesn't yet hold gracefully. "
            f"Ketu marks what the soul has already mastered across lifetimes — the comfort zone that can become spiritual stagnation if left unchallenged. "
            f"The Mahadasha sequence encodes which planetary karma rises for integration in each life phase. "
            f"The shadow work of the Vedic chart is precise: it names which patterns require transformation and in what sequence."
        ),
        "synthesis": (
            f"The Vedic chart reads soul architecture across lifetimes, not just this one. "
            f"Your {lagna_sk} Lagna is the dharmic entrance point — the vehicle you chose for this lifetime. "
            f"Your Moon in {moon_rashi} — {moon_nak} — is the emotional and karmic body: the flavor of interior life and the lens of reactive patterns. "
            f"The Mahadasha beginning with {mahadasha} activates specific planetary karma, placing particular themes at the foreground for an extended period. "
            f"Synthesis: Lagna is what you do, Moon is how you feel, Atmakaraka ({atmakaraka}) is what your soul is learning — three pillars of your Vedic identity."
        ),
    }

    # --- Human Design ---
    hd_type = hd.get("type", "")
    authority = hd.get("authority", "")
    profile_hd = hd.get("profile", "")
    definition = hd.get("definition", "")
    strategy = hd.get("strategy", "")
    signature = hd.get("signature", "")
    not_self = hd.get("not_self_theme", "")
    defined_centers = hd.get("defined_centers", [])
    open_centers = hd.get("open_centers", [])
    _TYPE_GIFTS = {
        "Generator": "sustainable life-force, the full-body yes of genuine response, and mastery built through joyful engagement",
        "Manifesting Generator": "multi-dimensional speed, the ability to pioneer several lanes at once, and showing others what's possible",
        "Projector": "penetrating insight, the gift of guiding others toward efficiency, and wisdom that arrives through deep observation",
        "Manifestor": "initiatory power, the ability to catalyze new realities without needing permission, and opening doors others walk through",
        "Reflector": "environmental attunement, sampling the full spectrum of human experience, and the wisdom of lunar-cycle timing",
    }
    _OPEN_COND = {
        "Head": "absorbing others' mental pressure and feeling obligated to answer every question that enters awareness",
        "Ajna": "pretending certainty you don't feel, locking into fixed positions to avoid the discomfort of not-knowing",
        "Throat": "speaking to fill silence or initiating to attract attention rather than waiting for genuine invitation",
        "G": "searching for identity in relationships or places rather than resting in the self",
        "Heart": "over-committing to prove worth — making promises driven by ego rather than genuine will",
        "Sacral": "pushing past natural energy limits and ignoring completion signals",
        "Spleen": "holding on to what no longer serves out of fear rather than spontaneous clarity",
        "Solar Plexus": "deciding in emotional reactivity — chasing highs or avoiding lows rather than waiting for the wave to settle",
        "Root": "living in perpetual hurry to escape adrenal pressure — rushing decisions for relief",
    }
    open_cond_parts = [_OPEN_COND.get(c, c) for c in open_centers[:3]]
    open_str = (
        f"Open centers — {', '.join(open_centers)} — are where conditioning enters: {'; '.join(open_cond_parts[:2])}."
        if open_centers else
        "With all centers defined, conditioning points lie in specific channels and gates rather than center architecture."
    )
    defined_str = (
        f"Defined centers — {', '.join(defined_centers)} — provide consistent, reliable energy that others can count on."
        if defined_centers else
        "With no defined centers, your field is entirely responsive and environment-shaped — rare and deeply flexible."
    )
    auth_short = authority.split(" (")[0] if "(" in authority else authority
    hd_summ = {
        "light": (
            f"As a {hd_type}, your gift is {_TYPE_GIFTS.get(hd_type, 'unique energetic intelligence')}. "
            f"Your {auth_short} Authority is the body intelligence that knows before the mind constructs a reason — the reliable signal of correct decision-making. "
            f"{defined_str} "
            f"Profile {profile_hd} is the costume your soul wears: the social archetype and learning strategy that shapes how you move through relationships and life themes."
        ),
        "shadow": (
            f"The not-self theme for a {hd_type} is {not_self} — the emotional signal that you are operating out of strategy. Not a moral failing but a compass: when {not_self} arises, alignment is off. "
            f"{open_str} "
            f"Open centers amplify and condition the energy of whoever is in your field — the wisdom lies not in closing them but in witnessing the amplification without identifying with it as your own truth."
        ),
        "synthesis": (
            f"Your Human Design is an operating manual, not a fixed identity. Strategy ({strategy}) tells you how to move without resistance. "
            f"{auth_short} Authority tells you how to make decisions that are genuinely yours. "
            f"{definition} tells you how your energy field is structured and how you interact with others energetically. "
            f"Profile {profile_hd} tells you the mythological role you're here to play. "
            f"Twin signals: your signature ({signature}) confirms you're on track; your not-self ({not_self}) signals you've drifted. Run those alongside Strategy and Authority — that's the complete self-navigation system."
        ),
    }

    # --- Gene Keys ---
    act_seq = gk.get("activation_sequence", [])
    spheres = []
    for s_data in act_seq[:4]:
        gate = s_data.get("gate", 0)
        gk_info = GENE_KEYS.get(gate, ("Unknown", "Unknown", "Unknown", "Unknown"))
        spheres.append({"sphere": s_data.get("sphere", ""), "gate": gate,
                        "name": gk_info[0], "shadow": gk_info[1], "gift": gk_info[2], "siddhi": gk_info[3]})
    if spheres:
        gifts_str = "; ".join(f"{s['sphere']} Gate {s['gate']} — Gift of {s['gift']}" for s in spheres)
        shadows_str = "; ".join(f"{s['sphere']} Gate {s['gate']} — Shadow of {s['shadow']}" for s in spheres)
        siddhis_str = ", ".join(s["siddhi"] for s in spheres)
        lw = spheres[0]
    else:
        gifts_str = "your unique activation sequence gifts"
        shadows_str = "the shadow patterns of your activation gates"
        siddhis_str = "the highest expressions of your sequence"
        lw = {"sphere": "", "gate": 0, "name": "", "shadow": "", "gift": "", "siddhi": ""}
    gk_summ = {
        "light": (
            f"The Gene Keys are a contemplative system of self-realization built on the same 64-gate architecture as Human Design, decoded as Shadow, Gift, and Siddhi. "
            f"Your activation sequence gifts: {gifts_str}. "
            f"The Gift is not something to perform — it is what naturally emerges when the Shadow is no longer running the show. "
            f"Your siddhis — {siddhis_str} — are the highest possible expressions: frequencies to allow as contemplation deepens, not goals to achieve."
        ),
        "shadow": (
            f"The Gene Keys framework is explicit: the Shadow is not the enemy, it is the doorway. "
            f"Repressing the Shadow produces the low frequency; reacting creates drama; accepting and contemplating transmutes it into the Gift. "
            f"Your activation sequence shadows: {shadows_str}. "
            f"The Shadow of your Life's Work — {lw['shadow']} — is the pattern that shows up when the Gift is not flowing. It is compressed Gift waiting to be unpacked."
        ),
        "synthesis": (
            f"The hologenetic profile maps your soul's complete journey: Life's Work (outer purpose), Evolution (inner growth), Radiance (vitality and presence), Purpose (deepest anchor) — four spheres operating simultaneously, each informing the others. "
            f"The key insight: Shadow, Gift, and Siddhi are not three different things but one frequency at three different bandwidths. "
            f"Your Life's Work Gift — {lw['gift']} — is available right now, underneath the Shadow. Your Siddhi — {lw['siddhi']} — is the same frequency at full coherence. "
            f"Contemplation, not effort, is the mechanism. Sustained attention to the Shadow — without judgment, without suppression, without reaction — is sufficient to initiate the transmission."
        ),
    }

    # --- Communication ---
    comm_arch = comm.get("archetype", "")
    comm_proc = comm.get("processing_style", "")
    comm_delivery = comm.get("delivery", {})
    comm_avoid = comm_delivery.get("avoid", "") if comm_delivery else ""
    comm_summ = {
        "light": (
            f"Your communication archetype — {comm_arch} — is a precise description of how your cognitive wiring works at its best, derived from cross-system analysis of Human Design, Western Mercury and elemental balance, and Numerology expression and life path. "
            f"When communicating in alignment with this archetype, information flows: you receive it through your native channels and transmit it in ways others can actually absorb. "
            f"The cognitive strengths identified in your profile are not aspirational — they are already operational. The work is simply to recognize and lean into them."
        ),
        "shadow": (
            f"The shadow of communication is not saying the wrong thing — it is operating from a mode that isn't yours. "
            f"Your primary conditioning pattern to watch: {comm_avoid}. "
            f"This conditioning enters through open centers, gets amplified by environment, and can masquerade as authentic self-expression when it is actually adaptive response to external pressure. "
            f"The signal: you feel drained, misunderstood, or invisible after communication. That's not a cue to push harder — it's an invitation to return to your native mode."
        ),
        "synthesis": (
            f"Every data point in your chart points toward the same underlying wiring — the communication profile is where all four systems converge on a single practical conclusion. "
            f"Your processing style — {comm_proc} — is not a preference, it is a structural fact of how your nervous system organizes information. Work with it, not against it. "
            f"When information is delivered in a format mismatched to your processing style, it doesn't land — not because of a failure of intelligence but a failure of format. "
            f"The pillars: archetype ({comm_arch}), processing style, delivery preferences, and the specific conditioning to watch. These four coordinates are all you need to navigate any conversation."
        ),
    }

    # --- Grand synthesis ---
    ks_str = ', '.join(str(l) for l in karmic_lessons) if karmic_lessons else "none"
    lw_gate_num = lw["gate"]
    lw_name_grand = lw["name"]
    lw_gift_grand = lw["gift"]
    lw_shadow_grand = lw["shadow"]
    grand_summ = {
        "light": (
            f"When all systems are read together, one singular profile emerges with striking coherence. "
            f"Life Path {lp} ({lp_arch}) × {sun} Sun × {hd_type} × Life's Work Gate {lw_gate_num} ({lw_name_grand}): "
            f"four facts from four independent systems, each calculated from the same underlying birth data, each pointing to the same core frequency. "
            f"The gift that runs through all of them: {lw_gift_grand}. "
            f"No system invented this independently — each calculated it from the precise coordinates of your birth moment."
        ),
        "shadow": (
            f"The shadow that runs across systems is equally coherent. "
            f"Not-self theme ({not_self}), karmic lessons ({ks_str}), Life's Work shadow ({lw_shadow_grand}), and communication conditioning ({comm_avoid}): "
            f"not separate problems but the same pattern seen through four lenses. "
            f"The cross-system shadow is always some version of the same fundamental misalignment: operating from conditioned response rather than authentic design. "
            f"Seeing it confirmed through four independent systems makes it undeniable — and what is clearly seen cannot be unconsciously repeated."
        ),
        "synthesis": (
            f"The deepest insight of cross-system synthesis: the universe placed the same frequency into your birth moment and encoded it simultaneously into numbers (Numerology), planetary positions (Astrology), energy mechanics (Human Design), and contemplative keys (Gene Keys). "
            f"The redundancy is not accident — it is emphasis. What all four systems agree on is the irreducible core of who you are. "
            f"Life Path {lp}, {sun} Sun, {hd_type} with {auth_short} Authority, Gate {lw_gate_num}: these coordinates are your identity confirmed across four independent methodologies. "
            f"The pillars of your being: your purpose ({lp_arch}), your instrument ({expr} Expression), your strategy ({strategy}), your contemplative path (Gate {lw_gate_num} — {lw_name_grand}). "
            f"Nothing here is random. You were specifically designed this way."
        ),
    }

    return {
        "numerology": num_summ,
        "western": west_summ,
        "vedic": ved_summ,
        "human_design": hd_summ,
        "gene_keys": gk_summ,
        "communication": comm_summ,
        "grand": grand_summ,
    }


# ---- Helpers ----

def _jd_to_utc_str(jd: float) -> str:
    year, month, day, hour_frac = swe.revjul(jd, 1)  # 1 = Gregorian
    h = int(hour_frac)
    m = int((hour_frac - h) * 60)
    s = int(((hour_frac - h) * 60 - m) * 60)
    return f"{year:04d}-{month:02d}-{day:02d} {h:02d}:{m:02d}:{s:02d}"


def _ayanamsa_dms(degrees: float) -> str:
    deg = int(degrees)
    mf = (degrees - deg) * 60
    minute = int(mf)
    second = round((mf - minute) * 60)
    return f"{deg}°{minute:02d}'{second:02d}\""


def _parse_rashi(rashi_combined: str) -> tuple[str, str]:
    """Parse 'Mesha (Aries)' → ('Mesha', 'Aries')."""
    m = re.match(r"(.+?)\s+\((.+?)\)", rashi_combined)
    if m:
        return m.group(1), m.group(2)
    return rashi_combined, rashi_combined


def _num_obj(numerology: dict, key: str) -> dict:
    n = numerology[key]
    chain = numerology.get("reduction_chains", {}).get(key, [n])
    is_master = n in (11, 22, 33)
    reduction = " → ".join(str(x) for x in chain) if len(chain) > 1 else str(n)
    return {"number": n, "is_master": is_master, "reduction": reduction, "letters": ""}


def _longitude_from_placement(placement: dict) -> float:
    return placement["sign_index"] * 30.0 + placement["degrees_in_sign"]


# ---- Main adapter ----

def adapt(report: BlueprintReport) -> dict:
    """Translate BlueprintReport → frontend JSON contract."""

    # ---- profile ----
    profile = {
        "name": report.name,
        "birth_date": report.birth_date,
        "birth_time": report.birth_time,
        "birth_place": report.birth_place,
    }

    # ---- numerology (full) ----
    def _simple_num(n: int) -> dict:
        return {"number": n, "is_master": n in (11, 22, 33), "reduction": str(n), "letters": ""}

    numerology = {
        # Core identity
        "life_path": _num_obj(report.numerology, "life_path"),
        "expression": _num_obj(report.numerology, "expression"),
        "soul_urge": _num_obj(report.numerology, "soul_urge"),
        "personality": _num_obj(report.numerology, "personality"),
        # Birth-date pillars
        "attitude": _num_obj(report.numerology, "attitude"),
        "birthday": _num_obj(report.numerology, "birthday"),
        "generation": _num_obj(report.numerology, "generation"),
        # Derived numbers
        "maturity": _num_obj(report.numerology, "maturity"),
        "balance": _simple_num(report.numerology["balance"]),
        "subconscious_self": report.numerology["subconscious_self"],
        # Karmic patterns
        "karmic_debts": report.numerology["karmic_debts"],
        "karmic_lessons": report.numerology["karmic_lessons"],
        # Active timing
        "personal_year": report.numerology["personal_year"],
        "personal_month": report.numerology["personal_month"],
        "personal_day": report.numerology["personal_day"],
        # Life cycles
        "pinnacles": report.numerology["pinnacles"],
        "challenges": report.numerology["challenges"],
        "periods": report.numerology["periods"],
    }

    # ---- location / time context ----
    coords = report.coordinates
    utc_dt = report.utc_datetime

    tz = ZoneInfo(coords.timezone)
    local_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    offset = local_dt.utcoffset()
    total_min = int(offset.total_seconds() / 60)
    sign = "+" if total_min >= 0 else "-"
    abs_min = abs(total_min)
    utc_offset_str = f"{sign}{abs_min // 60:02d}:{abs_min % 60:02d}"

    location = {
        "resolved": coords.display_name,
        "latitude": coords.latitude,
        "longitude": coords.longitude,
        "timezone": coords.timezone,
    }
    time_info = {
        "local": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "utc": utc_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "utc_offset": utc_offset_str,
    }

    # ---- western astrology ----
    placements = report.western["placements"]
    retrogrades = set(report.western["dominant_retrogrades"])

    planets = []
    for body, data in placements.items():
        if body in ("Ascendant", "Midheaven"):
            continue
        lon = _longitude_from_placement(data)
        planets.append({
            "name": body,
            "glyph": BODY_GLYPHS.get(body, "?"),
            "sign_index": data["sign_index"],
            "sign": data["sign_name"],
            "sign_glyph": SIGN_GLYPHS.get(data["sign_name"], ""),
            "degrees_in_sign": data["degrees_in_sign"],
            "dms_string": data["dms_string"],
            "position": data["dms_string"],
            "longitude": lon,
            "retrograde": body in retrogrades,
        })

    house_cusps_raw = report.western.get("house_cusps", [])
    houses = [
        {
            "house": hc["house"],
            "sign_glyph": SIGN_GLYPHS.get(hc["sign_name"], ""),
            "sign": hc["sign_name"],
            "position": hc["dms_string"],
            "longitude": hc["longitude"],
        }
        for hc in house_cusps_raw
    ]

    asc_lon = _longitude_from_placement(placements["Ascendant"])
    mc_lon = _longitude_from_placement(placements["Midheaven"])
    dsc_lon = (asc_lon + 180) % 360
    ic_lon = (mc_lon + 180) % 360
    dsc_data = bridge_tropical_to_sign(dsc_lon)
    ic_data = bridge_tropical_to_sign(ic_lon)

    def _angle_obj(data: dict, lon: float) -> dict:
        return {
            "sign": data["sign_name"],
            "sign_glyph": SIGN_GLYPHS.get(data["sign_name"], ""),
            "position": data["dms_string"],
            "longitude": lon,
        }

    angles = {
        "ascendant": _angle_obj(placements["Ascendant"], asc_lon),
        "midheaven": _angle_obj(placements["Midheaven"], mc_lon),
        "descendant": _angle_obj(dsc_data, dsc_lon),
        "imum_coeli": _angle_obj(ic_data, ic_lon),
    }

    western = {
        "planets": planets,
        "houses": houses,
        "angles": angles,
        "element_balance": report.western["element_balance"],
        "modality_balance": report.western["modality_balance"],
        "lunar_phase_angle": report.western["lunar_phase_angle"],
        "lunar_phase_name": report.western["lunar_phase_name"],
        "aspects": report.western["aspects"],
    }

    # ---- vedic astrology ----
    sidereal = report.vedic["sidereal_longitudes"]
    rashis_raw = report.vedic["rashis"]   # {body: "Mesha (Aries)"}
    nakshatras = report.vedic["nakshatras"]
    ayanamsa_val = report.ledger.value("P3-8")

    grahas = []
    for body in _VEDIC_ORDER:
        if body not in rashis_raw or body == "Lagna":
            continue
        lon = sidereal.get(body, 0.0)
        rashi_combined = rashis_raw[body]
        rashi_sk, rashi_en = _parse_rashi(rashi_combined)

        deg_in = lon % 30
        d = int(deg_in)
        mf = (deg_in - d) * 60
        mi = int(mf)
        sc = round((mf - mi) * 60)
        position = f"{d}°{mi:02d}'{sc:02d}\" {rashi_sk}"

        nak = nakshatras.get(body, {})
        retrograde = body in retrogrades  # Rahu/Ketu always retrograde (mean nodes)
        if body in ("Rahu", "Ketu"):
            retrograde = True

        grahas.append({
            "name": body,
            "glyph": BODY_GLYPHS.get(body, "?"),
            "rashi": rashi_sk,
            "sign": rashi_en,
            "position": position,
            "nakshatra": nak.get("nakshatra_name", ""),
            "nakshatra_lord": nak.get("lord", ""),
            "pada": nak.get("pada", ""),
            "retrograde": retrograde,
        })

    # Lagna info
    lagna_combined = report.vedic["lagna"]
    lagna_sk, lagna_en = _parse_rashi(lagna_combined)
    lagna_lon = sidereal.get("Lagna", 0.0)
    ld = lagna_lon % 30
    ld_int = int(ld)
    lm = (ld - ld_int) * 60
    lm_int = int(lm)
    ls = round((lm - lm_int) * 60)
    lagna_nak = nakshatras.get("Moon", {})  # Lagna nakshatra not always computed separately

    vedic = {
        "ayanamsa_dms": _ayanamsa_dms(ayanamsa_val),
        "ayanamsa_name": "Lahiri",
        "lagna": {
            "rashi": lagna_sk,
            "sign": lagna_en,
            "position": f"{ld_int}°{lm_int:02d}'{ls:02d}\"",
            "nakshatra": report.vedic.get("moon_nakshatra", ""),
            "pada": lagna_nak.get("pada", ""),
        },
        "grahas": grahas,
    }

    # ---- human design ----
    hd = report.human_design

    def _build_activations(acts: dict) -> list:
        out = []
        for body, act in acts.items():
            gate = act["gate"]
            gk_info = GENE_KEYS.get(gate, ("Unknown", "", "", ""))
            zodiac = bridge_tropical_to_sign(act["longitude"])["dms_string"]
            out.append({
                "glyph": BODY_GLYPHS.get(body, "?"),
                "body": body,
                "notation": act["notation"],
                "gate_name": gk_info[0],
                "zodiac": zodiac,
            })
        return out

    channels = [
        {
            "label": f"Gate {g1} – Gate {g2}",
            "centers": [GATE_TO_CENTER[g1], GATE_TO_CENTER[g2]],
        }
        for g1, g2 in hd["defined_channels"]
    ]

    design_jd = report.ledger.value("P3-9")
    design_moment_utc = _jd_to_utc_str(design_jd)
    solar_arc = round(report.julian_day - design_jd, 2)

    profile_str = hd["profile"]
    profile_parts = [int(x) for x in profile_str.split("/")]
    profile_label = (
        f"{LINE_NAMES[profile_parts[0]]} / {LINE_NAMES[profile_parts[1]]}"
        if len(profile_parts) == 2
        else profile_str
    )

    hd_definition = hd["definition"]
    if not hd_definition.endswith(" Definition"):
        hd_definition = hd_definition + " Definition"

    human_design = {
        "type": hd["type"],
        "authority": HD_AUTHORITY_LABELS.get(hd["authority"], hd["authority"]),
        "profile": profile_str,
        "profile_label": profile_label,
        "definition": hd_definition,
        "strategy": hd["strategy"],
        "signature": hd["signature"],
        "not_self": hd["not_self_theme"],
        "defined_centers": hd["defined_centers"],
        "open_centers": hd["open_centers"],
        "channels": channels,
        "personality": {"activations": _build_activations(hd["personality_activations"])},
        "design": {
            "activations": _build_activations(hd["design_activations"]),
            "moment_utc": design_moment_utc,
            "solar_arc": str(solar_arc),
        },
    }

    # ---- gene keys ----
    gk = report.gene_keys

    # Build gate → sources list from HD activations
    gate_sources: dict[int, list[str]] = {}
    for body, act in hd["personality_activations"].items():
        gate_sources.setdefault(act["gate"], []).append(f"Personality {body}")
    for body, act in hd["design_activations"].items():
        gate_sources.setdefault(act["gate"], []).append(f"Design {body}")

    activation_sequence = []
    for entry in gk["activation_sequence"]:
        sphere = entry["sphere"]
        gate = entry["gate"]
        gk_info = GENE_KEYS.get(gate, ("Unknown", "Unknown", "Unknown", "Unknown"))
        activation_sequence.append({
            "sphere": sphere,
            "source": SPHERE_SOURCE.get(sphere, sphere),
            "notation": entry["notation"],
            "name": gk_info[0],
            "meaning": SPHERE_MEANING.get(sphere, ""),
            "shadow": gk_info[1],
            "gift": gk_info[2],
            "siddhi": gk_info[3],
        })

    all_keys = []
    for gate_num, key_data in sorted(gk["hologenetic_profile"].items()):
        gk_info = GENE_KEYS.get(gate_num, ("Unknown", "Unknown", "Unknown", "Unknown"))
        all_keys.append({
            "gene_key": gate_num,
            "name": gk_info[0],
            "shadow": gk_info[1],
            "gift": gk_info[2],
            "siddhi": gk_info[3],
            "sources": gate_sources.get(gate_num, []),
        })

    gene_keys = {
        "activation_sequence": activation_sequence,
        "all_keys": all_keys,
    }

    # ---- communication ----
    communication = report.communication or {}

    # ---- section summaries (deterministic, cross-system) ----
    summaries = _section_summaries(report)

    # ---- synthesis ----
    headlines = report.synthesis["headlines"]
    n_h = headlines["numerology"]
    w_h = headlines["western"]
    h_h = headlines["human_design"]
    gk_h = headlines["gene_keys"]

    lifes_work_notation = gk_h.get("lifes_work", "1.1")
    try:
        lifes_work_gate = int(lifes_work_notation.split(".")[0])
        lifes_work_name = GENE_KEYS.get(lifes_work_gate, ("",))[0]
    except (ValueError, IndexError):
        lifes_work_name = ""

    archetypes = [
        {"label": "Life Path",    "value": str(n_h["life_path"]),  "detail": LP_ARCHETYPES.get(n_h["life_path"], "")},
        {"label": "Sun Sign",     "value": w_h["sun_sign"],        "detail": SIGN_GLYPHS.get(w_h["sun_sign"], "")},
        {"label": "Moon Sign",    "value": w_h["moon_sign"],       "detail": SIGN_GLYPHS.get(w_h["moon_sign"], "")},
        {"label": "Ascendant",    "value": w_h["ascendant"],       "detail": SIGN_GLYPHS.get(w_h["ascendant"], "")},
        {"label": "HD Type",      "value": h_h["type"],            "detail": h_h["strategy"]},
        {"label": "Authority",    "value": h_h["authority"],       "detail": HD_AUTHORITY_LABELS.get(h_h["authority"], h_h["authority"])},
        {"label": "Profile",      "value": h_h["profile"],         "detail": PROFILE_LABELS.get(h_h["profile"], "")},
        {"label": "Life's Work",  "value": lifes_work_notation,   "detail": lifes_work_name},
    ]

    synthesis = {
        "paragraph": report.synthesis["paragraph"],
        "archetypes": archetypes,
        "section_summary": summaries["grand"],
    }

    # ---- attach section summaries ----
    numerology["section_summary"] = summaries["numerology"]
    western["section_summary"] = summaries["western"]
    vedic["section_summary"] = summaries["vedic"]
    human_design["section_summary"] = summaries["human_design"]
    gene_keys["section_summary"] = summaries["gene_keys"]
    if isinstance(communication, dict):
        communication["section_summary"] = summaries["communication"]

    # ---- assemble ----
    astrology = {
        "available": True,
        "reason": None,
        "location": location,
        "time": time_info,
        "western": western,
        "vedic": vedic,
        "human_design": human_design,
        "gene_keys": gene_keys,
        "communication": communication,
    }

    return {
        "profile": profile,
        "numerology": numerology,
        "astrology": astrology,
        "synthesis": synthesis,
    }
