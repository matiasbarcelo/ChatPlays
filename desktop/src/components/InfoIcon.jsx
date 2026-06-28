import { useRef, useState } from "react";

export function InfoIcon({ tip, onClick, href, fixedOnHover = false }) {
  const isLink = Boolean(onClick || href);
  const iconRef = useRef(null);
  const [tooltipStyle, setTooltipStyle] = useState(null);

  function handleClick(event) {
    if (!isLink) return;
    event.stopPropagation();
    if (href) {
      window.open(href, "_blank", "noopener,noreferrer");
      return;
    }
    onClick?.();
  }

  function showFixedTooltip() {
    if (!fixedOnHover || !iconRef.current) return;
    const rect = iconRef.current.getBoundingClientRect();
    setTooltipStyle({
      position: "fixed",
      left: `${rect.right + 8}px`,
      top: `${rect.top + rect.height / 2}px`,
      transform: "translateY(-50%)",
      zIndex: 1200,
    });
  }

  function hideFixedTooltip() {
    if (fixedOnHover) {
      setTooltipStyle(null);
    }
  }

  return (
    <span
      ref={iconRef}
      className={`main-info-icon${isLink ? " main-info-icon--link" : ""}`}
      onClick={isLink ? handleClick : undefined}
      onMouseEnter={showFixedTooltip}
      onMouseLeave={hideFixedTooltip}
      onFocus={showFixedTooltip}
      onBlur={hideFixedTooltip}
      role={isLink ? "link" : undefined}
    >
      <span className="icon" style={{ fontSize: 18 }}>info</span>
      <span className="main-tooltip" style={tooltipStyle ?? undefined}>
        {tip}
      </span>
    </span>
  );
}
