# FND-01 — Home Page Information Architecture and UX Specification

> Status: Approved for implementation by Codex.  
> Parent: [Product foundation](01-product-foundation.md).  
> Source inputs: original Kyverance Home/Portfolio read-model, UX, AI-guardrail, portfolio-network UX, and Entra-branding documents listed in [source synthesis](00-source-synthesis.md).

## Outcome

Deliver a quiet, premium home page that makes the next useful portfolio action obvious. It must make Kyverance feel AI-native without allowing agent prose, performance theatre, or a dense terminal to replace trustworthy portfolio facts.

This first web slice is visual and navigational only. It uses typed fixture data behind a local interface; authentication, API reads, trading, Plaid, payments, and live agent calls arrive in later tasks.

## Design principles

1. **One decision at a time.** The page has one dominant CTA per state.
2. **Facts before forecasts.** Value, source, data status and simulation label render before any agent message.
3. **Calm, not casino.** No flashing price tape, confetti, rank, “hot” badge, infinite feed, or return-first promotion.
4. **AI with receipts.** Any agent proposal shows scenario framing, evidence count, assumptions and as-of time.
5. **Progressive disclosure.** Portfolio depth belongs in Portfolio; discovery depth belongs in Explore.
6. **Accessible confidence.** Color never alone communicates gain/loss, risk, source or status.

## Page states

| State | Hero message | Primary CTA | Required supporting content |
| --- | --- | --- | --- |
| Signed out | `Build an investing process you can inspect.` | `Create a simulated portfolio` | Simulation-only disclosure, `Explore portfolios` secondary action, three concise value points. |
| New member | `Start with one portfolio.` | `Create portfolio` | Three-step starter path: define objective → add/watch an asset → review a simulated decision. |
| Active member | `Your next best review.` | `Review agent brief` or `Continue portfolio` | One portfolio summary, data/source status, next action, compact agent card. |
| Creator | `Publish the work behind the performance.` | `Publish a version` | Draft/published version status and concise community health signal. |
| Agent proposal pending | `An agent prepared a scenario for review.` | `Review proposal` | Explicit “draft—no trade placed” label, evidence/as-of time, assumptions and confidence. |
| Loading/error/unavailable | Contextual, truthful status | Recovery CTA | Skeletons preserve layout; errors never show stale values as current; AI failure retains deterministic portfolio content. |

## Desktop information hierarchy

```text
Global header: wordmark | Explore | Portfolios | Agents | Learn | profile / sign in

Main column (max-width 1180px)
  1. Context eyebrow: SIMULATED INVESTING • data status
  2. State-specific headline, one-sentence support, primary CTA, quiet secondary link
  3. Portfolio snapshot card
       name / source badge / as-of
       total value / cash / day change (when applicable)
       allocation mini-visual + accessible table link
       one contextual next action
  4. Agent brief or proposal card
       agent name / scenario label / generated time / evidence count
       2–3 sentence summary, assumptions, confidence, review CTA
  5. Two secondary cards maximum
       continue learning; curated community portfolio or watchlist/research
  6. Disclosures and data notes
```

Desktop uses a 12-column grid. The hero and portfolio card occupy 8 columns; a slim agent/status rail occupies 4 columns only when content is present. The signed-out page uses a centered hero and three equal value cards.

## Mobile behavior

- Header collapses to wordmark, notification/status indicator, and menu; primary CTA remains visible in the first viewport.
- Sections stack: hero → portfolio → agent → secondary cards → disclosure.
- The portfolio summary uses two metric rows, not a horizontally scrolling dashboard.
- Charts must have a visible numeric/table alternative. No essential interaction depends on hover.
- Touch targets are at least 44×44 CSS pixels; keyboard focus remains apparent on desktop.

## Visual direction

Use the original Kyverance preference for a dark, restrained shell with a high-contrast light Entra sign-in card. The application uses near-black surfaces, warm coral as the intentional-action accent, quiet neutral borders, generous whitespace, and modern sans typography. The warm accent is used for actions—not for simulated gains/losses. Gains/losses use text and icon/label treatment in addition to color.

Use simple cards with one hierarchy each. Prefer thin dividers, concise labels, real whitespace, and data typography. Do not use gradients as decoration, glassmorphism, oversized dashboard counters, or ornamental illustrations.

## Components

| Component | Responsibility | Does not do |
| --- | --- | --- |
| `HomeShell` | Chooses a state and composes sections | Fetch data, decide permissions, mutate portfolios |
| `HomeHero` | State-specific message and one primary action | Render market metrics |
| `PortfolioSnapshotCard` | Present typed portfolio facts/provenance/freshness | Calculate P&L or execute a trade |
| `AgentProposalCard` | Present typed, prevalidated agent proposal summary | Call a model or imply an order is placed |
| `NextStepCard` | Present one contextual action | Compete with hero CTA |
| `DiscoveryPreview` | Present 1–3 curated public portfolio cards | Rank by raw returns or show private data |
| `DataStatus` | Reusable freshness/source/simulation label | Conceal unavailable/stale data |

## Fixture contract for this slice

Use frontend-local typed fixtures only. Money/quantity values are strings, matching the eventual API contract; components format but never calculate financial state.

```ts
type HomePortfolioSnapshot = {
  id: string;
  name: string;
  provenance: "simulated" | "manual_unverified" | "connected_read_only";
  valuationStatus: "available" | "unavailable" | "stale";
  asOf: string;
  totalValue?: string;
  cash?: string;
  dayChange?: { amount: string; percent: string };
  nextAction: { label: string; href: string };
};

type AgentProposalSummary = {
  status: "brief" | "proposal" | "unavailable";
  agentName: string;
  generatedAt?: string;
  evidenceCount?: number;
  confidence?: "low" | "medium" | "high";
  summary?: string;
  assumptions?: string[];
  href?: string;
};
```

## Acceptance criteria

- Every specified state can be demonstrated with a fixture and component test.
- Signed-out and new-member pages communicate simulation and have exactly one primary CTA.
- Active-member state renders source/freshness context before agent content.
- Agent proposal says it is a scenario/draft and that no trade has been placed.
- The page is responsive, keyboard navigable, semantic, and retains text/table alternatives for visual data.
- `npm run lint`, unit tests, and production build pass.
- No authentication, API, market-data, Plaid, trade, payment, or Azure change is included.

## Exclusions

This task does not implement a design system for every future page, the final logo, generic landing-page marketing, agent orchestration, auth, roles, portfolio CRUD, portfolio API, chart library, real market data, or a creator marketplace.
