import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Alert, Button } from "reactstrap";
import Modal from "react-bootstrap/Modal";
import axios from "axios";
import "../../assets/css/marketing.css";
import { apiPath, config } from "../../Constants";

const initialData = {
  username: "",
  mobile: "",
  password: "",
  cpassword: "",
  otp: "",
  usernameerr: "",
  mobileerr: "",
  otperr: "",
  passworderr: "",
  cpassworderr: "",
};

const ForgetPassword = () => {
  const navigate = useNavigate();
  const [addData, setAddData] = useState(initialData);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [step, setStep] = useState(true);
  const [show, setShow] = useState(false);

  const save = async (event) => {
    event.preventDefault();
    setErr("");

    const nextData = {
      ...addData,
      usernameerr: addData.username.trim() ? "" : "Username is required",
      mobileerr: addData.mobile.length === 10 ? "" : "Mobile number is required or invalid",
    };

    if (nextData.usernameerr || nextData.mobileerr) {
      setAddData(nextData);
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${apiPath}users/resetPassword/`,
        {
          mobile_number: addData.mobile,
          username: addData.username.trim(),
        },
        config
      );
      setStep(false);
    } catch (error) {
      setErr(error.response?.data?.error || "Unable to send OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    setErr("");

    const nextData = {
      ...addData,
      otperr: addData.otp.trim() && addData.otp.length === 6 ? "" : "OTP is required or invalid",
      passworderr: addData.password.trim() ? "" : "Password is required",
      cpassworderr: addData.cpassword && addData.cpassword === addData.password ? "" : "Password and Confirm Password does not match",
    };

    if (nextData.otperr || nextData.passworderr || nextData.cpassworderr) {
      setAddData(nextData);
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${apiPath}users/forgetPassword/`,
        {
          mobile_number: addData.mobile,
          username: addData.username.trim(),
          new_password: addData.password,
          confirm_new_password: addData.cpassword,
          otp: addData.otp,
        },
        config
      );
      setShow(true);
      window.setTimeout(() => navigate("/login"), 1800);
    } catch (error) {
      setErr(error.response?.data?.error || "Unable to reset password. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const inputError = (event) => {
    const { name, value } = event.target;
    setErr("");
    setAddData((current) => {
      const nextData = { ...current, [name]: value };

      if (name === "username") {
        nextData.usernameerr = value.trim() ? "" : "Username is required";
      }
      if (name === "mobile") {
        nextData.mobileerr = value.trim() === "" || value.length > 10 || Number.isNaN(Number(value))
          ? "Mobile number is required or invalid"
          : "";
      }
      if (name === "otp") {
        nextData.otperr = value.trim() === "" || value.length > 6 || Number.isNaN(Number(value))
          ? "OTP is required or invalid"
          : "";
      }
      if (name === "password") {
        nextData.passworderr = value.trim() ? "" : "Password is required";
        nextData.cpassworderr = nextData.cpassword && nextData.cpassword !== value
          ? "Password and Confirm Password does not match"
          : "";
      }
      if (name === "cpassword") {
        nextData.cpassworderr = value.trim() === "" || value !== current.password
          ? "Password and Confirm Password does not match"
          : "";
      }

      return nextData;
    });
  };

  return (
    <main className="marketing-page brand-page">
      {/* U: OLD: forgot-password used dashboard cards and inline icon inputs.
          U: NEW: match login/register brand layout while keeping the existing reset APIs. */}
      <Modal show={show} backdrop="static" keyboard={false} centered>
        <Modal.Body>
          <Alert color="success" className="mb-0">
            Your password has been updated. Redirecting to login...
          </Alert>
        </Modal.Body>
      </Modal>

      <section className="auth-shell">
        <div className="auth-story-panel">
          <span className="home-eyebrow">Password recovery</span>
          <h1>Reset access to your farm account.</h1>
          <p>
            Verify your username and registered mobile number, then use the OTP
            flow to set a new password for the farmer dashboard.
          </p>
          <div className="brand-check-list">
            <div>Step one sends OTP for the matching username and mobile.</div>
            <div>Step two verifies OTP and updates the password.</div>
            <div>After reset, continue from the normal farmer login page.</div>
          </div>
        </div>

        <div className="auth-card brand-auth-card">
          <h2>{step ? "Send reset OTP" : "Set new password"}</h2>
          <p>
            {step
              ? "Enter the farmer username and registered mobile number."
              : "Enter the OTP and your new password."}
          </p>
          {err && <Alert color="danger">{err}</Alert>}
          {step ? (
            <form className="auth-form" onSubmit={save}>
              <div className="form-field">
                <label htmlFor="forgot-username">Username</label>
                <input
                  id="forgot-username"
                  name="username"
                  onChange={inputError}
                  placeholder="Enter username"
                  type="text"
                  value={addData.username}
                />
                <small className="form-error">{addData.usernameerr}</small>
              </div>
              <div className="form-field">
                <label htmlFor="forgot-mobile">Mobile number</label>
                <input
                  id="forgot-mobile"
                  inputMode="numeric"
                  maxLength={10}
                  name="mobile"
                  onChange={inputError}
                  placeholder="10 digit mobile number"
                  type="tel"
                  value={addData.mobile}
                />
                <small className="form-error">{addData.mobileerr}</small>
              </div>
              <Button className="ck-button" disabled={loading} type="submit">
                {loading ? "Sending OTP..." : "Send OTP"}
              </Button>
            </form>
          ) : (
            <form className="auth-form" onSubmit={submit}>
              <div className="form-field">
                <label htmlFor="forgot-otp">OTP</label>
                <input
                  id="forgot-otp"
                  inputMode="numeric"
                  maxLength={6}
                  name="otp"
                  onChange={inputError}
                  placeholder="Enter OTP"
                  type="text"
                  value={addData.otp}
                />
                <small className="form-error">{addData.otperr}</small>
              </div>
              <div className="form-field">
                <label htmlFor="forgot-password">New password</label>
                <input
                  id="forgot-password"
                  name="password"
                  onChange={inputError}
                  placeholder="New password"
                  type="password"
                  value={addData.password}
                />
                <small className="form-error">{addData.passworderr}</small>
              </div>
              <div className="form-field">
                <label htmlFor="forgot-confirm-password">Confirm password</label>
                <input
                  id="forgot-confirm-password"
                  name="cpassword"
                  onChange={inputError}
                  placeholder="Confirm password"
                  type="password"
                  value={addData.cpassword}
                />
                <small className="form-error">{addData.cpassworderr}</small>
              </div>
              <Button className="ck-button" disabled={loading} type="submit">
                {loading ? "Updating password..." : "Update password"}
              </Button>
            </form>
          )}
          <div className="auth-switch">
            Remembered password? <Link to="/login">Login here</Link>
          </div>
          <div className="auth-switch">
            Not registered? <Link to="/register">Create account</Link>
          </div>
        </div>
      </section>
    </main>
  );
};

export default ForgetPassword;
