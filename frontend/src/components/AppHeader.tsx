import { Link } from "react-router-dom";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Bell, ChevronDown } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { getInitials, formatRole } from "../utils/userDisplay";

// Top bar for every authenticated page. Mounted ONCE by AppShell as
// part of the layout route, so it survives navigation instead of being
// rebuilt per page.
//
// The brand block moved to SideNav when the sidebar was introduced — a
// product name belongs in the app's top-left corner, and rendering it
// in both places read as a duplicated logo. This side of the header is
// now free for page-level context (breadcrumbs, a unit switcher) as
// those arrive.
export default function AppHeader() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    // Fixed height matches the sidebar's brand block, so the two
    // borders meet in one unbroken horizontal line across the top.
    <header className="flex h-[57px] shrink-0 items-center justify-between border-b border-stone-200 bg-white px-6">
      <p className="truncate text-xs italic text-stone-400">
        Early Detection · Timely Action · Better Outcomes
      </p>

      {/* Right side: notifications + user menu */}
      <div className="flex items-center gap-4">
        {/* Placeholder — not wired to a real notification system yet,
            since the alert/notification backend hasn't been built. */}
        <button
          type="button"
          className="relative rounded-full p-2 text-stone-500 transition hover:bg-stone-100"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />
        </button>

        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 rounded-md px-2 py-1.5 transition hover:bg-stone-100"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-stone-800 text-xs font-semibold text-white">
                {getInitials(user.full_name)}
              </div>
              <div className="text-left">
                <p className="text-sm font-medium leading-tight text-stone-900">
                  {user.full_name}
                </p>
                <p className="text-xs leading-tight text-stone-500">
                  {formatRole(user.role)}
                </p>
              </div>
              <ChevronDown className="h-4 w-4 text-stone-400" />
            </button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content
              align="end"
              sideOffset={8}
              className="w-44 rounded-md border border-stone-200 bg-white p-1 shadow-lg"
            >
              <DropdownMenu.Item asChild>
                <Link
                  to="/account"
                  className="block cursor-pointer rounded px-3 py-2 text-sm text-stone-700 outline-none hover:bg-stone-100"
                >
                  Account
                </Link>
              </DropdownMenu.Item>
              <DropdownMenu.Item asChild>
                <Link
                  to="/settings"
                  className="block cursor-pointer rounded px-3 py-2 text-sm text-stone-700 outline-none hover:bg-stone-100"
                >
                  Settings
                </Link>
              </DropdownMenu.Item>
              <DropdownMenu.Separator className="my-1 h-px bg-stone-200" />
              <DropdownMenu.Item
                onSelect={logout}
                className="cursor-pointer rounded px-3 py-2 text-sm text-red-600 outline-none hover:bg-red-50"
              >
                Logout
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  );
}
