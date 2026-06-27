import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Input, Label } from "reactstrap";
import '../../assets/css/header.css';
import { FaMapMarkerAlt } from "react-icons/fa";
import { contentArea, apiPath, config, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Modal from 'react-bootstrap/Modal';
import { writeCurrentWorkspace } from "../../utils/currentWorkspace";

const FARM_DRAFT_KEY = "chikooza-add-farm-draft";

const farmSteps = [
  { title: "Details", helper: "Farm name and sheds" },
  { title: "Location", helper: "Address, district and pincode" },
  { title: "Review", helper: "Check and save" },
];

const emptyFarmDraft = {
  farmname: '',
  address: '',
  cityorvillage: '',
  district: '',
  pincode: '',
  country: 0,
  numberofsheds: '',
  state: 0,
  coordinates: null,
};

const readFarmDraft = () => {
  try {
    return { ...emptyFarmDraft, ...JSON.parse(localStorage.getItem(FARM_DRAFT_KEY) || "{}") };
  } catch {
    return emptyFarmDraft;
  }
};

const resolveDefaultCountryId = (countries) => {
  const preferredCountry = countries.find((item) => String(item.name || "").toLowerCase() === "india");
  return String((preferredCountry || countries[0])?.public_id || "0");
};

const AddFarm = () => {
  const navigate = useNavigate();
  const [farmStep, setFarmStep] = useState(0);
  const [show, setShow] = useState(false);
  const [quardinatesModel, setQuardinatesModel] = useState(false);
  // U: OLD: let [quardinates, setQuardinates] = useState(...)
  // U: NEW: keep only the setter because the UI stores the selected coordinates in addData.
  let [, setQuardinates] = useState({ latitude: null, longitude: null, quardinates: null });
  let areaLocation = () => {
    navigator.geolocation.getCurrentPosition(function (position) {
      const coordinates = `${position.coords.latitude.toFixed(3)},${position.coords.longitude.toFixed(3)}`;
      setQuardinates({ latitude: position.coords.latitude.toFixed(3), longitude: position.coords.longitude.toFixed(3), quardinates: coordinates });
      // U: OLD: setAddData({ ...addData, coordinates: ... })
      // U: NEW: functional update avoids overwriting form edits with stale state.
      setAddData((currentData) => ({ ...currentData, coordinates }));
      setQuardinatesModel(false)
    });
  }
  let [country, setCountry] = useState([]);
  let [state, setState] = useState([]);
  let [loading, setLoading] = useState(false);
  let [addData, setAddData] = useState(readFarmDraft);
  let [farmnameError, setFarmnameError] = useState(null);
  let [addressError, setAddressError] = useState(null);
  let [cityorvillageError, setCityorvillageError] = useState(null);
  let [districtError, setDistrictError] = useState(null);
  let [pincodeError, setPincodeError] = useState(null);
  let [countryError, setCountryError] = useState(null);
  let [stateError, setStateError] = useState(null);
  let [numberofshedsError, setNumberofshedsError] = useState(null);
  let [err, setErr] = useState('');
  // U: OLD: let error = 0;
  // U: NEW: validation state is local to save() so stale renders cannot affect submission.

  useEffect(() => {
    localStorage.setItem(FARM_DRAFT_KEY, JSON.stringify(addData));
  }, [addData]);

  useEffect(() => {
    let url = `${apiPath}state/`;
    axios.get(url, config).then((res) => {
      setState(res.data.results);
    }).catch((err) => {
      handleUnauthorized(err, navigate);
    });
  }, [navigate])
  useEffect(() => {
    let url = `${apiPath}country/`;
    axios.get(url, config).then((res) => {
      const countries = res.data.results || [];
      setCountry(countries);
      setAddData((currentData) => {
        if (String(currentData.country || "0") !== "0" || countries.length === 0) {
          return currentData;
        }
        return { ...currentData, country: resolveDefaultCountryId(countries) };
      });
    }).catch((err) => {
      handleUnauthorized(err, navigate);
    });
  }, [navigate])
  let save = (e) => {
    return saveFarm(e, "manage");
  }

  const saveFarm = (e, nextAction = "manage") => {
    e.preventDefault();
    setLoading(false);
    setErr('');
    const identityValid = validateFarmIdentity();
    const locationValid = validateFarmLocation();
    if (!identityValid) {
      setFarmStep(0);
      return;
    }
    if (!locationValid) {
      setFarmStep(1);
      return;
    }
    if (identityValid && locationValid) {
      setLoading(true);
      let farm = {
        name: addData.farmname,
        address: addData.address,
        city: addData.cityorvillage,
        district: addData.district,
        state_public_id: addData.state,
        country_public_id: addData.country,
        pin: addData.pincode,
        lat_long: addData.coordinates,
        shed_count: addData.numberofsheds
      };
      let url = `${apiPath}farm/`;
      // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.post(url, farm, getAuthConfig()).then((res) => {
        const createdFarmId = res.data?.results?.public_id;
        if (createdFarmId) {
          writeCurrentWorkspace({ farmPublicId: createdFarmId, flockPublicId: "0", source: "add_farm_save" });
        }
        localStorage.removeItem(FARM_DRAFT_KEY);
        setLoading(false);
        setAddData({ ...emptyFarmDraft, country: resolveDefaultCountryId(country) });
        setFarmStep(0);
        setShow(true);
        setTimeout(() => {
          setShow(false);
          if (nextAction === "another") {
            return;
          }
          navigate("/managefarm");
        }, 1600);
      }).catch((err) => {
        setLoading(false);
        const apiError = err?.response?.data?.message || err?.response?.data?.error;
        setErr(apiError || 'Something went wrong. Please try again');
        handleUnauthorized(err, navigate);
      });
    }
  }
  let countryChange = (e) => {
    setAddData({ ...addData, country: e.target.value });
    // U: OLD: e.target.value.trim() === 0 compared a string to a number.
    e.target.value.trim() === "0" ? setCountryError('Please select country') : setCountryError('');
  }
  let stateChange = (e) => {
    setAddData({ ...addData, state: e.target.value });
    // U: OLD: e.target.value.trim() === 0 compared a string to a number.
    e.target.value.trim() === "0" ? setStateError('Please select state') : setStateError('');
  }
  let farmnameChange = (e) => {
    setAddData({ ...addData, farmname: e.target.value });
    e.target.value.trim() === '' ? setFarmnameError('Please enter name') : e.target.value.trim().length > 30 ? setFarmnameError('Farm name can be maximum 30 characters') : setFarmnameError('');
  }
  let addressChange = (e) => {
    setAddData({ ...addData, address: e.target.value });
    e.target.value.trim() === '' ? setAddressError('Please enter address') : setAddressError('');
  }
  let pincodeChange = (e) => {
    const value = e.target.value;
    if (!/^\d{0,6}$/.test(value)) {
      return;
    }
    setAddData({ ...addData, pincode: value });
    value.length !== 6 ? setPincodeError('Pincode must be 6 digits') : setPincodeError('');
  }

  let numberofshedsChange = (e) => {
    setAddData({ ...addData, numberofsheds: e.target.value });
    e.target.value.trim() === '' || Number(e.target.value.trim()) < 1 ? setNumberofshedsError('Please enter no of sheds') : setNumberofshedsError('');
  }
  let cityorvillageChange = (e) => {
    setAddData({ ...addData, cityorvillage: e.target.value });
    e.target.value.trim() === '' ? setCityorvillageError('Please enter city/Village name') : setCityorvillageError('');
  }
  let districtChange = (e) => {
    setAddData({ ...addData, district: e.target.value });
    e.target.value.trim() === '' ? setDistrictError('Please enter district') : setDistrictError('');
  }
  let closeAll = () => {
    navigate('/member')
  }
  const goNextStep = () => {
    // U: NEW: do not let users reach review/save until the current farm step is valid.
    if (farmStep === 0 && !validateFarmIdentity()) {
      return;
    }
    if (farmStep === 1 && !validateFarmLocation()) {
      return;
    }
    setFarmStep((currentStep) => Math.min(currentStep + 1, farmSteps.length - 1));
  };
  const goPreviousStep = () => {
    setFarmStep((currentStep) => Math.max(currentStep - 1, 0));
  };
  const goToStep = (targetStep) => {
    if (targetStep <= farmStep) {
      setFarmStep(targetStep);
      return;
    }
    // U: NEW: users can move backward freely, but cannot skip required farm fields.
    if (targetStep > 0 && !validateFarmIdentity()) {
      return;
    }
    if (targetStep > 1 && !validateFarmLocation()) {
      return;
    }
    setFarmStep(targetStep);
  };
  const validateFarmIdentity = () => {
    let valid = true;
    if (addData.farmname.trim() === '') { setFarmnameError('Please enter farm name'); valid = false; }
    else if (addData.farmname.trim().length > 30) { setFarmnameError('Farm name can be maximum 30 characters'); valid = false; }
    else { setFarmnameError(''); }
    if (addData.numberofsheds.trim() === '' || Number(addData.numberofsheds.trim()) < 1) { setNumberofshedsError('Enter at least 1 shed'); valid = false; } else { setNumberofshedsError(''); }
    return valid;
  };
  const validateFarmLocation = () => {
    let valid = true;
    if (addData.country === 0 || addData.country === "0") { setCountryError('Please select country'); valid = false; } else { setCountryError(''); }
    if (addData.state === 0 || addData.state === "0") { setStateError('Please select state'); valid = false; } else { setStateError(''); }
    if (addData.address.trim() === '') { setAddressError('Please enter address'); valid = false; } else { setAddressError(''); }
    if (addData.cityorvillage.trim() === '') { setCityorvillageError('Please enter city or village'); valid = false; } else { setCityorvillageError(''); }
    if (addData.district.trim() === '') { setDistrictError('Please enter district'); valid = false; } else { setDistrictError(''); }
    if (!/^\d{6}$/.test(addData.pincode.trim())) { setPincodeError('Pincode must be 6 digits'); valid = false; } else { setPincodeError(''); }
    return valid;
  };
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
                    <div className="form-stepper" aria-label="Farm setup steps">
                      {farmSteps.map((step, index) => (
                        <button
                          key={step.title}
                          type="button"
                          className={index === farmStep ? "is-active" : index < farmStep ? "is-complete" : ""}
                          onClick={() => goToStep(index)}
                        >
                          <span>{index + 1}</span>
                          <strong>{step.title}</strong>
                          <small>{step.helper}</small>
                        </button>
                      ))}
                    </div>
                    <Form onSubmit={save}>
                      {farmStep === 0 && (
                        <>
                          <FormGroup>
                            <Label for="exampleName">Farm Name</Label>
                            <div className="input-group input-group">
                              <input onChange={farmnameChange} value={addData.farmname} name="farmname" placeholder="Farm Name" type="text" maxLength="30" className="form-control" aria-label="Farm Name" aria-describedby="basic-addon1" />
                            </div>
                            <small id="passwordHelp" className="text-danger">{farmnameError}</small>
                          </FormGroup>
                          <FormGroup>
                            <Label for="exampleMobile">No. of sheds</Label>
                            <div className="input-group input-group">
                              <input onChange={numberofshedsChange} value={addData.numberofsheds} name="numberofsheds" placeholder="No. of sheds" type="number" className="form-control" aria-label="No. of sheds" aria-describedby="basic-addon1" />
                            </div>
                            <small id="passwordHelp" className="text-danger">{numberofshedsError}</small>
                          </FormGroup>
                        </>
                      )}
                      {farmStep === 1 && (
                        <>
                          <Row>
                            <Col md="6">
                              <FormGroup>
                                <Label for="farmAddress">Address</Label>
                                <div className="input-group input-group">
                                  <input id="farmAddress" onChange={addressChange} name="address" value={addData.address} placeholder="Farm address" type="text" className="form-control" aria-label="Address" aria-describedby="basic-addon1" />
                                </div>
                                <small id="passwordHelp" className="text-danger">{addressError}</small>
                              </FormGroup>
                            </Col>
                            <Col md="6">
                              <FormGroup>
                                <Label for="exampleCityOrVillage">City or Village</Label>
                                <div className="input-group input-group">
                                  <input onChange={cityorvillageChange} name="cityorvillage" value={addData.cityorvillage} placeholder="City or Village" type="text" className="form-control" aria-label="City or Village" aria-describedby="basic-addon1" />
                                </div>
                                <small id="passwordHelp" className="text-danger">{cityorvillageError}</small>
                              </FormGroup>
                            </Col>
                          </Row>
                          <Row>
                            <Col md="6">
                              <FormGroup>
                                <Label for="farmDistrict">District</Label>
                                <div className="input-group input-group">
                                  <input id="farmDistrict" onChange={districtChange} name="district" value={addData.district} placeholder="District" type="text" className="form-control" aria-label="District" aria-describedby="basic-addon1" />
                                </div>
                                <small id="passwordHelp" className="text-danger">{districtError}</small>
                              </FormGroup>
                            </Col>
                            <Col md="6">
                              <FormGroup>
                                <Label for="exampleMobile">Pincode</Label>
                                <div className="input-group input-group">
                                  <input onChange={pincodeChange} value={addData.pincode} name="pincode" placeholder="6 digit pincode" type="text" className="form-control" aria-label="Pincode" aria-describedby="basic-addon1" />
                                </div>
                                <small id="passwordHelp" className="text-danger">{pincodeError}</small>
                              </FormGroup>
                            </Col>
                          </Row>
                          <Row>
                            <Col md="6">
                              <FormGroup>
                                <Label for="country">Country</Label>
                                <Input id="country" onChange={countryChange} value={addData.country} name="country" type="select" disabled>
                                  <option value="0" disabled>Select Country</option>
                                  {
                                    country.map(item =>
                                      <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                    )
                                  }
                                </Input>
                                <small id="passwordHelp" className="text-danger">{countryError}</small>
                              </FormGroup>
                            </Col>
                            <Col md="6">
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
                            </Col>
                          </Row>
                          <FormGroup>
                            <Label for="exampleEmail">Coordinates</Label>
                            <div className="input-group input-group">
                              <input name="coordinates" value={addData.coordinates || ""} placeholder="Coordinates" className="form-control" aria-label="Username" aria-describedby="basic-addon1" disabled />
                              <span onClick={() => setQuardinatesModel(true)} className="input-group-text location" style={{ color: '#fd5c63' }} id="basic-addon1"><FaMapMarkerAlt></FaMapMarkerAlt></span>
                            </div>
                          </FormGroup>
                        </>
                      )}
                      {farmStep === 2 && (
                        <div className="form-review-card">
                          <span>Review farm</span>
                          <dl>
                            <div><dt>Name</dt><dd>{addData.farmname || "Not added"}</dd></div>
                            <div><dt>Sheds</dt><dd>{addData.numberofsheds || "Not added"}</dd></div>
                            <div><dt>Address</dt><dd>{addData.address || "Not added"}</dd></div>
                            <div><dt>City/Village</dt><dd>{addData.cityorvillage || "Not added"}</dd></div>
                            <div><dt>District</dt><dd>{addData.district || "Not added"}</dd></div>
                            <div><dt>Pincode</dt><dd>{addData.pincode || "Not added"}</dd></div>
                            <div><dt>Coordinates</dt><dd>{addData.coordinates || "Not added"}</dd></div>
                          </dl>
                        </div>
                      )}
                      <div className="form-wizard-actions">
                        {farmStep > 0 && (
                          <Button className="btn" color="secondary" type="button" onClick={goPreviousStep}>Back</Button>
                        )}
                        {farmStep < farmSteps.length - 1 && (
                          <Button className="btn" color="danger" type="button" onClick={goNextStep}>Next</Button>
                        )}
                        {farmStep === farmSteps.length - 1 && (
                          loading ?
                            <Button className="btn" color="danger" type="submit" disabled  >
                              Please wait...
                              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                            </Button>
                            :
                            <>
                              <Button className="btn" color="danger" type="submit">Save & review farms</Button>
                              <Button className="btn" color="secondary" outline type="button" onClick={(event) => saveFarm(event, "another")}>Save & add another farm</Button>
                            </>
                        )}
                        <Button className="btn" color="warning" type="button" onClick={closeAll} >Cancel</Button>
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
export default AddFarm;
