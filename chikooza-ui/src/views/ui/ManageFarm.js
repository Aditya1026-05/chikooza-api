import { Spinner, Alert, Row, Col, Card, CardTitle, CardBody, FormGroup, Label, Input, Button, Form } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, config, getAuthConfig, handleUnauthorized } from "../../Constants";
import { FaMapMarkerAlt } from "react-icons/fa";
import { useState, useEffect } from "react";
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Modal from 'react-bootstrap/Modal';

const ManageFarm = () => {

  const navigate = useNavigate();
  const [show, setShow] = useState(false);
  const [quardinatesModel, setQuardinatesModel] = useState(false);
  // U: The coordinate value is persisted in addData.lat_long; the local value itself was unused.
  let [, setQuardinates] = useState({ latitude: null, longitude: null, quardinates: null });
  let areaLocation = () => {
    navigator.geolocation.getCurrentPosition(function (position) {
      setQuardinates({ latitude: position.coords.latitude.toFixed(3), longitude: position.coords.longitude.toFixed(3), quardinates: `${position.coords.latitude.toFixed(3)},${position.coords.longitude.toFixed(3)}` });
      setCoordinatesError('');
      setAddData({ ...addData, lat_long: `${position.coords.latitude.toFixed(3)},${position.coords.longitude.toFixed(3)}` });
      setQuardinatesModel(false)
    });
  }
  let [country, setCountry] = useState([]);
  let [state, setState] = useState([]);
  let [loading, setLoading] = useState(false);
  let [addData, setAddData] = useState({});
  let [farmnameError, setFarmnameError] = useState(null);
  let [addressError, setAddressError] = useState(null);
  let [cityorvillageError, setCityorvillageError] = useState(null);
  let [pincodeError, setPincodeError] = useState(null);
  let [countryError, setCountryError] = useState(null);
  let [stateError, setStateError] = useState(null);
  let [numberofshedsError, setNumberofshedsError] = useState(null);
  let [coordinatesError, setCoordinatesError] = useState(null);
  let [err, setErr] = useState('');
  let error = 0;

  const [showForm, setShowForm] = useState(false);
  const [farm, setFarm] = useState([]);

  useEffect(() => {
    let url = `${apiPath}state/`;
    axios.get(url, config).then((res) => {
      setState(res.data.results);
    }).catch((err) => {
      //setState(res.data.results);
      handleUnauthorized(err, navigate);
    });
  }, [navigate])
  useEffect(() => {
    let url = `${apiPath}country/`;
    axios.get(url, config).then((res) => {
      setCountry(res.data.results);
    }).catch((err) => {
      //setCountry(res.data.results);
      handleUnauthorized(err, navigate);
    });
  }, [navigate])

  useEffect(() => {
    let url = `${apiPath}farm/`;
    // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
    // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
    axios.get(url, getAuthConfig()).then((res) => {
      if (res.data.results.length === 0) {
        setFarm([{ public_id: 0, name: 'No farm available' }]);
      } else {
        setFarm(res.data.results);
      }
    }).catch((err) => {
      setFarm([{ public_id: 0, name: 'No farm available' }]);
      handleUnauthorized(err, navigate);
    });
  }, [navigate])

  let save = (e) => {
    e.preventDefault();
    //console.log(e.target[4].value);
    //console.log(e.target[5].value);
    setLoading(false);
    if (String(addData.country_public_id) === "0") { setCountryError('Please select country'); error = 1; } else { setCountryError(''); }
    if (String(addData.state_public_id) === "0") { setStateError('Please select state'); error = 1; } else { setStateError(''); }
    if (addData.name.trim() === '') { setFarmnameError('Please enter name'); error = 1; } else { setFarmnameError(''); }
    if (addData.address.trim() === '') { setAddressError('Please enter address'); error = 1; } else { setAddressError(''); }
    if (addData.pin.trim() === '' || addData.pin.trim() < 1) { setPincodeError('Please enter pincode'); error = 1; } else { setPincodeError(''); }
    //if(addData.lat_long.trim() == ''){setCoordinatesError('Please enter coordinates');error = 1;}
    if (addData.shed_count === '' || addData.shed_count < 1) { setNumberofshedsError('Please enter no of sheds'); error = 1; } else { setNumberofshedsError(''); }
    if (addData.city.trim() === '') { setCityorvillageError('Please enter city/Village name'); error = 1; } else { setCityorvillageError(''); }
    if (e.target[0].value.trim() !== '' && e.target[1].value.trim() !== '' && e.target[2].value.trim() !== '' && e.target[3].value !== '' && e.target[6].value !== '')
      if (error === 0) {
        setLoading(true);
        let farmData = {
          name: addData.name,
          address: addData.address,
          city: addData.city,
          state_public_id: addData.state_public_id,
          country_public_id: addData.country_public_id,
          pin: addData.pin,
          lat_long: addData.lat_long,
          shed_count: addData.shed_count,
        };
        let url = `${apiPath}farm/${addData.public_id}/`;
        // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
        // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.patch(url, farmData, getAuthConfig()).then((res) => {
          //setErr('Farm Updated successfully');
          setShow(true);
          setLoading(false)
          setTimeout((() => {
            setShow(false);
            // U: Replaced find side effects with map so the callback always returns a value.
            setFarm((currentFarm) => currentFarm.map((item) => (
              item.public_id === addData.public_id ? { ...item, name: addData.name } : item
            )));
            setAddData({ ...addData, name: "", address: "", city: "", state_public_id: "", country_public_id: "", pin: "", lat_long: "", shed_count: "" })
            setShowForm(false)
            window.location.reload();

          }), 3000);
        }).catch((err) => {
          setLoading(false)
          setErr('Something went wrong. Please try again');
          handleUnauthorized(err, navigate);
        });
      }
  }
  let countryChange = (e) => {
    setAddData({ ...addData, country_public_id: e.target.value });
    e.target.value.trim() === "0" ? setCountryError('Please select country') : setCountryError('');
  }
  let stateChange = (e) => {
    setAddData({ ...addData, state_public_id: e.target.value });
    e.target.value.trim() === "0" ? setStateError('Please select state') : setStateError('');
  }
  let farmnameChange = (e) => {
    setAddData({ ...addData, name: e.target.value });
    e.target.value.trim() === '' ? setFarmnameError('Please enter name') : setFarmnameError('');
  }
  let addressChange = (e) => {
    setAddData({ ...addData, address: e.target.value });
    e.target.value.trim() === '' ? setAddressError('Please enter address') : setAddressError('');
  }
  let pincodeChange = (e) => {
    setAddData({ ...addData, pin: e.target.value });
    e.target.value.trim() === '' || e.target.value.trim() < 1 ? setPincodeError('Please enter pincode') : setPincodeError('');
  }
  // let coordinatesChange = (e) => {
  //   setAddData({...addData,lat_long:e.target.value});
  //   e.target.value.trim() == ''?setCoordinatesError('Please enter coordinates'):setCoordinatesError('');
  // }
  let numberofshedsChange = (e) => {
    setAddData({ ...addData, shed_count: e.target.value });
    e.target.value.trim() === '' || e.target.value.trim() < 1 ? setNumberofshedsError('Please enter no of sheds') : setNumberofshedsError('');
  }
  let cityorvillageChange = (e) => {
    setAddData({ ...addData, city: e.target.value });
    e.target.value.trim() === '' ? setCityorvillageError('Please enter city/Village name') : setCityorvillageError('');
  }
  let displayForm = (e) => {
    if (e.target.value !== "0") {
      let url = `${apiPath}farm/${e.target.value}/`;
      // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
      // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.get(url, getAuthConfig()).then((res) => {
        setAddData(res.data.results);
      }).catch((err) => {
        //setFarm(res.data.results);
        handleUnauthorized(err, navigate);
      });
      setShowForm(true);
    } else {
      setShowForm(false);
    }
  }
  let closeAll = () => {
    setAddData({ ...addData, name: "", address: "", city: "", state_public_id: "", country_public_id: "", pin: "", lat_long: "", shed_count: "" })
    setShowForm(false)
  }
  return (
    <>
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
              Updation successfully done
            </Alert>
            <Spinner animation="border" variant="primary" style={{ 'marginLeft': '45%' }} />
          </Modal.Body>
          <Modal.Footer>
          </Modal.Footer>
        </Modal>
        <Col>
          <Card className="pb-4">
            <CardTitle tag="h6" className="border-bottom p-3 mb-0">
              Manage Farm(s)
            </CardTitle>
            <CardBody>
              <Row className="mt-3">
                <Col sm="12" md={{ offset: 2, size: 8 }}>
                  <div className={contentArea}>
                    <div className='gridmargin'>
                      {(err !== '') && <Alert color="danger">{err}</Alert>}
                      <FormGroup>
                        <Label for="exampleSelect">Farm Name</Label>
                        <Input onChange={displayForm} id="farmSelect" defaultValue="0" name="farm" type="select">
                          <option value="0">Select Farm</option>
                          {
                            farm.map(item =>
                              <option key={item.public_id} value={item.public_id}>{item.name}</option>
                            )
                          }
                        </Input>
                      </FormGroup>
                      {
                        showForm &&
                        <Form onSubmit={save}>
                          <Alert color="secondary">Farm Detail</Alert>
                          <FormGroup>
                            <Label for="exampleName">Farm Name</Label>
                            <div className="input-group input-group">
                              <input onChange={farmnameChange} name="farmname" value={addData.name} placeholder="Farm Name" type="text" className="form-control" aria-label="Farm Name" aria-describedby="basic-addon1" />
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
                              <input onChange={cityorvillageChange} name="cityorvillage" value={addData.city} placeholder="City or Village" type="text" className="form-control" aria-label="City or Village" aria-describedby="basic-addon1" />
                            </div>
                            <small id="passwordHelp" className="text-danger">{cityorvillageError}</small>
                          </FormGroup>
                          <FormGroup>
                            <Label for="exampleMobile">Pincode</Label>
                            <div className="input-group input-group">
                              <input onChange={pincodeChange} name="pincode" value={addData.pin} placeholder="Pincode" type="text" className="form-control" aria-label="Pincode" aria-describedby="basic-addon1" />
                            </div>
                            <small id="passwordHelp" className="text-danger">{pincodeError}</small>
                          </FormGroup>
                          <FormGroup>
                            <Label for="country">Country</Label>
                            <Input id="country" onChange={countryChange} value={addData.country_public_id} name="country" type="select">
                              <option value="0" disabled>Select Country</option>
                              {
                                country.map(item => {
                                  return (
                                    <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                  )
                                }
                                )
                              }
                            </Input>
                            <small id="passwordHelp" className="text-danger">{countryError}</small>
                          </FormGroup>
                          <FormGroup>
                            <Label for="state">State</Label>
                            <Input id="state" onChange={stateChange} value={addData.state_public_id} name="state" type="select">
                              <option value="0" disabled={true}>Select State</option>
                              {
                                state.map(item => {
                                  return (
                                    <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                  )
                                }
                                )
                              }
                            </Input>
                            <small id="passwordHelp" className="text-danger">{stateError}</small>
                          </FormGroup>
                          <FormGroup>
                            <Label for="exampleMobile">No. of sheds</Label>
                            <div className="input-group input-group">
                              <input onChange={numberofshedsChange} value={addData.shed_count} name="numberofsheds" placeholder="No. of sheds" type="text" className="form-control" aria-label="No. of sheds" aria-describedby="basic-addon1" />
                            </div>
                            <small id="passwordHelp" className="text-danger">{numberofshedsError}</small>
                          </FormGroup>
                          <FormGroup>
                            <Label for="exampleEmail">Coordinates</Label>
                            <div className="input-group input-group">
                              <input name="coordinates" value={addData.lat_long} placeholder="Coordinates" className="form-control" aria-label="Username" aria-describedby="basic-addon1" disabled />
                              <span onClick={() => setQuardinatesModel(true)} className="input-group-text location" style={{ color: '#fd5c63' }} id="basic-addon1"><FaMapMarkerAlt></FaMapMarkerAlt></span>
                            </div>
                            <small id="passwordHelp" className="text-danger">{coordinatesError}</small>
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
                      }
                    </div>
                  </div>
                </Col>
              </Row>
            </CardBody>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default ManageFarm;
