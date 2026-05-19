import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label } from "reactstrap";
import '../../assets/css/header.css';
import { useState } from "react";
import { FaPhoneAlt } from "react-icons/fa";
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import Modal from 'react-bootstrap/Modal';
import { FaMobile } from "react-icons/fa";
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const UpdateMobile = () => {
  const navigate = useNavigate();
  let [mobileerr, setMobileerr] = useState('');
  let [mobile, setMobile] = useState('');
  let [otp, setOtp] = useState('');
  let [otperr, setOtpErr] = useState(null);
  let [err, setErr] = useState('');
  let [msg, setMsg] = useState(1);
  const [show, setShow] = useState(false);
  let [loading, setLoading] = useState(false)

  let inputMobile = (e) => {
    if (e.target.value.trim() === '' || e.target.value.length > 10 || isNaN(e.target.value)) {
      setMobileerr('Mobile is required or invalid');
    } else {
      setMobileerr('');
      setMobile(e.target.value);
    }
  }
  let change = (e) => {
    e.preventDefault();
    setLoading(false)
    if (mobile.trim() === '' || mobile.length > 10) {
      setMobileerr('Mobile is required or invalid');
    } else {
      setLoading(true)
      let user = {
        mobile_number: mobile
      };
      let url = `${apiPath}users/sendOtpForUpdateMobile/`;
      // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
      // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.post(url, user, getAuthConfig()).then((res) => {
        setShow(true);
        setLoading(false)
      }).catch((err) => {
        // U: Failed requests should leave loading state instead of keeping the button busy.
        setLoading(false)
        setErr(err.response?.data?.error || 'Unable to send OTP. Please try again.');
        handleUnauthorized(err, navigate);
      });
    }
  }
  let otpVerify = () => {
    if (otp.trim() === '' || otp.length !== 6 || isNaN(otp)) {
      setOtpErr('OTP is required or invalid');
    } else {
      setOtpErr(false);
      let user = {
        mobile_number: mobile,
        otp: otp
      };
      let url = `${apiPath}users/updateMobile/${localStorage.getItem('publicid')}/`;
      // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
      // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.patch(url, user, getAuthConfig()).then((res) => {
        setMsg(0)
        setTimeout(successMsg, 3000);
      }).catch((err) => {
        setOtpErr(err.response?.data?.error || 'Unable to update mobile number. Please try again.');
        setShow(true);
        handleUnauthorized(err, navigate);
      });
    }
  }
  function successMsg() {
    navigate("/profile");
  }

  return (
    <Row>
      <Modal show={show} backdrop="static" keyboard={false} >
        <Modal.Header>
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
                <Label for="exampleName">Please enter OTP</Label>
                <div className="input-group input-group">
                  <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaMobile></FaMobile></span>
                  <input onChange={(e) => { setOtp(e.target.value) }} name="otp" placeholder="OTP" type="text" maxLength="6" className="form-control" aria-label="OTP" aria-describedby="basic-addon1" />
                </div>
                <small id="otpHelp" className="text-danger">{otperr}</small>
              </FormGroup>
            </Modal.Body>
            <Modal.Footer>
              <Button className="btn" color="danger" type="submit" onClick={otpVerify}>OK</Button>
            </Modal.Footer>
          </>
        }
      </Modal>
      <Col>
        <Card >
          <CardTitle tag="h6" className="border-bottom p-3 mb-0">
            <i className="bi bi-bell me-2"> </i>
            Update Mobile Number
          </CardTitle>
          <CardBody>
            <Row className="mt-3">
              <Col sm="12" md={{ offset: 2, size: 8 }}>
                <div className={contentArea}>
                  <div className='gridmargin'>
                    {(err !== '') && <Alert color="danger">{err}</Alert>}
                    <Form onSubmit={change}>
                      <FormGroup>
                        <Label for="examplePassword">New Mobile No.</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaPhoneAlt></FaPhoneAlt></span>
                          <input onChange={inputMobile} name="mobile" placeholder="Mobile" type="text" maxLength="10" className="form-control" aria-label="Password" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{mobileerr}</small>
                      </FormGroup>
                      <div className="button-group">
                        {loading ?
                          <Button className="btn" color="danger" type="submit"   >
                            Please wait...
                            <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                          </Button>
                          :
                          <Button className="btn" color="danger" type="submit" >Send OTP</Button>
                        }
                      </div>
                    </Form>
                  </div>
                </div>
              </Col>
            </Row>
          </CardBody>
        </Card>
      </Col>
    </Row>
  );
};

export default UpdateMobile;
