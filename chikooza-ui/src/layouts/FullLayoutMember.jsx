import { Outlet } from "react-router-dom";
import Header from "./HeaderMember";
import MemberFooter from "./MemberFooter";
import { Container } from "reactstrap"
const FullLayoutMember = () => {
  return (
    <div className="app-layout">
      {/********header**********/}
      <Header />
      <div className="pageWrapper d-lg-flex">
        {/********Sidebar**********/}
        {/*<aside className="sidebarArea shadow" id="sidebarArea">
          <Sidebar />
        </aside>*/}
        {/********Content Area**********/}
        <div className="contentArea" id="main-content" tabIndex="-1">
          {/********Middle Content**********/}
          <Container className="member-page-container" fluid>
            {/* <Row>
              <Col>
                <Card className="sliderclass">
                  <CardBody className="">
                  <Carousel variant="dark">
                  <Carousel.Item>
                    <img
                      className="d-block"
                      src={firstimage}
                      height='100'
                      width='177'
                      alt="First slide"
                    />
                  </Carousel.Item>
                  <Carousel.Item>
                    <img
                      className="d-block"
                      src={firstimage}
                      height='100'
                      width='177'
                      alt="Second slide"
                    />
                  </Carousel.Item>
                  <Carousel.Item>
                    <img
                      className="d-block"
                      src={firstimage}
                      height='100'
                      width='177'
                      alt="Third slide"
                    />
                  </Carousel.Item>
                </Carousel>
                  </CardBody>
                </Card>
              </Col>
            </Row> */}
            {/*<Row>
              <Col>
                <Card>
                  <CardBody className="">
                    <Breadcrumb>
                      <BreadcrumbItem active>
                        <span style={{color: "#b71c1c"}}><Link to="/" style={{color: '#b71c1c','textDecoration':'none'}}>Home</Link></span> /
                        {
                          location.pathname.split('/')[1]=='login'?' Farmer Login':
                          location.pathname.split('/')[1]=='home'?' Home':
                          location.pathname.split('/')[1]=='about'?' About Us':
                          location.pathname.split('/')[1]=='register'?' Farmer Registration':
                          location.pathname.split('/')[1]=='contact'?' Contact Us':
                          'Page Not Found'
                        }
                      </BreadcrumbItem>
                      <BreadcrumbItem>
                        <a href="/">Library</a>
                      </BreadcrumbItem>
                      <BreadcrumbItem active>Data</BreadcrumbItem>
                    </Breadcrumb>
                  </CardBody>
                </Card>
              </Col>
            </Row>*/}
            <Outlet />
          </Container>
        </div>
      </div>
      <MemberFooter />
    </div>
  );
};

export default FullLayoutMember;
