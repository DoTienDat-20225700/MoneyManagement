import { useEffect, useState } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

/**
 * Custom hook to detect if the user has requested the system minimize the amount
 * of non-essential motion it uses (WCAG 2.3.3 Animation from Interactions - Level AAA).
 *
 * Safe for SSR and environments where window.matchMedia is not available.
 */
export function usePrefersReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    return window.matchMedia(QUERY).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const mediaQueryList = window.matchMedia(QUERY);
    const listener = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    if (mediaQueryList.addEventListener) {
      mediaQueryList.addEventListener("change", listener);
    } else if ((mediaQueryList as any).addListener) {
      (mediaQueryList as any).addListener(listener);
    }

    return () => {
      if (mediaQueryList.removeEventListener) {
        mediaQueryList.removeEventListener("change", listener);
      } else if ((mediaQueryList as any).removeListener) {
        (mediaQueryList as any).removeListener(listener);
      }
    };
  }, []);

  return prefersReducedMotion;
}
