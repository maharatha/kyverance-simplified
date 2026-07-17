import Link from "next/link";
import type { HomeFixture } from "@/lib/home";

type HomeHeroProps = {
  fixture: HomeFixture;
  centered?: boolean;
};

export function HomeHero({ fixture, centered = false }: HomeHeroProps) {
  return (
    <section className="home-hero" data-centered={centered ? "true" : "false"} aria-labelledby="home-hero-heading">
      <p className="home-eyebrow">{fixture.eyebrow}</p>
      <h1 id="home-hero-heading">{fixture.headline}</h1>
      <p className="home-support">{fixture.support}</p>
      <div className="home-cta-row">
        <Link href={fixture.primaryCta.href} className="btn-primary">
          {fixture.primaryCta.label}
        </Link>
        {fixture.secondaryCta ? (
          <Link href={fixture.secondaryCta.href} className="btn-ghost">
            {fixture.secondaryCta.label}
          </Link>
        ) : null}
      </div>
    </section>
  );
}
