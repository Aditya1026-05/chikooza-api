import React from "react";
import { Link, NavLink } from "react-router-dom";
import {
  Navbar,
  Collapse,
  Nav,
  NavItem,
  Button,
} from "reactstrap";
import '../assets/css/header.css';
import Logo from "../assets/images/logos/chikooza_logo.png";

const Header = () => {
  // const navigate = useNavigate();
  const [isOpen, setIsOpen] = React.useState(false);
  // U: OLD: public pages changed the right CTA to Dashboard when a token existed.
  // U: NEW: public marketing/info pages always show the public header; logged-in app
  // U: navigation lives only in HeaderMember so farmers do not bounce back to landing pages.
  // const [dropdownOpen, setDropdownOpen] = React.useState(false);

  // const toggle = () => setDropdownOpen((prevState) => !prevState);
  const Handletoggle = () => {
    setIsOpen(!isOpen);
  };
  // const showMobilemenu = () => {
  //   document.getElementById("sidebarArea").classList.toggle("showSidebar");
  // };
  return (
    <Navbar light expand="md" className="fix-header chikooza-public-header" aria-label="Public navigation">
      <div className="d-flex align-items-center">
        {/* U: OLD: header used a temporary CSS "C" mark that looked generic.
            U: NEW: restore the real Chikooza wordmark for a more professional brand header. */}
        <Link to="/" className="navbar-brand chikooza-brand">
          <img src={Logo} alt="Chikooza" className="chikooza-brand-logo" />
        </Link>
        {/*<Button
          color="primary"
          className=" d-lg-none"
          onClick={() => showMobilemenu()}
        >
          <i className="bi bi-list"></i>
        </Button>*/}
      </div>
      <div className="hstack gap-2">
        <Button
          color="success"
          size="sm"
          className="d-sm-block d-md-none chikooza-menu-button"
          onClick={Handletoggle}
          aria-controls="public-navigation"
          aria-expanded={isOpen}
          aria-label={isOpen ? "Close public navigation" : "Open public navigation"}
        >
          {isOpen ? (
            <i className="bi bi-x fs-5"></i>
          ) : (
            <i className="bi bi-three-dots-vertical fs-5"></i>
          )}
        </Button>
      </div>

      <Collapse navbar isOpen={isOpen} id="public-navigation">
        <Nav className="me-auto" navbar>
          <NavItem>
            <NavLink to="/" className={({ isActive }) => `linkheader ${isActive ? "linkheader-active" : ""}`}>
              Home
            </NavLink>
          </NavItem>
          <NavItem>
            <NavLink to="/about" className={({ isActive }) => `linkheader ${isActive ? "linkheader-active" : ""}`}>
              About Us
            </NavLink>
          </NavItem>
          <NavItem>
            <NavLink to="/contact" className={({ isActive }) => `linkheader ${isActive ? "linkheader-active" : ""}`}>
              Contact
            </NavLink>
          </NavItem>
          <NavItem>
            <Link to="/login" className="linkheader linkheader-cta">
              Login
            </Link>
          </NavItem>
          <NavItem>
            <Link to="/register" className="linkheader linkheader-secondary">
              Register for free
            </Link>
          </NavItem>
        </Nav>
      </Collapse>
    </Navbar>
  );
};

export default Header;
