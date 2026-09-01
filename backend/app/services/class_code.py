"""
The class code: which of a subject's parallel classes a unit offering is.

WHY THIS EXISTS.
KOI runs the same subject more than once in a trimester. ICT730 may have
two lecture classes and a non-campus class running at the same time, with
different lecturers, different students and — because each is taught
separately — genuinely different results. Until now the database refused
to hold them: `units` was unique on (unit_code, year, teaching_period),
so the second ICT730 of a trimester could not be created at all.

    ICT730LA1     lecture class 1
    ICT730LA2     lecture class 2
    ICT730NCLA    the non-campus class
    ICT730        a unit with no class split (the existing rows)

ONE COLUMN, NOT TWO, AND THE REASON IS SQL NULL.
The obvious model is `class_type` ("LA"/"NCLA") plus `class_number`, both
nullable. It is wrong, and quietly so: in SQL, NULL is not equal to
NULL, so a UNIQUE constraint containing a nullable column stops
constraining the moment that column is NULL. Two rows of
(ICT730, 2026, T2, NULL, NULL) would both be accepted on PostgreSQL —
which is exactly the duplicate the old constraint existed to prevent.
Storing ONE non-null `class_code` with "" meaning "no class" keeps the
empty case a real value the constraint can compare, so the guarantee
holds identically on SQLite and PostgreSQL.

`class_type` and `class_number` still exist — as derived properties for
the form, and as the two fields the API accepts. They are composed here
and never stored apart.

THE VOCABULARY IS LOCKED.
"LA" and "NCLA" only, LA numbered and NCLA not, because that is what KOI
uses. A free-text class field would be "LA1", "la1", "LA 1" and "Class 1"
inside a month, and every count grouped by class would silently
under-report from then on. Same reasoning as the audit log's action list.
"""

import re
from typing import Optional

#: The two class types, in the order the form offers them.
CLASS_TYPES: tuple[str, ...] = ("LA", "NCLA")

CLASS_TYPE_LABELS: dict[str, str] = {
    "LA": "LA — on-campus class",
    "NCLA": "NCLA — non-campus class",
}

#: LA carries a number, NCLA does not. A single NCLA runs per offering,
#: so "NCLA1" would be a number that never reaches 2 — and a counter
#: that can only ever read one is noise in every label that prints it.
NUMBERED_TYPES: tuple[str, ...] = ("LA",)

MAX_CLASS_NUMBER = 99

#: The stored form. Anchored, and deliberately strict: this is what the
#: uniqueness guarantee is computed over, so a value that slips past it
#: is a duplicate nobody can see.
CLASS_CODE_RE = re.compile(r"^(?:LA[1-9][0-9]?|NCLA)$")

#: What "no class" is stored as. Never NULL — see the module docstring.
NO_CLASS = ""


class ClassCodeError(ValueError):
    """A class code that is not in the locked vocabulary."""


def compose(class_type: Optional[str], class_number: Optional[int]) -> str:
    """
    Builds the stored class code from the two fields the form submits.

    Returns "" when no type was chosen, which is a unit with no class
    split — the state every existing row is in and a perfectly valid one.

    Raises ClassCodeError with a sentence a coordinator can act on. These
    strings are printed under the field that caused them, so "invalid
    input" would be a message that tells the person nothing they did not
    already know.
    """
    if class_type is None or str(class_type).strip() == "":
        # A number without a type is a form half-filled, not a class.
        # Silently dropping it would let someone believe they had set
        # class 2 and produce a unit with no class at all.
        if class_number is not None:
            raise ClassCodeError(
                "Choose a class type before entering a class number."
            )
        return NO_CLASS

    normalised = str(class_type).strip().upper()
    if normalised not in CLASS_TYPES:
        raise ClassCodeError(
            f"Class type must be one of {', '.join(CLASS_TYPES)}."
        )

    if normalised in NUMBERED_TYPES:
        if class_number is None:
            raise ClassCodeError(f"{normalised} classes need a class number.")
        if not isinstance(class_number, int) or isinstance(class_number, bool):
            raise ClassCodeError("The class number must be a whole number.")
        if class_number < 1 or class_number > MAX_CLASS_NUMBER:
            raise ClassCodeError(
                f"The class number must be between 1 and {MAX_CLASS_NUMBER}."
            )
        return f"{normalised}{class_number}"

    # NCLA takes no number. Refused rather than ignored: a coordinator
    # who typed 2 believes they created a second non-campus class.
    if class_number is not None:
        raise ClassCodeError(f"{normalised} classes are not numbered.")
    return normalised


def validate(class_code: str) -> str:
    """Checks an already-composed code, returning it normalised."""
    value = (class_code or "").strip().upper()
    if value == NO_CLASS:
        return NO_CLASS
    if not CLASS_CODE_RE.match(value):
        raise ClassCodeError(
            f"{class_code!r} is not a valid class code. Use LA followed by a "
            "number (LA1, LA2) or NCLA."
        )
    return value


def split(class_code: Optional[str]) -> tuple[Optional[str], Optional[int]]:
    """The inverse of `compose`, for rendering the edit form."""
    value = (class_code or "").strip().upper()
    if value == NO_CLASS:
        return None, None
    if value.startswith("LA"):
        digits = value[2:]
        return "LA", int(digits) if digits.isdigit() else None
    if value == "NCLA":
        return "NCLA", None
    return None, None


def full_code(unit_code: Optional[str], class_code: Optional[str]) -> str:
    """
    The identity a human uses: "ICT730LA1", or "ICT730" with no class.

    NO SEPARATOR, because that is how KOI writes it. This string is what
    goes on the unit card, in the dashboard filter, in the report header,
    in the PDF filename and in the typed unlock confirmation — every
    place where two classes of one subject would otherwise be
    indistinguishable.
    """
    return f"{(unit_code or '').strip()}{(class_code or '').strip().upper()}"