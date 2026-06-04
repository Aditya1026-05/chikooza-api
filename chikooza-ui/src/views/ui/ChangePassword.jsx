import { Alert, Row, Col, Button, Form, FormGroup, Label } from "reactstrap";
import '../../assets/css/header.css';
import { useState } from "react";
import { FaLock } from "react-icons/fa";
import { apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import axios from 'axios';
import { useNavigate } from "react-router-dom";
import Modal from 'react-bootstrap/Modal';


const ChangePassword = () => {
  let [addData, setAddData] = useState({ currentpassword: '', npassword: '', cpassword: '' });
  let [addDataError, setaddDataError] = useState({ currentpassword: '', npassword: '', cpassword: '' });
  let [err, setErr] = useState('');
  let navigate = useNavigate()
  let [loading, setLoading] = useState(false);
  let [show, setShow] = useState(false)

  let change = (e) => {
    e.preventDefault();
    setLoading(false)
    const nextError = {
      currentpassword: addData.currentpassword === ''
        ? 'Current password is required'
        : addData.currentpassword.length > 30
          ? 'Ensure this field has no more than 30 characters'
          : '',
      npassword: addData.npassword === '' ? 'New password is required' : '',
      cpassword: addData.cpassword === ''
        ? 'Confirm password is required'
        : addData.npassword !== addData.cpassword
          ? 'Password and confirm password do not match'
          : '',
    };
    setaddDataError(nextError);
    if (!nextError.currentpassword && !nextError.npassword && !nextError.cpassword) {
      setLoading(true)
      let user = {
        current_password: addData.currentpassword,
        new_password: addData.npassword,
        confirm_new_password: addData.cpassword
      };
      let url = `${apiPath}users/changePassword/`;
      // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
      // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.post(url, user, getAuthConfig()).then((res) => {
        setErr(res.data.message);
        setLoading(false)
        setShow(true)
        setTimeout(successMsg, 3000);
      }).catch((err) => {
        setErr(err.response?.data?.error || 'Unable to change password. Please try again.');
        if ((err.response?.data?.confirm_new_password ? true : false) || (err.response?.data?.current_password ? true : false) || (err.response?.data?.new_password ? true : false)) {
          setErr("White space may not be expected.")
        }

        handleUnauthorized(err, navigate);
        setLoading(false)
      });
    }
  }
  function successMsg() {
    navigate("/member");
  }
  let inputCurrentPassword = (e) => {
    if (e.target.value === '') {
      setaddDataError({ ...addDataError, currentpassword: 'Current password is required' });
    }
    else if (e.target.value.length > 30) {
      setaddDataError({
        ...addDataError, currentpassword: "Ensure this field has no more than 30 characters"
      });
    } else {
      setaddDataError({ ...addDataError, currentpassword: '' });
    }
    setAddData({ ...addData, currentpassword: e.target.value });
  }
  let inputNPassword = (e) => {
    if (e.target.value === '') {
      setaddDataError({ ...addDataError, npassword: 'New password is required' });
    } else {
      setaddDataError({ ...addDataError, npassword: '' });
    }
    setAddData({ ...addData, npassword: e.target.value });
  }
  let inputCPassword = (e) => {
    if ((e.target.value === '') || (e.target.value !== addData.npassword)) {
      setaddDataError({ ...addDataError, cpassword: 'Password and Confirm Password does not match' });
    } else {
      setaddDataError({ ...addDataError, cpassword: '' });
    }
    setAddData({ ...addData, cpassword: e.target.value });
  }
  let closeAll = () => {
    setAddData({
      ...addData, currentpassword: '', npassword: '', cpassword: ''
    })
    setaddDataError({ currentpassword: '', npassword: '', cpassword: '' });
    setErr("")

  }
  return (
    <Row>
      <Modal show={show} backdrop="static" keyboard={false} >
        <Modal.Header>
        </Modal.Header>
        <Modal.Body>
          <Alert color="success">
            Successfully updated password
          </Alert>
        </Modal.Body>
        <Modal.Footer>
        </Modal.Footer>
      </Modal>
      <Col>
        <section className="account-settings-page">
          <div className="account-settings-card">
            <div className="account-settings-header">
              <span>Account security</span>
              <h1>Change password</h1>
              <p>Use a password only you know. After changing it, continue using the same farmer workspace.</p>
            </div>
            {(err !== '') && <Alert color="info">{err}</Alert>}
            <Form onSubmit={change} className="account-settings-form">
              <FormGroup>
                <Label for="currentPassword">Current password</Label>
                <div className="account-password-input">
                  <span><FaLock /></span>
                  <input id="currentPassword" onChange={inputCurrentPassword} name="currentpassword" value={addData.currentpassword} placeholder="Current password" type="password" className="form-control" />
                </div>
                <small className="text-danger">{addDataError.currentpassword}</small>
              </FormGroup>
              <FormGroup>
                <Label for="newPassword">New password</Label>
                <div className="account-password-input">
                  <span><FaLock /></span>
                  <input id="newPassword" onChange={inputNPassword} value={addData.npassword} name="npassword" placeholder="New password" type="password" className="form-control" />
                </div>
                <small className="text-danger">{addDataError.npassword}</small>
              </FormGroup>
              <FormGroup>
                <Label for="confirmPassword">Confirm password</Label>
                <div className="account-password-input">
                  <span><FaLock /></span>
                  <input id="confirmPassword" onChange={inputCPassword} value={addData.cpassword} name="cpassword" placeholder="Confirm password" type="password" className="form-control" />
                </div>
                <small className="text-danger">{addDataError.cpassword}</small>
              </FormGroup>
              <div className="form-wizard-actions">
                {loading ?
                  <Button className="btn" color="danger" type="submit" disabled>
                    Please wait...
                    <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                  </Button>
                  :
                  <Button className="btn" color="danger" type="submit">Save</Button>
                }
                <Button color="secondary" type="button" onClick={closeAll}>Cancel</Button>
              </div>
            </Form>
          </div>
        </section>
      </Col>
    </Row>
  );
};

export default ChangePassword;
