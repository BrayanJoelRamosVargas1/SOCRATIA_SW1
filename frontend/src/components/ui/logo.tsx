import Link from "next/link";

export function Logo() {
  return (
    <Link className="logo" href="/" aria-label="Socratia, inicio">
      <span className="logo-mark" aria-hidden="true">
        S
      </span>
      <span>Socratia</span>
    </Link>
  );
}

