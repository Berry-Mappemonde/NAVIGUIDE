import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import L from "leaflet";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
import "leaflet/dist/leaflet.css";
import "./index.css";
import App from "./App.jsx";
import { LangProvider } from "./i18n/LangContext.jsx";
import { RootBoundary } from "./components/PanelBoundary.jsx";
import { captureAdminSecretFromUrl } from "./utils/adminSecret.js";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });

// `?admin=…` once → stored in this browser, removed from the address bar.
captureAdminSecretFromUrl();

// #101 : toute erreur de rendu laisse une trace en console ; RootBoundary évite la page blanche.
const logRenderError = (kind) => (error, info) => {
  console.error(`[naviguide] ${kind}`, error, info?.componentStack);
};

createRoot(document.getElementById("root"), {
  onUncaughtError: logRenderError("erreur de rendu non rattrapée"),
  onCaughtError: logRenderError("erreur de rendu rattrapée par un filet"),
}).render(
  <StrictMode>
    <RootBoundary>
      <LangProvider>
        <App />
      </LangProvider>
    </RootBoundary>
  </StrictMode>,
);
