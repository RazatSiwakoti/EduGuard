"""
The class code: the locked vocabulary, and the uniqueness guarantee it
has to keep.

Section [4] is the reason this suite exists. The obvious way to model a
class is `class_type` plus `class_number`, both nullable — and it is
wrong in a way no amount of reading catches, because SQL does not treat
NULL as equal to NULL. A UNIQUE constraint containing a nullable column
stops constraining the moment that column is NULL, so two classless
ICT730 rows in one trimester would BOTH be accepted and the duplicate
the old constraint existed to refuse would be back. [4] proves the
empty-string design actually closes that, against a real database, by
trying the duplicate and requiring it to fail.

Run:  cd backend && PYTHONPATH=. python3 tests/test_class_code.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.routes.criteria import router as criteria_router
from app.api.routes.units import router as units_router
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.base import Base
from app.models.enums import UserRole
from app.models.unit import Unit
from app.models.user import User
from app.services import class_code as cc

failures: list[str] = []
section = 0
checks = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if condition:
        print(f"    PASS  {label}")
    else:
        print(f"    FAIL  {label}  {detail}")
        failures.append(label)


def heading(title: str) -> None:
    global section
    section += 1
    print(f"\n[{section}] {title}")


def raises(fn) -> str:
    """Returns the error message, or "" if nothing was raised."""
    try:
        fn()
    except cc.ClassCodeError as exc:
        return str(exc)
    return ""


# ---------------------------------------------------------------------

heading("Composing a class code from the form's two fields")

check("LA with a number composes", cc.compose("LA", 1) == "LA1", cc.compose("LA", 1))
check("LA2 composes", cc.compose("LA", 2) == "LA2")
check("a two-digit class composes", cc.compose("LA", 12) == "LA12")
check("NCLA composes with no number", cc.compose("NCLA", None) == "NCLA")
check("nothing chosen is no class, not an error", cc.compose(None, None) == "")
check("an empty type is also no class", cc.compose("", None) == "")
check("lowercase is normalised", cc.compose("la", 3) == "LA3")
check("whitespace is trimmed", cc.compose("  LA  ", 3) == "LA3")

check("LA without a number is refused",
      "need a class number" in raises(lambda: cc.compose("LA", None)),
      raises(lambda: cc.compose("LA", None)))
check("NCLA WITH a number is refused - it is not numbered",
      "not numbered" in raises(lambda: cc.compose("NCLA", 2)),
      raises(lambda: cc.compose("NCLA", 2)))
check("a number with no type is refused, not silently dropped",
      "before entering a class number" in raises(lambda: cc.compose(None, 2)),
      raises(lambda: cc.compose(None, 2)))
check("class 0 is refused", "between 1 and" in raises(lambda: cc.compose("LA", 0)))
check("a negative class is refused", "between 1 and" in raises(lambda: cc.compose("LA", -1)))
check("class 100 is refused", "between 1 and" in raises(lambda: cc.compose("LA", 100)))
check("True is not a class number", "whole number" in raises(lambda: cc.compose("LA", True)))


heading("The vocabulary is locked to LA and NCLA")

for bad in ("TUT", "LEC", "A", "CLASS", "la1", "NC", "ONLINE"):
    check(f"{bad!r} is not a class type", "must be one of" in raises(lambda b=bad: cc.compose(b, 1)))

check("only two types are offered", cc.CLASS_TYPES == ("LA", "NCLA"), str(cc.CLASS_TYPES))
check("only LA is numbered", cc.NUMBERED_TYPES == ("LA",), str(cc.NUMBERED_TYPES))
check("every type has a label a coordinator can read",
      set(cc.CLASS_TYPE_LABELS) == set(cc.CLASS_TYPES))

check("validate accepts a stored code", cc.validate("LA1") == "LA1")
check("validate accepts the empty code", cc.validate("") == "")
check("validate normalises case", cc.validate("ncla") == "NCLA")
check("validate refuses free text",
      "not a valid class code" in raises(lambda: cc.validate("Class 1")))
check("validate refuses LA0", "not a valid class code" in raises(lambda: cc.validate("LA0")))
check("validate refuses a bare LA", "not a valid class code" in raises(lambda: cc.validate("LA")))


heading("Splitting and printing round-trip")

for value in ("LA1", "LA2", "LA12", "NCLA", ""):
    kind, number = cc.split(value)
    check(f"{value or '(none)'} splits and recomposes",
          cc.compose(kind, number) == value, f"{kind!r}/{number!r}")

check("the full code has no separator", cc.full_code("ICT730", "LA1") == "ICT730LA1")
check("no class means the subject alone", cc.full_code("ICT730", "") == "ICT730")
check("NCLA prints in full", cc.full_code("ICT730", "NCLA") == "ICT730NCLA")


# ---------------------------------------------------------------------

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
configure_mappers()
Base.metadata.create_all(engine)
db = sessionmaker(bind=engine)()

admin = User(email="admin@example.com", full_name="Ada Admin", role=UserRole.ADMIN,
             hashed_password="x", is_active=True)
db.add(admin)
db.commit()


def make_unit(code: str, klass: str, period: str = "T2", year: int = 2026) -> Unit:
    unit = Unit(
        unit_code=code, unit_name="Systems Analysis", year=year,
        teaching_period=period, level="master", start_date=date(2026, 2, 23),
        class_code=klass, is_active=True, status="UNASSIGNED",
    )
    db.add(unit)
    db.commit()
    return unit


heading("The database refuses a duplicate class - INCLUDING the empty one")

first = make_unit("ICT730", "LA1")
check("the first class is created", first.id is not None)
check("its full code reads ICT730LA1", first.full_code == "ICT730LA1", first.full_code)

second = make_unit("ICT730", "LA2")
check("a SECOND class of the same subject is now possible", second.id is not None)
check("which was the whole point of this change", second.full_code == "ICT730LA2")

ncla = make_unit("ICT730", "NCLA")
check("and so is the non-campus class", ncla.full_code == "ICT730NCLA")


def rejected(code: str, klass: str, period: str = "T2", year: int = 2026) -> bool:
    try:
        make_unit(code, klass, period, year)
    except IntegrityError:
        db.rollback()
        return True
    return False


check("the SAME class twice is refused", rejected("ICT730", "LA1"))
check("...and so is a repeated NCLA", rejected("ICT730", "NCLA"))

# THE TRAP. With nullable class_type/class_number this would pass twice
# on PostgreSQL, because NULL != NULL inside a UNIQUE constraint.
classless = make_unit("ICT800", "")
check("a unit with NO class is allowed", classless.full_code == "ICT800", classless.full_code)
check("a SECOND classless unit of the same subject is REFUSED - the "
      "NULL-uniqueness trap is closed", rejected("ICT800", ""))

check("the same subject in a DIFFERENT trimester is fine",
      not rejected("ICT730", "LA1", period="T3"))
check("the same subject in a different YEAR is fine",
      not rejected("ICT730", "LA1", period="T2", year=2027))


# ---------------------------------------------------------------------

acting = {"user": admin}
api = FastAPI()
api.include_router(units_router)
api.include_router(criteria_router)
api.dependency_overrides[get_db] = lambda: db
api.dependency_overrides[get_current_user] = lambda: acting["user"]
client = TestClient(api)

BASE = {"unit_name": "Networks", "year": 2026, "teaching_period": "T1", "level": "master"}


heading("Over real HTTP: creating a class")

created = client.post("/admin/units", json={**BASE, "unit_code": "ICT500", "class_type": "LA", "class_number": 1})
check("a class is created", created.status_code == 201, created.text[:250])
body = created.json()
check("the response carries the class code", body["class_code"] == "LA1", str(body.get("class_code")))
check("and the full code", body["full_code"] == "ICT500LA1", str(body.get("full_code")))
check("and the split fields for the edit form",
      body["class_type"] == "LA" and body["class_number"] == 1, str(body))
check("unit_code remains the SUBJECT", body["unit_code"] == "ICT500", body["unit_code"])

second_class = client.post("/admin/units", json={**BASE, "unit_code": "ICT500", "class_type": "LA", "class_number": 2})
check("a second class of the same subject is accepted", second_class.status_code == 201, second_class.text[:250])

dup = client.post("/admin/units", json={**BASE, "unit_code": "ICT500", "class_type": "LA", "class_number": 1})
check("the same class twice is a 409", dup.status_code == 409, str(dup.status_code))
check("and the message names the class, not just 'this unit'",
      "ICT500LA1" in dup.json()["detail"], dup.text[:200])

no_class = client.post("/admin/units", json={**BASE, "unit_code": "ICT600"})
check("a unit with no class is still creatable", no_class.status_code == 201, no_class.text[:200])
check("its full code is the bare subject", no_class.json()["full_code"] == "ICT600")
dup_none = client.post("/admin/units", json={**BASE, "unit_code": "ICT600"})
check("and duplicating it is refused", dup_none.status_code == 409)
check("with a message suggesting a class code as the way forward",
      "class code" in dup_none.json()["detail"].lower(), dup_none.text[:250])


heading("Over real HTTP: the API refuses a bad class")

check("an unknown type is a 422 from the schema",
      client.post("/admin/units", json={**BASE, "unit_code": "ICT510", "class_type": "TUT", "class_number": 1}).status_code == 422)
check("class 0 is a 422",
      client.post("/admin/units", json={**BASE, "unit_code": "ICT510", "class_type": "LA", "class_number": 0}).status_code == 422)

la_no_number = client.post("/admin/units", json={**BASE, "unit_code": "ICT510", "class_type": "LA"})
check("LA with no number is a 400, not a 422", la_no_number.status_code == 400, str(la_no_number.status_code))
check("...and says what to do", "class number" in la_no_number.json()["detail"], la_no_number.text[:200])

ncla_numbered = client.post("/admin/units", json={**BASE, "unit_code": "ICT510", "class_type": "NCLA", "class_number": 1})
check("NCLA with a number is a 400", ncla_numbered.status_code == 400, str(ncla_numbered.status_code))
check("...and says NCLA is not numbered", "not numbered" in ncla_numbered.json()["detail"])

number_only = client.post("/admin/units", json={**BASE, "unit_code": "ICT510", "class_number": 2})
check("a number with no type is a 400", number_only.status_code == 400, str(number_only.status_code))
check("nothing was created by any refused request",
      db.query(Unit).filter(Unit.unit_code == "ICT510").count() == 0,
      str(db.query(Unit).filter(Unit.unit_code == "ICT510").count()))


heading("Over real HTTP: changing a class after creation")

target_id = created.json()["id"]
renamed = client.patch(f"/admin/units/{target_id}", json={"class_type": "LA", "class_number": 3})
check("a class can be changed - a label is not a rule", renamed.status_code == 200, renamed.text[:200])
check("the full code moved", renamed.json()["full_code"] == "ICT500LA3", renamed.json()["full_code"])

clash = client.patch(f"/admin/units/{target_id}", json={"class_type": "LA", "class_number": 2})
check("moving onto an existing class is a 409", clash.status_code == 409, str(clash.status_code))
check("...naming the clash", "ICT500LA2" in clash.json()["detail"], clash.text[:200])
db.refresh(db.get(Unit, target_id))
check("and the unit did NOT move", db.get(Unit, target_id).class_code == "LA3",
      db.get(Unit, target_id).class_code)

half = client.patch(f"/admin/units/{target_id}", json={"class_number": 5})
check("a number without its type is a 400", half.status_code == 400, str(half.status_code))
check("...and says to send both", "together" in half.json()["detail"], half.text[:200])

cleared = client.patch(f"/admin/units/{target_id}", json={"class_type": None, "class_number": None})
check("a class can be cleared back to none", cleared.status_code == 200, cleared.text[:200])
check("leaving the bare subject", cleared.json()["full_code"] == "ICT500", cleared.json()["full_code"])

untouched = client.patch(f"/admin/units/{target_id}", json={"unit_name": "Renamed only"})
check("a PATCH that omits the class leaves it alone",
      untouched.status_code == 200 and untouched.json()["class_code"] == "",
      untouched.text[:200])


heading("The typed unlock confirmation names the CLASS, not the subject")

unlock_target = db.query(Unit).filter(Unit.unit_code == "ICT500", Unit.class_code == "LA2").first()
check("the fixture unit is ICT500LA2", unlock_target is not None and unlock_target.full_code == "ICT500LA2")

path = f"/units/{unlock_target.id}/criteria/unlock"
subject_only = client.post(path, json={"unit_code": "ICT500"})
check("typing the bare SUBJECT is refused - it names two classes",
      subject_only.status_code == 400, subject_only.text[:200])
check("...and the message states the full code to type",
      "ICT500LA2" in subject_only.json()["detail"], subject_only.text[:200])

full = client.post(path, json={"unit_code": "ict500la2"})
check("typing the full code works, case-insensitively", full.status_code == 200, full.text[:200])

# On a unit with no class, full_code IS unit_code, so nothing changed
# for every unit that existed before this feature.
plain = db.query(Unit).filter(Unit.unit_code == "ICT600").first()
plain_unlock = client.post(f"/units/{plain.id}/criteria/unlock", json={"unit_code": "ICT600"})
check("a classless unit still unlocks with its bare code - no regression",
      plain_unlock.status_code == 200, plain_unlock.text[:200])


heading("The class reaches every place a unit is identified")

from app.services import audit_service  # noqa: E402
from app.services.report_service import build_unit_report  # noqa: E402

event = audit_service.record(
    db, action=audit_service.CRITERIA_UNLOCKED, actor=admin,
    unit=unlock_target, summary="test", entity_type="unit",
)
db.commit()
check("an audit row records the FULL code", event.unit_code == "ICT500LA2", str(event.unit_code))

lecturer = User(email="bo@example.com", full_name="Bo Lecturer", role=UserRole.LECTURER,
                hashed_password="x", is_active=True)
db.add(lecturer)
db.commit()
unlock_target.lecturer_id = lecturer.id
db.commit()

report = build_unit_report(db, lecturer.id, unlock_target.id, checkpoint_week=8)
check("the report carries the class code", report["class_code"] == "LA2", str(report.get("class_code")))
check("and the full code", report["full_code"] == "ICT500LA2", str(report.get("full_code")))
check("while unit_code stays the subject", report["unit_code"] == "ICT500")

from app.services.report_pdf import report_filename  # noqa: E402
name = report_filename(report)
check("the PDF filename uses the full code, so two classes cannot collide",
      name.startswith("ICT500LA2_"), name)

from app.services.dashboard_service import get_lecturer_dashboard  # noqa: E402
dash = get_lecturer_dashboard(db, lecturer.id, checkpoint_week=8)
check("the dashboard unit carries the full code",
      dash["units"] and dash["units"][0]["full_code"] == "ICT500LA2",
      str(dash["units"][:1]))
check("and the subject, so classes can be grouped",
      dash["units"][0]["unit_code"] == "ICT500")


print("\n" + "=" * 62)
if failures:
    print(f"FAILED: {len(failures)} of {checks} checks across {section} sections")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections, {checks} checks)")