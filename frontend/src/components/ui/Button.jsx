export default function Button({
  children,
  variant = "primary",
  dark = false,
  onClick,
  type = "button",
  href,
  className = "",
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
    <button className={classes} type={type} onClick={onClick}>
      {children}
    </button>
  );
}
