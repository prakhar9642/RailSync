export default function Button({
  children,
  variant = "primary",
  dark = false,
  onClick,
  type = "button",
  href,
  className = "",
  disabled = false,
  ariaBusy = false,
}) {
  const classes = [
    "rs-btn",
    `rs-btn-${variant}`,
    dark ? "dark" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  if (href) {
    return (
      <a className={classes} href={href} onClick={onClick}>
        {children}
      </a>
    );
  }

  return (
    <button
      className={classes}
      type={type}
      onClick={onClick}
      disabled={disabled}
      aria-busy={ariaBusy}
    >
      {children}
    </button>
  );
}
