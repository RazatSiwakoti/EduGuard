import {
  CircleDashed,
  OctagonAlert,
  Scale,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { RiskBucket } from "../../types/dashboard";
import { BUCKET_LABELS } from "../../utils/dashboardAggregations";
import { BUCKET_STYLES } from "./chartTheme";

/**
 * Icon per risk bucket.
 *
 * This is an accessibility requirement, not decoration. Two of the tier
 * colours sit below 3:1 contrast on a white card, so colour alone is
 * not allowed to carry the meaning anywhere in this dashboard. Every
 * badge therefore pairs a distinct SHAPE with a written LABEL — a
 * reader with any form of colour-vision deficiency, or looking at a
 * greyscale printout, still reads it correctly.
 */
const BUCKET_ICONS: Record<RiskBucket, LucideIcon> = {
  high_risk: OctagonAlert,
  low_risk: TriangleAlert,
  safe: ShieldCheck,
  needs_review: Scale, // Scales = two engines weighed against each other.
  not_analysed: CircleDashed, // Dashed outline = nothing measured yet.
};

interface BucketBadgeProps {
  bucket: RiskBucket;
  /** Hides the text label. Only safe where a nearby label already exists. */
  iconOnly?: boolean;
}

export default function BucketBadge({ bucket, iconOnly = false }: BucketBadgeProps) {
  const Icon = BUCKET_ICONS[bucket];
  const style = BUCKET_STYLES[bucket];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${style.pill}`}
      title={style.hint}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      {iconOnly ? (
        // Kept in the accessibility tree even when visually hidden.
        <span className="sr-only">{BUCKET_LABELS[bucket]}</span>
      ) : (
        BUCKET_LABELS[bucket]
      )}
    </span>
  );
}

export { BUCKET_ICONS };