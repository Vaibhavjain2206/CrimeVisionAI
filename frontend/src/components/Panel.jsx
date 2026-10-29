import React from "react";

export default function Panel({ eyebrow, title, aside, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h2>{title}</h2>
        </div>
        {aside && <div className="panel-aside">{aside}</div>}
      </div>
      {children}
    </section>
  );
}
