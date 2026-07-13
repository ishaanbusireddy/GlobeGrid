"""v8.16 — the INTERNAL, strongly-worded definition of every event category.

The owner's complaint was exact: "too many things are being categorized as
other … its all over the place … too many random things going into domestic."
These paragraphs are the single normative source for what belongs where. They
are (a) injected into every LLM prompt that classifies or reviews events,
(b) the reference the keyword tables in processing/extract.py are tuned
against, and (c) surfaced in the ? guide so the user can see the contract.
When a classification dispute comes up, THIS file wins.
"""

CATEGORY_DEFINITIONS = {
    "conflict": (
        "Active organized violence between armed actors: battles, strikes, "
        "shelling, drone/missile attacks, offensives, insurgent attacks, "
        "ceasefire violations, war casualties, territorial capture. The "
        "violence must be happening or have just happened. NOT posturing, "
        "NOT exercises, NOT arms deals (those are 'military'), NOT ordinary "
        "crime (that is 'domestic')."),
    "military": (
        "Armed-forces activity SHORT of active combat: deployments, drills "
        "and exercises, weapons tests, procurement and arms deals, defense "
        "budgets, mobilization, force posture changes, military diplomacy "
        "(basing agreements, joint patrols). If people are being shot at "
        "right now, it is 'conflict' instead."),
    "geopolitics": (
        "Relations BETWEEN states and international bodies: summits, "
        "treaties, sanctions, embassies and expulsions, border and maritime "
        "disputes, UN votes, alliance politics, state visits, international "
        "law, recognition questions, NATIONAL elections and leadership "
        "changes with cross-border significance. A country's PURELY internal "
        "politics without international dimension is 'domestic'."),
    "finance": (
        "Markets, money and macroeconomics: equities, bonds, currencies, "
        "commodities prices, central banks and interest rates, inflation, "
        "GDP releases, trade figures and tariffs, corporate earnings and "
        "M&A of global significance, sovereign debt, IMF/World Bank "
        "programs. Big-picture economic POLICY belongs here, not in "
        "'domestic', even when announced by one government."),
    "technology": (
        "The tech world: AI, chips and semiconductors, software platforms, "
        "cybersecurity and breaches, space launches and satellites, "
        "telecoms, consumer electronics, biotech tools, tech regulation and "
        "antitrust, research breakthroughs. A tech company's EARNINGS story "
        "may be finance; its product/technology story is technology."),
    "disaster": (
        "Natural and industrial catastrophes: earthquakes, floods, storms, "
        "wildfires, volcanic eruptions, droughts, landslides, major "
        "industrial/transport accidents, building collapses. Sudden, "
        "physical, destructive events — not slow policy failures."),
    "health": (
        "Disease and public health: outbreaks, epidemics and pandemics, "
        "vaccines, WHO declarations, drug approvals, health-system crises, "
        "food-safety emergencies. Hospital attacks in a war are 'conflict'; "
        "the epidemiology is 'health'."),
    "domestic": (
        "A country's INTERNAL civil life with no strong international or "
        "macro-financial dimension: local crime and courts, sports, "
        "entertainment and culture, local elections and municipal politics, "
        "strikes and protests over domestic issues, education, transport, "
        "weather (below disaster scale), human-interest stories. This is "
        "the home for 'random national news' — NOT for finance, NOT for "
        "national elections with international stakes, NOT for anything a "
        "foreign ministry would comment on."),
    "other": (
        "Genuinely unclassifiable content only. If a story plausibly fits "
        "ANY category above, it goes there — 'other' is a failure bucket to "
        "be kept as close to empty as possible, not a catch-all."),
}


def definitions_prompt_block() -> str:
    """The definitions as a compact prompt block for LLM classification and
    title-review calls."""
    return "\n".join(f"- {cat}: {text}" for cat, text in
                     CATEGORY_DEFINITIONS.items())
