import React from "react";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  lead: string;
  health: string;
  metaLabel?: string;
  metaValue?: string;
  className?: string;
};

export function PageHeader({
  eyebrow,
  title,
  lead,
  health,
  metaLabel,
  metaValue,
  className,
}: PageHeaderProps): React.JSX.Element {
  return (
    <section className={className ?? "hero-panel"}>
      <div className="intro-copy">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="lede">{lead}</p>
      </div>

      <div className="intro-meta">
        <div className="signal-pill">
          <span className="signal-dot-live" />
          <strong>{health}</strong>
        </div>
        {metaLabel && metaValue ? (
          <div className="meta-chip">
            <span>{metaLabel}</span>
            <strong>{metaValue}</strong>
          </div>
        ) : null}
      </div>
    </section>
  );
}
