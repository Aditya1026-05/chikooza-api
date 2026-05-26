import { Link } from "react-router-dom";
import "../../assets/css/marketing.css";

const principles = [
  {
    label: "Records",
    title: "Operational clarity",
    copy: "Farm teams should quickly see flock health, feed, mortality, purchases, sales, and reports without hunting across spreadsheets.",
  },
  {
    label: "Privacy",
    title: "Data ownership",
    copy: "Each farmer's records stay scoped to their account. Private AI answers are generated only from the logged-in farmer's data.",
  },
  {
    label: "Decisions",
    title: "Practical decisions",
    copy: "The product focuses on useful farm questions: FCR, current birds, mortality, sale amount, profit/loss, and purchase trends.",
  },
];

const About = () => {
  const isLoggedIn = localStorage.getItem("token") !== null;

  return (
    <main className="marketing-page brand-page">
      {isLoggedIn && (
        <Link className="public-back-to-app" to="/member" aria-label="Back to logged-in app">
          <span aria-hidden="true">←</span>
          Back to app
        </Link>
      )}
      {/* U: OLD: About page used legacy cards, typo-heavy copy, and fake social blocks.
          U: NEW: match the Home page's brand/product story structure. */}
      <section className="brand-hero">
        <div className="brand-hero-copy">
          <span className="home-eyebrow">About Chikooza</span>
          <h1>The operating layer for broiler farm records.</h1>
          <p>
            Chikooza is built for farmers and farm operators who need a cleaner
            way to capture daily work, understand flock performance, and keep
            every farm record connected to the right account.
          </p>
          <div className="home-actions">
            <Link className="home-primary-action" to="/register">
              Create account
            </Link>
            <Link className="home-secondary-action" to="/contact">
              Contact team
            </Link>
          </div>
        </div>

        <div className="brand-side-panel" aria-label="Chikooza farm operations coverage">
          {/* U: OLD: this page displayed a generic stock image that did not match poultry farming.
              U: NEW: use a product-relevant operations summary instead of misleading imagery. */}
          <div>
            <span>Farm records</span>
            <strong>Country, state, farm, and flock setup</strong>
          </div>
          <div>
            <span>Daily work</span>
            <strong>Mortality, feed, weight and vaccination entries</strong>
          </div>
          <div>
            <span>Business result</span>
            <strong>Purchases, sales, PDF reports and Farmer AI</strong>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="home-section-heading">
          <span>Why it exists</span>
          <h2>Less guessing, better farm records.</h2>
          <p>
            The product combines farm setup, flock records, daily data,
            purchase logs, sales tracking, dashboard charts, PDF reports, and AI
            query support. The goal is to turn scattered farm activity into
            usable performance information.
          </p>
        </div>
        <div className="home-know-grid">
          {principles.map((item) => (
            <article className="home-know-card" key={item.title}>
              <small>{item.label}</small>
              <h3>{item.title}</h3>
              <p>{item.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="home-red-band">
        <div>
          <span>What farmers can do</span>
          <h2>Manage the whole flock cycle from one account.</h2>
        </div>
        <div className="home-band-list">
          <div>
            <strong>01</strong>
            <p>Register, verify OTP, and create the farmer workspace.</p>
          </div>
          <div>
            <strong>02</strong>
            <p>Add farms, create flocks, enter daily data, purchases, and sales.</p>
          </div>
          <div>
            <strong>03</strong>
            <p>Export reports and ask Farmer AI questions from scoped records.</p>
          </div>
        </div>
      </section>
    </main>
  );
};

export default About;
