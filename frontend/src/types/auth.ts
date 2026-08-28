// Shape of the request body sent to POST /auth/login
export interface LoginRequest {
  email: string;
  password: string;
}

// Shape of the response from POST /auth/login
export interface LoginResponse {
  access_token: string;
  token_type: string;
}

// Shape of the response from GET /auth/me
//
// THREE roles, not four. "student" was removed in T5: the backend enum
// app/models/enums.py:UserRole has only super_admin / admin / lecturer,
// so /auth/me could never return "student" and every branch written for
// it — getRedirectPath had one — was unreachable code pretending to be
// a supported case. Students exist in this system as the SUBJECT of
// analysis (app.models.student), never as accounts that sign in.
export type UserRole = "lecturer" | "admin" | "super_admin";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login: string;

  /**
   * Does this account hold at least one ACTIVE unit? — T5.
   *
   * Computed per request by GET /auth/me, deliberately not a JWT claim:
   * a token lives for hours and a unit assignment changes in a second.
   * It is what makes an admin "also a lecturer".
   *
   * Reports units held, NOT permission. Use usesLecturerSurface() rather
   * than reading this directly — a lecturer with no units still belongs
   * on the lecturer surface and this flag is false for them.
   */
  holds_units: boolean;
}