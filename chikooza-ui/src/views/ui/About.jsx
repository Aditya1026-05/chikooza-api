import { Link } from "react-router-dom";
import "../../assets/css/marketing.css";
import BroilerHouseImage from "../../assets/images/poultry/broiler-house.png";
import FarmerBirdImage from "../../assets/images/poultry/farmer-holding-bird.png";
import FeedingImage from "../../assets/images/poultry/broiler-feeding.png";
import TeamAvatarImage from "../../assets/images/poultry/team-avatar.png";

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

const teamMembers = [
  {
    name: "Manish Goyal",
    role: "Founder",
  },
  {
    name: "Utkarsh Goel",
    role: "Developer",
  },
  {
    name: "Aditya Tayal",
    role: "Team Member",
  },
];

const About = () => {
  return (
    <main className="marketing-page brand-page">
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

        <div className="brand-photo-panel" aria-label="Broiler farm record workflow">
          {/* U: NEW: real poultry images make the About page feel tied to this product domain. */}
          <img src={BroilerHouseImage} alt="Broiler farm house with flock" />
          <div>
            <img src={FarmerBirdImage} alt="Farmer checking a broiler bird" />
            <img src={FeedingImage} alt="Broiler feeding line" />
          </div>
          <aside>
            <span>Product focus</span>
            <strong>Farm setup, flock records, daily entries, purchases, sales, reports, and Farmer AI.</strong>
          </aside>
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

      <section className="home-section team-section">
        <div className="home-section-heading">
          <span>Project team</span>
        </div>

        <div className="team-grid">
          {teamMembers.map((member) => (
            <article className="team-card" key={member.name}>
              <div className="team-avatar-frame">
                {/* U: NEW: reuse the supplied team avatar while tinting it through CSS to match the Chikooza palette. */}
                <img src={TeamAvatarImage} alt="" aria-hidden="true" />
              </div>
              <div>
                <h3>{member.name}</h3>
                <strong>{member.role}</strong>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
};

export default About;
