// U: OLD unused reactstrap imports kept this screen noisy during builds.
// import { Table, Input, FormText, Nav, NavItem } from "reactstrap";
import { Alert, Row, Col, Button, Form, FormGroup, Label } from "reactstrap";
import '../../assets/css/header.css';
import { Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import axios from 'axios';
import { useNavigate } from "react-router-dom";
import Modal from 'react-bootstrap/Modal';


const Profile = () => {
  let [loading, setLoading] = useState(false);
  let [data, setData] = useState({ name: '', email: '', username: '', mobile_number: '' });
  let [error, setError] = useState({ name: '', email: '' });
  let [err, setErr] = useState('');
  let navigate = useNavigate();
  const [show, setShow] = useState(false);


  useEffect(() => {
    let url = `${apiPath}users/profile/${localStorage.getItem('publicid')}/`;
    // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
    axios.get(url, getAuthConfig()).then((res) => {
      setData(res.data.results);
    }).catch((err) => {
      handleUnauthorized(err, navigate);
    });
  }, [navigate])
  let inputValue = (e) => {
    if (e.target.name === 'name') {
      // U: OLD: e.target.name == 'name' and e.target.value.trim() == "" used loose equality.
      if (e.target.value.trim() === "") {
        setError({ ...error, name: 'Name is required' });
        setData({ ...data, name: e.target.value });
      } else {
        setError({ ...error, name: '' });
        setData({ ...data, name: e.target.value });
      }
    } else {
      if (!(RegExp(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,15}/g).test(e.target.value.trim()))) {
        setError({ ...error, email: 'Email is required or invalid' });
        setData({ ...data, email: e.target.value });
      } else {
        // U: OLD: setError('') replaced the error object with a string.
        setError({ ...error, email: '' });
        setData({ ...data, email: e.target.value });
      }
    }
  }
  let update = (e) => {
    e.preventDefault();
    setLoading(false);
    const nextError = {
      name: data.name.trim() === '' ? 'Name is required' : '',
      email: RegExp(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,15}/g).test(data.email.trim()) ? '' : 'Email is required or invalid'
    };
    setError(nextError);
    // U: OLD: if ((data.name === '') || emailIsValid) allowed invalid profile updates.
    // U: NEW: submit only when both fields are valid.
    if (nextError.name === '' && nextError.email === '') {
      let user = {
        name: data.name,
        email: data.email
      };
      setLoading(true);
      let url = `${apiPath}users/profile/${localStorage.getItem('publicid')}/`;
      axios.patch(url, user, getAuthConfig()).then((res) => {
        setErr(res.data.message);
        setShow(true);
        setLoading(false);
        setTimeout(successMsg, 3000)
      }).catch((err) => {
        setLoading(false);
        setErr(err?.response?.data?.error || 'Something went wrong. Please try again');
        handleUnauthorized(err, navigate);
      });
    }
  }
  function successMsg() {
    navigate("/member");
  }
  let closeAll = () => {
    navigate("/member")
  }
  return (
    <Row>
      <Modal show={show} backdrop="static" keyboard={false} >
        <Modal.Header>
        </Modal.Header>
        <Modal.Body>
          <Alert color="success">
            Successfully updated profile
          </Alert>
        </Modal.Body>
        <Modal.Footer>
        </Modal.Footer>
      </Modal>
      <Col>
        <section className="account-settings-page">
          <div className="account-settings-card">
            <div className="account-settings-header">
              <span>Account settings</span>
              <h1>User profile</h1>
              <p>Manage your account information.</p>
            </div>
            {/* U: OLD success/error alert was fully commented out, leaving err state unused. */}
            {(err !== '' && !show) && <Alert color="danger">{err}</Alert>}
            <Form onSubmit={update} className="account-settings-form">
              <FormGroup>
                <div className="account-field-row">
                  <div>
                    <Label for="mobileNumber">Mobile number</Label>
                    <input id="mobileNumber" name="mobile" value={data.mobile_number} className="form-control" disabled />
                  </div>
                  <Link to="/updatemobile" className="account-inline-action">Update mobile no.</Link>
                </div>
              </FormGroup>
              <FormGroup>
                <Label for="username">Username</Label>
                <input id="username" name="username" value={data.username} className="form-control" disabled />
              </FormGroup>
              <FormGroup>
                <Label for="profileName">Name</Label>
                <input id="profileName" name="name" placeholder="Name" onChange={inputValue} value={data.name} className="form-control" />
                <small className="text-danger">{error.name}</small>
              </FormGroup>
              <FormGroup>
                <Label for="profileEmail">Email</Label>
                <input id="profileEmail" name="email" placeholder="Email" onChange={inputValue} value={data.email} type="email" className="form-control" />
                <small className="text-danger">{error.email}</small>
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

export default Profile;
