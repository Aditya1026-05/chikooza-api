// U: OLD unused dashboard/form/table imports were removed from runtime imports to reduce build noise.
// import ProjectTables from "../../components/dashboard/ProjectTable";
// import { Table, Card, CardTitle, CardBody, Form, FormGroup, Label } from "reactstrap";
import { Row, Col, Button } from "reactstrap";
// import home from "../../assets/images/front/home.png";
// import profile1 from "../../assets/images/front/profile2.png";
// import HeaderImg from "../../assets/frontimages/1.jpg";
// import Image3 from "../../assets/frontimages/2.jpg";
// import Image4 from "../../assets/frontimages/3.jpg";
// import Image5 from "../../assets/frontimages/4.jpg";
// import Image6 from "../../assets/frontimages/about.jpg";
// import Image7 from "../../assets/frontimages/bg.jpg";
// import Image8 from "../../assets/frontimages/bg1.jpg";
import Image9 from "../../assets/frontimages/bg2.jpg";
// U: OLD: import Marquee from "react-fast-marquee";
// U: NEW: use a CSS marquee so the home page does not depend on an old React-only package.
import CarousalHome from "./CarousalHome"

// MV-2025-07-05-<9>  STARTS
import ChikoozaChatbot from '../../components/ChikoozaChatbot/ChikoozaChatbot';
// MV-2025-07-05-<9>  ENDS


// import { useNavigate } from "react-router-dom";

// U: OLD unused contact icons were removed from runtime imports; contact UI is handled on the Contact page.
// import { FaPhoneAlt, FaUser, FaUserCircle } from "react-icons/fa";
// import { MdEmail } from "react-icons/md";
import { useNavigate } from "react-router-dom";
const Home = () => {
  let navigate = useNavigate();
  let Aboutus = () => {
    navigate("/about");
  }
  return (
    <>
      <Row className="chikooza-hero g-0">
        <Col sm="12" lg="6" xl="6" xxl="6" className="chikooza-hero-copy">
          <div className="chikooza-hero-panel">
            {/* U: OLD hero used inline 50px text and a generic danger button. */}
            <span className="chikooza-eyebrow">Poultry farm intelligence</span>
            <h1 className="chikooza-hero-title">
              Insights into your flock, from placement to performance.
            </h1>
            <p className="chikooza-hero-subtitle">
              Track broiler performance, daily operations, purchases, sales, and flock health in one focused workspace.
            </p>
            <div className="chikooza-hero-actions">
              <Button type="button" className="chikooza-primary-action" onClick={Aboutus}>Explore Chikooza</Button>
              <Button type="button" className="chikooza-secondary-action" outline onClick={() => navigate("/register")}>Create farmer account</Button>
            </div>
            <div className="chikooza-metrics-strip" aria-label="Product capabilities">
              <div><strong>FCR</strong><span>Performance tracking</span></div>
              <div><strong>Daily</strong><span>Mortality & feed logs</span></div>
              <div><strong>Sales</strong><span>Revenue visibility</span></div>
            </div>
          </div>
        </Col>
        <Col sm="12" lg="6" xl="6" xxl="6" className="chikooza-hero-media">
          <div className="chikooza-carousel-shell">
            <CarousalHome />
          </div>
        </Col>
    </Row>
    <Row className="chikooza-welcome-section g-0">
      <div className="grid mt-2">
        <div className="col-12 index_banner">
          <h1 className="chikooza-banner-title">Welcome to Chikooza</h1>
          <p className="chikooza-banner-copy">A practical operating system for farms that need clearer decisions, not more spreadsheets.</p>
          <div className="flex justify-content-center">
              <Button type="button" className="chikooza-banner-action" onClick={Aboutus}>Read more</Button>
          </div>
        </div>
      </div>
    </Row>
    <Row className="chikooza-gallery-band g-0">
      <div className="chikooza-marquee" aria-label="Poultry farm gallery">
        <div className="chikooza-marquee-track">
          <img src={Image9} className="chikooza-marquee-image" alt="Poultry farm environment" />
          <img src={Image9} className="chikooza-marquee-image" alt="" aria-hidden="true" />
        </div>
      </div>
    </Row>
{/* MV-2025-07-05-<9>  STARTS */}
    <ChikoozaChatbot alwaysVisible={true} defaultOpen={false} />
{/* MV-2025-07-05-<9>  ENDS */}
    </>
  );
};
export default Home;
