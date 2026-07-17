import { RoutePlaceholder } from "@/components/RoutePlaceholder";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function PortfolioDiscussionPage({ params }: PageProps) {
  const { id } = await params;
  return (
    <RoutePlaceholder
      title="Portfolio discussion"
      description={`Discussion for “${id}” will arrive with community features.`}
    />
  );
}
