import React from "react";

type EmptyStateProps = {
  children: React.ReactNode;
  className?: string;
};

export function EmptyState({ children, className }: EmptyStateProps): React.JSX.Element {
  return <div className={["empty-state", className].filter(Boolean).join(" ")}>{children}</div>;
}
