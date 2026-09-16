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

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <LangProvider>
      <App />
    </LangProvider>
  </StrictMode>,
);
