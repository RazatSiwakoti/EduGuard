import { Users } from "lucide-react";
import ComingSoon from "../components/layout/ComingSoon";

/**
 * Placeholder — the real version needs a per-student detail endpoint
 * that does not exist yet. Deliberately not built against a stub
 * endpoint that would then be thrown away.
 */
export default function StudentsPage() {
  return (
    <ComingSoon
      title="Students"
      icon={Users}
      description="Every student across your units, and the full picture behind their risk verdict."
      planned={[
        "Searchable list of every student enrolled in any unit you teach",
        "Per-student detail: attendance, tutorial submissions, assessment marks and Moodle activity",
        "Why a student was flagged — the rule engine's breakdown and the ML model's contributing features side by side",
        "Resolve a Needs Review verdict where the two engines disagreed",
        "History across units, since a student can be high risk in one and safe in another",
      ]}
    />
  );
}
