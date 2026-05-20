import { Outlet } from "react-router-dom";
//import Sidebar from "./Sidebar";
import Header from "./Header";
import Footer from "./Footer";

const FullLayout = () => {
  return (
    <main>
      {/********header**********/}
      <Header />
      <div className="pageWrapper d-lg-flex">
        {/********Sidebar**********/}
        {/*<aside className="sidebarArea shadow" id="sidebarArea">
          <Sidebar />
        </aside>*/}
        {/********Content Area**********/}
        {/* U: OLD: public routes were wrapped in a dashboard breadcrumb card.
            U: NEW: public/auth pages render as modern full-width product pages. */}
        <div className="contentArea public-content-area">
          {/********Middle Content**********/}
          <Outlet />
        </div>
      </div>
      <Footer />
    </main>
  );
};

export default FullLayout;
