import { FileBarChart } from "lucide-react";
import ComingSoon from "../components/layout/ComingSoon";

/**
 * Placeholder — export formats and their contents are not specified
 * yet, and guessing at them would mean rebuilding this twice.
 */
export default function ReportsPage() {
  return (
    <ComingSoon
      title="Reports"
      icon={FileBarChart}
      description="Take the analysis out of EduGuard and into a meeting, an email, or a filing system."
      planned={[
        "Export a unit's risk breakdown to CSV or Excel",
        "A printable PDF summary with the dashboard's charts included",
        "Filter what goes into an export by unit and risk tier",
        "An intervention log suitable for faculty reporting",
      ]}
    />
  );
}
