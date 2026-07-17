import type { HomeFixture } from "@/lib/home";

type DataStatusProps = {
  dataStatus: HomeFixture["dataStatus"];
  compact?: boolean;
};

export function DataStatus({ dataStatus, compact = false }: DataStatusProps) {
  if (compact) {
    return (
      <p className="home-card-meta" data-tone={dataStatus.tone} role="status">
        <span className="home-badge">{dataStatus.simulationLabel}</span>
        <span>{dataStatus.freshnessLabel}</span>
        <span>{dataStatus.sourceLabel}</span>
      </p>
    );
  }

  return (
    <div className="home-disclosures" data-tone={dataStatus.tone} role="status">
      <p style={{ margin: 0 }}>{dataStatus.simulationLabel}</p>
      <p style={{ margin: "0.35rem 0 0" }}>
        Data: {dataStatus.freshnessLabel}. Source: {dataStatus.sourceLabel}.
      </p>
    </div>
  );
}
