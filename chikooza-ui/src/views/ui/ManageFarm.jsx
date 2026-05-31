import { Spinner, Alert, Row, Col, Card, CardTitle, CardBody, FormGroup, Label, Input, Button, Form } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, config, getAuthConfig, handleUnauthorized } from "../../Constants";
import { FaMapMarkerAlt } from "react-icons/fa";
import { useState, useEffect } from "react";
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Modal from 'react-bootstrap/Modal';

const MANAGE_FARM_DRAFT_KEY = "chikooza-manage-farm-draft";

const manageFarmSteps = [
  { title: "Select", helper: "Choose farm" },
  { title: "Details", helper: "Name and address" },
  { title: "Location", helper: "State, sheds, map" },
  { title: "Review", helper: "Check and save" },
];

const emptyManageFarmData = {
  public_id: "",
  name: "",
  address: "",
  city: "",
  state_public_id: "0",
  country_public_id: "0",
  pin: "",
  lat_long: "",
  shed_count: "",
};

const readManageFarmDraft = () => {
  try {
    const draft = JSON.parse(localStorage.getItem(MANAGE_FARM_DRAFT_KEY) || "{}");
    return {
      data: { ...emptyManageFarmData, ...(draft.data || {}) },
      selectedFarmId: draft.selectedFarmId || "0",
      farmStep: Number(draft.farmStep || 0),
    };
  } catch {
    return { data: emptyManageFarmData, selectedFarmId: "0", farmStep: 0 };
  }
};

const ManageFarm = () => {

  const [initialDraft] = useState(() => readManageFarmDraft());
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
  let [addData, setAddData] = useState(initialDraft.data);
  let [farmnameError, setFarmnameError] = useState(null);
  let [addressError, setAddressError] = useState(null);
  let [cityorvillageError, setCityorvillageError] = useState(null);
  let [pincodeError, setPincodeError] = useState(null);
  let [countryError, setCountryError] = useState(null);
  let [stateError, setStateError] = useState(null);
  let [numberofshedsError, setNumberofshedsError] = useState(null);
  let [coordinatesError, setCoordinatesError] = useState(null);
  let [err, setErr] = useState('');
  const [showForm, setShowForm] = useState(Boolean(initialDraft.data.public_id));
  const [farm, setFarm] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState(initialDraft.selectedFarmId);
  const [farmStep, setFarmStep] = useState(initialDraft.farmStep);
  const farmList = farm.filter((item) => String(item.public_id) !== "0");

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
    if (!showForm) {
      return;
    }
    // U: NEW: keep edit progress locally so farmers/admins do not lose long
    // U: farm edits while moving between steps.
    localStorage.setItem(MANAGE_FARM_DRAFT_KEY, JSON.stringify({
      data: addData,
      selectedFarmId,
      farmStep,
    }));
  }, [addData, selectedFarmId, farmStep, showForm]);

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

  const validateFarmDetails = () => {
    // U: OLD: validation depended on e.target indexes, which breaks when the
    // U: form layout changes. NEW: validate from named state fields.
    let valid = true;
    if (String(addData.country_public_id || "0") === "0") { setCountryError('Please select country'); valid = false; } else { setCountryError(''); }
    if (String(addData.state_public_id || "0") === "0") { setStateError('Please select state'); valid = false; } else { setStateError(''); }
    if ((addData.name || '').trim() === '') { setFarmnameError('Please enter farm name'); valid = false; }
    else if ((addData.name || '').trim().length > 30) { setFarmnameError('Farm name can be maximum 30 characters'); valid = false; }
    else { setFarmnameError(''); }
    if ((addData.address || '').trim() === '') { setAddressError('Please enter address'); valid = false; } else { setAddressError(''); }
    if ((addData.city || '').trim() === '') { setCityorvillageError('Please enter city/village name'); valid = false; } else { setCityorvillageError(''); }
    if (!/^\d{6}$/.test(String(addData.pin || ''))) { setPincodeError('Pincode must be 6 digits'); valid = false; } else { setPincodeError(''); }
    if (Number(addData.shed_count) <= 0) { setNumberofshedsError('Number of sheds must be greater than 0'); valid = false; } else { setNumberofshedsError(''); }
    return valid;
  };

  const goNextFarmStep = () => {
    if (farmStep === 0 && !showForm) {
      setErr('Select a farm first.');
      return;
    }
    if (farmStep === 1) {
      const basicValid = (addData.name || '').trim() !== '' && (addData.address || '').trim() !== '' && (addData.city || '').trim() !== '' && /^\d{6}$/.test(String(addData.pin || ''));
      if (!basicValid) {
        validateFarmDetails();
        return;
      }
    }
    if (farmStep === 2 && !validateFarmDetails()) {
      return;
    }
    setErr('');
    setFarmStep((currentStep) => Math.min(currentStep + 1, manageFarmSteps.length - 1));
  };

  const goPreviousFarmStep = () => {
    setFarmStep((currentStep) => Math.max(currentStep - 1, 0));
  };

  let save = (e) => {
    e.preventDefault();
    setLoading(false);
    if (!validateFarmDetails()) {
      setErr('Validation error. Please check all required fields.');
      setFarmStep(1);
      return;
    }
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
          setShow(true);
          setLoading(false)
          setTimeout((() => {
            setShow(false);
            // U: Replaced find side effects with map so the callback always returns a value.
            setFarm((currentFarm) => currentFarm.map((item) => (
              String(item.public_id) === String(addData.public_id) ? { ...item, ...addData, name: addData.name } : item
            )));
            setAddData(emptyManageFarmData)
            setSelectedFarmId("0");
            setShowForm(false);
            setFarmStep(0);
            localStorage.removeItem(MANAGE_FARM_DRAFT_KEY);

          }), 3000);
        }).catch((err) => {
          setLoading(false)
          setErr('Something went wrong. Please try again');
          handleUnauthorized(err, navigate);
        });
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
    setAddData({ ...addData, pin: value });
    value.length !== 6 ? setPincodeError('Pincode must be 6 digits') : setPincodeError('');
  }
  // let coordinatesChange = (e) => {
  //   setAddData({...addData,lat_long:e.target.value});
  //   e.target.value.trim() == ''?setCoordinatesError('Please enter coordinates'):setCoordinatesError('');
  // }
  let numberofshedsChange = (e) => {
    setAddData({ ...addData, shed_count: e.target.value });
    Number(e.target.value) <= 0 ? setNumberofshedsError('Number of sheds must be greater than 0') : setNumberofshedsError('');
  }
  let cityorvillageChange = (e) => {
    setAddData({ ...addData, city: e.target.value });
    e.target.value.trim() === '' ? setCityorvillageError('Please enter city/Village name') : setCityorvillageError('');
  }
  const loadFarmForEdit = (farmId) => {
    if (String(farmId) !== "0") {
      setSelectedFarmId(String(farmId));
      let url = `${apiPath}farm/${farmId}/`;
      // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
      // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.get(url, getAuthConfig()).then((res) => {
        setAddData({ ...emptyManageFarmData, ...res.data.results });
        setFarmStep(1);
        setErr('');
      }).catch((err) => {
        //setFarm(res.data.results);
        handleUnauthorized(err, navigate);
      });
      setShowForm(true);
    } else {
      setSelectedFarmId("0");
      setShowForm(false);
      setFarmStep(0);
    }
  };
  let displayForm = (e) => {
    loadFarmForEdit(e.target.value);
  }
  let closeAll = () => {
    setAddData(emptyManageFarmData)
    setSelectedFarmId("0");
    setShowForm(false)
    setFarmStep(0);
    localStorage.removeItem(MANAGE_FARM_DRAFT_KEY);
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
                      <div className="record-review-toolbar">
                        <div>
                          <span>Saved farms</span>
                          <strong>{farmList.length} farm{farmList.length === 1 ? "" : "s"} in this account</strong>
                          <p>Review an existing farm or add another location before creating more flocks.</p>
                        </div>
                        <Button color="danger" type="button" onClick={() => navigate("/addfarm")}>Add another farm</Button>
                      </div>
                      {farmList.length > 0 ? (
                        <div className="record-review-grid" aria-label="Saved farms">
                          {farmList.map((item) => (
                            <article key={item.public_id} className={String(item.public_id) === selectedFarmId ? "is-selected" : ""}>
                              <div>
                                <span>Farm</span>
                                <strong>{item.name}</strong>
                                <p>{[item.city, item.state_name].filter(Boolean).join(", ") || "Location not added"}</p>
                              </div>
                              <dl>
                                <div><dt>Sheds</dt><dd>{item.shed_count ?? "Not added"}</dd></div>
                                <div><dt>Status</dt><dd>{item.status ? "Active" : "Inactive"}</dd></div>
                                <div><dt>Pin</dt><dd>{item.pin || "Not added"}</dd></div>
                              </dl>
                              <Button color="danger" outline type="button" onClick={() => loadFarmForEdit(item.public_id)}>Review / edit</Button>
                            </article>
                          ))}
                        </div>
                      ) : (
                        <div className="record-review-empty">
                          <strong>No farms saved yet.</strong>
                          <p>Add the first farm before creating flocks, purchases, sales, reports, and Farmer AI answers.</p>
                          <Button color="danger" type="button" onClick={() => navigate("/addfarm")}>Add first farm</Button>
                        </div>
                      )}
                      <div className="form-stepper" aria-label="Manage farm steps">
                        {manageFarmSteps.map((step, index) => (
                          <button
                            key={step.title}
                            type="button"
                            className={index === farmStep ? "is-active" : index < farmStep ? "is-complete" : ""}
                            onClick={() => {
                              if (index === 0 || showForm) {
                                setFarmStep(index);
                              }
                            }}
                          >
                            <span>{index + 1}</span>
                            <strong>{step.title}</strong>
                            <small>{step.helper}</small>
                          </button>
                        ))}
                      </div>
                      {(!showForm || farmStep === 0) && (
                        <FormGroup>
                          <Label for="exampleSelect">Farm Name</Label>
                          <Input onChange={displayForm} id="farmSelect" value={selectedFarmId} name="farm" type="select">
                            <option value="0">Select Farm</option>
                            {
                              farm.map(item =>
                                <option key={item.public_id} value={item.public_id}>{item.name}</option>
                              )
                            }
                          </Input>
                        </FormGroup>
                      )}
                      {
                        showForm &&
                        <Form onSubmit={save}>
                          {farmStep === 1 && (
                            <>
                              <Alert color="secondary">Farm Detail</Alert>
                              <FormGroup>
                                <Label for="exampleName">Farm Name</Label>
                                <div className="input-group input-group">
                                  <input onChange={farmnameChange} name="farmname" value={addData.name || ""} placeholder="Farm Name" type="text" maxLength="30" className="form-control" aria-label="Farm Name" aria-describedby="basic-addon1" />
                                </div>
                                <small className="text-muted">{(addData.name || "").length}/30 characters</small>
                                <small id="passwordHelp" className="text-danger">{farmnameError}</small>
                              </FormGroup>
                              <FormGroup>
                                <Label for="exampleEmail">Address</Label>
                                <div className="input-group input-group">
                                  <input onChange={addressChange} name="address" value={addData.address || ""} placeholder="Address" type="text" className="form-control" aria-label="Address" aria-describedby="basic-addon1" />
                                </div>
                                <small id="passwordHelp" className="text-danger">{addressError}</small>
                              </FormGroup>
                              <FormGroup>
                                <Label for="exampleCityOrVillage">City or Village</Label>
                                <div className="input-group input-group">
                                  <input onChange={cityorvillageChange} name="cityorvillage" value={addData.city || ""} placeholder="City or Village" type="text" className="form-control" aria-label="City or Village" aria-describedby="basic-addon1" />
                                </div>
                                <small id="passwordHelp" className="text-danger">{cityorvillageError}</small>
                              </FormGroup>
                              <FormGroup>
                                <Label for="exampleMobile">Pincode</Label>
                                <div className="input-group input-group">
                                  <input onChange={pincodeChange} name="pincode" value={addData.pin || ""} placeholder="Pincode" type="text" className="form-control" aria-label="Pincode" aria-describedby="basic-addon1" />
                                </div>
                                <small id="passwordHelp" className="text-danger">{pincodeError}</small>
                              </FormGroup>
                            </>
                          )}
                          {farmStep === 2 && (
                            <>
                              <FormGroup>
                                <Label for="country">Country</Label>
                                <Input id="country" onChange={countryChange} value={addData.country_public_id || "0"} name="country" type="select">
                                  <option value="0" disabled>Select Country</option>
                                  {country.map(item => (
                                    <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                  ))}
                                </Input>
                                <small id="passwordHelp" className="text-danger">{countryError}</small>
                              </FormGroup>
                              <FormGroup>
                                <Label for="state">State</Label>
                                <Input id="state" onChange={stateChange} value={addData.state_public_id || "0"} name="state" type="select">
                                  <option value="0" disabled={true}>Select State</option>
                                  {state.map(item => (
                                    <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                  ))}
                                </Input>
                                <small id="passwordHelp" className="text-danger">{stateError}</small>
                              </FormGroup>
                              <FormGroup>
                                <Label for="exampleMobile">No. of sheds</Label>
                                <div className="input-group input-group">
                                  <input onChange={numberofshedsChange} value={addData.shed_count || ""} name="numberofsheds" placeholder="No. of sheds" type="number" min="1" className="form-control" aria-label="No. of sheds" aria-describedby="basic-addon1" />
                                </div>
                                <small id="passwordHelp" className="text-danger">{numberofshedsError}</small>
                              </FormGroup>
                              <FormGroup>
                                <Label for="exampleEmail">Coordinates</Label>
                                <div className="input-group input-group">
                                  <input name="coordinates" value={addData.lat_long || ""} placeholder="Coordinates" className="form-control" aria-label="Username" aria-describedby="basic-addon1" disabled />
                                  <span onClick={() => setQuardinatesModel(true)} className="input-group-text location" style={{ color: '#fd5c63' }} id="basic-addon1"><FaMapMarkerAlt></FaMapMarkerAlt></span>
                                </div>
                                <small id="passwordHelp" className="text-danger">{coordinatesError}</small>
                              </FormGroup>
                            </>
                          )}
                          {farmStep === 3 && (
                            <div className="form-review-card">
                              <span>Review farm update</span>
                              <dl>
                                <div><dt>Name</dt><dd>{addData.name || "Missing"}</dd></div>
                                <div><dt>Address</dt><dd>{addData.address || "Missing"}</dd></div>
                                <div><dt>City/Village</dt><dd>{addData.city || "Missing"}</dd></div>
                                <div><dt>Pincode</dt><dd>{addData.pin || "Missing"}</dd></div>
                                <div><dt>Sheds</dt><dd>{addData.shed_count || "Missing"}</dd></div>
                                <div><dt>Coordinates</dt><dd>{addData.lat_long || "Not set"}</dd></div>
                              </dl>
                            </div>
                          )}
                          <div className="form-wizard-actions">
                            {farmStep > 0 && <Button type="button" color="secondary" outline onClick={goPreviousFarmStep}>Back</Button>}
                            {farmStep < manageFarmSteps.length - 1 && <Button type="button" color="danger" onClick={goNextFarmStep}>Next</Button>}
                            {farmStep === manageFarmSteps.length - 1 && (loading ?
                              <Button className="btn" color="danger" type="submit" disabled>
                                Please wait...
                                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                              </Button>
                              :
                              <Button className="btn" color="danger" type="submit">Save</Button>
                            )}
                            <Button className="btn" color="secondary" outline type="button" onClick={closeAll}>Cancel</Button>
                          </div>
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
