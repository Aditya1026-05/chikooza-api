import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Alert, Button } from "reactstrap";
import Modal from "react-bootstrap/Modal";
import axios from "axios";
import "../../assets/css/marketing.css";
import { apiPath, config } from "../../Constants";

const apiUrl = (path) => `${apiPath.replace(/\/?$/, "/")}users/${path}/`;

const initialForm = {
  name: "",
  email: "",
  mobile: "",
  username: "",
  password: "",
  cpassword: "",
};

const Register = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState(initialForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [showOtp, setShowOtp] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");
  const [otpSuccess, setOtpSuccess] = useState(false);
  const [resendAfter, setResendAfter] = useState(0);

  useEffect(() => {
    if (!showOtp || resendAfter <= 0) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      setResendAfter((current) => Math.max(current - 1, 0));
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [showOtp, resendAfter]);

  const updateField = (event) => {
    setError("");
    setMessage("");
    setFieldErrors((current) => ({ ...current, [event.target.name]: "" }));
    setFormData((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  };

  const cleanMobile = formData.mobile.replace(/\D/g, "");

  const validate = () => {
    const errors = {};
    if (formData.name.trim().length < 3) {
      errors.name = "Name must be at least 3 characters.";
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
      errors.email = "Enter a valid email address.";
    }
    if (cleanMobile.length !== 10) {
      errors.mobile = "Enter a 10 digit mobile number.";
    }
    if (formData.username.trim().length < 3) {
      errors.username = "Username must be at least 3 characters.";
    }
    if (formData.password.length < 5) {
      errors.password = "Password must be at least 5 characters.";
    }
    if (formData.password !== formData.cpassword) {
      errors.cpassword = "Passwords do not match.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const payload = () => ({
    mobile_number: cleanMobile,
    name: formData.name.trim(),
    email: formData.email.trim(),
    username: formData.username.trim(),
    password: formData.password,
    confirm_password: formData.cpassword,
  });

  const sendOtp = async (event) => {
    if (event) {
      event.preventDefault();
    }
    setError("");
    setMessage("");

    if (!apiPath) {
      setError("Frontend API base URL is missing. Check chikooza-ui/.env.");
      return;
    }

    if (!validate()) {
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(apiUrl("sendOtp"), payload(), config);
      const returnedOtp = response.data?.results?.otp;
      setMessage(
        returnedOtp
          ? `OTP sent. Local MVP OTP is ${returnedOtp}.`
          : "OTP sent. Check the delivery channel configured on the backend."
      );
      setShowOtp(true);
      setOtp("");
      setOtpError("");
      setOtpSuccess(false);
      setResendAfter(55);
    } catch (err) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.message ||
          "Unable to send OTP. Check whether username, email, or mobile already exists."
      );
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async () => {
    const cleanOtp = otp.replace(/\D/g, "");
    if (cleanOtp.length !== 6) {
      setOtpError("Enter the 6 digit OTP.");
      return;
    }

    setLoading(true);
    setOtpError("");
    try {
      await axios.post(apiUrl("signUp"), { ...payload(), otp: cleanOtp }, config);
      setOtpSuccess(true);
      setMessage("Registration complete. You can now login.");
      window.setTimeout(() => navigate("/login"), 1200);
    } catch (err) {
      setOtpError(
        err?.response?.data?.error ||
          err?.response?.data?.message ||
          "OTP verification failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="marketing-page brand-page">
      {/* U: OLD: registration used a dashboard card with immediate loading reset and fragile OTP timer.
          U: NEW: brand-consistent auth page with a stable OTP modal and verified /users/sendOtp/ + /users/signUp/ flow. */}
      <section className="auth-shell register-shell">
        <div className="auth-story-panel">
          <span className="home-eyebrow">Farmer registration</span>
          <h1>Start with a clean farmer workspace.</h1>
          <p>
            Register once, verify OTP, and keep every farm, flock, daily entry,
            purchase, sale, report, and AI answer under one account.
          </p>
          <div className="brand-check-list">
            <div>
              <strong>Verified account</strong>
              <span>Use OTP before the farmer workspace is created.</span>
            </div>
            <div>
              <strong>Structured records</strong>
              <span>Add farms first, then flocks, daily work, costs, and sales.</span>
            </div>
            <div>
              <strong>Data ownership</strong>
              <span>Your farm records stay scoped to your own login.</span>
            </div>
          </div>
        </div>

        <div className="auth-card brand-auth-card register-card">
          <h2>Register</h2>
          <p>Enter farmer details. You will verify OTP before the account is created.</p>
          {error && <Alert color="danger">{error}</Alert>}
          {message && <Alert color="success">{message}</Alert>}
          <form className="auth-form" onSubmit={sendOtp}>
            <div className="form-field">
              <label htmlFor="register-name">Full name</label>
              <input id="register-name" name="name" onChange={updateField} placeholder="Farmer name" type="text" value={formData.name} />
              <small className="form-error">{fieldErrors.name}</small>
            </div>
            <div className="form-field">
              <label htmlFor="register-email">Email</label>
              <input autoComplete="email" id="register-email" name="email" onChange={updateField} placeholder="name@example.com" type="email" value={formData.email} />
              <small className="form-error">{fieldErrors.email}</small>
            </div>
            <div className="form-field">
              <label htmlFor="register-mobile">Mobile number</label>
              <input id="register-mobile" inputMode="numeric" maxLength={10} name="mobile" onChange={updateField} placeholder="10 digit mobile number" type="tel" value={formData.mobile} />
              <small className="form-error">{fieldErrors.mobile}</small>
            </div>
            <div className="form-field">
              <label htmlFor="register-username">Username</label>
              <input autoComplete="username" id="register-username" name="username" onChange={updateField} placeholder="Choose username" type="text" value={formData.username} />
              <small className="form-error">{fieldErrors.username}</small>
            </div>
            <div className="form-field">
              <label htmlFor="register-password">Password</label>
              <input autoComplete="new-password" id="register-password" name="password" onChange={updateField} placeholder="Minimum 5 characters" type="password" value={formData.password} />
              <small className="form-error">{fieldErrors.password}</small>
            </div>
            <div className="form-field">
              <label htmlFor="register-cpassword">Confirm password</label>
              <input autoComplete="new-password" id="register-cpassword" name="cpassword" onChange={updateField} placeholder="Confirm password" type="password" value={formData.cpassword} />
              <small className="form-error">{fieldErrors.cpassword}</small>
            </div>
            <Button className="ck-button" disabled={loading} type="submit">
              {loading ? "Sending OTP..." : "Send OTP"}
            </Button>
          </form>
          <div className="auth-switch">
            Already registered? <Link to="/login">Login here</Link>
          </div>
        </div>
      </section>

      <Modal className="otp-modal" show={showOtp} backdrop="static" keyboard={false} centered>
        <Modal.Header>
          <Modal.Title>Verify OTP</Modal.Title>
          <Button className="btn-close" color="transparent" aria-label="Close" onClick={() => setShowOtp(false)} />
        </Modal.Header>
        <Modal.Body>
          {otpSuccess ? (
            <Alert color="success">Registration complete. Redirecting to login...</Alert>
          ) : (
            <>
              <p>Enter the 6 digit OTP for {cleanMobile}.</p>
              {otpError && <Alert color="danger">{otpError}</Alert>}
              <div className="form-field">
                <label htmlFor="register-otp">OTP</label>
                <input
                  id="register-otp"
                  inputMode="numeric"
                  maxLength={6}
                  onChange={(event) => setOtp(event.target.value)}
                  placeholder="123456"
                  type="text"
                  value={otp}
                />
              </div>
            </>
          )}
        </Modal.Body>
        {!otpSuccess && (
          <Modal.Footer>
            <Button className="ck-button-secondary" disabled={loading || resendAfter > 0} onClick={sendOtp} type="button">
              {resendAfter > 0 ? `Resend in ${resendAfter}s` : "Resend OTP"}
            </Button>
            <Button className="ck-button" disabled={loading} onClick={verifyOtp} type="button">
              {loading ? "Verifying..." : "Verify and register"}
            </Button>
          </Modal.Footer>
        )}
      </Modal>
    </main>
  );
};

export default Register;
