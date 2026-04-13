import React from "react";
import { Link } from "react-router-dom";

type DetailLinkProps = {
  children: React.ReactNode;
  className?: string;
  href?: string;
  onClick?: () => void;
  rel?: string;
  soft?: boolean;
  target?: string;
  to?: string;
  type?: "button" | "submit";
};

function buildClassName(soft: boolean, className?: string): string {
  return ["detail-link", soft ? "detail-link-soft" : null, className].filter(Boolean).join(" ");
}

export function DetailLink({
  children,
  className,
  href,
  onClick,
  rel,
  soft = false,
  target,
  to,
  type = "button",
}: DetailLinkProps): React.JSX.Element {
  const resolvedClassName = buildClassName(soft, className);

  if (to) {
    return (
      <Link className={resolvedClassName} to={to}>
        {children}
      </Link>
    );
  }

  if (href) {
    return (
      <a className={resolvedClassName} href={href} rel={rel} target={target}>
        {children}
      </a>
    );
  }

  return (
    <button className={resolvedClassName} onClick={onClick} type={type}>
      {children}
    </button>
  );
}
