import { Suspense } from "react";
import { createRoot } from "react-dom/client";
import "./assets/scss/style.scss";
import "bootstrap-icons/font/bootstrap-icons.css";
import App from "./App";
import { BrowserRouter } from "react-router-dom";
import Loader from "./layouts/loader/Loader";
import "./assets/css/design-system.css";

const rootElement = document.getElementById("root");

createRoot(rootElement).render(
  <Suspense fallback={<Loader />}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </Suspense>
);
