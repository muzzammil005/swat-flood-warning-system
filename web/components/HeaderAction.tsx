"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function HeaderAction() {
  const pathname = usePathname();
  const isAdminPath = pathname?.startsWith('/admin');

  return (
    <Link 
      href={isAdminPath ? "/" : "/admin/login"} 
      className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-lg bg-neutral-900 text-white hover:bg-neutral-800 transition-colors shadow-sm"
    >
      {isAdminPath ? "Home" : "Admin"}
    </Link>
  );
}
