import { useState, useEffect, useRef } from "react";
import { Box } from "@mui/material";
import AppDrawer, {
  SIDEBAR_WIDTH,
  SIDEBAR_COLLAPSED_WIDTH,
  TOPBAR_HEIGHT,
} from "../components/AppDrawer";
import RequireAuth from "../components/auth/RequireAuth";
import { useLanguage } from "../context/LanguageContext";
import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion";
import { paletteTokens } from "../theme";

function Root() {
  const { t } = useLanguage();
  const prefersReducedMotion = usePrefersReducedMotion();

  // Default state on every page load: sidebar OPEN (collapsed = false).
  // NO persistence in localStorage (per Yêu cầu 2).
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const isTransitioningRef = useRef<boolean>(false);

  const handleToggleCollapse = () => {
    if (isTransitioningRef.current) return;
    setCollapsed((prev) => !prev);
  };

  // Auto-collapse on main content click (desktop only, when sidebar is open)
  const handleMainContentClick = (event: React.MouseEvent<HTMLElement>) => {
    // Below md (< 900px), do nothing
    if (window.innerWidth < 900) return;

    // Only collapse when currently open, and ignore while in transition
    if (collapsed || isTransitioningRef.current) return;

    // Synthetic keyboard click (Enter / Space) has event.detail === 0 -> Do NOT collapse (WCAG 3.2.1)
    if (event.detail === 0) return;

    // Skip if user is dragging/selecting text in content
    const selection = window.getSelection();
    if (selection && selection.toString().trim().length > 0) return;

    // Verify click is inside <main>
    const mainEl = document.getElementById("main-content");
    if (!mainEl || !mainEl.contains(event.target as Node)) return;

    // Risk 8 Mitigation: Do NOT collapse if user clicked an element that triggers/controls a popup,
    // select dropdown, menu, or dialog (avoids popover anchor shift and misplacement).
    const target = event.target as HTMLElement | null;
    if (target) {
      const isPopupTrigger = target.closest(
        '[aria-haspopup], [aria-expanded], .MuiSelect-select, .MuiAutocomplete-popupIndicator, .MuiMenu-root, .MuiPopover-root'
      );
      if (isPopupTrigger) return;
    }

    // Also do not collapse if an overlay (Menu / Popover / Dialog) is currently active in the DOM
    const hasOpenOverlay = document.querySelector(
      '.MuiPopover-root:not([style*="visibility: hidden"]), .MuiDialog-root, .MuiMenu-root'
    );
    if (hasOpenOverlay) return;

    // Collapse on valid mouse/touch click in main content area
    isTransitioningRef.current = !prefersReducedMotion;
    setCollapsed(true);
  };

  // When prefers-reduced-motion is active, immediately dispatch resize on collapse change
  useEffect(() => {
    if (prefersReducedMotion) {
      isTransitioningRef.current = false;
      window.dispatchEvent(new Event("resize"));
    }
  }, [collapsed, prefersReducedMotion]);

  // Transitionend handler: dispatch exactly ONE resize event after transition completes
  const handleTransitionEnd = (e: React.TransitionEvent<HTMLElement>) => {
    if (e.target === e.currentTarget && (e.propertyName === "width" || e.propertyName === "margin-left")) {
      isTransitioningRef.current = false;
      window.dispatchEvent(new Event("resize"));
    }
  };

  const currentSidebarWidth = collapsed
    ? SIDEBAR_COLLAPSED_WIDTH
    : SIDEBAR_WIDTH;

  const transitionDuration = prefersReducedMotion ? "none" : "0.2s cubic-bezier(0.4, 0, 0.2, 1)";
  const transitionStyle = prefersReducedMotion
    ? "none"
    : `margin-left ${transitionDuration}, width ${transitionDuration}`;

  return (
    <Box
      sx={{
        minHeight: "100vh",
        position: "relative",
        overflowX: "hidden",
        backgroundColor: paletteTokens.bgDefault,
      }}
    >
      {/* Accessible Skip Link (WCAG 2.4.1 Bypass Blocks) */}
      <Box
        component="a"
        href="#main-content"
        sx={{
          position: "fixed",
          top: "-100px",
          left: 16,
          zIndex: 99999,
          backgroundColor: paletteTokens.primary,
          color: paletteTokens.primaryContrastText,
          px: 2.5,
          py: 1.25,
          borderRadius: "8px",
          fontWeight: 600,
          fontSize: "14px",
          textDecoration: "none",
          boxShadow: "0 4px 16px rgba(0, 0, 0, 0.6)",
          transition: prefersReducedMotion ? "none" : "top 0.2s ease-in-out",
          "&:focus": {
            top: 16,
            outline: "2px solid #ffffff",
            outlineOffset: 2,
          },
        }}
      >
        {t("skip_to_content")}
      </Box>

      {/* Main navigation & content layer */}
      <Box
        sx={{
          position: "relative",
          zIndex: 1,
          display: "flex",
          minHeight: "100vh",
          width: "100%",
        }}
      >
        <AppDrawer
          collapsed={collapsed}
          onToggleCollapse={handleToggleCollapse}
        />

        <Box
          component="main"
          id="main-content"
          tabIndex={-1}
          onClick={handleMainContentClick}
          onTransitionEnd={handleTransitionEnd}
          sx={{
            flexGrow: 1,
            minWidth: 0,
            ml: { xs: 0, md: `${currentSidebarWidth}px` },
            mt: `${TOPBAR_HEIGHT}px`,
            p: { xs: 2, sm: 2.5, md: 3, lg: 3.5 },
            width: {
              xs: "100%",
              md: `calc(100% - ${currentSidebarWidth}px)`,
            },
            maxWidth: "1600px",
            boxSizing: "border-box",
            transition: transitionStyle,
            outline: "none",
            "@media print": {
              ml: "0 !important",
              mt: "0 !important",
              p: "0 !important",
              width: "100% !important",
              maxWidth: "100% !important",
            },
          }}
        >
          <RequireAuth />
        </Box>
      </Box>
    </Box>
  );
}

export default Root;
