"use client";

import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Home" },
  { href: "/dashboard/history", label: "History" },
  { href: "/dashboard/escalation", label: "Escalation" },
  { href: "/dashboard/tasks", label: "Tasks" },
  { href: "/dashboard/training", label: "Training" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-10 bg-white border-b border-gray-200">
      <div className="max-w-5xl mx-auto px-4 flex items-center gap-1 h-12">
        <span className="text-sm font-semibold text-gray-800 mr-4">FleetPanda</span>
        {links.map((link) => {
          const isActive =
            link.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(link.href);
          return (
            <a
              key={link.href}
              href={link.href}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-500 hover:text-gray-800 hover:bg-gray-50"
              }`}
            >
              {link.label}
            </a>
          );
        })}
        <div className="ml-auto">
          <a
            href="/api/auth/signout"
            className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-50"
          >
            Sign out
          </a>
        </div>
      </div>
    </nav>
  );
}
