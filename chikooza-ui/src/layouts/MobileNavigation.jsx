import { useEffect } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

const publicItems = [
  { to: "/", label: "Home", icon: "house-door" },
  { to: "/about", label: "About", icon: "info-circle" },
  { to: "/contact", label: "Contact", icon: "chat-dots" },
  { to: "/login", label: "Login", icon: "person" },
];

const recordRoutes = [
  "/flocksale",
  "/viewsale",
  "/editsale",
  "/addpurchase",
  "/listpurchase",
  "/viewpurchase",
  "/dailydatasheet",
  "/flocksummary",
];

const moreRoutes = [
  "/addflock",
  "/manageflock",
  "/chatbot",
  "/profile",
  "/changepassword",
  "/updatemobile",
  "/member/about",
  "/member/contact",
];

const routeMatches = (pathname, routes) => routes.some((route) => pathname.startsWith(route));

export const PublicMobileNavigation = () => (
  <nav className="mobile-tab-bar public-mobile-tab-bar" aria-label="Public mobile navigation">
    {publicItems.map((item) => (
      <NavLink
        className={({ isActive }) => `mobile-tab ${isActive ? "is-active" : ""}`}
        end={item.to === "/"}
        key={item.to}
        to={item.to}
      >
        <i className={`bi bi-${item.icon}`} aria-hidden="true" />
        <span>{item.label}</span>
      </NavLink>
    ))}
  </nav>
);

export const PublicMobileMenu = ({ close }) => (
  <div className="mobile-sheet-layer public-mobile-menu-layer">
    <button className="mobile-sheet-backdrop" aria-label="Close navigation" onClick={close} type="button" />
    <section className="mobile-full-menu" role="dialog" aria-modal="true" aria-labelledby="public-mobile-menu-title">
      <div className="mobile-full-menu-header">
        <div>
          <span>Explore Chikooza</span>
          <h2 id="public-mobile-menu-title">Menu</h2>
        </div>
        <button className="mobile-sheet-close" aria-label="Close navigation" onClick={close} type="button">
          <i className="bi bi-x-lg" aria-hidden="true" />
        </button>
      </div>
      <div className="mobile-full-menu-links">
        <SheetLink close={close} icon="house-door" label="Home" supportingText="Product overview" to="/" />
        <SheetLink close={close} icon="info-circle" label="About Chikooza" supportingText="Why the product exists" to="/about" />
        <SheetLink close={close} icon="chat-dots" label="Contact" supportingText="Get product help" to="/contact" />
        <SheetLink close={close} icon="person" label="Farmer login" supportingText="Open your workspace" to="/login" />
      </div>
      <Link className="mobile-full-menu-cta" onClick={close} to="/register">Create free account</Link>
    </section>
  </div>
);

const SheetLink = ({ close, icon, label, supportingText, to }) => (
  <Link className="mobile-sheet-link" onClick={close} to={to}>
    <span className="mobile-sheet-icon"><i className={`bi bi-${icon}`} aria-hidden="true" /></span>
    <span>
      <strong>{label}</strong>
      {supportingText && <small>{supportingText}</small>}
    </span>
    <i className="bi bi-chevron-right mobile-sheet-chevron" aria-hidden="true" />
  </Link>
);

export const MemberMobileNavigation = ({ activeSheet, closeSheet, logout, openSheet }) => {
  const location = useLocation();
  const pathname = location.pathname;
  const recordsActive = routeMatches(pathname, recordRoutes);
  const moreActive = routeMatches(pathname, moreRoutes);

  useEffect(() => {
    if (!activeSheet) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event) => {
      if (event.key === "Escape") closeSheet();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [activeSheet, closeSheet]);

  return (
    <>
      {activeSheet && (
        <div className="mobile-sheet-layer" role="presentation">
          <button className="mobile-sheet-backdrop" aria-label="Close menu" onClick={closeSheet} type="button" />
          <section className={`mobile-bottom-sheet ${activeSheet === "all" ? "mobile-bottom-sheet--all" : ""}`} role="dialog" aria-modal="true" aria-labelledby="mobile-sheet-title">
            <div className="mobile-sheet-handle" aria-hidden="true" />
            <div className="mobile-sheet-header">
              <div>
                <span>Chikooza workspace</span>
                <h2 id="mobile-sheet-title">{activeSheet === "records" ? "Records and reports" : activeSheet === "all" ? "All tools" : "More tools"}</h2>
              </div>
              <button className="mobile-sheet-close" aria-label="Close menu" onClick={closeSheet} type="button">
                <i className="bi bi-x-lg" aria-hidden="true" />
              </button>
            </div>

            <div className="mobile-sheet-list">
              {activeSheet === "records" ? (
                <>
                  <SheetLink close={closeSheet} icon="cash-coin" label="Add sale" supportingText="Record a flock lifting" to="/flocksale" />
                  <SheetLink close={closeSheet} icon="receipt" label="Sales" supportingText="Review and edit sales" to="/viewsale" />
                  <SheetLink close={closeSheet} icon="cart-plus" label="Add purchase" supportingText="Save feed and other costs" to="/addpurchase" />
                  <SheetLink close={closeSheet} icon="bag-check" label="Purchases" supportingText="Review and edit purchases" to="/listpurchase" />
                  <SheetLink close={closeSheet} icon="table" label="Daily data sheet" supportingText="Filter and export daily records" to="/dailydatasheet" />
                  <SheetLink close={closeSheet} icon="graph-up-arrow" label="Flock summary" supportingText="Performance, costs, and sales" to="/flocksummary" />
                </>
              ) : activeSheet === "all" ? (
                <>
                  <p className="mobile-sheet-section-label">Daily work</p>
                  <SheetLink close={closeSheet} icon="house-door" label="Dashboard" supportingText="Farm overview and next action" to="/member" />
                  <SheetLink close={closeSheet} icon="calendar2-check" label="Daily data" supportingText="Record today’s flock activity" to="/flockdailydata" />
                  <SheetLink close={closeSheet} icon="stars" label="Farmer AI" supportingText="Ask about your records" to="/chatbot" />
                  <p className="mobile-sheet-section-label">Farm setup</p>
                  <SheetLink close={closeSheet} icon="buildings" label="Farms" supportingText="Add, view, and update farms" to="/managefarm" />
                  <SheetLink close={closeSheet} icon="collection" label="Flocks" supportingText="Add, view, and update flocks" to="/manageflock" />
                  <p className="mobile-sheet-section-label">Business records</p>
                  <SheetLink close={closeSheet} icon="receipt" label="Sales" supportingText="Add and review sales" to="/viewsale" />
                  <SheetLink close={closeSheet} icon="bag-check" label="Purchases" supportingText="Add and review costs" to="/listpurchase" />
                  <SheetLink close={closeSheet} icon="graph-up-arrow" label="Reports" supportingText="Daily sheet and flock summary" to="/flocksummary" />
                  <p className="mobile-sheet-section-label">Account</p>
                  <SheetLink close={closeSheet} icon="person-circle" label="Profile" supportingText="Farmer account information" to="/profile" />
                  <SheetLink close={closeSheet} icon="shield-lock" label="Security" supportingText="Change your password" to="/changepassword" />
                  <button className="mobile-sheet-link mobile-sheet-logout" onClick={logout} type="button">
                    <span className="mobile-sheet-icon"><i className="bi bi-box-arrow-right" aria-hidden="true" /></span>
                    <span><strong>Logout</strong><small>Sign out of this device</small></span>
                  </button>
                </>
              ) : (
                <>
                  <SheetLink close={closeSheet} icon="plus-circle" label="Add flock" supportingText="Start a new flock cycle" to="/addflock" />
                  <SheetLink close={closeSheet} icon="collection" label="Manage flocks" supportingText="View and update flock details" to="/manageflock" />
                  <SheetLink close={closeSheet} icon="stars" label="AI assistant" supportingText="Ask questions about farm records" to="/chatbot" />
                  <SheetLink close={closeSheet} icon="person-circle" label="Profile" supportingText="Farmer and contact details" to="/profile" />
                  <SheetLink close={closeSheet} icon="shield-lock" label="Change password" supportingText="Update account security" to="/changepassword" />
                  <SheetLink close={closeSheet} icon="info-circle" label="About Chikooza" to="/member/about" />
                  <SheetLink close={closeSheet} icon="headset" label="Contact support" to="/member/contact" />
                  <button className="mobile-sheet-link mobile-sheet-logout" onClick={logout} type="button">
                    <span className="mobile-sheet-icon"><i className="bi bi-box-arrow-right" aria-hidden="true" /></span>
                    <span><strong>Logout</strong><small>Sign out of this device</small></span>
                  </button>
                </>
              )}
            </div>
          </section>
        </div>
      )}

      <nav className="mobile-tab-bar member-mobile-tab-bar" aria-label="Farmer workspace mobile navigation">
        <NavLink className={({ isActive }) => `mobile-tab ${isActive ? "is-active" : ""}`} end to="/member">
          <i className="bi bi-house-door" aria-hidden="true" /><span>Home</span>
        </NavLink>
        <NavLink className={({ isActive }) => `mobile-tab ${isActive || pathname === "/addfarm" ? "is-active" : ""}`} to="/managefarm">
          <i className="bi bi-buildings" aria-hidden="true" /><span>Farms</span>
        </NavLink>
        <NavLink className={() => `mobile-tab ${pathname.startsWith("/flockdailydata") || pathname.startsWith("/daydata") ? "is-active" : ""}`} to="/flockdailydata">
          <i className="bi bi-calendar2-check" aria-hidden="true" /><span>Daily</span>
        </NavLink>
        <button className={`mobile-tab ${recordsActive || activeSheet === "records" ? "is-active" : ""}`} onClick={() => openSheet("records")} type="button">
          <i className="bi bi-journal-text" aria-hidden="true" /><span>Records</span>
        </button>
        <button className={`mobile-tab ${moreActive || activeSheet === "more" ? "is-active" : ""}`} onClick={() => openSheet("more")} type="button">
          <i className="bi bi-grid" aria-hidden="true" /><span>More</span>
        </button>
      </nav>
    </>
  );
};
