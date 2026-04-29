"""Pre-built routine templates surfaced through GET /routines/templates.

Templates are read-only suggestions. Selecting a template in the UI
pre-fills the New Routine form; the user can then edit any field
(name, days, steps, points, etc.) before saving via the normal
POST /routines path. There is no special "create from template"
endpoint — templates are just hydrated payloads.

Days of week: 0=Monday … 6=Sunday (matches the Routine model).
"""
from __future__ import annotations

from typing import Final


WEEKDAYS: Final[list[int]] = [0, 1, 2, 3, 4]
EVERY_DAY: Final[list[int]] = [0, 1, 2, 3, 4, 5, 6]


ROUTINE_TEMPLATES: Final[list[dict]] = [
    {
        "id": "morning-routine",
        "name": "Morning Routine",
        "description": "Wake up, get ready, and out the door on time.",
        "icon": "🌅",
        "time_block": "morning",
        "days_of_week": WEEKDAYS,
        "steps": [
            {"label": "Brush teeth",     "icon": "🪥", "points_value": 5},
            {"label": "Wash face",       "icon": "🧼", "points_value": 5},
            {"label": "Get dressed",     "icon": "👕", "points_value": 5},
            {"label": "Eat breakfast",   "icon": "🥣", "points_value": 5},
            {"label": "Pack backpack",   "icon": "🎒", "points_value": 5},
        ],
    },
    {
        "id": "after-school-routine",
        "name": "After-School Routine",
        "description": "Decompress, refuel, and tackle homework.",
        "icon": "🎒",
        "time_block": "afternoon",
        "days_of_week": WEEKDAYS,
        "steps": [
            {"label": "Unpack backpack", "icon": "🎒", "points_value": 5},
            {"label": "Snack",           "icon": "🍎", "points_value": 5},
            {"label": "Homework",        "icon": "📚", "points_value": 10},
            {"label": "Free time",       "icon": "🎮", "points_value": 0},
        ],
    },
    {
        "id": "bedtime-routine",
        "name": "Bedtime Routine",
        "description": "Wind down for a good night's sleep.",
        "icon": "🌙",
        "time_block": "bedtime",
        "days_of_week": EVERY_DAY,
        "steps": [
            {"label": "Pajamas on",      "icon": "🩲", "points_value": 5},
            {"label": "Brush teeth",     "icon": "🪥", "points_value": 5},
            {"label": "Wash face",       "icon": "🧼", "points_value": 5},
            {"label": "Read a book",     "icon": "📖", "points_value": 5},
            {"label": "Lights out",      "icon": "💡", "points_value": 5},
        ],
    },
    {
        "id": "tidy-up",
        "name": "Tidy Up",
        "description": "A quick clean-up sweep before the day ends.",
        "icon": "🧹",
        "time_block": "evening",
        "days_of_week": EVERY_DAY,
        "steps": [
            {"label": "Pick up toys",          "icon": "🧸", "points_value": 5},
            {"label": "Dirty clothes in hamper", "icon": "🧺", "points_value": 5},
            {"label": "Books on the shelf",    "icon": "📚", "points_value": 5},
        ],
    },
]
