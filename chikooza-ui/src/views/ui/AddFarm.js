import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Input, Label } from "reactstrap";
import '../../assets/css/header.css';
import { FaMapMarkerAlt } from "react-icons/fa";
import { contentArea, apiPath, config } from "../../Constants";
import { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Modal from 'react-bootstrap/Modal';

const AddFarm = () => {
  const navigate = useNavigate();
  const [show, setShow] = useState(false);
  const [quardinatesModel, setQuardinatesModel] = useState(false);
  let [quardinates, setQuardinates] = useState({ latitude: null, longitude: null, quardinates: null });
  let areaLocation = () => {
    navigator.geolocation.getCurrentPosition(function (position) {
      setQuardinates({ latitude: position.coords.latitude.toFixed(3), longitude: position.coords.longitude.toFixed(3), quardinates: `${position.coords.latitude.toFixed(3)},${position.coords.longitude.toFixed(3)}` });
      setAddData({ ...addData, coordinates: `${position.coords.latitude.toFixed(3)},${position.coords.longitude.toFixed(3)}` });
      setQuardinatesModel(false)
    });
  }
  let [country, setCountry] = useState([]);
  let [state, setState] = useState([]);
  let [loading, setLoading] = useState(false);
  let [addData, setAddData] = useState({ farmname: '', address: '', cityorvillage: '', pincode: '', country: 0, numberofsheds: '', state: 0, coordinates: null });
  let [farmnameError, setFarmnameError] = useState(null);
  let [addressError, setAddressError] = useState(null);
  let [cityorvillageError, setCityorvillageError] = useState(null);
  let [pincodeError, setPincodeError] = useState(null);
  let [countryError, setCountryError] = useState(null);
  let [stateError, setStateError] = useState(null);
  let [numberofshedsError, setNumberofshedsError] = useState(null);
  let [err, setErr] = useState('');
  let error = 0;

  useEffect(() => {
    let url = `${apiPath}state/`;
    axios.get(url, config).then((res) => {
      setState(res.data.results);
    }).catch((err) => {
      if (err.response.status === 401) {
        localStorage.clear();
        navigate("/login")
      }
    });
  }, [])
  useEffect(() => {
    let url = `${apiPath}country/`;
    axios.get(url, config).then((res) => {
      setCountry(res.data.results);
    }).catch((err) => {
      if (err.response.status === 401) {
        localStorage.clear();
        navigate("/login")
      }
    });
  }, [])
  let save = (e) => {
    e.preventDefault();
    setLoading(false);
    if (addData.country === 0) { setCountryError('Please select country'); error = 1; } else { setCountryError(''); }
    if (addData.state === 0) { setStateError('Please select state'); error = 1; } else { setStateError(''); }
    if (addData.farmname.trim() === '') { setFarmnameError('Please enter name'); error = 1; } else { setFarmnameError(''); }
    if (addData.address.trim() === '') { setAddressError('Please enter address'); error = 1; } else { setAddressError(''); }
    if (addData.pincode.trim() === '' || addData.pincode.trim() < 1) { setPincodeError('Please enter pincode'); error = 1; } else { setPincodeError(''); }
    if (addData.numberofsheds.trim() === '' || addData.numberofsheds.trim() < 1) { setNumberofshedsError('Please enter no of sheds'); error = 1; } else { setNumberofshedsError(''); }
    if (addData.cityorvillage.trim() === '') { setCityorvillageError('Please enter city/Village name'); error = 1; } else { setCityorvillageError(''); }
    if (error === 0) {
      setLoading(true);
      let farm = {
        name: addData.farmname,
        address: addData.address,
        city: addData.cityorvillage,
        state_public_id: addData.state,
        country_public_id: addData.country,
        pin: addData.pincode,
        lat_long: addData.coordinates,
        shed_count: addData.numberofsheds
      };
      let url = `${apiPath}farm/`;
      config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.post(url, farm, config).then((res) => {
        setLoading(false);
        setShow(true);
        setTimeout(successMsg, 3000);
      }).catch((err) => {
        setErr('Something went wrong. Please try again');
        console.log(err)
        if (err.response.status === 401) {
          localStorage.clear();
          navigate("/login")
        }
      });
    }
  }
  let countryChange = (e) => {
    setAddData({ ...addData, country: e.target.value });
    e.target.value.trim() === 0 ? setCountryError('Please select country') : setCountryError('');
  }
  let stateChange = (e) => {
    setAddData({ ...addData, state: e.target.value });
    e.target.value.trim() === 0 ? setStateError('Please select state') : setStateError('');
  }
  let farmnameChange = (e) => {
    setAddData({ ...addData, farmname: e.target.value });
    e.target.value.trim() === '' ? setFarmnameError('Please enter name') : setFarmnameError('');
  }
  let addressChange = (e) => {
    setAddData({ ...addData, address: e.target.value });
    e.target.value.trim() === '' ? setAddressError('Please enter address') : setAddressError('');
  }
  let pincodeChange = (e) => {
    setAddData({ ...addData, pincode: e.target.value });
    e.target.value.trim() === '' || e.target.value.trim() < 1 ? setPincodeError('Please enter pincode') : setPincodeError('');
  }

  let numberofshedsChange = (e) => {
    setAddData({ ...addData, numberofsheds: e.target.value });
    e.target.value.trim() === '' || e.target.value.trim() < 1 ? setNumberofshedsError('Please enter no of sheds') : setNumberofshedsError('');
  }
  let cityorvillageChange = (e) => {
    setAddData({ ...addData, cityorvillage: e.target.value });
    e.target.value.trim() === '' ? setCityorvillageError('Please enter city/Village name') : setCityorvillageError('');
  }
  function successMsg() {
    navigate("/managefarm");
  }
  let closeAll = () => {
    navigate('/member')
  }
  return (
    <Row>
      <Modal show={quardinatesModel} backdrop="static" keyboard={false} >
        <Modal.Header><h3>Attention!</h3></Modal.Header>
        <Modal.Body>
          <h3>Are you at the farm?</h3>
          <p>Use it only when you are at the farm.</p>
        </Modal.Body>
        <Modal.Footer>
          <Button className="btn" color="danger" onClick={areaLocation}>Yes</Button>
          <Button className="btn ml-4" color="warning" onClick={() => setQuardinatesModel(false)}>No</Button>
        </Modal.Footer>
      </Modal>
      <Modal show={show} backdrop="static" keyboard={false} >
        <Modal.Header>
        </Modal.Header>
        <Modal.Body>
          <Alert color="success">
            Farm created successfully
          </Alert>
        </Modal.Body>
        <Modal.Footer>
        </Modal.Footer>
      </Modal>
      <Col>
        <Card>
          <CardTitle tag="h6" className="border-bottom p-3 mb-0">
            New Farm
          </CardTitle>
          <CardBody>
            <Row className="mt-3">
              <Col sm="12" md={{ offset: 2, size: 8 }}>
                <div className={contentArea}>
                  <div className='gridmargin'>
                    {(err !== '') && <Alert color="danger">{err}</Alert>}
                    <Form onSubmit={save}>
                      <FormGroup>
                        <Label for="exampleName">Farm Name</Label>
                        <div className="input-group input-group">
                          <input onChange={farmnameChange} value={addData.farmname} name="farmname" placeholder="Farm Name" type="text" className="form-control" aria-label="Farm Name" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{farmnameError}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleEmail">Address</Label>
                        <div className="input-group input-group">
                          <input onChange={addressChange} name="address" value={addData.address} placeholder="Address" type="text" className="form-control" aria-label="Address" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{addressError}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleCityOrVillage">City or Village</Label>
                        <div className="input-group input-group">
                          <input onChange={cityorvillageChange} name="cityorvillage" value={addData.cityorvillage} placeholder="City or Village" type="text" className="form-control" aria-label="City or Village" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{cityorvillageError}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleMobile">Pincode</Label>
                        <div className="input-group input-group">
                          <input onChange={pincodeChange} value={addData.pincode} name="pincode" placeholder="Pincode" type="text" className="form-control" aria-label="Pincode" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{pincodeError}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="country">Country</Label>
                        <Input id="country" onChange={countryChange} value={addData.country} name="country" type="select">
                          <option value="0" disabled>Select Country</option>
                          {
                            country.map(item =>
                              <option key={item.public_id} value={item.public_id}>{item.name}</option>
                            )
                          }
                        </Input>
                        <small id="passwordHelp" className="text-danger">{countryError}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="state">State</Label>
                        <Input id="state" onChange={stateChange} value={addData.state} name="state" type="select">
                          <option value="0" disabled={true}>Select State</option>
                          {
                            state.map(item =>
                              <option key={item.public_id} value={item.public_id}>{item.name}</option>
                            )
                          }
                        </Input>
                        <small id="passwordHelp" className="text-danger">{stateError}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleMobile">No. of sheds</Label>
                        <div className="input-group input-group">
                          <input onChange={numberofshedsChange} value={addData.numberofsheds} name="numberofsheds" placeholder="No. of sheds" type="number" className="form-control" aria-label="No. of sheds" aria-describedby="basic-addon1" />
                        </div>
                        <small id="passwordHelp" className="text-danger">{numberofshedsError}</small>
                      </FormGroup>
                      <FormGroup>
                        <Label for="exampleEmail">Coordinates</Label>
                        <div className="input-group input-group">
                          <input name="coordinates" value={addData.coordinates} placeholder="Coordinates" className="form-control" aria-label="Username" aria-describedby="basic-addon1" disabled />
                          <span onClick={() => setQuardinatesModel(true)} className="input-group-text location" style={{ color: '#fd5c63' }} id="basic-addon1"><FaMapMarkerAlt></FaMapMarkerAlt></span>
                        </div>
                      </FormGroup>
                      {loading ?
                        <Button className="btn" color="danger" type="submit" disabled  >
                          Please wait...
                          <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                        </Button>
                        :
                        <Button className="btn" color="danger" type="submit">Save</Button>
                      }
                      <Button className="btn ml-4" color="warning" type="button" onClick={closeAll} >Cancel</Button>
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
export default AddFarm;
