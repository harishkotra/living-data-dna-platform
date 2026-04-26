"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  ["/", "Dashboard"],
  ["/graph", "DNA Graph"],
  ["/timeline", "Timeline"],
  ["/copilot", "Chat Copilot"],
] as const;

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="nav">
      {links.map(([href, label]) => {
        const active = pathname === href;
        return (
          <Link key={href} href={href} className={active ? "active" : ""}>
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
