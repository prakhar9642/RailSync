export default function SectionHeading({ eyebrow, title, children }) {
  return (
    <header className="section-heading">
      {eyebrow ? <span className="section-eyebrow">{eyebrow}</span> : null}
      <h2>{title}</h2>
      {children ? <p>{children}</p> : null}
    </header>
  );
}
