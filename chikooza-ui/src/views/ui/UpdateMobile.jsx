import { Alert, Row, Col, Button, Form, FormGroup, Label } from "reactstrap";
import '../../assets/css/header.css';
import { useState } from "react";
import { FaPhoneAlt } from "react-icons/fa";
import { apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import Modal from 'react-bootstrap/Modal';
import { FaMobile } from "react-icons/fa";
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const UpdateMobile = () => {
  const navigate = useNavigate();
  const [mobileerr, setMobileerr] = useState('');
  const [mobile, setMobile] = useState('');
  const [otp, setOtp] = useState('');
  const [otperr, setOtpErr] = useState('');
  const [err, setErr] = useState('');
  const [msg, setMsg] = useState(1);
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  const inputMobile = (e) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 10);
    setMobile(value);
    if (value !== '' && value.length !== 10) {
      setMobileerr('Enter a 10 digit mobile number.');
    } else {
      setMobileerr('');
    }
  };

  const inputOtp = (e) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 6);
    setOtp(value);
    if (value !== '' && value.length !== 6) {
      setOtpErr('Enter the 6 digit OTP.');
    } else {
      setOtpErr('');
    }
  };

  const change = (e) => {
    e.preventDefault();
    setErr('');
    if (mobile.trim() === '' || mobile.length !== 10) {
      setMobileerr('Enter a 10 digit mobile number.');
    } else {
      setLoading(true);
      let user = {
        mobile_number: mobile
      };
      let url = `${apiPath}users/sendOtpForUpdateMobile/`;
      // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
      // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.post(url, user, getAuthConfig()).then((res) => {
        setShow(true);
        setLoading(false);
      }).catch((err) => {
        // U: Failed requests should leave loading state instead of keeping the button busy.
        setLoading(false);
        setErr(err.response?.data?.error || 'Unable to send OTP. Please try again.');
        handleUnauthorized(err, navigate);
      });
    }
  };

  const otpVerify = () => {
    if (otp.trim() === '' || otp.length !== 6) {
      setOtpErr('Enter the 6 digit OTP.');
    } else {
      setOtpErr('');
      let user = {
        mobile_number: mobile,
        otp: otp
      };
      let url = `${apiPath}users/updateMobile/${localStorage.getItem('publicid')}/`;
      // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
      // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.patch(url, user, getAuthConfig()).then((res) => {
        setMsg(0);
        setTimeout(successMsg, 3000);
      }).catch((err) => {
        setOtpErr(err.response?.data?.error || 'Unable to update mobile number. Please try again.');
        setShow(true);
        handleUnauthorized(err, navigate);
      });
    }
  };

  function successMsg() {
    navigate("/profile");
  }

  return (
    <Row>
      <Modal show={show} backdrop="static" keyboard={false} centered dialogClassName="account-otp-modal">
        <Modal.Header closeButton={msg !== 0} onHide={() => setShow(false)}>
          <Modal.Title>{msg === 0 ? "Mobile updated" : "Verify OTP"}</Modal.Title>
        </Modal.Header>
        {msg === 0 ?
          <>
            <Modal.Body>
              <Alert color="success">
                Successfully updated mobile number
              </Alert>
            </Modal.Body>
            <Modal.Footer>
            </Modal.Footer>
          </>
          :
          <>
            <Modal.Body>
              <FormGroup>
                <Label for="mobileOtp">Enter OTP sent to {mobile}</Label>
                <div className="account-password-input">
                  <span><FaMobile /></span>
                  <input id="mobileOtp" onChange={inputOtp} name="otp" placeholder="6 digit OTP" type="text" inputMode="numeric" maxLength="6" className="form-control" value={otp} />
                </div>
                <small className="text-danger">{otperr}</small>
              </FormGroup>
            </Modal.Body>
            <Modal.Footer>
              <Button color="secondary" type="button" onClick={() => setShow(false)}>Cancel</Button>
              <Button color="danger" type="button" onClick={otpVerify}>Verify OTP</Button>
            </Modal.Footer>
          </>
        }
      </Modal>
      <Col>
        <section className="account-settings-page">
          <div className="account-settings-card">
            <div className="account-settings-header">
              <span>Account security</span>
              <h1>Update mobile number</h1>
              <p>Verify your new number before saving it.</p>
            </div>
            {(err !== '') && <Alert color="danger">{err}</Alert>}
            <Form onSubmit={change} className="account-settings-form">
              <FormGroup>
                <Label for="newMobile">New mobile number</Label>
                <div className="account-password-input">
                  <span><FaPhoneAlt /></span>
                  <input id="newMobile" onChange={inputMobile} name="mobile" placeholder="10 digit mobile number" type="tel" inputMode="numeric" maxLength="10" className="form-control" value={mobile} />
                </div>
                <small className="text-danger">{mobileerr}</small>
              </FormGroup>
              <div className="form-wizard-actions">
                {loading ?
                  <Button color="danger" type="submit" disabled>
                    Please wait...
                    <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                  </Button>
                  :
                  <Button color="danger" type="submit">Send OTP</Button>
                }
                <Button color="secondary" type="button" onClick={() => navigate("/profile")}>Cancel</Button>
              </div>
            </Form>
          </div>
        </section>
      </Col>
    </Row>
  );
};

export default UpdateMobile;
