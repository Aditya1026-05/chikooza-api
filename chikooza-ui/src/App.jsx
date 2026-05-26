import { useEffect } from "react";
import { useLocation, useRoutes } from "react-router-dom";
import Themeroutes from "./routes/Router";

const App = () => {
  const location = useLocation();
  const routing = useRoutes(Themeroutes);

  useEffect(() => {
    // U: React Router navigation does not reload the page, so reset scroll
    // U: manually to match normal website navigation behavior.
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [location.pathname]);

  return <div className="dark">{routing}</div>;
};

export default App;
