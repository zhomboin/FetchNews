import React from "react";

type PanelHeaderProps = {
  kicker: string;
  title: string;
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
};

export function PanelHeader({
  kicker,
  title,
  meta,
  actions,
  className,
}: PanelHeaderProps): React.JSX.Element {
  return (
    <header className={["section-title", className].filter(Boolean).join(" ")}>
      <div>
        <p>{kicker}</p>
        <h2>{title}</h2>
      </div>
      {actions ?? (meta ? <span>{meta}</span> : null)}
    </header>
  );
}
