import { useRef, useState } from "react";

const TOOLTIP_GAP = 8;
const TOOLTIP_MAX_WIDTH = 280;

/** `placement="left"` opens the tooltip leftward, sized to the space left of the icon. */
export function InfoIcon({ tip, onClick, href, fixedOnHover = false, placement = "right" }) {
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
    if (!iconRef.current) return;
    const rect = iconRef.current.getBoundingClientRect();
    if (placement === "left") {
      const room = rect.left - TOOLTIP_GAP * 2;
      setTooltipStyle({ maxWidth: `${Math.min(TOOLTIP_MAX_WIDTH, room)}px` });
      return;
    }
    if (!fixedOnHover) return;
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
      className={`main-info-icon${isLink ? " main-info-icon--link" : ""}${
        placement === "left" ? " main-info-icon--tip-left" : ""
      }`}
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
