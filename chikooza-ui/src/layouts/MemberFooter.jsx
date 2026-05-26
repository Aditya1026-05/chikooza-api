import React from "react";
import { Link } from "react-router-dom";
import '../assets/css/header.css';
import Logo from "../assets/images/logos/chikooza_logo.png";

const MemberFooter = () => {
  return (
    <footer className="chikooza-footer chikooza-member-footer">
      <div className="chikooza-footer-inner">
        <div className="chikooza-footer-brand">
          <Link to="/member" className="navbar-brand chikooza-brand chikooza-footer-logo">
            <img src={Logo} alt="Chikooza" className="chikooza-brand-logo" />
          </Link>
          <p>
            Logged-in farmer workspace for daily flock work, business records,
            reports, and private Farmer AI.
          </p>
        </div>

        <div className="chikooza-footer-links">
          <div>
            <strong>App</strong>
            <Link to="/member">Home</Link>
            <Link to="/managefarm">Farm</Link>
            <Link to="/manageflock">Flock</Link>
          </div>
          <div>
            <strong>Records</strong>
            <Link to="/viewsale">Sales</Link>
            <Link to="/listpurchase">Purchases</Link>
            <Link to="/dailydatasheet">Reports</Link>
          </div>
          <div>
            <strong>Account</strong>
            <Link to="/chatbot">Farmer AI</Link>
            <Link to="/profile">Profile</Link>
            <Link to="/member/about">About Chikooza</Link>
            <Link to="/member/contact">Contact</Link>
          </div>
        </div>
      </div>

      <div className="chikooza-footer-bottom">
        <p>Farmer workspace. Your records stay scoped to your account.</p>
        <span>About and Contact open member-side pages without adding them to the header.</span>
      </div>
    </footer>
  );
};

export default MemberFooter;
