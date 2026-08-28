"""Stable selector preference order for common application fields (spec §16).

We prefer accessible roles/labels/placeholders over fragile CSS. Each entry is
a list of strategies tried in order against the application form.
"""
from __future__ import annotations

# {canonical_field: [ (strategy, match) ... ]} where strategy in
# {"label", "placeholder", "role", "name"}
FIELD_SELECTORS: dict[str, list[tuple[str, str]]] = {
    "full_name": [
        ("label", "full name"), ("label", "name"), ("name", "fullName"),
        ("placeholder", "full name"),
    ],
    "email": [("label", "email"), ("name", "email"), ("placeholder", "email")],
    "phone": [("label", "phone"), ("name", "phone"), ("placeholder", "phone")],
    "location": [("label", "location"), ("label", "city"), ("name", "location")],
    "linkedin": [
        ("label", "linkedin"), ("placeholder", "linkedin"), ("name", "linkedin_url"),
    ],
    "website": [("label", "website"), ("label", "portfolio"), ("name", "website")],
    "cover_letter": [
        ("label", "cover letter"), ("name", "cover_letter"), ("placeholder", "why"),
    ],
    "resume": [("label", "resume"), ("label", "cv"), ("name", "resume")],
    "years_experience": [
        ("label", "years"), ("name", "years_experience"), ("label", "experience"),
    ],
}


def strategies_for(field: str) -> list[tuple[str, str]]:
    """Return the ordered strategies for a canonical field (or empty list)."""
    return FIELD_SELECTORS.get(field, [])
