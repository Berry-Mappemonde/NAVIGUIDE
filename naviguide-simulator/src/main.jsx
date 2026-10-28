import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import L from "leaflet";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
import "leaflet/dist/leaflet.css";
import "@fontsource-variable/atkinson-hyperlegible-next";
import "@fontsource-variable/source-serif-4";
import "@fontsource-variable/ibm-plex-sans";
import "@fontsource-variable/fraunces";
import "@fontsource-variable/public-sans";
import "./index.css";
import App from "./App.jsx";
import { LangProvider } from "./i18n/LangContext.jsx";
import { captureAdminSecretFromUrl } from "./utils/adminSecret.js";
import { installChartTileFilters } from "./map/chartTiles.js";
import { applyThemeToDocument, readStoredTheme } from "./constants/themes.js";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });
installChartTileFilters();
// Before the first render, so the page never flashes the default theme or fetches its fonts.
applyThemeToDocument(readStoredTheme());

// `?admin=…` once → stored in this browser, removed from the address bar.
captureAdminSecretFromUrl();

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <LangProvider>
      <App />
    </LangProvider>
  </StrictMode>,
);
