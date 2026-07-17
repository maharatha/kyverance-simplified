import { ProposalReviewClient } from "@/components/portfolios/ProposalReviewClient";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function AgentProposalPage({ params }: PageProps) {
  const { id } = await params;
  return <ProposalReviewClient proposalId={id} />;
}
