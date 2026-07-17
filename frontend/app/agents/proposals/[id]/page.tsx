import { RoutePlaceholder } from "@/components/RoutePlaceholder";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function AgentProposalPage({ params }: PageProps) {
  const { id } = await params;
  return (
    <RoutePlaceholder
      title="Review proposal"
      description={`Proposal “${id}” review UI ships with agent tasks. No trade can be placed from this placeholder.`}
    />
  );
}
