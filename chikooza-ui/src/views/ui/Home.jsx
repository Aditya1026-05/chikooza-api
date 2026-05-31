import { Link } from "react-router-dom";
import "../../assets/css/marketing.css";
import HeroImage from "../../assets/images/poultry/broiler-house.png";
import BroilerFlockImage from "../../assets/images/poultry/broiler-flock.png";
import FeedingImage from "../../assets/images/poultry/broiler-feeding.png";
import ChicksImage from "../../assets/images/poultry/chicks-brooding.png";
import FarmerBirdImage from "../../assets/images/poultry/farmer-holding-bird.png";
import ChikoozaChatbot from "../../components/ChikoozaChatbot/ChikoozaChatbot";

const operationTiles = [
  {
    label: "Record daily work",
    eyebrow: "Operations",
    copy: "Mortality, feed intake, bird weight, vaccination, and flock status in one flow.",
    path: "/register",
  },
  {
    label: "Track cost and sales",
    eyebrow: "Business",
    copy: "Feed, medicine, equipment, lifting details, buyer information, and sale value.",
    path: "/login",
  },
  {
    label: "Review reports and AI",
    eyebrow: "Review",
    copy: "Dashboard charts, PDF reports, and Farmer AI answers from saved records.",
    path: "/login",
  },
];

const workflowSteps = [
  {
    step: "01",
    title: "Create the farm base",
    copy: "Register, verify OTP, add farm details, then add the active flock.",
  },
  {
    step: "02",
    title: "Keep daily work current",
    copy: "Enter feed, mortality, bird weight, vaccinations, purchases, and sales as work happens.",
  },
  {
    step: "03",
    title: "Review numbers clearly",
    copy: "Use dashboard charts, PDF reports, and Farmer AI to understand flock performance.",
  },
];

const proofCards = [
  {
    title: "Less guessing",
    copy: "The farmer can see what is recorded, what is missing, and what should be entered next.",
  },
  {
    title: "Cleaner handover",
    copy: "Farm, flock, purchase, sale, and daily records stay structured instead of scattered in notebooks.",
  },
  {
    title: "Better review",
    copy: "Reports and AI answers become more useful because they are based on saved operational records.",
  },
];

const imageRail = [
  {
    image: BroilerFlockImage,
    title: "Flock records",
  },
  {
    image: FeedingImage,
    title: "Feed tracking",
  },
  {
    image: ChicksImage,
    title: "Placement cycle",
  },
  {
    image: FarmerBirdImage,
    title: "Daily checks",
  },
];

const Home = () => {
  const railItems = [...imageRail, ...imageRail];

  return (
    <main className="marketing-page home-page">
      {/* U: OLD: home read like a generic SaaS landing page.
          U: NEW: product-first landing page focused on broiler farm operations. */}
      <section className="home-hero">
        <div className="home-hero-copy">
          <span className="home-eyebrow">Broiler farm operations platform</span>
          <h1>Poultry farm records without the notebook mess.</h1>
          <p>
            Track farms, flocks, daily data, purchases, sales, reports, and
            private Farmer AI in one clean workspace.
          </p>
          <div className="home-actions">
            <Link className="home-primary-action" to="/register">
              Register for free
            </Link>
            <Link className="home-secondary-action" to="/login">
              Farmer login
            </Link>
          </div>
        </div>

        <div className="home-hero-media" aria-label="Chikooza poultry farm operations">
          <div className="home-image-card">
            <img src={HeroImage} alt="Broiler poultry house with flock and feeding lines" />
            <div className="home-visual-note home-visual-note-bottom">
              <span>Current flock</span>
              <strong>Daily data, costs, sales, and reports stay connected.</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="home-photo-rail" aria-label="Chikooza poultry work areas">
        <div className="home-photo-track">
          {railItems.map((item, index) => (
            <figure key={`${item.title}-${index}`}>
              <img src={item.image} alt={item.title} />
              <figcaption>{item.title}</figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="home-section home-directory">
        <div className="home-section-heading">
          <span>What it manages</span>
          <h2>Three simple areas instead of scattered records.</h2>
          <p>
            The landing page stays simple. The dashboard gives farmers the full
            step-by-step workflow after login.
          </p>
        </div>
        <div className="home-tile-grid">
          {operationTiles.map((tile) => (
            <Link className="home-tile" key={tile.label} to={tile.path}>
              <small>{tile.eyebrow}</small>
              <strong>{tile.label}</strong>
              <span>{tile.copy}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="home-red-band">
        <div>
          <span>From placement to sale</span>
          <h2>A simple operating flow for every flock cycle.</h2>
        </div>
        <div className="home-band-list" aria-label="Chikooza operating flow">
          {workflowSteps.map((item) => (
            <div key={item.step}>
              <strong>{item.step}</strong>
              <p>
                <b>{item.title}</b>
                {item.copy}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="home-section-heading">
          <span>Why it helps</span>
          <h2>Less scattered data. More usable farm decisions.</h2>
        </div>
        <div className="home-know-grid">
          {proofCards.map((card) => (
            <article className="home-know-card" key={card.title}>
              <h3>{card.title}</h3>
              <p>{card.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="home-final-cta">
        <div>
          <span>Ready to test the MVP?</span>
          <h2>Create a farmer account and walk through one flock cycle.</h2>
          <p>
            Add a farm, add a flock, enter daily data, record purchases and
            sales, then check reports and Farmer AI from the logged-in dashboard.
          </p>
        </div>
        <div className="home-actions">
          <Link className="home-primary-action" to="/register">
            Register for free
          </Link>
          <Link className="home-secondary-action" to="/login">
            Login
          </Link>
        </div>
      </section>

      <ChikoozaChatbot alwaysVisible={true} defaultOpen={false} />
    </main>
  );
};

export default Home;
