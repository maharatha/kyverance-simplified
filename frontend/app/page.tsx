import { PRODUCT_NAME, PRODUCT_TAGLINE } from "@/lib/product";

export default function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "2.5rem clamp(1.25rem, 4vw, 4rem)",
        maxWidth: "42rem",
      }}
    >
      <p
        style={{
          margin: 0,
          fontFamily: "var(--font-display)",
          fontSize: "clamp(2.5rem, 6vw, 3.75rem)",
          fontWeight: 650,
          letterSpacing: "-0.03em",
          lineHeight: 1.05,
        }}
      >
        {PRODUCT_NAME}
      </p>
      <p
        style={{
          margin: "1rem 0 0",
          color: "var(--muted)",
          fontSize: "1.125rem",
          lineHeight: 1.5,
          maxWidth: "28rem",
        }}
      >
        {PRODUCT_TAGLINE}
      </p>
    </main>
  );
}
