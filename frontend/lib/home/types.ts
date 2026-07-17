/** Money and quantity values are decimal strings; UI formats but never calculates. */
export type DecimalString = string;

export type HomePageState =
  | "signed-out"
  | "new-member"
  | "active-member"
  | "creator"
  | "agent-proposal"
  | "loading"
  | "unavailable";

export type PortfolioProvenance =
  | "simulated"
  | "manual_unverified"
  | "connected_read_only";

export type ValuationStatus = "available" | "unavailable" | "stale";

export type HomePortfolioSnapshot = {
  id: string;
  name: string;
  provenance: PortfolioProvenance;
  valuationStatus: ValuationStatus;
  asOf: string;
  totalValue?: DecimalString;
  cash?: DecimalString;
  dayChange?: { amount: DecimalString; percent: DecimalString };
  allocation?: Array<{ label: string; weightPercent: DecimalString }>;
  nextAction: { label: string; href: string };
};

export type AgentProposalSummary = {
  status: "brief" | "proposal" | "unavailable";
  agentName: string;
  generatedAt?: string;
  evidenceCount?: number;
  confidence?: "low" | "medium" | "high";
  summary?: string;
  assumptions?: string[];
  href?: string;
};

export type HomeLink = {
  label: string;
  href: string;
};

export type HomeFixture = {
  state: HomePageState;
  eyebrow: string;
  headline: string;
  support: string;
  primaryCta: HomeLink;
  secondaryCta?: HomeLink;
  dataStatus: {
    simulationLabel: string;
    freshnessLabel: string;
    sourceLabel: string;
    tone: "ok" | "stale" | "unavailable";
  };
  valuePoints?: Array<{ title: string; body: string }>;
  starterSteps?: Array<{ title: string; body: string }>;
  portfolio?: HomePortfolioSnapshot | null;
  agent?: AgentProposalSummary | null;
  nextStep?: {
    title: string;
    description: string;
    action: HomeLink;
  } | null;
  discovery?: Array<{
    id: string;
    name: string;
    thesis: string;
    href: string;
  }>;
  creator?: {
    versionStatus: "draft" | "published";
    versionLabel: string;
    communitySignal: string;
  } | null;
  statusMessage?: string;
  recoveryCta?: HomeLink;
};
