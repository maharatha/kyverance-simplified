import type { HomeFixture, HomePageState } from "./types";

const SHARED_DISCLOSURE =
  "Simulation only. No brokerage orders are placed from this product surface.";

export const HOME_PAGE_STATES: HomePageState[] = [
  "signed-out",
  "new-member",
  "active-member",
  "creator",
  "agent-proposal",
  "loading",
  "unavailable",
];

const activePortfolio = {
  id: "pf_core_growth",
  name: "Core Growth Practice",
  provenance: "simulated" as const,
  valuationStatus: "available" as const,
  asOf: "2026-07-16T16:00:00Z",
  totalValue: "128450.27",
  cash: "8420.15",
  dayChange: { amount: "312.40", percent: "0.24" },
  allocation: [
    { label: "Equities", weightPercent: "62.0" },
    { label: "ETFs", weightPercent: "24.5" },
    { label: "Cash", weightPercent: "13.5" },
  ],
  nextAction: { label: "Open portfolio", href: "/portfolios/pf_core_growth" },
};

export const HOME_FIXTURES: Record<HomePageState, HomeFixture> = {
  "signed-out": {
    state: "signed-out",
    eyebrow: "SIMULATED INVESTING",
    headline: "Build an investing process you can inspect.",
    support:
      "Create a simulated portfolio, review agent scenarios with evidence, and keep every decision explainable.",
    primaryCta: {
      label: "Create a simulated portfolio",
      href: "/portfolios/new",
    },
    secondaryCta: { label: "Explore portfolios", href: "/explore" },
    dataStatus: {
      simulationLabel: SHARED_DISCLOSURE,
      freshnessLabel: "Fixture demo",
      sourceLabel: "No live market connection",
      tone: "ok",
    },
    valuePoints: [
      {
        title: "Facts before forecasts",
        body: "Portfolio value, provenance, and data status always appear before agent commentary.",
      },
      {
        title: "AI with receipts",
        body: "Agent proposals show evidence counts, assumptions, confidence, and as-of time.",
      },
      {
        title: "Practice without brokerage risk",
        body: "Every action stays inside simulation. No live orders leave this product.",
      },
    ],
  },

  "new-member": {
    state: "new-member",
    eyebrow: "SIMULATED INVESTING • READY TO START",
    headline: "Start with one portfolio.",
    support:
      "Define an objective, add or watch an asset, then review one simulated decision with clear provenance.",
    primaryCta: { label: "Create portfolio", href: "/portfolios/new" },
    secondaryCta: { label: "Browse learn path", href: "/learn" },
    dataStatus: {
      simulationLabel: SHARED_DISCLOSURE,
      freshnessLabel: "No holdings yet",
      sourceLabel: "Simulated workspace",
      tone: "ok",
    },
    starterSteps: [
      {
        title: "Define an objective",
        body: "Write the purpose of the portfolio in plain language before adding assets.",
      },
      {
        title: "Add or watch an asset",
        body: "Start small with one holding or watchlist item so the next review stays focused.",
      },
      {
        title: "Review a simulated decision",
        body: "Use an agent brief only after the deterministic portfolio facts are in place.",
      },
    ],
  },

  "active-member": {
    state: "active-member",
    eyebrow: "SIMULATED INVESTING • DATA AVAILABLE",
    headline: "Your next best review.",
    support:
      "Portfolio facts are current. Review the latest agent brief, then continue the portfolio workspace.",
    primaryCta: { label: "Review agent brief", href: "/agents/brief/latest" },
    secondaryCta: {
      label: "Continue portfolio",
      href: "/portfolios/pf_core_growth",
    },
    dataStatus: {
      simulationLabel: SHARED_DISCLOSURE,
      freshnessLabel: "As of 16:00 UTC",
      sourceLabel: "Simulated valuation",
      tone: "ok",
    },
    portfolio: activePortfolio,
    agent: {
      status: "brief",
      agentName: "Process Coach",
      generatedAt: "2026-07-16T15:40:00Z",
      evidenceCount: 4,
      confidence: "medium",
      summary:
        "Concentration in the top two equity names rose this week. A rebalance scenario keeps the objective intact while trimming overlap.",
      assumptions: [
        "Uses end-of-day simulated marks only",
        "No tax-lot optimization in this brief",
      ],
      href: "/agents/brief/latest",
    },
    nextStep: {
      title: "Continue learning",
      description: "Revisit position sizing before the next simulated change.",
      action: { label: "Open learn module", href: "/learn" },
    },
    discovery: [
      {
        id: "pub_defensive_income",
        name: "Defensive Income Study",
        thesis: "Public template focused on cash yield and drawdown notes.",
        href: "/explore/pub_defensive_income",
      },
      {
        id: "pub_research_watch",
        name: "Research Watchlist",
        thesis: "Curated names with thesis snippets — not a ranked feed.",
        href: "/explore/pub_research_watch",
      },
    ],
  },

  creator: {
    state: "creator",
    eyebrow: "SIMULATED INVESTING • CREATOR DRAFT",
    headline: "Publish the work behind the performance.",
    support:
      "Your draft version is ready for review. Publish when the thesis, holdings snapshot, and disclosures are complete.",
    primaryCta: { label: "Publish a version", href: "/portfolios/pf_core_growth/publish" },
    secondaryCta: {
      label: "Edit draft",
      href: "/portfolios/pf_core_growth",
    },
    dataStatus: {
      simulationLabel: SHARED_DISCLOSURE,
      freshnessLabel: "Draft as of 15:10 UTC",
      sourceLabel: "Creator workspace",
      tone: "ok",
    },
    portfolio: {
      ...activePortfolio,
      name: "Core Growth — creator draft",
      nextAction: {
        label: "Review draft holdings",
        href: "/portfolios/pf_core_growth",
      },
    },
    creator: {
      versionStatus: "draft",
      versionLabel: "v0.9 draft — not published",
      communitySignal: "12 watchers · 3 thoughtful comments awaiting reply",
    },
    nextStep: {
      title: "Community health",
      description: "Respond to open questions before publishing a new version.",
      action: { label: "Open discussion", href: "/portfolios/pf_core_growth/discussion" },
    },
  },

  "agent-proposal": {
    state: "agent-proposal",
    eyebrow: "SIMULATED INVESTING • SCENARIO READY",
    headline: "An agent prepared a scenario for review.",
    support:
      "This is a draft proposal. No trade has been placed. Confirm only after you inspect evidence and assumptions.",
    primaryCta: { label: "Review proposal", href: "/agents/proposals/prop_trim_overlap" },
    secondaryCta: {
      label: "Keep portfolio unchanged",
      href: "/portfolios/pf_core_growth",
    },
    dataStatus: {
      simulationLabel: SHARED_DISCLOSURE,
      freshnessLabel: "Proposal as of 15:55 UTC",
      sourceLabel: "Simulated marks + research notes",
      tone: "ok",
    },
    portfolio: activePortfolio,
    agent: {
      status: "proposal",
      agentName: "Rebalance Scout",
      generatedAt: "2026-07-16T15:55:00Z",
      evidenceCount: 6,
      confidence: "high",
      summary:
        "Draft scenario: trim overlapping mega-cap exposure by 4% and raise cash buffer. Scenario framing only — draft, no trade placed.",
      assumptions: [
        "Liquidity assumed at last simulated close",
        "No corporate actions pending in the horizon",
        "Owner confirmation required before any simulated order",
      ],
      href: "/agents/proposals/prop_trim_overlap",
    },
  },

  loading: {
    state: "loading",
    eyebrow: "SIMULATED INVESTING • LOADING",
    headline: "Loading your home workspace.",
    support: "Preserving layout while fixture content resolves.",
    primaryCta: { label: "Create portfolio", href: "/portfolios/new" },
    dataStatus: {
      simulationLabel: SHARED_DISCLOSURE,
      freshnessLabel: "Loading",
      sourceLabel: "Pending",
      tone: "ok",
    },
    statusMessage: "Loading portfolio and agent context…",
  },

  unavailable: {
    state: "unavailable",
    eyebrow: "SIMULATED INVESTING • TEMPORARILY UNAVAILABLE",
    headline: "Home content is temporarily unavailable.",
    support:
      "Portfolio and agent summaries are hidden so stale values are not shown as current. Retry when ready.",
    primaryCta: { label: "Retry home", href: "/" },
    dataStatus: {
      simulationLabel: SHARED_DISCLOSURE,
      freshnessLabel: "Unavailable",
      sourceLabel: "No current valuation",
      tone: "unavailable",
    },
    statusMessage:
      "Deterministic portfolio facts and agent content are unavailable. Nothing below is current market state.",
    recoveryCta: { label: "Retry home", href: "/" },
    portfolio: null,
    agent: {
      status: "unavailable",
      agentName: "Process Coach",
      summary:
        "Agent brief unavailable. Portfolio facts are also withheld to avoid presenting stale values as current.",
    },
  },
};

export function getHomeFixture(state: HomePageState): HomeFixture {
  return HOME_FIXTURES[state];
}
