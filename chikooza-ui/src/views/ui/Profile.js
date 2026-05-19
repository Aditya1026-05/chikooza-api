// U: OLD unused reactstrap imports kept this screen noisy during builds.
// import { Table, Input, FormText, Nav, NavItem } from "reactstrap";
import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label } from "reactstrap";
import '../../assets/css/header.css';
import { Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
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
        <Card >
          <CardTitle tag="h6" className="border-bottom p-3 mb-0">
            <i className="bi bi-bell me-2"> </i>
            User Profile
          </CardTitle>
          <CardBody>
            <Row className="mt-3">
              <Col sm="12" md={{ offset: 2, size: 8 }}>
                <div className={contentArea}>
                  <div className='gridmargin'>
                    {/* U: OLD success/error alert was fully commented out, leaving err state unused. */}
                    {(err !== '' && !show) && <Alert color="danger">{err}</Alert>}
                    <Form onSubmit={update}>
                      <FormGroup >
                        <Row >
                          <Label for="exampleEmail">Mobile No.</Label>
                          <div className="input-group input-group col-6">
                            <input name="mobile" value={data.mobile_number} className="form-control ml-1" aria-label="Username" aria-describedby="basic-addon1" disabled />
                          </div>
                          <div className="button-group col-6">
                            <Link to="/updatemobile" ><Button className="btn " color="danger">Update Mobile No.</Button></Link>
                          </div>
                        </Row>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleEmail">Username</Label>
                        <div className="input-group input-group">
                          <input name="username" value={data.username} className="form-control " aria-label="Username" aria-describedby="basic-addon1" disabled />
                        </div>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleEmail">Name</Label>
                        <div className="input-group input-group">
                          <input name="name" placeholder="Name" onChange={inputValue} value={data.name} className="form-control" aria-label="Username" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{error.name}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleEmail">Email</Label>
                        <div className="input-group input-group">
                          <input name="email" placeholder="Email" onChange={inputValue} value={data.email} type="email" className="form-control" aria-label="Username" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{error.email}</small>
                      </FormGroup>
                      <div className="button-group">
                        {loading ?
                          <Button className="btn" color="danger" type="submit" disabled  >
                            Please wait...
                            <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                          </Button>
                          :
                          <Button className="btn" color="danger" type="submit">Save</Button>
                        }
                        <Button color="warning" type="button" className="text-black" onClick={closeAll}>Cancel</Button>
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

export default Profile;
