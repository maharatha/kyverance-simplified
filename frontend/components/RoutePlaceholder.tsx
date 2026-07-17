import Link from "next/link";
import { PRODUCT_NAME } from "@/lib/product";

type RoutePlaceholderProps = {
  title: string;
  description: string;
};

export function RoutePlaceholder({ title, description }: RoutePlaceholderProps) {
  return (
    <main
      style={{
        minHeight: "100vh",
        maxWidth: "40rem",
        margin: "0 auto",
        padding: "3rem clamp(1rem, 3vw, 2rem)",
      }}
    >
      <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.85rem" }}>
        {PRODUCT_NAME}
      </p>
      <h1
        style={{
          margin: "0.75rem 0 0",
          fontFamily: "var(--font-display)",
          fontSize: "clamp(1.75rem, 4vw, 2.25rem)",
          letterSpacing: "-0.03em",
        }}
      >
        {title}
      </h1>
      <p style={{ margin: "0.85rem 0 0", color: "var(--muted)", lineHeight: 1.55 }}>
        {description}
      </p>
      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/" className="btn-secondary" style={{ display: "inline-flex" }}>
          Back to home
        </Link>
      </p>
    </main>
  );
}
