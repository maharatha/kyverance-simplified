import { PortfolioDetailClient } from "@/components/portfolios/PortfolioDetailClient";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function PortfolioDetailPage({ params }: PageProps) {
  const { id } = await params;
  return <PortfolioDetailClient portfolioId={id} />;
}
