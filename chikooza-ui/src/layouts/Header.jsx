import React, { useEffect } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
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
  const location = useLocation();
  const [isOpen, setIsOpen] = React.useState(false);

  const closeNavigation = () => setIsOpen(false);

  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  return (
    <Navbar light expand="md" className="fix-header chikooza-public-header" aria-label="Public navigation">
      <div className="d-flex align-items-center">
        <Link to="/" className="navbar-brand chikooza-brand" onClick={closeNavigation}>
          <img src={Logo} alt="Chikooza" className="chikooza-brand-logo" />
        </Link>
      </div>
      <div className="hstack gap-2">
        <Button
          color="success"
          size="sm"
          className="d-sm-block d-md-none chikooza-menu-button"
          type="button"
          onClick={() => setIsOpen((current) => !current)}
          aria-controls="public-navigation"
          aria-expanded={isOpen}
          aria-label={isOpen ? "Close public navigation" : "Open public navigation"}
        >
          {isOpen ? (
            <i className="bi bi-x-lg fs-5" aria-hidden="true"></i>
          ) : (
            <i className="bi bi-list fs-4" aria-hidden="true"></i>
          )}
        </Button>
      </div>

      <Collapse navbar isOpen={isOpen} id="public-navigation">
        <Nav className="me-auto" navbar>
          <NavItem>
            <NavLink to="/" onClick={closeNavigation} className={({ isActive }) => `linkheader ${isActive ? "linkheader-active" : ""}`}>
              Home
            </NavLink>
          </NavItem>
          <NavItem>
            <NavLink to="/about" onClick={closeNavigation} className={({ isActive }) => `linkheader ${isActive ? "linkheader-active" : ""}`}>
              About Us
            </NavLink>
          </NavItem>
          <NavItem>
            <NavLink to="/contact" onClick={closeNavigation} className={({ isActive }) => `linkheader ${isActive ? "linkheader-active" : ""}`}>
              Contact
            </NavLink>
          </NavItem>
          <NavItem>
            <Link to="/login" className="linkheader linkheader-cta" onClick={closeNavigation}>
              Login
            </Link>
          </NavItem>
          <NavItem>
            <Link to="/register" className="linkheader linkheader-secondary" onClick={closeNavigation}>
              Register for free
            </Link>
          </NavItem>
        </Nav>
      </Collapse>
    </Navbar>
  );
};

export default Header;
