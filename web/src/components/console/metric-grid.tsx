import React from "react";

type MetricItem = {
  label: string;
  value: React.ReactNode;
  note: React.ReactNode;
};

type MetricGridProps = {
  items: MetricItem[];
  ariaLabel: string;
  className?: string;
  variant?: "grid" | "strip";
};

export function MetricGrid({
  items,
  ariaLabel,
  className,
  variant = "grid",
}: MetricGridProps): React.JSX.Element {
  const classes = [variant === "strip" ? "metric-strip" : "stats-grid", className].filter(Boolean).join(" ");

  return (
    <section aria-label={ariaLabel} className={classes}>
      {items.map((metric) => (
        <article key={metric.label} className="metric-cell">
          <p>{metric.label}</p>
          <strong>{metric.value}</strong>
          <span>{metric.note}</span>
        </article>
      ))}
    </section>
  );
}
