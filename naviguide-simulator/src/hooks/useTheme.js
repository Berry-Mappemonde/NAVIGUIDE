import { useCallback, useEffect, useState } from "react";
import {
  applyThemeToDocument,
  isDayTheme,
  readStoredTheme,
  storeTheme,
  themeForMode,
} from "../constants/themes.js";

/** Current theme, remembered per browser; the Dark/Light switch maps onto it. */
export function useTheme() {
  const [theme, setThemeState] = useState(() => readStoredTheme());

  useEffect(() => {
    applyThemeToDocument(theme);
    storeTheme(theme);
  }, [theme]);

  const setTheme = useCallback((id) => setThemeState(id), []);
  const setIsLightMode = useCallback((wantDay) => {
    setThemeState((current) => themeForMode(current, wantDay));
  }, []);

  return { theme, setTheme, isLightMode: isDayTheme(theme), setIsLightMode };
}
