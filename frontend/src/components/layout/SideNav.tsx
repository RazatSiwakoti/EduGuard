import { NavLink } from "react-router-dom";
import {
  BellRing,
  BookOpen,
  FileBarChart,
  LayoutDashboard,
  ShieldCheck,
  Users,
  UsersRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import type { UserRole } from "../../types/auth";
import { usesLecturerSurface } from "../../utils/teaching";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Which roles see this item. Omitted = every signed-in role. */
  roles?: UserRole[];
  /**
   * Hide this item unless the account actually uses the lecturer
   * surface — T5.
   *
   * A role list alone cannot express the rule. Every lecturer item is
   * now visible to `admin` as well, because an admin who holds a unit
   * teaches it; but an admin who holds none must not see any of them,
   * and role is identical in both cases. This flag carries the
   * difference.
   */
  requiresTeaching?: boolean;
  /** Renders above the item, once, as a group label. */
  group?: string;
}

/**
 * The whole navigation map, in one array.
 *
 * Declared as data rather than as hand-written JSX so adding a section
 * later is a one-line change, and so role visibility is decided in a
 * single readable place instead of scattered across conditionals.
 *
 * Ordered by how often a lecturer actually needs each one: the risk
 * dashboard is the reason they logged in, units is where they upload
 * and configure, and the rest are follow-up actions.
 */
const TEACHING: UserRole[] = ["lecturer", "admin"];

const NAV_ITEMS: NavItem[] = [
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    roles: TEACHING,
    requiresTeaching: true,
    group: "Teaching",
  },
  {
    to: "/units",
    label: "Units",
    icon: BookOpen,
    roles: TEACHING,
    requiresTeaching: true,
  },
  {
    to: "/students",
    label: "Students",
    icon: Users,
    roles: TEACHING,
    requiresTeaching: true,
  },
  {
    to: "/alerts",
    label: "Alerts",
    icon: BellRing,
    roles: TEACHING,
    requiresTeaching: true,
  },
  // Built in 7.9 / section C3 - the "Soon" tag goes with it, or the
  // sidebar keeps advertising a stub that no longer exists.
  {
    to: "/reports",
    label: "Reports",
    icon: FileBarChart,
    roles: TEACHING,
    requiresTeaching: true,
  },
  // Admin and super admin keep their existing single-page panels; they
  // appear here so those roles get a working sidebar too rather than an
  // empty rail.
  //
  // No `requiresTeaching`: this is the item an admin must ALWAYS see,
  // and for an admin with no units it is the only item in the rail.
  {
    to: "/admin",
    label: "Admin Panel",
    icon: UsersRound,
    roles: ["admin"],
    group: "Administration",
  },
  {
    to: "/super-admin",
    label: "Super Admin",
    icon: UsersRound,
    roles: ["super_admin"],
  },
];

/**
 * Persistent left navigation.
 *
 * Collapses to an icon-only rail below the `lg` breakpoint rather than
 * disappearing behind a hamburger. A single set of markup that narrows
 * beats maintaining two separate navs that can drift apart, and the
 * icons stay reachable at every width.
 *
 * Every item keeps its `title` attribute, so the collapsed rail is
 * still usable — hovering an icon names it.
 */
export default function SideNav() {
  const { user } = useAuth();
  if (!user) return null;

  // Computed once, not per item: the answer is the same for every row
  // and it is what separates a teaching admin from a desk admin.
  const teaches = usesLecturerSurface(user);

  const items = NAV_ITEMS.filter((item) => {
    if (item.roles && !item.roles.includes(user.role)) return false;
    if (item.requiresTeaching && !teaches) return false;
    return true;
  });

  // Group labels only earn their space when there is more than one
  // group on screen. A plain lecturer sees five items under a redundant
  // "Teaching" heading otherwise, and a desk admin sees "Administration"
  // above a single row.
  const showGroups =
    new Set(items.map((item) => item.group).filter(Boolean)).size > 1;

  return (
    <aside className="flex w-16 shrink-0 flex-col border-r border-stone-200 bg-white lg:w-60">
      {/* Brand. Lives here rather than in the header now that a sidebar
          exists — the top-left corner is where a product name belongs,
          and it frees the header for page-level context. */}
      <div className="flex h-[57px] items-center gap-2.5 border-b border-stone-200 px-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-green-500">
          <ShieldCheck className="h-4.5 w-4.5 text-white" strokeWidth={2.5} />
        </div>
        <span className="hidden text-base font-bold text-stone-900 lg:inline">
          Ed<span className="font-semibold italic text-blue-600">Guard</span>
        </span>
      </div>

      <nav className="flex-1 space-y-0.5 p-2">
        {items.map((item) => {
          const Icon = item.icon;

          return (
            <div key={item.to}>
              {showGroups && item.group && (
                <p className="mt-3 px-3 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-stone-400 first:mt-0 max-lg:sr-only">
                  {item.group}
                </p>
              )}
            <NavLink
              to={item.to}
              title={item.label}
              // NavLink hands us the active state, so the current
              // section is highlighted without comparing pathnames by
              // hand anywhere in this component.
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition ${
                  isActive
                    ? "bg-stone-100 font-medium text-stone-900"
                    : "text-stone-600 hover:bg-stone-50 hover:text-stone-900"
                }`
              }
            >
              <Icon className="h-4.5 w-4.5 shrink-0" aria-hidden="true" />
              <span className="hidden lg:inline">{item.label}</span>
            </NavLink>
            </div>
          );
        })}
      </nav>

      <div className="hidden border-t border-stone-200 px-4 py-3 lg:block">
        <p className="text-[11px] leading-relaxed text-stone-400">
          Early Detection · Timely Action
        </p>
      </div>
    </aside>
  );
}