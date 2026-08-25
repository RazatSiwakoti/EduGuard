import { Link } from "react-router-dom";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Bell, ChevronDown, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { getInitials, formatRole } from "../utils/userDisplay";

// Top bar shown on every authenticated page (rendered once, inside
// ProtectedRoute, rather than duplicated per page). Left side is the
// EdGuard brand block; right side is notifications + the user menu.
export default function AppHeader() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <header className="flex items-center justify-between border-b border-stone-200 bg-white px-6 py-3">
      {/* Brand block — placeholder icon for now. Swap the div below for
          an <img src="/logo.png" .../> once the real logo asset is added. */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-green-500">
          <ShieldCheck className="h-5 w-5 text-white" strokeWidth={2.5} />
        </div>
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold text-stone-900">
              Ed<span className="font-semibold italic text-blue-600">Guard</span>
            </span>
            <span className="text-xs font-medium uppercase tracking-wide text-stone-400">
              KOI · V2.4
            </span>
          </div>
          <p className="text-xs italic text-stone-400">
            Early Detection · Timely Action · Better Outcomes
          </p>
        </div>
      </div>

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