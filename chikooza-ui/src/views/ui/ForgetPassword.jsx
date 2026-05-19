import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label } from "reactstrap";
import '../../assets/css/header.css';
import { Link } from "react-router-dom";
import { useState } from "react";
import { FaUser, FaPhoneAlt, FaMobile, FaLock } from "react-icons/fa";
import { contentArea, apiPath, config } from "../../Constants";
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Modal from 'react-bootstrap/Modal';

const ForgetPassword = () => {
  const navigate = useNavigate();
  let [addData, setAddData] = useState({ username: '', mobile: '', password: '', cpassword: '', otp: '', usernameerr: '', mobileerr: '', otperr: '', passworderr: '', cpassworderr: '' });
  let [loading, setLoading] = useState(false);
  let [err, setErr] = useState('');
  const [step, setStep] = useState(true);
  const [show, setShow] = useState(false);

  let save = (e) => {
    setLoading(true);
    e.preventDefault();
    if (addData.username.trim() === '') {
      // U: Replaced direct state mutation with an immutable state update.
      // setAddData(addData.usernameerr = 'Username is required');
      setAddData({ ...addData, usernameerr: 'Username is required' });
    }
    if ((addData.mobile === '') || (addData.mobile.length !== 10)) {
      setAddData({ ...addData, mobileerr: 'Mobile number is required or invalid' });
    }
    if (!((addData.username === '') || (addData.mobile === '') || (addData.mobile.length !== 10))) {
      let user = {
        mobile_number: addData.mobile,
        username: addData.username
      };
      let url = `${apiPath}users/resetPassword/`;
      axios.post(url, user, config).then((res) => {
        setStep(false);
      }).catch((err) => {
        setErr(err.response?.data?.error || 'Unable to send OTP. Please try again.');
      });
    }
    setLoading(false);
  }
  let submit = (e) => {
    setLoading(true);
    e.preventDefault();
    if (addData.otp.trim() === '' || addData.otp.length > 6) {
      // U: Replaced direct state mutation with an immutable state update.
      // setAddData(addData.otperr = 'OTP is required');
      setAddData({ ...addData, otperr: 'OTP is required' });
    }
    if (addData.password.trim() === '') {
      // U: Replaced direct state mutation with an immutable state update.
      // setAddData(addData.passworderr = 'Password is required');
      setAddData({ ...addData, passworderr: 'Password is required' });
    }
    if (addData.cpassword.trim() === '' || addData.cpassword !== addData.password) {
      setAddData({ ...addData, cpassworderr: 'Password and Confirm Password does not match' });
    }
    if (!((addData.username === '') || (addData.password === '') || (addData.cpassword === '') || (addData.mobile === '') || (addData.mobile.length !== 10) || (addData.password !== addData.cpassword))) {
      let user = {
        mobile_number: addData.mobile,
        username: addData.username,
        new_password: addData.password,
        confirm_new_password: addData.cpassword,
        otp: addData.otp
      };
      let url = `${apiPath}users/forgetPassword/`;
      axios.post(url, user, config).then((res) => {
        setShow(true);
        setTimeout(successMsg, 3000);
      }).catch((err) => {
        setErr(err.response?.data?.error || 'Unable to reset password. Please try again.');
        console.log(err);
      });
    }
    setLoading(false);
  }

  let inputError = (e) => {
    if (e.target.name === 'username') {
      if (e.target.value.trim() !== '') {
        setAddData({ ...addData, username: e.target.value, usernameerr: '' });
      } else {
        setAddData({ ...addData, username: e.target.value, usernameerr: 'Username is required' });
      }
    } else if (e.target.name === 'mobile') {
      if (e.target.value.trim() === '' || e.target.value.length > 10 || isNaN(e.target.value)) {
        setAddData({ ...addData, mobile: e.target.value, mobileerr: 'Mobile number is required or invalid' });
      } else {
        setAddData({ ...addData, mobile: e.target.value, mobileerr: '' });
      }
    } else if (e.target.name === 'otp') {
      if (e.target.value.trim() === '' || e.target.value.length > 6 || isNaN(e.target.value)) {
        setAddData({ ...addData, otp: e.target.value, otperr: 'OTP is required or invalid' });
      } else {
        setAddData({ ...addData, otp: e.target.value, otperr: '' });
      }
    } else if (e.target.name === 'password') {
      if (e.target.value.trim() === '') {
        setAddData({ ...addData, password: e.target.value, passworderr: 'Password is required' });
      } else {
        setAddData({ ...addData, password: e.target.value, passworderr: '' });
      }
    } else if (e.target.name === 'cpassword') {
      if (e.target.value.trim() === '' || e.target.value !== addData.password) {
        setAddData({ ...addData, cpassword: e.target.value, cpassworderr: 'Password and Confirm Password does not match' });
      } else {
        setAddData({ ...addData, cpassword: e.target.value, cpassworderr: '' });
      }
    }
  }
  function successMsg() {
    navigate("/login");
  }
  return (
    <Row>
      <Modal show={show} backdrop="static" keyboard={false} >
        <Modal.Header>
        </Modal.Header>
        <Modal.Body>
          <Alert color="success">
            Your password has been updated
          </Alert>
        </Modal.Body>
        <Modal.Footer>
        </Modal.Footer>
      </Modal>
      <Col>
        <Card >
          <CardTitle tag="h6" className="border-bottom p-3 mb-0">
            <i className="bi bi-bell me-2"> </i>
            Reset Password
          </CardTitle>
          <CardBody>
            <Row className="mt-3">
              <Col sm="12" md={{ offset: 2, size: 8 }}>
                <div className={contentArea}>
                  <div className='gridmargin'>
                    {(err !== '') && <Alert color="danger">{err}</Alert>}
                    {step ?
                      <Form onSubmit={save}>
                        <FormGroup>
                          <Label for="examplePassword">User Name</Label>
                          <div className="input-group input-group">
                            <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaUser></FaUser></span>
                            <input onChange={inputError} name="username" placeholder="Enter Your User Name" className="form-control" aria-label="Password" aria-describedby="basic-addon1" />
                          </div>
                          <small id="passwordHelp" className="text-danger">{addData.usernameerr}</small>
                        </FormGroup>
                        <FormGroup>
                          <Label for="examplePassword">Phone Number</Label>
                          <div className="input-group input-group">
                            <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaPhoneAlt></FaPhoneAlt></span>
                            <input type="text" maxLength="10" onChange={inputError} name="mobile" placeholder="Enter Your Phone Number" className="form-control" aria-label="Password" aria-describedby="basic-addon1" />
                          </div>
                          <small id="passwordHelp" className="text-danger">{addData.mobileerr}</small>
                        </FormGroup>
                        <div className="button-group">
                          {loading ?
                            <Button className="btn" color="danger" type="submit" disabled  >
                              Please wait...
                              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                            </Button>
                            :
                            <Button className="btn" color="danger" type="submit">Send OTP</Button>
                          }
                        </div>
                      </Form>
                      :
                      <Form onSubmit={submit}>
                        <FormGroup>
                          <Label for="examplePassword">User Name</Label>
                          <div className="input-group input-group">
                            <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaUser></FaUser></span>
                            <input disabled onChange={inputError} name="username" placeholder="Enter Your User Name" className="form-control" aria-label="Password" aria-describedby="basic-addon1" />
                          </div>
                          <small id="passwordHelp" className="text-danger">{addData.usernameerr}</small>
                        </FormGroup>
                        <FormGroup>
                          <Label for="examplePassword">Phone Number</Label>
                          <div className="input-group input-group">
                            <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaPhoneAlt></FaPhoneAlt></span>
                            <input disabled type="text" maxLength="10" onChange={inputError} name="mobile" placeholder="Enter Your Phone Number" className="form-control" aria-label="Password" aria-describedby="basic-addon1" />
                          </div>
                          <small id="passwordHelp" className="text-danger">{addData.mobileerr}</small>
                        </FormGroup>
                        <FormGroup>
                          <Label for="exampleMobile">OTP</Label>
                          <div className="input-group input-group">
                            <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaMobile></FaMobile></span>
                            <input onChange={inputError} name="otp" placeholder="OTP" type="text" maxLength="6" className="form-control" aria-label="Mobile" aria-describedby="basic-addon1" />
                          </div>
                          <small id="passwordHelp" className="text-danger">{addData.otperr}</small>
                        </FormGroup>
                        <FormGroup>
                          <Label for="examplePassword">Password</Label>
                          <div className="input-group input-group">
                            <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaLock></FaLock></span>
                            <input onChange={inputError} name="password" placeholder="Password" type="password" className="form-control" aria-label="Password" aria-describedby="basic-addon1" />
                          </div>
                          <small id="passwordHelp" className="text-danger">{addData.passworderr}</small>
                        </FormGroup>
                        <FormGroup>
                          <Label for="exampleConfirmPassword">Confirm Password</Label>
                          <div className="input-group input-group">
                            <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaLock></FaLock></span>
                            <input onChange={inputError} name="cpassword" placeholder="Confirm Password" type="password" className="form-control" aria-label="cpassword" aria-describedby="basic-addon1" />
                          </div>
                          <small id="passwordHelp" className="text-danger">{addData.cpassworderr}</small>
                        </FormGroup>
                        <div className="button-group">
                          {loading ?
                            <Button className="btn" color="danger" type="submit" disabled  >
                              Please wait...
                              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                            </Button>
                            :
                            <Button className="btn" color="danger" type="submit">Submit</Button>
                          }
                        </div>
                      </Form>
                    }
                  </div>
                </div>
                <div className="button-group  mt-4">
                  Not Registered?
                  <Link to="/register" className="btn rowlink">
                    Register here
                  </Link>
                </div>
              </Col>
            </Row>
          </CardBody>
        </Card>
      </Col>
    </Row>
  );
};

export default ForgetPassword;
