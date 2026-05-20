import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Alert, Button } from "reactstrap";
import axios from "axios";
import "../../assets/css/marketing.css";
import { apiPath, config } from "../../Constants";

const loginUrl = () => `${apiPath.replace(/\/?$/, "/")}users/login/`;

const Login = () => {
  const navigate = useNavigate();
  const [loginData, setLoginData] = useState({ username: "", password: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const updateField = (event) => {
    setError("");
    setFieldErrors((current) => ({ ...current, [event.target.name]: "" }));
    setLoginData((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  };

  const validate = () => {
    const errors = {};
    if (!loginData.username.trim()) {
      errors.username = "Username is required.";
    }
    if (!loginData.password) {
      errors.password = "Password is required.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const submitLogin = async (event) => {
    event.preventDefault();
    setError("");

    if (!apiPath) {
      setError("Frontend API base URL is missing. Check chikooza-ui/.env.");
      return;
    }

    if (!validate()) {
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        loginUrl(),
        {
          username: loginData.username.trim(),
          password: loginData.password,
        },
        config
      );
      const results = response.data?.results || {};
      if (!results.access_token) {
        throw new Error("Login response did not include an access token.");
      }
      localStorage.setItem("fname", results.name || loginData.username.trim());
      localStorage.setItem("token", results.access_token);
      localStorage.setItem("publicid", results.public_id);
      navigate("/member");
    } catch (err) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.message ||
          err.message ||
          "Login failed. Please check your username and password."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="marketing-page brand-page">
      {/* U: OLD: login used a nested dashboard card and inline red icons.
          U: NEW: brand-consistent auth page connected to the verified /users/login/ API. */}
      <section className="auth-shell">
        <div className="auth-story-panel">
          <span className="home-eyebrow">Farmer login</span>
          <h1>Continue your flock records.</h1>
          <p>
            Login to manage farms, flocks, daily records, purchases, sales,
            reports, and the private Farmer AI assistant.
          </p>
          <div className="brand-check-list">
            <div>OAuth token login is verified against the Django backend.</div>
            <div>Your dashboard and AI assistant use your authenticated account.</div>
            <div>New users can register with the local MVP OTP flow.</div>
          </div>
        </div>

        <div className="auth-card brand-auth-card">
          <h2>Login</h2>
          <p>Use the username and password created during registration.</p>
          {error && <Alert color="danger">{error}</Alert>}
          <form className="auth-form" onSubmit={submitLogin}>
            <div className="form-field">
              <label htmlFor="login-username">Username</label>
              <input
                autoComplete="username"
                id="login-username"
                name="username"
                onChange={updateField}
                placeholder="Enter username"
                type="text"
                value={loginData.username}
              />
              <small className="form-error">{fieldErrors.username}</small>
            </div>
            <div className="form-field">
              <label htmlFor="login-password">Password</label>
              <input
                autoComplete="current-password"
                id="login-password"
                name="password"
                onChange={updateField}
                placeholder="Enter password"
                type="password"
                value={loginData.password}
              />
              <small className="form-error">{fieldErrors.password}</small>
            </div>
            <Button className="ck-button" disabled={loading} type="submit">
              {loading ? "Logging in..." : "Login to dashboard"}
            </Button>
          </form>
          <div className="auth-switch">
            <Link to="/forgetpassword">Forgot password?</Link>
            <span> | </span>
            <span>New farmer? </span>
            <Link to="/register">Create account</Link>
          </div>
        </div>
      </section>
    </main>
  );
};

export default Login;
