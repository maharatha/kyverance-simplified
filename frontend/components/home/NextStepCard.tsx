import Link from "next/link";
import type { HomeLink } from "@/lib/home";

type NextStepCardProps = {
  title: string;
  description: string;
  action: HomeLink;
};

export function NextStepCard({ title, description, action }: NextStepCardProps) {
  return (
    <section className="home-card" aria-labelledby="next-step-heading">
      <h2 id="next-step-heading">{title}</h2>
      <p className="home-support" style={{ marginTop: "0.55rem" }}>
        {description}
      </p>
      <div className="home-card-actions">
        <Link href={action.href} className="btn-ghost">
          {action.label}
        </Link>
      </div>
    </section>
  );
}
