import { RoutePlaceholder } from "@/components/RoutePlaceholder";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function PortfolioDetailPage({ params }: PageProps) {
  const { id } = await params;
  return (
    <RoutePlaceholder
      title="Portfolio workspace"
      description={`Portfolio “${id}” detail will open here. Home links remain safe placeholders until SIM tasks land.`}
    />
  );
}
