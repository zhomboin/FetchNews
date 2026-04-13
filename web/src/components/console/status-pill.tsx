import React from "react";

type StatusPillProps = {
  status: string;
  className?: string;
  children: React.ReactNode;
};

function buildClassName(status: string, className?: string): string {
  return ["status-pill", `status-${status}`, className].filter(Boolean).join(" ");
}

export function StatusPill({ status, className, children }: StatusPillProps): React.JSX.Element {
  return <span className={buildClassName(status, className)}>{children}</span>;
}
