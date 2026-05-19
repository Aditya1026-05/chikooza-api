import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label } from "reactstrap";
import '../../assets/css/header.css';
import { Link } from "react-router-dom";
import { useState } from "react";
import { FaUserCircle, FaMailBulk, FaMobile, FaUser, FaLock} from "react-icons/fa";
import { contentArea, apiPath, config } from "../../Constants";
import Modal from 'react-bootstrap/Modal';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { MdCancel } from "react-icons/md";

const Register = () => {
  const navigate = useNavigate();
  //OTP Alert
  const [show, setShow] = useState(false);
  const handleClose = () => setShow(false);
  //OTP Alert
  let [addData, setAddData] = useState({name:'',password:'',cpassword:'',username:'',email:'',mobile:'',err:''});
  let [nameerr ,setName] = useState(null);
  let [usernameerr ,setUsername] = useState(null);
  let [emailerr ,setEmail] = useState(null);
  let [mobileerr ,setMobile] = useState(null);
  let [passworderr ,setPassword] = useState(null);
  let [cpassworderr ,setCpassword] = useState(null);
  let [loading, setLoading] = useState(false);
  let [otp, setOtp] = useState('');
  let [otperr, setOtpErr] = useState(null);
  let [err, setErr] = useState('');
  let [msg, setMsg] = useState(1);
  let [resend, setResend] = useState(1);
  let [minute, setMinute] = useState(59);
  let save = (e) => {
    setLoading(true);
    e.preventDefault();
    //setStatus(null);
    if(addData.name === ''){
      setName('Name is required');
    }
    if(addData.username === ''){
      setUsername('Username is required');
    }
    if(addData.password === ''){
      setPassword('Password is required');
    }
    if(addData.cpassword === ''){
      setCpassword('Confirm Password is required');
    }
    if(addData.password !== addData.cpassword){
      setCpassword('Password and Confirm Password does not match');
    }
    if(!(RegExp(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,15}/g).test(addData.email))){
      setEmail('Email is required');
    }
    if((addData.mobile === '') || (addData.mobile.length !== 10)){
      setMobile('Mobile is required');
    }
    if(!( (addData.name === '') || (addData.username === '') || (addData.password === '') || (addData.cpassword === '') || (addData.email === '') || (addData.mobile === '') || (addData.mobile.length !== 10) || (addData.password !== addData.cpassword) )){
      let user = {
        mobile_number : addData.mobile,
        name : addData.name,
        email : addData.email,
        username : addData.username,
        password : addData.password,
        confirm_password : addData.cpassword,
      };
      let url = `${apiPath}users/sendOtp/`;
      axios.post(url, user, config).then((res)=>{
        setShow(true);
        let mid = 59;
        let timer = setInterval(()=>{
          mid = mid-1;
          if(mid === 55){
            setResend(0);
            clearInterval(timer);
            setMinute(59);
          }else{
            setMinute(mid);
          }
        },1000);
      }).catch((err)=>{
        setErr(err.response?.data?.message || 'Unable to send OTP. Please try again.');
      });
    }
    setLoading(false);
  }

  let resentOTP = () => {
    let user = {
      mobile_number : addData.mobile,
      name : addData.name,
      email : addData.email,
      username : addData.username,
      password : addData.password,
      confirm_password : addData.cpassword,
    };
    let url = `${apiPath}users/sendOtp/`;
    axios.post(url, user, config).then((res)=>{
      //setOtpErr("Otp sent");
      setResend(1);
      let mid = 59;
      let timer = setInterval(()=>{
        mid = mid-1;
        if(mid === 0){
          setResend(0);
          clearInterval(timer);
          setMinute(59);
        }else{
          setMinute(mid);
        }
      },1000);
    }).catch((err)=>{
      setOtpErr(err.response?.data?.message || 'Unable to resend OTP. Please try again.');
    });
  }

  let inputCpassword = (e) => {
    if(e.target.value===addData.password){
      setCpassword(false);
      setAddData({...addData,[e.target.name]:e.target.value});
    }else{
      setCpassword('Password not match');
      setAddData({...addData,[e.target.name]:e.target.value});
    }
  }
  let inputPassword = (e) => {
    if(e.target.value.trim()===''){
      setPassword('Password is required');
      setAddData({...addData,[e.target.name]:e.target.value});
    }else{
      setPassword(false);
      setAddData({...addData,[e.target.name]:e.target.value});
    }
  }
  let inputUsername = (e) => {
    if(e.target.value.trim()===''){
      setUsername('Username is required');
      setAddData({...addData,[e.target.name]:e.target.value});
    }else{
      setUsername(false);
      setAddData({...addData,[e.target.name]:e.target.value});
    }
  }
  let inputMobile = (e) => {
    if(e.target.value.trim()==='' || e.target.value.length > 14 || isNaN(e.target.value)){
      setMobile('Mobile is required or invalid');
      setAddData({...addData,[e.target.name]:e.target.value});
    }else{
      setMobile(false);
      setAddData({...addData,[e.target.name]:e.target.value});
    }
  }
  let inputEmail = (e) => {
    if(!(RegExp(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,15}/g).test(e.target.value.trim()))){
      setEmail('Email is required or invalid');
      setAddData({...addData,[e.target.name]:e.target.value});
    }else{
      setEmail(false);
      setAddData({...addData,[e.target.name]:e.target.value});
    }
  }
  let inputName = (e) => {
    if(e.target.value.trim()===''){
      setName('Name is required');
      setAddData({...addData,[e.target.name]:e.target.value});
    }else{
      setName(false);
      setAddData({...addData,[e.target.name]:e.target.value});
    }
  }
  let otpVerify = () => {
    if(otp.trim() === '' || otp.length !== 6 || isNaN(otp)){
      setOtpErr('OTP is required or invalid');
    }else{
      setOtpErr(false);
      let user = {
        mobile_number : addData.mobile,
        name : addData.name,
        email : addData.email,
        username : addData.username,
        password : addData.password,
        confirm_password : addData.cpassword,
        otp : otp,
      };
      let url = `${apiPath}users/signUp/`;
      axios.post(url, user, config).then((res)=>{
        setMsg(0)
        setTimeout(successMsg, 3000);
      }).catch((err)=>{
        setOtpErr(err.response?.data?.error || 'OTP verification failed. Please try again.');
        setShow(true);
      });
    }
  }
  function successMsg() {
    navigate("/login");
  }

  return (
    <Row>
    <Modal show={show} backdrop="static" keyboard={false} >
        <Modal.Header>
              <div
            style={{ cursor: "pointer", zoom: "1.5",position: 'absolute', right: "1%"}}
            onClick={handleClose}
            className="text-end"
              >
                <MdCancel />
            </div>
      </Modal.Header>
      {msg === 0?
      <>
      <Modal.Body>
        <Alert color="success">
          Registration successfully done
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
            <span className="input-group-text" style={{color:'#fd5c63'}} id="basic-addon1"><FaMobile></FaMobile></span>
            <input onChange={(e)=>{setOtp(e.target.value)}} name="otp" placeholder="OTP" type="text" maxLength="6" className="form-control" aria-label="OTP" aria-describedby="basic-addon1" />
          </div>
          <small id="otpHelp" className="text-danger">{otperr}</small>
        </FormGroup>
      </Modal.Body>
      <Modal.Footer>
      {resend===1?<p>Resend Otp in 0 : {minute}</p>:<Button className="btn" color="warning" type="submit" onClick={resentOTP}>Resend</Button>}
        <Button className="btn" color="danger" type="submit" onClick={otpVerify}>OK</Button>
      </Modal.Footer>
      </>
      }
    </Modal>
      <Col>
        {/* --------------------------------------------------------------------------------*/}
        {/* Card-1*/}
        {/* --------------------------------------------------------------------------------*/}
        <Card >
          <CardTitle tag="h6" className="border-bottom p-3 mb-0">
            <i className="bi bi-bell me-2"> </i>
            Please Signup
          </CardTitle>
          <CardBody>
            <Row className="mt-3">
              <Col sm="12" md={{offset: 2,size: 8}}>
                <div className={contentArea}>
                  <div className='gridmargin'>
                  {(err !== '') && <Alert color="danger">{err}</Alert>}
                   <Form onSubmit={save}>
                      <FormGroup>
                        <Label for="exampleName">Name</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{color:'#fd5c63'}} id="basic-addon1"><FaUserCircle></FaUserCircle></span>
                          <input onChange={inputName} name="name" placeholder="Name" type="text" className="form-control" aria-label="Name" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{nameerr}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleEmail">Email</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{color:'#fd5c63'}} id="basic-addon1"><FaMailBulk></FaMailBulk></span>
                          <input onChange={inputEmail} name="email" placeholder="Email" type="email" className="form-control" aria-label="Email" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{emailerr}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleMobile">Mobile</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{color:'#fd5c63'}} id="basic-addon1"><FaMobile></FaMobile></span>
                          <span className="input-group-text">+91</span>
                          <input onChange={inputMobile} name="mobile" placeholder="Mobile" type="text" maxLength="13" className="form-control" aria-label="Mobile" aria-describedby="basic-addon1" />
                        </div>

                        <small id="passwordHelp" className="text-danger">{mobileerr}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleUsername">Username</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{color:'#fd5c63'}} id="basic-addon1"><FaUser></FaUser></span>
                          <input onChange={inputUsername} name="username" placeholder="Username" type="text" className="form-control" aria-label="Username" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{usernameerr}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="examplePassword">Password</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{color:'#fd5c63'}} id="basic-addon1"><FaLock></FaLock></span>
                          <input onChange={inputPassword} name="password" placeholder="Password" type="password" className="form-control" aria-label="Password" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{passworderr}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleConfirmPassword">Confirm Password</Label>
                        <div className="input-group input-group">
                          <span className="input-group-text" style={{color:'#fd5c63'}} id="basic-addon1"><FaLock></FaLock></span>
                          <input onChange={inputCpassword} name="cpassword" placeholder="Confirm Password" type="password" className="form-control" aria-label="cpassword" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{cpassworderr}</small>
                      </FormGroup>
                      {loading?
                        <Button className="btn" color="danger" type="submit" disabled  >
                          Please wait...
                          <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                        </Button>
                        :
                        <Button className="btn" color="danger" type="submit">Sign Up</Button>
                      }
                    </Form>
                  </div>
                </div>
                <div className="button-group mt-4" style={{}}>
                    Already Registered?
                    <Link to="/login" className="btn rowlink">
                    Login Here
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
export default Register;
