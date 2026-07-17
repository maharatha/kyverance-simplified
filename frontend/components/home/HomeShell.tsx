import Link from "next/link";
import type { HomeFixture } from "@/lib/home";
import { AgentProposalCard } from "./AgentProposalCard";
import { DataStatus } from "./DataStatus";
import { DiscoveryPreview } from "./DiscoveryPreview";
import { GlobalHeader } from "./GlobalHeader";
import { HomeHero } from "./HomeHero";
import { NextStepCard } from "./NextStepCard";
import { PortfolioSnapshotCard } from "./PortfolioSnapshotCard";

type HomeShellProps = {
  fixture: HomeFixture;
  /** Real session state for header; fixture state still drives Home content. */
  sessionSignedIn?: boolean;
  menuOpen?: boolean;
  onMenuToggle?: () => void;
  onSignOut?: () => void;
};

export function HomeShell({
  fixture,
  sessionSignedIn,
  menuOpen = false,
  onMenuToggle,
  onSignOut,
}: HomeShellProps) {
  const fixtureSignedIn = fixture.state !== "signed-out";
  const signedIn = sessionSignedIn ?? fixtureSignedIn;
  const centered = fixture.state === "signed-out" && !signedIn;
  const showRail =
    Boolean(fixture.agent) ||
    Boolean(fixture.creator) ||
    fixture.state === "loading" ||
    fixture.state === "unavailable";

  return (
    <div className="home-shell">
      <GlobalHeader
        signedIn={signedIn}
        menuOpen={menuOpen}
        onMenuToggle={onMenuToggle ?? (() => undefined)}
        onSignOut={signedIn ? onSignOut : undefined}
      />
      <main className="home-main">
        <div
          className="home-grid"
          data-layout={showRail && !centered ? "split" : "stack"}
        >
          <div className="home-primary-col">
            <HomeHero fixture={fixture} centered={centered} />
            <DataStatus dataStatus={fixture.dataStatus} />

            {fixture.state === "loading" ? (
              <div className="home-status-banner" role="status" aria-live="polite">
                <p style={{ margin: 0 }}>{fixture.statusMessage}</p>
                <div className="home-skeleton" style={{ marginTop: "1rem" }} aria-hidden>
                  <div className="home-skeleton-block" data-size="lg" />
                  <div className="home-skeleton-block" />
                </div>
              </div>
            ) : null}

            {fixture.state === "unavailable" ? (
              <div
                className="home-status-banner"
                data-tone="unavailable"
                role="alert"
              >
                <p style={{ margin: 0 }}>{fixture.statusMessage}</p>
                {fixture.recoveryCta ? (
                  <div style={{ marginTop: "0.85rem" }}>
                    <Link href={fixture.recoveryCta.href} className="btn-primary">
                      {fixture.recoveryCta.label}
                    </Link>
                  </div>
                ) : null}
              </div>
            ) : null}

            {fixture.valuePoints ? (
              <section className="home-card" aria-labelledby="value-points-heading">
                <h2 id="value-points-heading" className="visually-hidden">
                  Why Kyverance
                </h2>
                <div className="home-value-grid">
                  {fixture.valuePoints.map((point) => (
                    <article key={point.title}>
                      <h3>{point.title}</h3>
                      <p>{point.body}</p>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {fixture.starterSteps ? (
              <section className="home-card" aria-labelledby="starter-heading">
                <h2 id="starter-heading">Starter path</h2>
                <div className="home-steps" style={{ marginTop: "0.85rem" }}>
                  {fixture.starterSteps.map((step, index) => (
                    <article key={step.title}>
                      <h3>
                        {index + 1}. {step.title}
                      </h3>
                      <p>{step.body}</p>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {fixture.portfolio ? (
              <PortfolioSnapshotCard portfolio={fixture.portfolio} />
            ) : null}

            {fixture.creator ? (
              <section className="home-card" aria-labelledby="creator-heading">
                <h2 id="creator-heading">Creator version</h2>
                <div className="home-card-meta">
                  <span className="home-badge">
                    {fixture.creator.versionStatus === "draft" ? "Draft" : "Published"}
                  </span>
                  <span>{fixture.creator.versionLabel}</span>
                </div>
                <p className="home-support" style={{ marginTop: "0.75rem" }}>
                  {fixture.creator.communitySignal}
                </p>
              </section>
            ) : null}

            {(fixture.nextStep || fixture.discovery) && fixture.state !== "signed-out" ? (
              <div className="home-secondary-row">
                {fixture.nextStep ? (
                  <NextStepCard
                    title={fixture.nextStep.title}
                    description={fixture.nextStep.description}
                    action={fixture.nextStep.action}
                  />
                ) : null}
                {fixture.discovery ? (
                  <DiscoveryPreview items={fixture.discovery} />
                ) : null}
              </div>
            ) : null}
          </div>

          {showRail && !centered ? (
            <aside className="home-rail" aria-label="Agent and status">
              {fixture.agent ? <AgentProposalCard agent={fixture.agent} /> : null}
              {fixture.state === "loading" ? (
                <div className="home-skeleton" aria-hidden>
                  <div className="home-skeleton-block" data-size="lg" />
                </div>
              ) : null}
            </aside>
          ) : null}
        </div>
      </main>
    </div>
  );
}
