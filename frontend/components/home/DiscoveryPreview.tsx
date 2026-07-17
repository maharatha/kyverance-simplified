import Link from "next/link";

type DiscoveryItem = {
  id: string;
  name: string;
  thesis: string;
  href: string;
};

type DiscoveryPreviewProps = {
  items: DiscoveryItem[];
};

export function DiscoveryPreview({ items }: DiscoveryPreviewProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="home-card" aria-labelledby="discovery-heading">
      <h2 id="discovery-heading">Curated portfolios</h2>
      <p className="home-support" style={{ marginTop: "0.45rem" }}>
        A short preview of public work to explore — not a ranked feed.
      </p>
      <div className="home-discovery" style={{ marginTop: "0.85rem" }}>
        {items.map((item) => (
          <article key={item.id}>
            <h3>
              <Link href={item.href}>{item.name}</Link>
            </h3>
            <p>{item.thesis}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
