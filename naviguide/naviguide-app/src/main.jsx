import { StrictMode, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { LangProvider } from "./i18n/LangContext.jsx";

const App = lazy(() => import("./App.jsx"));

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <LangProvider>
      <Suspense fallback={null}>
        <App />
      </Suspense>
    </LangProvider>
  </StrictMode>
);
