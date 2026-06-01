import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Alert, Button } from "reactstrap";
import axios from "axios";
import "../../assets/css/marketing.css";
import { apiPath, config } from "../../Constants";

const apiUrl = (path) => `${apiPath.replace(/\/?$/, "/")}users/${path}/`;

const initialForm = {
  username: "",
  mobile: "",
  password: "",
  cpassword: "",
  otp: "",
};

const ForgetPassword = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState(initialForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [otpSent, setOtpSent] = useState(false);

  const cleanMobile = formData.mobile.replace(/\D/g, "");
  const cleanOtp = formData.otp.replace(/\D/g, "");

  const updateField = (event) => {
    const { name, value } = event.target;
    setError("");
    setMessage("");
    setFieldErrors((current) => ({ ...current, [name]: "" }));
    setFormData((current) => ({
      ...current,
      [name]: name === "mobile" || name === "otp" ? value.replace(/\D/g, "") : value,
    }));
  };

  const validateIdentity = () => {
    const errors = {};
    if (formData.username.trim().length < 3) {
      errors.username = "Enter the username used for this account.";
    }
    if (cleanMobile.length !== 10) {
      errors.mobile = "Enter the registered 10 digit mobile number.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const validateReset = () => {
    const errors = {};
    if (cleanOtp.length !== 6) {
      errors.otp = "Enter the 6 digit OTP.";
    }
    if (formData.password.length < 5) {
      errors.password = "Password must be at least 5 characters.";
    }
    if (formData.password.length > 30) {
      errors.password = "Password must be 30 characters or less.";
    }
    if (formData.password !== formData.cpassword) {
      errors.cpassword = "Passwords do not match.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const sendResetOtp = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!apiPath) {
      setError("Frontend API base URL is missing. Check chikooza-ui/.env.");
      return;
    }

    if (!validateIdentity()) {
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        apiUrl("resetPassword"),
        {
          mobile_number: cleanMobile,
          username: formData.username.trim(),
        },
        config
      );
      const returnedOtp = response.data?.results?.otp;
      setMessage(
        returnedOtp
          ? `OTP sent. Local MVP OTP is ${returnedOtp}.`
          : "OTP sent. Check the delivery channel configured on the backend."
      );
      setOtpSent(true);
    } catch (error) {
      setError(
        error?.response?.data?.error ||
          error?.response?.data?.message ||
          "No matching account found for this username and mobile number."
      );
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!validateReset()) {
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        apiUrl("forgetPassword"),
        {
          mobile_number: cleanMobile,
          username: formData.username.trim(),
          new_password: formData.password,
          confirm_new_password: formData.cpassword,
          otp: cleanOtp,
        },
        config
      );
      setMessage("Password updated. Redirecting to login...");
      window.setTimeout(() => navigate("/login"), 1200);
    } catch (error) {
      setError(
        error?.response?.data?.error ||
          error?.response?.data?.message ||
          "Unable to reset password. Check the OTP and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const editIdentity = () => {
    setOtpSent(false);
    setMessage("");
    setError("");
    setFieldErrors({});
    setFormData((current) => ({
      ...current,
      otp: "",
      password: "",
      cpassword: "",
    }));
  };

  return (
    <main className="marketing-page brand-page">
      {/* U: OLD: forgot-password used a public-layout two-column card.
          U: NEW: match login/register as a focused standalone auth flow. */}
      <section className="auth-shell auth-shell-centered">
        <div className="auth-card brand-auth-card auth-form-card">
          <Link className="auth-back-link" to="/">
            Back to Chikooza home
          </Link>
          <span className="auth-kicker">Password recovery</span>
          <h1>{otpSent ? "Set new password." : "Reset password."}</h1>
          <p>
            {otpSent
              ? `Enter the OTP sent for ${cleanMobile} and choose a new password.`
              : "Enter your username and registered mobile number. We will send an OTP before changing the password."}
          </p>
          {error && <Alert color="danger">{error}</Alert>}
          {message && <Alert color="success">{message}</Alert>}
          {!otpSent ? (
            <form className="auth-form" onSubmit={sendResetOtp}>
              <div className="form-field">
                <label htmlFor="forgot-username">Username</label>
                <input
                  autoComplete="username"
                  id="forgot-username"
                  name="username"
                  onChange={updateField}
                  placeholder="Enter username"
                  type="text"
                  value={formData.username}
                />
                <small className="form-error">{fieldErrors.username}</small>
              </div>
              <div className="form-field">
                <label htmlFor="forgot-mobile">Mobile number</label>
                <input
                  id="forgot-mobile"
                  inputMode="numeric"
                  maxLength={10}
                  name="mobile"
                  onChange={updateField}
                  placeholder="10 digit mobile number"
                  type="tel"
                  value={formData.mobile}
                />
                <small className="form-error">{fieldErrors.mobile}</small>
              </div>
              <Button className="ck-button" disabled={loading} type="submit">
                {loading ? "Sending OTP..." : "Send OTP"}
              </Button>
            </form>
          ) : (
            <form className="auth-form" onSubmit={resetPassword}>
              <div className="form-field">
                <label htmlFor="forgot-otp">OTP</label>
                <input
                  id="forgot-otp"
                  inputMode="numeric"
                  maxLength={6}
                  name="otp"
                  onChange={updateField}
                  placeholder="6 digit OTP"
                  type="text"
                  value={formData.otp}
                />
                <small className="form-error">{fieldErrors.otp}</small>
              </div>
              <div className="form-field">
                <label htmlFor="forgot-password">New password</label>
                <input
                  autoComplete="new-password"
                  id="forgot-password"
                  name="password"
                  onChange={updateField}
                  placeholder="Minimum 5 characters"
                  type="password"
                  value={formData.password}
                />
                <small className="form-error">{fieldErrors.password}</small>
              </div>
              <div className="form-field">
                <label htmlFor="forgot-confirm-password">Confirm password</label>
                <input
                  autoComplete="new-password"
                  id="forgot-confirm-password"
                  name="cpassword"
                  onChange={updateField}
                  placeholder="Confirm password"
                  type="password"
                  value={formData.cpassword}
                />
                <small className="form-error">{fieldErrors.cpassword}</small>
              </div>
              <Button className="ck-button" disabled={loading} type="submit">
                {loading ? "Updating password..." : "Update password"}
              </Button>
              <Button className="ck-button-secondary" disabled={loading} onClick={editIdentity} type="button">
                Change username/mobile
              </Button>
            </form>
          )}
          <div className="auth-switch">
            <Link to="/login">Back to login</Link>
            <span>New farmer? </span>
            <Link to="/register">Create account</Link>
          </div>
        </div>
      </section>
    </main>
  );
};

export default ForgetPassword;
