import React from "react";
import { Link } from "react-router-dom";
import '../assets/css/header.css';
import Logo from "../assets/images/logos/chikooza_logo.png";
const Footer = () => {
  return (
    <>
      {/* U: OLD: footer used the legacy red brand block.
          U: NEW: this footer is public-only; logged-in app pages use MemberFooter. */}
      <footer className="chikooza-footer">
        <div className="chikooza-footer-inner">
          <div className="chikooza-footer-brand">
            <Link to="/" className="navbar-brand chikooza-brand chikooza-footer-logo">
              <img src={Logo} alt="Chikooza" className="chikooza-brand-logo" />
            </Link>
            <p>
              Poultry farm management for flocks, daily records, purchases,
              sales, reports, and private farmer AI.
            </p>
          </div>
          <div className="chikooza-footer-links">
            <div>
              <strong>Product</strong>
              <Link to="/">Home</Link>
              <Link to="/about">About</Link>
              <Link to="/register">Register</Link>
            </div>
            <div>
              <strong>Farm Tools</strong>
              <Link to="/login">Farmer login</Link>
              <Link to="/login">Farmer AI</Link>
              <Link to="/contact">Contact</Link>
            </div>
            <div>
              <strong>Contact</strong>
              <a href="mailto:bhucho@yahoo.com">bhucho@yahoo.com</a>
              <a href="tel:+915689425798">+91 56894 25798</a>
            </div>
          </div>
        </div>
        <div className="chikooza-footer-bottom">
          <p>Copyright © 2026 chikooza.com. All rights reserved.</p>
          <span>Built for broiler farm operations.</span>
        </div>
      </footer>
    </>
  );
};
export default Footer;
