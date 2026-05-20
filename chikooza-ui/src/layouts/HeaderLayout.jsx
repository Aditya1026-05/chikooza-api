import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";

const FullLayout = () => {

  return (
    <main>
      {/********header**********/}
      <Header />
      <div className="pageWrapper d-lg-flex">
        {/* U: OLD: home was forced inside a padded Bootstrap container, making the landing page look boxed-in.
            U: NEW: let marketing pages control their own responsive spacing and full-width sections. */}
        <Outlet />
      </div>
      <Footer />
    </main>
  );
};

export default FullLayout;
