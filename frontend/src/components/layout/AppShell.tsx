import { Outlet } from "react-router-dom";
import AppHeader from "../AppHeader";
import SideNav from "./SideNav";

/**
 * The frame every authenticated page renders inside: sidebar on the
 * left, header across the top, routed content below it.
 *
 * WHY THIS IS A LAYOUT ROUTE, NOT A WRAPPER COMPONENT
 * ---------------------------------------------------
 * Previously each route rendered its own <AppHeader /> via
 * ProtectedRoute's children. That meant the header was a fresh element
 * on every navigation — React unmounted and remounted it each time, so
 * any state it held (an open user menu, later a notification count)
 * was destroyed on every page change, and the whole bar visibly
 * repainted.
 *
 * Rendering <Outlet /> here instead means the shell mounts ONCE and
 * only the inner content swaps. That is the difference between an app
 * that feels like an app and one that feels like a set of pages.
 *
 * The `min-w-0` on the content column matters more than it looks: a
 * flex child defaults to min-width:auto, which refuses to shrink below
 * its content. Without it, a wide table or chart inside a page forces
 * the whole layout wider and the entire window scrolls sideways
 * instead of just that one element.
 */
export default function AppShell() {
  return (
    <div className="eduguard-page flex min-h-screen">
      <SideNav />

      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader />
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
