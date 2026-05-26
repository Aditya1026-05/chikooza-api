import { Link } from "react-router-dom";
import "../../assets/css/header.css";

const MemberAbout = () => {
  return (
    <section className="member-info-page">
      <Link className="member-info-back" to="/member" aria-label="Back to dashboard">
        <span aria-hidden="true">←</span>
        Back to home
      </Link>

      <div className="member-info-hero">
        <span className="member-info-kicker">About Chikooza</span>
        <h1>Built around the daily work inside a broiler farm.</h1>
        <p>
          Chikooza keeps farm setup, flock lifecycle, daily entries, purchases,
          sales, reports, and Farmer AI in one logged-in workspace.
        </p>
      </div>

      <div className="member-info-grid">
        <article>
          <span>01</span>
          <h2>Structured records</h2>
          <p>Farms come first, flocks connect to farms, and daily records, purchases, and sales connect to flocks.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Private workspace</h2>
          <p>The authenticated app is designed so each farmer works with their own data and dashboard.</p>
        </article>
        <article>
          <span>03</span>
          <h2>AI-ready data</h2>
          <p>Clean SQL records make reports and Farmer AI answers more reliable than scattered spreadsheets.</p>
        </article>
      </div>
    </section>
  );
};

export default MemberAbout;
