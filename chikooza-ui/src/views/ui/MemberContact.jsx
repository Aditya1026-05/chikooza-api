import { Link } from "react-router-dom";
import "../../assets/css/header.css";

const MemberContact = () => {
  return (
    <section className="member-info-page">
      <Link className="member-info-back" to="/member" aria-label="Back to dashboard">
        <span aria-hidden="true">←</span>
        Back to home
      </Link>

      <div className="member-info-hero">
        <span className="member-info-kicker">Contact Chikooza</span>
        <h1>Need help with your farmer workspace?</h1>
        <p>
          Use this member-side contact page for setup, farm records, flock
          entries, reports, or Farmer AI questions.
        </p>
      </div>

      <div className="member-contact-panel">
        <div>
          <span>Email</span>
          <a href="mailto:bhucho@yahoo.com">bhucho@yahoo.com</a>
        </div>
        <div>
          <span>Phone</span>
          <a href="tel:+915689425798">+91 56894 25798</a>
        </div>
        <div>
          <span>Best context to share</span>
          <strong>Farm name, flock name, date, and the screen where you are stuck.</strong>
        </div>
      </div>
    </section>
  );
};

export default MemberContact;
