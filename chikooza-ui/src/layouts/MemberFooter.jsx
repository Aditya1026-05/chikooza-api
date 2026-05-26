import React from "react";
import { Link } from "react-router-dom";
import '../assets/css/header.css';
import Logo from "../assets/images/logos/chikooza_logo.png";

const scrollToTop = () => {
  window.requestAnimationFrame(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  });
};

const MemberFooter = () => {
  return (
    <footer className="chikooza-footer chikooza-member-footer">
      <div className="chikooza-footer-inner">
        <div className="chikooza-footer-brand">
          <Link to="/member" className="navbar-brand chikooza-brand chikooza-footer-logo" onClick={scrollToTop}>
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
            <Link to="/member" onClick={scrollToTop}>Home</Link>
            <Link to="/managefarm" onClick={scrollToTop}>Farm</Link>
            <Link to="/manageflock" onClick={scrollToTop}>Flock</Link>
          </div>
          <div>
            <strong>Records</strong>
            <Link to="/viewsale" onClick={scrollToTop}>Sales</Link>
            <Link to="/listpurchase" onClick={scrollToTop}>Purchases</Link>
            <Link to="/dailydatasheet" onClick={scrollToTop}>Reports</Link>
          </div>
          <div>
            <strong>Account</strong>
            <Link to="/chatbot" onClick={scrollToTop}>Farmer AI</Link>
            <Link to="/profile" onClick={scrollToTop}>Profile</Link>
            <Link to="/member/about" onClick={scrollToTop}>About Chikooza</Link>
            <Link to="/member/contact" onClick={scrollToTop}>Contact</Link>
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
