import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";

const FullLayout = () => {

  return (
    <div className="app-layout public-app-layout">
      {/********header**********/}
      <Header />
      <div className="pageWrapper d-lg-flex" id="main-content" tabIndex="-1">
        {/* U: OLD: home was forced inside a padded Bootstrap container, making the landing page look boxed-in.
            U: NEW: let marketing pages control their own responsive spacing and full-width sections. */}
        <Outlet />
      </div>
      <Footer />
    </div>
  );
};

export default FullLayout;
