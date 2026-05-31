import { Suspense } from "react";
// U: OLD: import ReactDOM from "react-dom";
// U: NEW: React 19 uses the concurrent root API from react-dom/client.
import { createRoot } from "react-dom/client";
import "./assets/scss/style.scss";
import "bootstrap-icons/font/bootstrap-icons.css";
import App from "./App";
// U: OLD: import { BrowserRouter, HashRouter } from "react-router-dom";
// U: NEW: HashRouter was unused; the app currently runs with BrowserRouter.
import { BrowserRouter } from "react-router-dom";
import Loader from "./layouts/loader/Loader";
// U: OLD: PrimeReact theme/runtime CSS was loaded globally even though no PrimeReact components are used.
// import "primereact/resources/themes/lara-light-indigo/theme.css";
// import "primereact/resources/primereact.min.css";
import "primeicons/primeicons.css";
// U: NEW: last global stylesheet for Chikooza tokens and shared component standards.
import "./assets/css/design-system.css";
// U: OLD: PrimeFlex utilities were imported globally but are not used by the current UI.
// import "primeflex/primeflex.css";

const rootElement = document.getElementById("root");

createRoot(rootElement).render(
  <Suspense fallback={<Loader />}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </Suspense>
);
