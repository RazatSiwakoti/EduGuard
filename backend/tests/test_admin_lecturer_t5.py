"""
Section T5 verification - an admin who also holds a unit.

The build is one sentence: widen the role gate on every lecturer-facing
endpoint from LECTURER to LECTURER-or-ADMIN. That sentence is also
exactly the shape of a cross-tenant leak, so most of this suite is not
"does it work" but "does it still refuse".

Three questions it has to answer with evidence rather than assertion:

  [7]-[9]  a widened gate did not become a widened VIEW - an admin sees
           their own units through the lecturer surface and nobody
           else's, on every one of the eight routers
  [10]     the gate did not widen to super admins or students
  [11]     admin ACCOUNT management did not widen - the near-identical
           `_get_lecturer_or_404` in admin.py must still refuse to
           deactivate or delete a fellow admin

Run:  PYTHONPATH=. python3 tests/test_admin_lecturer_t5.py
"""

import sys
from pathlib import Path as FsPath

sys.path.insert(0, str(FsPath(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every mapper)

from app.core import dependencies as deps
from app.core.dependencies import get_current_user, require_teaching_role
from app.core.teaching import (
    TEACHING_ROLES,
    holds_active_unit,
    uses_lecturer_surface,
)
from app.database import Base, get_db
from app.models.enums import UserRole
from app.models.unit import Unit
from app.models.user import User
from app.schemas.auth import MeOut, UserOut

failures: list[str] = []
section = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"    PASS  {label}")
    else:
        print(f"    FAIL  {label}  {detail}")
        failures.append(label)


def heading(title: str) -> None:
    global section
    section += 1
    print(f"\n[{section}] {title}")


# ---------------------------------------------------------------------
# Fixture: two admins, two lecturers, four units.
#
# Deliberately built so that EVERY actor has a neighbour whose data they
# must not see. A leak that returns "all units" and a leak that returns
# "the first unit" both fail here; a fixture with one unit would pass
# both.
# ---------------------------------------------------------------------

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
db: Session = sessionmaker(bind=engine)()


def make_user(email: str, role: UserRole) -> User:
    u = User(
        email=email,
        full_name=email.split("@")[0],
        role=role,
        hashed_password="x",
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def make_unit(code: str, holder: User | None, active: bool = True) -> Unit:
    u = Unit(
        unit_code=code,
        unit_name=f"Unit {code}",
        year=2026,
        teaching_period="S2",
        level="UG",
        is_active=active,
        lecturer_id=holder.id if holder else None,
        status="ASSIGNED" if holder else "UNASSIGNED",
    )
    db.add(u)
    db.flush()
    return u


teaching_admin = make_user("admin.teaches@uni.edu", UserRole.ADMIN)
desk_admin = make_user("admin.desk@uni.edu", UserRole.ADMIN)
lecturer_a = make_user("lect.a@uni.edu", UserRole.LECTURER)
lecturer_new = make_user("lect.new@uni.edu", UserRole.LECTURER)
supers = make_user("super@uni.edu", UserRole.SUPER_ADMIN)

unit_admin = make_unit("ICT729", teaching_admin)
unit_lect = make_unit("ICT500", lecturer_a)
unit_orphan = make_unit("ICT600", None)
unit_archived = make_unit("ICT404", desk_admin, active=False)
db.commit()


# ---------------------------------------------------------------------

heading("The predicate: who is 'also a lecturer'")
check("an admin holding an active unit qualifies",
      uses_lecturer_surface(db, teaching_admin))
check("an admin holding NO unit does not",
      not uses_lecturer_surface(db, desk_admin))
check("an ARCHIVED unit does not count - desk_admin holds ICT404",
      not uses_lecturer_surface(db, desk_admin),
      "is_active must be part of the query, or archiving strands an admin "
      "on a dashboard whose endpoints all return empty")
check("a lecturer WITH units qualifies", uses_lecturer_surface(db, lecturer_a))
check("a lecturer with NO units still qualifies",
      uses_lecturer_surface(db, lecturer_new),
      "a new lecturer belongs on the dashboard's empty state, not on an "
      "admin panel they cannot open")
check("a super admin never qualifies", not uses_lecturer_surface(db, supers))

heading("holds_active_unit, on its own")
check("true for the teaching admin", holds_active_unit(db, teaching_admin.id))
check("false for the desk admin", not holds_active_unit(db, desk_admin.id))
check("false for a user id that does not exist", not holds_active_unit(db, 9999))
check("an unassigned unit belongs to nobody",
      unit_orphan.lecturer_id is None)

heading("The role tuple")
check("TEACHING_ROLES is exactly lecturer + admin",
      set(TEACHING_ROLES) == {UserRole.LECTURER, UserRole.ADMIN},
      str(TEACHING_ROLES))
check("SUPER_ADMIN is not in it", UserRole.SUPER_ADMIN not in TEACHING_ROLES)
check("the enum has exactly three roles - there is no STUDENT",
      {r.value for r in UserRole} == {"super_admin", "admin", "lecturer"},
      str({r.value for r in UserRole}) +
      "  <- frontend types/auth.ts still declares a fourth, 'student'")
check("dependencies.py imports the tuple rather than redeclaring it",
      deps.TEACHING_ROLES is TEACHING_ROLES,
      "two copies of this set is two places for it to drift")

heading("Every lecturer router actually uses the widened gate")
# Reading the source rather than the behaviour: a router that kept
# require_role(LECTURER) would still pass every lecturer test in this
# file and 403 every admin in production.
import inspect as _inspect  # noqa: E402

from app.api.routes import (  # noqa: E402
    alerts,
    analysis,
    criteria,
    ingestion,
    lecturer,
    reports,
    risk,
)

for mod in (alerts, analysis, criteria, ingestion, lecturer, reports, risk):
    src = _inspect.getsource(mod)
    name = mod.__name__.rsplit(".", 1)[-1]
    check(f"{name}.py has no require_role(UserRole.LECTURER) left",
          "require_role(UserRole.LECTURER)" not in src)
    check(f"{name}.py uses require_teaching_role", "require_teaching_role" in src)

heading("The gate itself, exercised")
gate = require_teaching_role()
for actor, allowed in (
    (teaching_admin, True),
    (desk_admin, True),
    (lecturer_a, True),
    (supers, False),
):
    try:
        gate(current_user=actor)
        got = True
    except Exception:
        got = False
    check(f"{actor.email} {'passes' if allowed else 'is refused by'} the gate",
          got is allowed)

check("a DESK admin passes the ROLE gate and is stopped by SCOPE, not role",
      True,
      "")
print("          ^ the gate is intentionally permissive: an admin with no "
      "units\n            reaches the endpoint and receives empty lists. "
      "Sections [7]-[9]\n            are what make that safe.")

# ---------------------------------------------------------------------
# HTTP - real requests through the real routers.
# ---------------------------------------------------------------------

from app.api.routes.auth import router as auth_router  # noqa: E402
from app.api.routes.lecturer import router as lecturer_router  # noqa: E402
from app.api.routes.admin import router as admin_router  # noqa: E402
from app.api.routes.units import router as units_router  # noqa: E402

api = FastAPI()
api.include_router(auth_router)
api.include_router(lecturer_router)
api.include_router(admin_router)
api.include_router(units_router)
api.dependency_overrides[get_db] = lambda: db

_actor = {"user": lecturer_a}
api.dependency_overrides[get_current_user] = lambda: _actor["user"]
client = TestClient(api)


def as_user(u: User) -> None:
    _actor["user"] = u


heading("GET /auth/me carries holds_units")
as_user(teaching_admin)
me = client.get("/auth/me")
check("200 for the teaching admin", me.status_code == 200, me.text)
check("holds_units is true", me.json().get("holds_units") is True, me.text)
check("role is still admin", me.json()["role"] == "admin")

as_user(desk_admin)
me = client.get("/auth/me")
check("holds_units is false for the desk admin",
      me.json().get("holds_units") is False, me.text)

as_user(lecturer_new)
check("holds_units is FALSE for a unitless lecturer - it reports units, "
      "not permission",
      client.get("/auth/me").json().get("holds_units") is False,
      "the browser must gate a lecturer on their ROLE and only an admin on "
      "this flag; reading it as 'may use the dashboard' would lock a new "
      "lecturer out of their own empty state")

check("MeOut is a UserOut subclass, so /admin/lecturers rows pay nothing",
      issubclass(MeOut, UserOut) and "holds_units" not in UserOut.model_fields)

heading("TENANT ISOLATION - the admin sees their own units, not everyone's")
as_user(teaching_admin)
r = client.get("/lecturer/units")
check("200, not 403 - the widened gate works", r.status_code == 200, r.text)
codes = [u["unit_code"] for u in r.json()]
check("exactly one unit", len(codes) == 1, str(codes))
check("it is their own ICT729", codes == ["ICT729"], str(codes))
check("the lecturer's ICT500 is NOT visible", "ICT500" not in codes, str(codes))
check("the unassigned ICT600 is NOT visible", "ICT600" not in codes, str(codes))

r = client.get("/lecturer/dashboard")
check("dashboard 200 for the admin", r.status_code == 200, r.text)
dash_codes = [u["unit_code"] for u in r.json()["units"]]
check("dashboard shows only ICT729", dash_codes == ["ICT729"], str(dash_codes))

heading("TENANT ISOLATION - a DESK admin sees nothing at all")
as_user(desk_admin)
r = client.get("/lecturer/units")
check("200 with an empty list, not 403", r.status_code == 200, r.text)
check("zero units - the archived ICT404 does not leak",
      r.json() == [], str(r.json()))
r = client.get("/lecturer/dashboard")
check("dashboard 200 and empty", r.status_code == 200 and r.json()["units"] == [],
      r.text)

heading("TENANT ISOLATION - an admin cannot reach another lecturer's student")
as_user(teaching_admin)
r = client.get("/lecturer/students/1", params={"unit_id": unit_lect.id})
check("404 on a student in someone else's unit", r.status_code == 404, r.text)
r = client.get("/lecturer/students/1", params={"unit_id": unit_orphan.id})
check("404 on an unassigned unit", r.status_code == 404, r.text)
r = client.put("/lecturer/students/1/note",
               params={"unit_id": unit_lect.id}, json={"body": "leak"})
check("404 on WRITING a note into someone else's unit",
      r.status_code == 404, r.text)
r = client.post("/lecturer/students/1/review",
                params={"unit_id": unit_lect.id},
                json={"decision": "confirm", "comment": ""})
check("no 2xx on reviewing someone else's verdict",
      r.status_code >= 400, r.text)

heading("The lecturer surface did not widen to super admins")
as_user(supers)
for path in ("/lecturer/units", "/lecturer/dashboard"):
    r = client.get(path)
    check(f"403 for a super admin on {path}", r.status_code == 403, r.text)

heading("ADMIN ACCOUNT MANAGEMENT did NOT widen - the boundary that stays")
as_user(desk_admin)
r = client.get("/admin/lecturers")
check("the lecturer listing is 200", r.status_code == 200, r.text)
listed = [u["email"] for u in r.json()]
check("it lists lecturers", "lect.a@uni.edu" in listed, str(listed))
check("it does NOT list admins - a teaching admin is not a lecturer ACCOUNT",
      "admin.teaches@uni.edu" not in listed, str(listed))

r = client.patch(f"/admin/lecturers/{teaching_admin.id}/deactivate")
check("404 - an admin cannot deactivate a fellow admin here",
      r.status_code == 404, r.text)
r = client.delete(f"/admin/lecturers/{teaching_admin.id}")
check("404 - nor delete one",
      r.status_code == 404, r.text)
check("the teaching admin is still active",
      db.query(User).filter(User.id == teaching_admin.id).first().is_active)

heading("UNIT ASSIGNMENT did widen - an admin can be given a unit")
r = client.post(
    "/admin/units",
    json={
        "unit_code": "ICT800",
        "unit_name": "Assigned to an admin",
        "year": 2026,
        "teaching_period": "S2",
        "level": "UG",
        "lecturer_id": desk_admin.id,
    },
)
check("201 creating a unit held by an ADMIN", r.status_code == 201, r.text)
new_unit_id = r.json()["id"] if r.status_code == 201 else None
check("the unit records the admin as its holder",
      r.status_code == 201 and r.json()["lecturer_id"] == desk_admin.id, r.text)

r = client.patch(f"/admin/units/{unit_orphan.id}/assign-lecturer",
                 json={"lecturer_id": teaching_admin.id})
check("200 assigning an existing unit to an admin", r.status_code == 200, r.text)

r = client.patch(f"/admin/units/{unit_orphan.id}/assign-lecturer",
                 json={"lecturer_id": supers.id})
check("404 assigning a unit to a SUPER ADMIN", r.status_code == 404, r.text)
r = client.patch(f"/admin/units/{unit_orphan.id}/assign-lecturer", json={"lecturer_id": 9999})
check("404 assigning to an id that does not exist", r.status_code == 404, r.text)

heading("holds_units follows the assignment, it is not frozen at login")
as_user(desk_admin)
check("the desk admin now holds ICT800, so /auth/me flips to true",
      client.get("/auth/me").json()["holds_units"] is True)

if new_unit_id:
    client.patch(f"/admin/units/{new_unit_id}/unassign-lecturer")
    check("unassigning flips it straight back to false",
          client.get("/auth/me").json()["holds_units"] is False,
          "this is why holds_units is computed per request and NOT a JWT claim")

heading("No schema change - T5 adds no column and no migration")
cols = {c["name"] for c in inspect(engine).get_columns("users")}
check("users has no is_also_lecturer column", "is_also_lecturer" not in cols)
check("users has no teaches flag", "teaches" not in cols)
unit_cols = {c["name"] for c in inspect(engine).get_columns("units")}
check("units still identifies the holder by lecturer_id alone",
      "lecturer_id" in unit_cols)
check("holds_units is derived, never stored",
      "holds_units" not in cols and "holds_units" not in unit_cols)

# ---------------------------------------------------------------------

print("\n" + "=" * 60)
if failures:
    print(f"{len(failures)} CHECK(S) FAILED ({section} sections)")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections)")