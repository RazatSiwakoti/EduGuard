import { BellRing } from "lucide-react";
import ComingSoon from "../components/layout/ComingSoon";

/**
 * Placeholder — needs mail infrastructure that is not in the codebase
 * yet. The SMTP settings exist in .env.example, but no mail service
 * has been written.
 */
export default function AlertsPage() {
  return (
    <ComingSoon
      title="Alerts"
      icon={BellRing}
      description="Reach the students who need reaching, without leaving EduGuard."
      planned={[
        "Compose and send an email to one student, or to everyone in a risk tier",
        "Reusable message templates for common interventions",
        "A record of what was sent, to whom and when — so an intervention is auditable",
        "Optional automatic notification when a student first crosses into high risk",
      ]}
    />
  );
}
