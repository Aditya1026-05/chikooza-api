import React from "react";
import { Link } from "react-router-dom";
import {
  Navbar,
  Collapse,
  Nav,
  NavItem,
  NavbarBrand,
  Button,
} from "reactstrap";
import { useEffect, useState } from "react";
import logo from "../assets/images/logos/chikooza_logo.svg";
import logoMobile from "../assets/images/logos/chikooza_logo_mobile.png";
import '../assets/css/header.css';

const Header = () => {
  // const navigate = useNavigate();
  const [isOpen, setIsOpen] = React.useState(false);
  const [user, SetUser] = useState(localStorage.getItem('token') !== null ? false : true)
  // const [dropdownOpen, setDropdownOpen] = React.useState(false);

  // const toggle = () => setDropdownOpen((prevState) => !prevState);
  const Handletoggle = () => {
    setIsOpen(!isOpen);
  };
  // const showMobilemenu = () => {
  //   document.getElementById("sidebarArea").classList.toggle("showSidebar");
  // };
  useEffect(() => {
    // if(localStorage.getItem('token')!==null){
    //   navigate("/member")
    // }
  }, [])
  return (
    <Navbar color="white" light expand="md" className="fix-header">
      <div className="d-flex align-items-center">
        <div className="d-lg-block d-none me-5 pe-3">
          <img src={logo} width='156' height='35' alt="user" />
        </div>
        <NavbarBrand href="/">
          <img src={logoMobile} width='35' height='35' alt="user" className="d-lg-none" />
        </NavbarBrand>
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
          color="danger"
          size="sm"
          className="d-sm-block d-md-none"
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
            <Link to="/" className="linkheader">
              Home
            </Link>
          </NavItem>
          <NavItem>
            <Link to="/about" className="linkheader">
              About Us
            </Link>
          </NavItem>
          {user === true ?
            <>
              <NavItem>
                <Link to="/login" className="linkheader">
                  Farmer Login
                </Link>
              </NavItem>
              <NavItem>
                <Link to="/register" className="linkheader">
                  Register
                </Link>
              </NavItem>
            </>
            : <NavItem>
              <Link to="/member" className="linkheader">
                Member
              </Link>
            </NavItem>
          }
          <NavItem>
            <Link to="/contact" className="linkheader">
              Contact Us
            </Link>
          </NavItem>
        </Nav>
      </Collapse>
    </Navbar>
  );
};

export default Header;
