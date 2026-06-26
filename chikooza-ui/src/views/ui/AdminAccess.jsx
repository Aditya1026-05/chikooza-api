import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Alert } from "reactstrap";
import "../../assets/css/marketing.css";

const readParams = () => {
  const rawHash = window.location.hash ? window.location.hash.slice(1) : "";
  const rawSearch = window.location.search ? window.location.search.slice(1) : "";
  return new URLSearchParams(rawHash || rawSearch);
};

const AdminAccess = () => {
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    const params = readParams();
    const token = params.get("token");
    const publicId = params.get("publicid");
    const name = params.get("name");

    if (!token || !publicId) {
      setError("Admin access link is missing a farmer token.");
      return;
    }

    localStorage.setItem("fname", name || "Farmer");
    localStorage.setItem("token", token);
    localStorage.setItem("publicid", publicId);
    localStorage.setItem("adminInspect", params.get("adminInspect") || "1");
    window.history.replaceState({}, document.title, "/admin-access");
    navigate("/member", { replace: true });
  }, [navigate]);

  return (
    <main className="marketing-page brand-page">
      <section className="auth-shell auth-shell-centered">
        <div className="auth-card brand-auth-card auth-form-card">
          <span className="auth-kicker">Admin access</span>
          <h1>Opening dashboard.</h1>
          {error ? (
            <>
              <Alert color="danger">{error}</Alert>
              <Link to="/login">Back to login</Link>
            </>
          ) : (
            <p>Loading the farmer workspace...</p>
          )}
        </div>
      </section>
    </main>
  );
};

export default AdminAccess;
