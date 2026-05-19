import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label } from "reactstrap";
import '../../assets/css/header.css';
import { useState } from "react";
import { FaLock } from "react-icons/fa";
import { contentArea, apiPath, config } from "../../Constants";
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
    console.log("adsfgh");
    e.preventDefault();
    setLoading(false)
    if (addData.currentpassword === '') {
      setaddDataError(addDataError.currentpassword = 'Current password is required');
    } console.log(addData.currentpassword.length);
    if (addData.currentpassword.length > 30) {
      setaddDataError(addDataError.currentpassword = "Ensure this field has no more than 30 characters");
    }
    if (addData.npassword === '') {
      setaddDataError(addDataError.npassword = 'New password is required');
    }
    if ((addData.cpassword === '') || (addData.npassword !== addData.cpassword)) {
      setaddDataError({ ...addDataError, cpassword: 'Confirm password is required or password and confirm Password does not match' });
    }
    console.log(addDataError.currentpassword, addData.npassword, addData.cpassword, "0002");
    if (!((addData.currentpassword === '') || (addData.npassword === '') || (addData.cpassword === '') || (addData.npassword !== addData.cpassword))) {
      setLoading(true)
      let user = {
        current_password: addData.currentpassword,
        new_password: addData.npassword,
        confirm_new_password: addData.cpassword
      };
      let url = `${apiPath}users/changePassword/`;
      config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.post(url, user, config).then((res) => {
        setErr(res.data.message);
        setLoading(false)
        setShow(true)
        setTimeout(successMsg, 3000);
        console.log("res");
      }).catch((err) => {
        console.log("err");
        setErr(err.response.data.error);
        if ((err.response.data.confirm_new_password ? true : false) || (err.response.data.current_password ? true : false) || (err.response.data.new_password ? true : false)) {
          setErr("White space may not be expected.")
        }

        console.log(err);
        if (err.response.status === 401) {
          localStorage.clear();
          navigate("/login")
        } setLoading(false)
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
      setAddData({ ...addData, currentpassword: e.target.value });
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
        <Card >
          <CardTitle tag="h6" className="border-bottom p-3 mb-0">
            <i className="bi bi-bell me-2"> </i>
            Change Password
          </CardTitle>
          <CardBody>
            <Row className="mt-3">
              <Col sm="12" md={{ offset: 2, size: 8 }}>
                <div className={contentArea}>
                  <div className='gridmargin'>
                    {(err !== '') && <Alert color="info">{err}</Alert>}
                    <Form onSubmit={change}>
                      <FormGroup>
                        <Label for="examplePassword">Current Password</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaLock></FaLock></span>
                          <input onChange={inputCurrentPassword} name="currentpassword" value={addData.currentpassword} placeholder="Current Password" type="password" className="form-control" aria-label="Password" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{addDataError.currentpassword}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="examplePassword">New Password</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaLock></FaLock></span>
                          <input onChange={inputNPassword} value={addData.npassword} name="npassword" placeholder="New Password" type="password" className="form-control" aria-label="Password" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{addDataError.npassword}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleConfirmPassword">Confirm Password</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{ color: '#fd5c63' }} id="basic-addon1"><FaLock></FaLock></span>
                          <input onChange={inputCPassword} value={addData.cpassword} name="cpassword" placeholder="Confirm Password" type="password" className="form-control" aria-label="cpassword" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{addDataError.cpassword}</small>
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

export default ChangePassword;
