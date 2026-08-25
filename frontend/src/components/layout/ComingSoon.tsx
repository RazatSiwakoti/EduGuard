import type { LucideIcon } from "lucide-react";

interface ComingSoonProps {
  title: string;
  icon: LucideIcon;
  /** What this section will do, in plain language. */
  description: string;
  /** The concrete capabilities planned — keeps the promise specific. */
  planned: string[];
}

/**
 * Placeholder for a navigation section that is routed but not built.
 *
 * A stub is better than omitting the nav item entirely: it shows the
 * shape of the finished product, and a link that explains itself is
 * far less frustrating than one that 404s or silently does nothing.
 *
 * It deliberately lists the SPECIFIC things the section will do rather
 * than saying "coming soon". Vague placeholders age badly and tell a
 * reader nothing about whether this is the screen they wanted.
 */
export default function ComingSoon({
  title,
  icon: Icon,
  description,
  planned,
}: ComingSoonProps) {
  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-2xl">
        <header className="mb-6">
          <h1 className="flex items-center gap-2 text-xl font-semibold text-stone-900">
            <Icon className="h-5 w-5 text-stone-400" aria-hidden="true" />
            {title}
          </h1>
          <p className="mt-1 text-sm text-stone-500">{description}</p>
        </header>

        <div className="rounded-lg border border-dashed border-stone-300 bg-white p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-stone-400">
            Planned for this section
          </p>

          <ul className="mt-3 space-y-2">
            {planned.map((item) => (
              <li key={item} className="flex gap-2.5 text-sm text-stone-600">
                <span
                  className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-stone-300"
                  aria-hidden="true"
                />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
