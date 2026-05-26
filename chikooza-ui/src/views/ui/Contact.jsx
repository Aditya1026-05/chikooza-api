import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Button } from "reactstrap";
import "../../assets/css/marketing.css";

const contactMethods = [
  {
    label: "Email",
    value: "bhucho@yahoo.com",
    href: "mailto:bhucho@yahoo.com",
  },
  {
    label: "Phone",
    value: "+91 56894 25798",
    href: "tel:+915689425798",
  },
  {
    label: "Product help",
    value: "Setup, records, reports, AI",
    href: null,
  },
];

const Contact = () => {
  const isLoggedIn = localStorage.getItem("token") !== null;
  const [formData, setFormData] = useState({
    name: "",
    mobile: "",
    message: "",
  });
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  const updateField = (event) => {
    setSent(false);
    setError("");
    setFormData((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  };

  const submitContact = (event) => {
    event.preventDefault();
    const cleanMobile = formData.mobile.replace(/\D/g, "");

    if (!formData.name.trim() || cleanMobile.length < 10 || !formData.message.trim()) {
      setError("Please enter your name, a valid mobile number, and your message.");
      return;
    }

    // U: OLD: contact form submitted nowhere and caused a browser refresh.
    // U: NEW: keep the form usable locally until a real contact API/email service is added.
    setSent(true);
    setFormData({ name: "", mobile: "", message: "" });
  };

  return (
    <main className="marketing-page brand-page">
      {isLoggedIn && (
        <Link className="public-back-to-app" to="/member" aria-label="Back to logged-in app">
          <span aria-hidden="true">←</span>
          Back to app
        </Link>
      )}
      <section className="brand-hero contact-brand-hero">
        <div className="brand-hero-copy">
          <span className="home-eyebrow">Contact Chikooza</span>
          <h1>Need help setting up farm records?</h1>
          <p>
            Share what you are trying to do: setup, registration, reports,
            private AI, farm data, or deployment. We will help route the next
            step clearly.
          </p>
        </div>

        <aside className="brand-side-panel contact-methods">
          {contactMethods.map((method) => (
            <div key={method.label}>
              <span>{method.label}</span>
              {method.href ? (
                <a href={method.href}>{method.value}</a>
              ) : (
                <strong>{method.value}</strong>
              )}
            </div>
          ))}
        </aside>
      </section>

      <section className="home-section contact-form-section">
        <div className="home-section-heading">
          <span>Send a message</span>
          <h2>Tell us what you need.</h2>
          <p>
            The form is local for now. For real delivery, wire this page to an
            email/contact API before production.
          </p>
        </div>

        <div className="brand-form-card">
          {error && <Alert color="danger">{error}</Alert>}
          {sent && <Alert color="success">Message captured locally. Add a backend contact API before production email delivery.</Alert>}
          <form className="contact-form" onSubmit={submitContact}>
            <div className="form-field">
              <label htmlFor="contact-name">Full name</label>
              <input
                id="contact-name"
                name="name"
                onChange={updateField}
                placeholder="Your name"
                type="text"
                value={formData.name}
              />
            </div>
            <div className="form-field">
              <label htmlFor="contact-mobile">Mobile number</label>
              <input
                id="contact-mobile"
                inputMode="numeric"
                name="mobile"
                onChange={updateField}
                placeholder="10 digit mobile number"
                type="tel"
                value={formData.mobile}
              />
            </div>
            <div className="form-field">
              <label htmlFor="contact-message">What can we help you with?</label>
              <textarea
                id="contact-message"
                name="message"
                onChange={updateField}
                placeholder="Example: I need help adding my first farm and flock."
                rows={5}
                value={formData.message}
              />
            </div>
            <Button className="ck-button" type="submit">
              Submit message
            </Button>
          </form>
        </div>
      </section>
    </main>
  );
};

export default Contact;
