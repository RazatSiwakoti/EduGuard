import type { User } from "../types/auth";

/**
 * Does this account use the lecturer surface? — T5.
 *
 * ONE predicate, three callers: the sidebar decides which items to
 * render, getRedirectPath decides where a sign-in lands, and RoleRoute
 * decides whether a typed URL is allowed through. Written out three
 * times it would eventually be written three different ways, and the
 * failure mode is a nav item that leads to a page that bounces you
 * straight back to where you came from.
 *
 * The rule Razat set: an admin is "also a lecturer" exactly when they
 * hold at least one active unit. The server answers that on /auth/me as
 * `holds_units`; nothing here recomputes it.
 */
export function usesLecturerSurface(user: User | null): boolean {
  if (!user) return false;

  // A lecturer always qualifies, units or none. `holds_units` reports
  // units held, NOT permission — reading it as permission would lock a
  // brand-new lecturer out of the dashboard's own empty state, which
  // GET /lecturer/dashboard returns 200 for on purpose.
  if (user.role === "lecturer") return true;

  if (user.role === "admin") return user.holds_units;

  // super_admin manages admins and is never assigned a unit.
  return false;
}