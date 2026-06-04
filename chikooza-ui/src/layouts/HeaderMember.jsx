import React from "react";
import { Link } from "react-router-dom";
import {
  Navbar,
  Collapse,
  Nav,
  NavItem,
  DropdownToggle,
  DropdownMenu,
  Dropdown,
  Button,
} from "reactstrap";
//import { ReactComponent as LogoWhite } from "../assets/images/logos/adminprowhite.svg";
import '../assets/css/header.css';
import Logo from "../assets/images/logos/chikooza_logo.png";
import { useEffect } from "react";
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { apiPath, getAuthConfig } from "../Constants";
import { FaAngleDown } from "react-icons/fa";

const Header = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = React.useState(false);
  const [activeMenu, setActiveMenu] = React.useState(null);

  const [dropdownOpen, setDropdownOpen] = React.useState(false);

  const toggle = () => setDropdownOpen((prevState) => !prevState);
  const toggleMenu = (menu) => {
    setActiveMenu((current) => (current === menu ? null : menu));
  };
  const closeMenus = () => {
    setActiveMenu(null);
  };
  const Handletoggle = () => {
    setIsOpen(!isOpen);
    setActiveMenu(null);
  };
  useEffect(() => {
    if (localStorage.getItem('token') === null) {
      navigate("/login")
    }
  // U: OLD dependency list was empty and triggered React hook warnings.
  // U: NEW includes navigate so the auth redirect effect follows React hook rules.
  }, [navigate])
  let logout = () => {
    let url = `${apiPath}users/logout/`;
    // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
    // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
    axios.get(url, getAuthConfig()).then((res) => {
      localStorage.clear();
      navigate("/login");
    }).catch((err) => {
      localStorage.clear();
      navigate("/login");
    });
  }
  // const showMobilemenu = () => {
  //   document.getElementById("sidebarArea").classList.toggle("showSidebar");
  // };
  return (
    <Navbar light expand="md" className="fix-header chikooza-public-header" aria-label="Farmer workspace navigation">
      <div className="d-flex align-items-center">
        {/* U: OLD: member header used a temporary CSS "C" mark.
            U: NEW: use the same real Chikooza wordmark as the public header. */}
        <Link to="/member" className="navbar-brand chikooza-brand">
          <img src={Logo} alt="Chikooza" className="chikooza-brand-logo" />
        </Link>
        {/* <Button
          color="primary"
          className=" d-lg-none"
          onClick={() => showMobilemenu()}
        >
          <i className="bi bi-list"></i>
        </Button> */}
      </div>
      <div className="hstack gap-2">
        <Button
          color="success"
          size="sm"
          className="d-sm-block d-md-none chikooza-menu-button"
          onClick={Handletoggle}
          aria-controls="member-navigation"
          aria-expanded={isOpen}
          aria-label={isOpen ? "Close farmer workspace navigation" : "Open farmer workspace navigation"}
        >
          {isOpen ? (
            <i className="bi bi-x fs-5"></i>
          ) : (
            <i className="bi bi-three-dots-vertical fs-5"></i>
          )}
        </Button>
      </div>

      <Collapse navbar isOpen={isOpen} id="member-navigation">
        <Nav className="me-auto" navbar>
          <NavItem>
            <Link to="/member" className="linkheader" onClick={closeMenus}>
              Home
            </Link>
          </NavItem>
          {/* U: OLD: independent uncontrolled dropdowns could stay open together and overlap.
              U: NEW: control member-nav dropdowns with one active menu so opening Flock closes Farm. */}
          <Dropdown inNavbar nav isOpen={activeMenu === "farm"} toggle={() => toggleMenu("farm")}>
            <DropdownToggle caret nav className="linkheader">
              Farm
            </DropdownToggle>
            <DropdownMenu end>
              {/* U: OLD: DropdownItem tag={Link} did not navigate reliably after making menus controlled.
                  U: NEW: render real React Router links inside the dropdown menu. */}
              <Link to="/addfarm" className="dropdown-item member-dropdown-link" onClick={closeMenus}>
                Add Farm
              </Link>
              <Link to="/managefarm" className="dropdown-item member-dropdown-link" onClick={closeMenus}>
                View/Edit Farm
              </Link>
            </DropdownMenu>
          </Dropdown>
          <Dropdown inNavbar nav isOpen={activeMenu === "flock"} toggle={() => toggleMenu("flock")}>
            <DropdownToggle caret nav className="linkheader">
              Flock
            </DropdownToggle>
            <DropdownMenu end>
              <Link to="/addflock" className="dropdown-item member-dropdown-link" onClick={closeMenus}>Add Flock</Link>
              <Link to="/manageflock" className="dropdown-item member-dropdown-link" onClick={closeMenus}>View/Edit Flock</Link>
              <Link to="/flockdailydata" className="dropdown-item member-dropdown-link" onClick={closeMenus}>Flock Daily Data</Link>
            </DropdownMenu>
          </Dropdown>
          <Dropdown inNavbar nav isOpen={activeMenu === "sales"} toggle={() => toggleMenu("sales")}>
            <DropdownToggle caret nav className="linkheader">
              Sales
            </DropdownToggle>
            <DropdownMenu end>
              <Link to="/flocksale" className="dropdown-item member-dropdown-link" onClick={closeMenus}>Flock Sale</Link>
              <Link to="/viewsale" className="dropdown-item member-dropdown-link" onClick={closeMenus}>View/Edit Sales</Link>
            </DropdownMenu>
          </Dropdown>
          <Dropdown inNavbar nav isOpen={activeMenu === "purchases"} toggle={() => toggleMenu("purchases")}>
            <DropdownToggle caret nav className="linkheader">
              Purchases
            </DropdownToggle>
            <DropdownMenu end>
              <Link to="/addpurchase" className="dropdown-item member-dropdown-link" onClick={closeMenus}>Add Purchase</Link>
              <Link to="/listpurchase" className="dropdown-item member-dropdown-link" onClick={closeMenus}>View/Edit Purchase</Link>
            </DropdownMenu>
          </Dropdown>
          <Dropdown inNavbar nav isOpen={activeMenu === "reports"} toggle={() => toggleMenu("reports")}>
            <DropdownToggle caret nav className="linkheader">
              Reports
            </DropdownToggle>
            <DropdownMenu end>
              <Link to="/dailydatasheet" className="dropdown-item member-dropdown-link" onClick={closeMenus}>Daily Data Sheet</Link>
              <Link to="/flocksummary" className="dropdown-item member-dropdown-link" onClick={closeMenus}>Flock Summary</Link>
            </DropdownMenu>
          </Dropdown>
          <NavItem>
            <Link to="/chatbot" className="linkheader linkheader-cta" onClick={closeMenus}>
              AI Assistant
            </Link>
          </NavItem>
        </Nav>
        <Dropdown isOpen={dropdownOpen} toggle={toggle} className="member-user-menu">
          <DropdownToggle color="transparent" className="member-user-toggle" aria-label="Open farmer account menu">
            Hi, {localStorage.getItem('fname')} <FaAngleDown></FaAngleDown>
            {/*<img src={user1} alt="profile" className="rounded-circle" width="30"></img>*/}
          </DropdownToggle>
          <DropdownMenu end className="member-user-dropdown">
            <Link to="/profile" className="member-user-dropdown__item" onClick={toggle}>Profile</Link>
            <Link to="/changepassword" className="member-user-dropdown__item" onClick={toggle}>Change password</Link>
            <button type="button" className="member-user-dropdown__item member-user-dropdown__item--danger" onClick={logout}>Logout</button>
          </DropdownMenu>
        </Dropdown>
      </Collapse>
    </Navbar>
  );
};

export default Header;
