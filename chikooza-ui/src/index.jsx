import React, { Suspense } from "react";
import ReactDOM from "react-dom";
import "./assets/scss/style.scss";
import "bootstrap-icons/font/bootstrap-icons.css";
import App from "./App";
// U: OLD: import { BrowserRouter, HashRouter } from "react-router-dom";
// U: NEW: HashRouter was unused; the app currently runs with BrowserRouter.
import { BrowserRouter } from "react-router-dom";
import Loader from "./layouts/loader/Loader";
import "primereact/resources/themes/lara-light-indigo/theme.css";
import "primereact/resources/primereact.min.css";
import "primeicons/primeicons.css";
import "primeflex/primeflex.css";

ReactDOM.render(
  <Suspense fallback={<Loader />}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </Suspense>,

  document.getElementById("root")
);
