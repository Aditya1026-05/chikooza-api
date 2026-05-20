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
  // U: OLD: const [user, SetUser] = useState(localStorage.getItem('token') !== null ? false : true)
  // U: NEW: derive auth state directly; no unused setter and no stale header state.
  const isGuest = localStorage.getItem('token') === null;
  // const [dropdownOpen, setDropdownOpen] = React.useState(false);

  // const toggle = () => setDropdownOpen((prevState) => !prevState);
  const Handletoggle = () => {
    setIsOpen(!isOpen);
  };
  // const showMobilemenu = () => {
  //   document.getElementById("sidebarArea").classList.toggle("showSidebar");
  // };
  return (
    <Navbar light expand="md" className="fix-header chikooza-public-header">
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
        >
          {isOpen ? (
            <i className="bi bi-x fs-5"></i>
          ) : (
            <i className="bi bi-three-dots-vertical fs-5"></i>
          )}
        </Button>
      </div>

      <Collapse navbar isOpen={isOpen}>
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
          {isGuest ?
            <>
              <NavItem>
                <Link to="/login" className="linkheader linkheader-cta">
                  Login
                </Link>
              </NavItem>
              <NavItem>
                <Link to="/register" className="linkheader linkheader-secondary">
                  Start free
                </Link>
              </NavItem>
            </>
            : <NavItem>
              <Link to="/member" className="linkheader linkheader-cta">
                Dashboard
              </Link>
            </NavItem>
          }
        </Nav>
      </Collapse>
    </Navbar>
  );
};

export default Header;
