import { RoutePlaceholder } from "@/components/RoutePlaceholder";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function ExploreItemPage({ params }: PageProps) {
  const { id } = await params;
  return (
    <RoutePlaceholder
      title="Portfolio preview"
      description={`Public portfolio “${id}” will open here. Navigation from Home is intentionally a safe placeholder.`}
    />
  );
}
