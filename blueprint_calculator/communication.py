"""
Communication Style Engine — deterministic cross-system analysis.

Scores five cognitive axes from Human Design, Western Astrology, and
Numerology indicators, then derives an archetype and delivery preferences.
No LLM or probabilistic reasoning — every output traces to a specific
data point already computed in the pipeline.
"""
from __future__ import annotations

from .constants.hd_wheel import LINE_NAMES


def record_communication(numerology: dict, western: dict, hd: dict, gk: dict) -> dict:
    """Derive communication style profile from cross-system data."""

    # -- Extract indicators --
    defined_centers = set(hd.get("defined_centers", []))
    open_centers = set(hd.get("open_centers", []))
    profile = hd.get("profile", "")
    profile_lines = [int(x) for x in profile.split("/")] if "/" in profile else []
    channels_list = hd.get("defined_channels", [])
    channel_set = set(tuple(sorted(c)) for c in channels_list)

    mercury_sign = western.get("placements", {}).get("Mercury", {}).get("sign_name", "")
    element_balance = western.get("element_balance", {})
    dominant_element = max(element_balance, key=element_balance.get) if element_balance else None

    expression = numerology.get("expression", 5)
    life_path = numerology.get("life_path", 5)
    hd_type = hd.get("type", "Generator")

    # -- Step 1: Score cognitive axes --
    mental_certainty = (
        (2 if "Ajna" in defined_centers else 0) +
        (1 if "Head" in defined_centers else 0) +
        (1 if 1 in profile_lines else 0) +
        (1 if 5 in profile_lines else 0)
    )
    relational = (
        (1 if 2 in profile_lines else 0) +
        (1 if 4 in profile_lines else 0) +
        (1 if 6 in profile_lines else 0) +
        (1 if "Throat" in open_centers else 0)
    )
    experiential = (
        (2 if 3 in profile_lines else 0) +
        (1 if {(3, 60), (36, 35)} & channel_set else 0)
    )
    analytical = (
        (2 if mercury_sign in ("Virgo", "Capricorn", "Aquarius") else 0) +
        (1 if expression in (7, 9) else 0) +
        (1 if {(17, 62), (4, 63)} & channel_set else 0)
    )
    intuitive = (
        (2 if mercury_sign in ("Pisces", "Scorpio", "Cancer") else 0) +
        (1 if dominant_element == "Water" else 0) +
        (1 if "Ajna" in open_centers else 0)
    )

    scores = {
        "mental_certainty": mental_certainty,
        "relational": relational,
        "experiential": experiential,
        "analytical": analytical,
        "intuitive": intuitive,
    }

    # -- Step 2: Derive archetype --
    if analytical > intuitive and mental_certainty >= 3:
        archetype = "The Systematic Analyst"
        summary = "You process information through structured frameworks and proven methodologies. Rigorous mental infrastructure gives you the confidence to teach and be taught systematically."
        processing_style = "Linear, logical, evidence-based — you build understanding step by step, needing the 'why' behind each claim before you move on."
    elif intuitive > analytical and relational >= 2:
        archetype = "The Empathic Visionary"
        summary = "You receive information through feeling, pattern recognition, and relational context. Complex ideas land faster through metaphor and personal story than through data alone."
        processing_style = "Non-linear, holistic — you sense the whole before examining the parts, and trust gut-level knowing as valid intelligence."
    elif experiential >= 2:
        archetype = "The Trial-and-Error Pioneer"
        summary = "Your deepest learning comes through direct experience and iterative discovery. Abstract concepts crystallize only once you've touched them."
        processing_style = "Hands-on, kinesthetic — you need to try things to truly understand them. Failure is data, not defeat."
    elif relational >= 2 and (4 in profile_lines or 6 in profile_lines):
        archetype = "The Networked Strategist"
        summary = "You assimilate information through trusted relationships and community context. The right introduction opens more doors than the most thorough research."
        processing_style = "Social, collaborative — ideas come alive through dialogue and shared meaning rather than solo study."
    elif analytical > intuitive:
        archetype = "The Methodical Researcher"
        summary = "You approach information through careful analysis and systematic inquiry, preferring depth over breadth."
        processing_style = "Detailed, thorough — you need complete information before drawing conclusions and resist being rushed."
    elif intuitive > analytical:
        archetype = "The Intuitive Synthesizer"
        summary = "You integrate complex information through gut feeling and creative leaps, often arriving at conclusions before you can explain how."
        processing_style = "Associative, fluid — insights arrive whole rather than step by step; you trust internal knowing."
    elif mental_certainty >= 2:
        archetype = "The Conceptual Architect"
        summary = "You build mental models to understand and communicate complex systems. You teach best when you can map the territory first."
        processing_style = "Conceptual, abstract — you need the big picture before the details, and think best in frameworks."
    else:
        archetype = "The Adaptive Communicator"
        summary = "Your communication style is context-sensitive and fluidly responsive to the moment, the person, and the environment."
        processing_style = "Flexible, present-oriented — you read each situation and adapt accordingly rather than defaulting to a fixed approach."

    # -- Step 3: Delivery preferences --
    if life_path in (1, 8) or expression in (1, 8):
        tone = "Direct and authoritative — lead with the bottom line; context supports, not precedes."
    elif life_path in (2, 6, 9) or expression in (2, 6, 9):
        tone = "Warm and relational — anchor ideas in personal relevance and shared meaning."
    elif life_path in (11, 22, 33) or expression in (11, 22, 33):
        tone = "Visionary and inspiring — connect everyday detail to the larger purpose and possibility."
    else:
        tone = "Thoughtful and curious — balance information density with open-ended inquiry."

    if dominant_element == "Fire":
        fmt = "Stories, inspiration, and big-picture vision — lead with the WHY, not the HOW."
    elif dominant_element == "Earth":
        fmt = "Practical steps and tangible examples — ground every concept in real-world application."
    elif dominant_element == "Air":
        fmt = "Concepts, frameworks, and comparative analysis — maps and models over raw data."
    else:
        fmt = "Metaphor, emotional resonance, and narrative arc — feeling first, then facts."

    if "Sacral" in defined_centers:
        pacing = "Respond in the moment when the energy is alive — sustained focus follows the natural gut response."
    elif hd_type == "Manifestor":
        pacing = "Initiate when the impulse is clear — allow pauses between initiatives for the field to integrate."
    elif hd_type == "Projector":
        pacing = "Invite-driven depth over broad coverage — quality of understanding over speed of delivery."
    elif hd_type == "Reflector":
        pacing = "Slow, cyclical integration — revisit ideas over a lunar cycle before drawing final conclusions."
    else:
        pacing = "Follow the natural response rhythm — trust the gut-yes as the green light to proceed."

    avoids = []
    if "Head" in open_centers:
        avoids.append("information overload from unfiltered mental pressure")
    if "Ajna" in open_centers:
        avoids.append("premature certainty or fixed mental positions")
    if "Throat" in open_centers:
        avoids.append("speaking to fill silence — wait for genuine invitation")
    if "G" in open_centers:
        avoids.append("identity-based filtering — stay curious rather than fixed in self-concept")
    if "Sacral" in open_centers:
        avoids.append("pushing past natural energy limits — honor completion signals")
    if "Solar Plexus" in open_centers:
        avoids.append("emotionally amplified urgency — avoid decisions made in reactive states")
    avoid = avoids[0] if avoids else "No significant conditioning patterns identified"

    delivery = {"tone": tone, "format": fmt, "pacing": pacing, "avoid": avoid}

    # -- Step 4: Cognitive strengths (top 3 with source attribution) --
    strength_descriptions = {
        "mental_certainty": (
            "Structured Mental Processing",
            f"Defined {'Ajna ' if 'Ajna' in defined_centers else ''}{'and Head centers provide' if 'Head' in defined_centers else 'center provides'} consistent, reliable cognitive frameworks",
        ),
        "relational": (
            "Relational Intelligence",
            f"Profile {profile} orientation attunes naturally to interpersonal dynamics and social learning",
        ),
        "experiential": (
            "Experiential Learning Drive",
            f"Profile {profile} line 3 creates deep learning through direct trial, iteration, and discovery",
        ),
        "analytical": (
            "Analytical Depth",
            f"Mercury in {mercury_sign or 'analytical signs'} with Expression {expression} sharpens precision and logical structure",
        ),
        "intuitive": (
            "Intuitive Pattern Recognition",
            f"Mercury in {mercury_sign or 'receptive signs'}{' and Water-dominant field' if dominant_element == 'Water' else ''} attunes to non-logical intelligence signals",
        ),
    }

    top_strengths = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    strengths = [
        {"strength": strength_descriptions[k][0], "source": strength_descriptions[k][1]}
        for k, v in top_strengths
        if v > 0
    ][:3]

    # -- Step 5: Key indicators (top 5 cross-system) --
    line_label_0 = LINE_NAMES.get(profile_lines[0], "") if profile_lines else ""
    line_label_1 = LINE_NAMES.get(profile_lines[1], "") if len(profile_lines) > 1 else ""

    key_indicators = []
    if mercury_sign:
        key_indicators.append({
            "system": "Western Astrology",
            "indicator": f"Mercury in {mercury_sign}",
            "implication": "Shapes raw cognitive wiring, communication style, and language pattern",
        })
    if profile:
        key_indicators.append({
            "system": "Human Design",
            "indicator": f"Profile {profile} ({line_label_0} / {line_label_1})" if line_label_1 else f"Profile {profile}",
            "implication": "Defines the social role, learning archetype, and interaction strategy",
        })
    if defined_centers:
        key_indicators.append({
            "system": "Human Design",
            "indicator": f"Defined: {', '.join(sorted(defined_centers))}",
            "implication": "Consistent, reliable energetic channels that others can count on",
        })
    key_indicators.append({
        "system": "Numerology",
        "indicator": f"Life Path {life_path} · Expression {expression}",
        "implication": "Core purpose and natural communication register encoded in birth data",
    })
    if dominant_element:
        key_indicators.append({
            "system": "Western Astrology",
            "indicator": f"{dominant_element} element dominant",
            "implication": "Informs preferred delivery medium, learning modality, and emotional register",
        })

    return {
        "archetype": archetype,
        "summary": summary,
        "processing_style": processing_style,
        "delivery": delivery,
        "strengths": strengths,
        "key_indicators": key_indicators[:5],
    }
