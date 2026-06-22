import { Link, NavLink, Outlet } from "react-router-dom";
import Logo from "../assets/images/logos/chikooza_logo.png";

const AuthLayout = () => {
  return (
    <div className="auth-route-layout" id="main-content" tabIndex="-1">
      <header className="mobile-auth-header">
        <Link to="/" aria-label="Chikooza home"><img src={Logo} alt="Chikooza" /></Link>
        <nav aria-label="Account navigation">
          <NavLink to="/login">Login</NavLink>
          <NavLink to="/register">Sign up</NavLink>
        </nav>
      </header>
      {/* U: NEW: Login/Register are standalone auth screens, so they do not use
          U: the public marketing header/footer layout. */}
      <Outlet />
    </div>
  );
};

export default AuthLayout;
