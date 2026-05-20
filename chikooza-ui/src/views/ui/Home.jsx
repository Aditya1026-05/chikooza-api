import { Link } from "react-router-dom";
import "../../assets/css/marketing.css";
import HeroImage from "../../assets/images/frontimages/Chicken.jpeg";
import ChikoozaChatbot from "../../components/ChikoozaChatbot/ChikoozaChatbot";

const exploreTiles = [
  {
    label: "Farm setup",
    copy: "Create country, state, farm, and flock records before daily work starts.",
    path: "/register",
  },
  {
    label: "Daily records",
    copy: "Capture mortality, feed, weight, vaccination, and farm observations.",
    path: "/login",
  },
  {
    label: "Purchases",
    copy: "Track feed, medicine, equipment, and operating cost entries.",
    path: "/login",
  },
  {
    label: "Sales",
    copy: "Record bird sales and understand sale value at flock level.",
    path: "/login",
  },
  {
    label: "Reports",
    copy: "Export summaries and keep flock history ready for review.",
    path: "/login",
  },
  {
    label: "Farmer AI",
    copy: "Ask private questions from the logged-in farmer's own data.",
    path: "/login",
  },
];

const knowMoreCards = [
  {
    title: "For farmers",
    copy: "Simple data entry for farms, flocks, daily operations, purchases, and sales.",
  },
  {
    title: "For supervisors",
    copy: "Cleaner records and repeatable reports for reviewing flock performance.",
  },
  {
    title: "For AI answers",
    copy: "A safer base for RAG and Text-to-SQL because the source records stay structured.",
  },
];

const Home = () => {
  return (
    <main className="marketing-page home-page">
      {/* U: OLD: home followed a generic SaaS landing page pattern.
          U: NEW: Amul-inspired brand/product structure: strong hero, product tiles, and know-more cards. */}
      <section className="home-hero">
        <div className="home-hero-copy">
          <span className="home-eyebrow">Poultry farm operations</span>
          <h1>One reliable place for every broiler flock record.</h1>
          <p>
            Chikooza helps farmers manage farm setup, flock lifecycle, daily
            work, purchases, sales, reports, and private AI questions from one
            focused account.
          </p>
          <div className="home-actions">
            <Link className="home-primary-action" to="/register">
              Create farmer account
            </Link>
            <Link className="home-secondary-action" to="/login">
              Farmer login
            </Link>
          </div>
        </div>

        <div className="home-hero-media" aria-label="Chikooza poultry farm operations">
          <div className="home-image-card">
            <img src={HeroImage} alt="Chicken and poultry performance graph" />
          </div>
          <div className="home-badge-card">
            <span>Current flock view</span>
            <strong>Mortality, feed, weight and sale data together.</strong>
          </div>
        </div>
      </section>

      <section className="home-section home-directory">
        <div className="home-section-heading">
          <span>Explore Chikooza</span>
          <h2>Farm tools grouped around real daily work.</h2>
          <p>
            Like a product directory, each area is easy to understand before the
            farmer enters the dashboard.
          </p>
        </div>
        <div className="home-tile-grid">
          {exploreTiles.map((tile) => (
            <Link className="home-tile" key={tile.label} to={tile.path}>
              <strong>{tile.label}</strong>
              <span>{tile.copy}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="home-red-band">
        <div>
          <span>From placement to sale</span>
          <h2>Structured records first. Better dashboard and AI answers after that.</h2>
        </div>
        <div className="home-band-list" aria-label="Chikooza operating flow">
          <div>
            <strong>01</strong>
            <p>Register farmer and verify OTP.</p>
          </div>
          <div>
            <strong>02</strong>
            <p>Add farm, flock, daily data, purchases, and sales.</p>
          </div>
          <div>
            <strong>03</strong>
            <p>Review reports and ask Farmer AI scoped to that account.</p>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="home-section-heading">
          <span>Know More</span>
          <h2>Built for practical farm management, not decorative dashboards.</h2>
        </div>
        <div className="home-know-grid">
          {knowMoreCards.map((card) => (
            <article className="home-know-card" key={card.title}>
              <h3>{card.title}</h3>
              <p>{card.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <ChikoozaChatbot alwaysVisible={true} defaultOpen={false} />
    </main>
  );
};

export default Home;
