import { RoutePlaceholder } from "@/components/RoutePlaceholder";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function PublishPortfolioPage({ params }: PageProps) {
  const { id } = await params;
  return (
    <RoutePlaceholder
      title="Publish version"
      description={`Publishing for “${id}” is out of scope for WEB-01. This placeholder preserves navigation.`}
    />
  );
}
