import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";
import { Container } from "reactstrap";

const FullLayout = () => {

  return (
    <main>
      {/********header**********/}
      <Header />
      <div className="pageWrapper d-lg-flex">
        <Container className="p-4" fluid>
          <Outlet />
        </Container>
      </div>
      <Footer />
    </main>
  );
};

export default FullLayout;
