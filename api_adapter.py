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

    # ---- numerology ----
    numerology = {
        "life_path": _num_obj(report.numerology, "life_path"),
        "expression": _num_obj(report.numerology, "expression"),
        "soul_urge": _num_obj(report.numerology, "soul_urge"),
        "personality": _num_obj(report.numerology, "personality"),
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
    }

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
