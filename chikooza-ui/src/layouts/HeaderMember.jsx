import React, { useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
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
import '../assets/css/header.css';
import Logo from "../assets/images/logos/chikooza_logo.png";
import axios from 'axios';
import { apiPath, getAuthConfig } from "../Constants";
import { FaAngleDown } from "react-icons/fa";

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = React.useState(false);
  const [activeMenu, setActiveMenu] = React.useState(null);
  const [dropdownOpen, setDropdownOpen] = React.useState(false);

  const toggleUserMenu = () => {
    setDropdownOpen((current) => !current);
    setActiveMenu(null);
  };
  const toggleMenu = (menu) => {
    setActiveMenu((current) => (current === menu ? null : menu));
    setDropdownOpen(false);
  };
  const closeMenus = () => {
    setActiveMenu(null);
    setDropdownOpen(false);
    setIsOpen(false);
  };
  const toggleNavigation = () => {
    setIsOpen((current) => !current);
    setActiveMenu(null);
    setDropdownOpen(false);
  };

  useEffect(() => {
    if (localStorage.getItem('token') === null) {
      navigate("/login")
    }
  }, [navigate])

  useEffect(() => {
    setIsOpen(false);
    setActiveMenu(null);
    setDropdownOpen(false);
  }, [location.pathname]);

  let logout = () => {
    closeMenus();
    let url = `${apiPath}users/logout/`;
    axios.get(url, getAuthConfig()).then((res) => {
      localStorage.clear();
      navigate("/login");
    }).catch((err) => {
      localStorage.clear();
      navigate("/login");
    });
  }
  return (
    <Navbar light expand="md" className="fix-header chikooza-public-header" aria-label="Farmer workspace navigation">
      <div className="d-flex align-items-center">
        <Link to="/member" className="navbar-brand chikooza-brand" onClick={closeMenus}>
          <img src={Logo} alt="Chikooza" className="chikooza-brand-logo" />
        </Link>
      </div>
      <div className="hstack gap-2">
        <Button
          color="success"
          size="sm"
          className="d-sm-block d-md-none chikooza-menu-button"
          type="button"
          onClick={toggleNavigation}
          aria-controls="member-navigation"
          aria-expanded={isOpen}
          aria-label={isOpen ? "Close farmer workspace navigation" : "Open farmer workspace navigation"}
        >
          {isOpen ? (
            <i className="bi bi-x-lg fs-5" aria-hidden="true"></i>
          ) : (
            <i className="bi bi-list fs-4" aria-hidden="true"></i>
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
          <Dropdown inNavbar nav isOpen={activeMenu === "farm"} toggle={() => toggleMenu("farm")}>
            <DropdownToggle caret nav className="linkheader">
              Farm
            </DropdownToggle>
            <DropdownMenu end>
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
        <Dropdown isOpen={dropdownOpen} toggle={toggleUserMenu} className="member-user-menu">
          <DropdownToggle color="transparent" className="member-user-toggle" aria-label="Open farmer account menu">
            Hi, {localStorage.getItem('fname')} <FaAngleDown></FaAngleDown>
          </DropdownToggle>
          <DropdownMenu end className="member-user-dropdown">
            <Link to="/profile" className="member-user-dropdown__item" onClick={closeMenus}>Profile</Link>
            <Link to="/changepassword" className="member-user-dropdown__item" onClick={closeMenus}>Change password</Link>
            <button type="button" className="member-user-dropdown__item member-user-dropdown__item--danger" onClick={logout}>Logout</button>
          </DropdownMenu>
        </Dropdown>
      </Collapse>
    </Navbar>
  );
};

export default Header;
