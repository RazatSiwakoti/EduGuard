import { BookOpen } from "lucide-react";
import ComingSoon from "../components/layout/ComingSoon";

/**
 * Placeholder — replaced in Phase 7.3 by the real units list, which
 * links through to a per-unit workspace at /units/:unitId.
 */
export default function UnitsPage() {
  return (
    <ComingSoon
      title="Units"
      icon={BookOpen}
      description="Every unit you teach, and everything you configure per unit."
      planned={[
        "A card per unit showing enrolment count, teaching period and current risk summary",
        "Open a unit to reach its own workspace at /units/:unitId",
        "Import cohort data by CSV or Excel, with column mapping",
        "Add a single student manually",
        "Define the assessment criteria that unit is actually marked on",
      ]}
    />
  );
}
