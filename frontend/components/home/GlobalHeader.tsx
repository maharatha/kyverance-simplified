import Link from "next/link";
import { PRODUCT_NAME } from "@/lib/product";

const NAV_LINKS = [
  { href: "/explore", label: "Explore" },
  { href: "/portfolios", label: "Portfolios" },
  { href: "/agents", label: "Agents" },
  { href: "/learn", label: "Learn" },
] as const;

type GlobalHeaderProps = {
  signedIn: boolean;
  menuOpen: boolean;
  onMenuToggle: () => void;
};

export function GlobalHeader({ signedIn, menuOpen, onMenuToggle }: GlobalHeaderProps) {
  return (
    <header className="home-header">
      <div className="home-header-inner">
        <Link href="/" className="home-wordmark">
          {PRODUCT_NAME}
        </Link>
        <nav className="home-nav" aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <Link key={link.href} href={link.href}>
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="home-header-actions">
          <Link
            href={signedIn ? "/profile" : "/sign-in"}
            className="btn-secondary"
            style={{ minHeight: 40, paddingInline: "0.9rem" }}
          >
            {signedIn ? "Profile" : "Sign in"}
          </Link>
          <button
            type="button"
            className="home-menu-toggle"
            aria-expanded={menuOpen}
            aria-controls="home-mobile-nav"
            onClick={onMenuToggle}
          >
            Menu
          </button>
        </div>
      </div>
      <nav
        id="home-mobile-nav"
        className="home-mobile-nav"
        data-open={menuOpen ? "true" : "false"}
        aria-label="Mobile"
      >
        {NAV_LINKS.map((link) => (
          <Link key={link.href} href={link.href}>
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
