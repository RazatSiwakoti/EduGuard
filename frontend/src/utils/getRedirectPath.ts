import type { User } from "../types/auth";
import { usesLecturerSurface } from "./teaching";

/**
 * Where a signed-in account belongs.
 *
 * Takes the whole USER, not just the role — since T5 the answer for an
 * admin depends on whether they hold a unit, and a role string cannot
 * carry that.
 *
 * Order matters. super_admin is checked first because it is the only
 * role with a landing page of its own that is not the lecturer surface
 * and not /admin.
 */
export function getRedirectPath(user: User): string {
  if (user.role === "super_admin") return "/super-admin";

  // Lecturers, and admins who hold a unit, land on the risk dashboard —
  // the reason either of them signed in.
  if (usesLecturerSurface(user)) return "/dashboard";

  // Everyone left is an admin with no units: the admin panel is their
  // whole application.
  return "/admin";
}