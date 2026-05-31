import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
import Modal from 'react-bootstrap/Modal';
import { Link, useNavigate } from 'react-router-dom';
import moment from "moment";

const FLOCK_DRAFT_KEY = "chikooza-add-flock-draft";

const flockSteps = [
    { title: "Farm", helper: "Choose where this batch belongs" },
    { title: "Batch", helper: "Name, hatch date and bird count" },
    { title: "Source", helper: "Breed, hatchery and cost" },
    { title: "Systems", helper: "Shed, feed and drinking setup" },
    { title: "Review", helper: "Check and save flock" },
];

const emptyFlockDraft = {
    hatch_date: '',
    flock_size: null,
    actual_birds: null,
    flock_name: '',
    breed_public_id: null,
    hatchery_name: '',
    chick_weight: null,
    integration: null,
    integrator_public_id: null,
    chick_cost: null,
    ec_shed: null,
    feed_sys: null,
    drinking_sys: null,
    farm_public_id: null
};

const readFlockDraft = () => {
    try {
        return { ...emptyFlockDraft, ...JSON.parse(localStorage.getItem(FLOCK_DRAFT_KEY) || "{}") };
    } catch {
        return emptyFlockDraft;
    }
};

const AddFlock = () => {
    let [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const [flockStep, setFlockStep] = useState(0);
    let [err, setErr] = useState('');
    const [show, setShow] = useState(false);
    let [farms, setFarms] = useState([]);
    let [breeds, setBreeds] = useState([]);
    let [intgcom, setIntgcom] = useState([]);
    const [existingFlocks, setExistingFlocks] = useState([]);
    const [flockReviewLoading, setFlockReviewLoading] = useState(false);

    var hatchdate = moment();
    var currentDate = hatchdate.format('YYYY-MM-DD');

    useEffect(() => {
        let url = `${apiPath}farm/`;
        // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, getAuthConfig()).then((res) => {
            if (res.data.results.length === 0) {
                setFarms([{ public_id: 0, name: 'No farm available' }]);
            } else {
                setFarms(res.data.results);
            }
        }).catch((err) => {
            setFarms([{ public_id: 0, name: 'No farm available' }]);
            handleUnauthorized(err, navigate);
        });
    }, [navigate])
    useEffect(() => {
        let url = `${apiPath}breeds/`;
        // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, getAuthConfig()).then((res) => {
            setBreeds(res.data.results);
        }).catch((err) => {
            handleUnauthorized(err, navigate);
        });
    }, [navigate])
    useEffect(() => {
        let url = `${apiPath}integrators/`;
        // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, getAuthConfig()).then((res) => {
            setIntgcom(res.data.results);
        }).catch((err) => {
            //setIntgcom(res.data.results);
            handleUnauthorized(err, navigate);
        });
    }, [navigate])
    let [addData, setAddData] = useState(readFlockDraft);
    let [hatch_dateerr, setHatch_dateerr] = useState(null);
    let [flock_sizeerr, setFlock_sizeerr] = useState(null);
    let [flock_nameerr, setFlock_nameerr] = useState(null);
    let [actual_birdserr, setActual_birdserr] = useState(null);
    let [hatchery_nameerr, setHatchery_nameerr] = useState(null);
    let [breed_public_iderr, setBreed_public_iderr] = useState(null);
    let [chick_weighterr, setChick_weighterr] = useState(null);
    let [integrationerr, setIntegrationerr] = useState(null);
    let [chick_costerr, setChick_costerr] = useState(null);
    let [integrator_public_iderr, setIntegrator_public_iderr] = useState(null);
    let [ec_shederr, setEc_shederr] = useState(null);
    let [feed_syserr, setFeed_syserr] = useState(null);
    let [drinking_syserr, setDrinking_syserr] = useState(null);
    let [farm_public_iderr, setFarm_public_iderr] = useState(null);
    let [integration, setIntegration] = useState(2);

    useEffect(() => {
        localStorage.setItem(FLOCK_DRAFT_KEY, JSON.stringify(addData));
    }, [addData]);

    const hasFarmPrerequisite = farms.some((farm) => String(farm.public_id) !== "0");
    const hasSelectedFarm = addData.farm_public_id && String(addData.farm_public_id) !== "0";
    const selectedFarmRecord = farms.find((farm) => String(farm.public_id) === String(addData.farm_public_id));

    const loadExistingFlocks = (farmPublicId) => {
        if (!farmPublicId || String(farmPublicId) === "0") {
            setExistingFlocks([]);
            return;
        }

        setFlockReviewLoading(true);
        axios.get(`${apiPath}flocks/${farmPublicId}/`, getAuthConfig()).then((res) => {
            if (res.data.results.total_records === 0) {
                setExistingFlocks([]);
            } else {
                setExistingFlocks(res.data.results.flock_list || []);
            }
        }).catch((err) => {
            setExistingFlocks([]);
            handleUnauthorized(err, navigate);
        }).finally(() => {
            setFlockReviewLoading(false);
        });
    };

    useEffect(() => {
        // U: NEW: if a saved draft already has a farm selected, show the saved
        // U: flocks under that farm before the farmer creates another one.
        if (hasSelectedFarm) {
            loadExistingFlocks(addData.farm_public_id);
        }
    }, [navigate]);

    useEffect(() => {
        if (String(addData.integration) === "1") {
            setIntegration(1);
        } else if (String(addData.integration) === "2") {
            setIntegration(2);
        }
    }, [addData.integration]);

    const save = (e) => {
        e.preventDefault();
        setLoading(false);
        const validations = [
            validateFarmStep(),
            validateBatchStep(),
            validateSourceStep(),
            validateSystemsStep(),
        ];
        const firstInvalidStep = validations.findIndex((isValid) => !isValid);
        if (firstInvalidStep !== -1) {
            setFlockStep(firstInvalidStep);
            return;
        }
        if (validations.every(Boolean)) {
            setLoading(true)
            // if (addData.integration === 1) {
            //     addData.integration = true;
            //     //addData.chick_cost=1;
            // } else {
            //     addData.integration = false;
            //     //addData.integrator_public_id=1;
            // }
            // U: OLD: save() mutated addData.ec_shed and treated boolean true as false.
            const ecShed = addData.ec_shed === true || addData.ec_shed === "true" || addData.ec_shed === 1 || addData.ec_shed === "1";
            let flock = {
                hatch_date: addData.hatch_date,
                flock_size: addData.flock_size,
                actual_birds: addData.actual_birds,
                flock_name: addData.flock_name,
                breed_public_id: addData.breed_public_id,
                hatchery_name: addData.hatchery_name,
                chick_weight: addData.chick_weight,
                // integration: addData.integration,
                // integrator_public_id: addData.integrator_public_id,
                // chick_cost: addData.chick_cost,
                ec_shed: ecShed,
                feed_sys: addData.feed_sys,
                drinking_sys: addData.drinking_sys,
                farm_public_id: addData.farm_public_id
            };
            if (String(addData.integration) === "1") {
                flock.integration = true;
                flock.integrator_public_id = addData.integrator_public_id;
            } else {
                flock.integration = false;
                flock.chick_cost = addData.chick_cost;
            }
            let url = `${apiPath}flocks/`;
            // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.post(url, flock, getAuthConfig()).then(() => {
                localStorage.removeItem(FLOCK_DRAFT_KEY);
                //setErr('Form created successfully');
                setShow(true);
                setLoading(false);
                setTimeout(successMsg, 3000);
            }).catch((err) => {
                setErr(err?.response?.data?.message || 'Something went wrong. Please try again');
                handleUnauthorized(err, navigate);
            });
        }
    }
    let changeFarm = (e) => {
        setAddData({ ...addData, farm_public_id: e.target.value });
        // U: OLD: e.target.value === 0 compared a string to a number.
        e.target.value === "0" ? setFarm_public_iderr('Please select farm') : setFarm_public_iderr('');
        loadExistingFlocks(e.target.value);
    }
    let changeBreed = (e) => {
        setAddData({ ...addData, breed_public_id: e.target.value });
        e.target.value === "0" ? setBreed_public_iderr('Please select Breed') : setBreed_public_iderr('');
    }
    let changeIntrigation = (e) => {
        setAddData({ ...addData, integration: e.target.value });
        e.target.value === "0" ? setIntegrationerr('Please select integration') : setIntegrationerr('');
        if (e.target.value === "1") {
            setIntegration(1)
        } else {
            setIntegration(2)
        }
    }
    let changeActualbirds = (e) => {
        setAddData({ ...addData, actual_birds: e.target.value });
        e.target.value <= 0 ? setActual_birdserr('Flock Actual birds count is required') : setActual_birdserr('');
    }
    let changeHatchery = (e) => {
        setAddData({ ...addData, hatchery_name: e.target.value });
        e.target.value.trim() === '' ? setHatchery_nameerr('Hatchery name is required') : setHatchery_nameerr('');
    }
    let changeDayoneweight = (e) => {
        setAddData({ ...addData, chick_weight: e.target.value });
        e.target.value <= 0 ? setChick_weighterr('Day one weight is required') : setChick_weighterr('');
    }
    let changeChickcost = (e) => {
        if (addData.integration !== 1) {
            setAddData({ ...addData, chick_cost: e.target.value });
            e.target.value <= 0 ? setChick_costerr('Chicks Cost is required') : setChick_costerr('');
        }
    }
    let changeEcshed = (e) => {
        const value = e.target.value === "true"; // Convert string "true" or "false" to boolean
        setAddData({ ...addData, ec_shed: value });
        setEc_shederr(''); // Clear the error message
    };

    let changeDrinkingsys = (e) => {
        setAddData({ ...addData, drinking_sys: e.target.value });
        e.target.value === "0" ? setDrinking_syserr('Please select Drinking System') : setDrinking_syserr('');
    }
    let changeFeedsys = (e) => {
        setAddData({ ...addData, feed_sys: e.target.value });
        e.target.value === "0" ? setFeed_syserr('Please select feed system') : setFeed_syserr('');
    }
    let changeFlockname = (e) => {
        setAddData({ ...addData, flock_name: e.target.value });
        e.target.value.trim() === '' ? setFlock_nameerr('Flock name is required') : setFlock_nameerr('');
    }
    let changeHatchdate = (e) => {
        setAddData({ ...addData, hatch_date: e.target.value });
        e.target.value === '' ? setHatch_dateerr('Hatch date is required') : setHatch_dateerr('');
    }
    let changeFlocksize = (e) => {
        setAddData({ ...addData, flock_size: e.target.value });
        e.target.value <= 0 ? setFlock_sizeerr('Flock size is required') : setFlock_sizeerr('');
    }
    let changeIntco = (e) => {
        if (integration === 1) {
            setAddData({ ...addData, integrator_public_id: e.target.value });
            e.target.value === "0" ? setIntegrator_public_iderr('Please select Intrigation company') : setIntegrator_public_iderr('');
        }
    }
    function successMsg() {
        navigate("/manageflock");
    }
    let closeAll = () => {
        navigate('/member');
    }
    const goNextStep = () => {
        // U: NEW: keep the flock wizard sequential so farmers do not save half-filled batches.
        const validators = [validateFarmStep, validateBatchStep, validateSourceStep, validateSystemsStep];
        if (validators[flockStep] && !validators[flockStep]()) {
            return;
        }
        setFlockStep((currentStep) => Math.min(currentStep + 1, flockSteps.length - 1));
    };
    const goPreviousStep = () => {
        setFlockStep((currentStep) => Math.max(currentStep - 1, 0));
    };
    const validateFarmStep = () => {
        if (!hasFarmPrerequisite) {
            setFarm_public_iderr('Add a farm first, then create a flock.');
            return false;
        }
        if (addData.farm_public_id === 0 || addData.farm_public_id === "0" || addData.farm_public_id === null) { setFarm_public_iderr('Please select farm'); return false; }
        setFarm_public_iderr('');
        return true;
    };
    const validateBatchStep = () => {
        let valid = true;
        if (addData.hatch_date.trim() === '') { setHatch_dateerr('Hatch date is required'); valid = false; } else { setHatch_dateerr(''); }
        if (addData.flock_name.trim() === '') { setFlock_nameerr('Flock name is required'); valid = false; } else { setFlock_nameerr(''); }
        if (Number(addData.flock_size) <= 0 || addData.flock_size === null) { setFlock_sizeerr('Flock size is required'); valid = false; } else { setFlock_sizeerr(''); }
        if (Number(addData.actual_birds) <= 0 || addData.actual_birds === null) { setActual_birdserr('Actual bird count is required'); valid = false; } else { setActual_birdserr(''); }
        if (Number(addData.actual_birds) > Number(addData.flock_size)) { setActual_birdserr('Actual birds cannot be more than flock size'); valid = false; }
        return valid;
    };
    const validateSourceStep = () => {
        let valid = true;
        if (addData.breed_public_id === 0 || addData.breed_public_id === "0" || addData.breed_public_id === null) { setBreed_public_iderr('Please select breed'); valid = false; } else { setBreed_public_iderr(''); }
        if (addData.hatchery_name.trim() === '') { setHatchery_nameerr('Hatchery name is required'); valid = false; } else { setHatchery_nameerr(''); }
        if (addData.integration === 0 || addData.integration === "0" || addData.integration === null) {
            setIntegrationerr('Please select integration'); valid = false;
        } else {
            setIntegrationerr('');
            if (String(addData.integration) === "1") {
                if (addData.integrator_public_id === 0 || addData.integrator_public_id === "0" || addData.integrator_public_id === null) { setIntegrator_public_iderr('Please select integration company'); valid = false; } else { setIntegrator_public_iderr(''); }
                setChick_costerr('');
            } else if (String(addData.integration) === "2") {
                if (Number(addData.chick_cost) <= 0 || addData.chick_cost === null) { setChick_costerr('Chicks cost is required'); valid = false; } else { setChick_costerr(''); }
                setIntegrator_public_iderr('');
            }
        }
        return valid;
    };
    const validateSystemsStep = () => {
        let valid = true;
        if (Number(addData.chick_weight) <= 0 || addData.chick_weight === null) { setChick_weighterr('Day one weight is required'); valid = false; } else { setChick_weighterr(''); }
        if (addData.ec_shed === 0 || addData.ec_shed === "0" || addData.ec_shed === null) { setEc_shederr('Please select EC shed'); valid = false; } else { setEc_shederr(''); }
        if (addData.feed_sys === 0 || addData.feed_sys === "0" || addData.feed_sys === null) { setFeed_syserr('Please select feed system'); valid = false; } else { setFeed_syserr(''); }
        if (addData.drinking_sys === 0 || addData.drinking_sys === "0" || addData.drinking_sys === null) { setDrinking_syserr('Please select drinking system'); valid = false; } else { setDrinking_syserr(''); }
        return valid;
    };
    return (
        <Row>
            <Modal show={show} backdrop="static" keyboard={false} >
                <Modal.Header>
                </Modal.Header>
                <Modal.Body>
                    <Alert color="success">
                        Flock created successfully
                    </Alert>
                </Modal.Body>
                <Modal.Footer>
                </Modal.Footer>
            </Modal>
            <Col>
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-1*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card className="pb-4">
                    <CardTitle tag="h6" className="border-bottom p-3 mb-0">New Flock</CardTitle>
                    <CardBody>
                        <Row className="mt-3">
                            <Col sm="12" md={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        {(err !== '') && <Alert color="danger">{err}</Alert>}
                                        {!hasFarmPrerequisite && (
                                            <div className="form-prerequisite-card">
                                                <span>Farm required</span>
                                                <p>Create a farm before adding a flock. Flocks, daily data, purchases, sales, reports, and Farmer AI answers all depend on a farm.</p>
                                                <Link to="/addfarm">Add farm first</Link>
                                            </div>
                                        )}
                                        <Form onSubmit={save}>
                                            <div className="form-stepper" aria-label="Flock setup steps">
                                                {flockSteps.map((step, index) => (
                                                    <button
                                                        key={step.title}
                                                        type="button"
                                                        className={index === flockStep ? "is-active" : index < flockStep ? "is-complete" : ""}
                                                        onClick={() => setFlockStep(index)}
                                                    >
                                                        <span>{index + 1}</span>
                                                        <strong>{step.title}</strong>
                                                        <small>{step.helper}</small>
                                                    </button>
                                                ))}
                                            </div>
                                            {flockStep === 0 && (
                                                <>
                                                    <FormGroup>
                                                        <Label for="farmselect">Select Farm</Label>
                                                        <div className="input-group">
                                                            <Input onChange={changeFarm} id="farmSelect" value={addData.farm_public_id || "0"} name="farm" type="select">
                                                                <option value="0" disabled>Select Farm</option>
                                                                {
                                                                    farms.map((item) => {
                                                                        return (
                                                                            <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                                                        )
                                                                    })
                                                                }
                                                            </Input>
                                                        </div>
                                                        <small className="text-danger">{farm_public_iderr}</small>
                                                    </FormGroup>
                                                    {hasSelectedFarm && (
                                                        <>
                                                            <div className="record-review-toolbar record-review-toolbar--compact">
                                                                <div>
                                                                    <span>Existing flocks</span>
                                                                    <strong>{selectedFarmRecord?.name || "Selected farm"}</strong>
                                                                    <p>{flockReviewLoading ? "Checking saved flocks..." : `${existingFlocks.length} flock${existingFlocks.length === 1 ? "" : "s"} already saved. Continue below only if you are adding a new batch.`}</p>
                                                                </div>
                                                                {existingFlocks.length > 0 && (
                                                                    <Button color="danger" outline type="button" onClick={() => navigate("/manageflock", { state: { farmPublicId: addData.farm_public_id } })}>Review existing</Button>
                                                                )}
                                                            </div>
                                                            {!flockReviewLoading && existingFlocks.length > 0 && (
                                                                <div className="record-summary-strip">
                                                                    <strong>Latest saved:</strong> {existingFlocks[0]?.flock_name || "Existing flock"}
                                                                    <div className="record-summary-chips">
                                                                        {existingFlocks.slice(0, 3).map((item) => (
                                                                            <span key={item.flock_public_id}>{item.flock_name}</span>
                                                                        ))}
                                                                        {existingFlocks.length > 3 && <span>+{existingFlocks.length - 3} more</span>}
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </>
                                                    )}
                                                </>
                                            )}
                                            {flockStep === 1 && (
                                                <>
                                                    <FormGroup>
                                                        <Label for="flockname">Flock Name</Label>
                                                        <div className="input-group">
                                                            <input onChange={changeFlockname} value={addData.flock_name} name="flockname" placeholder="Flock Name" type="text" className="form-control" aria-label="flockname" aria-describedby="basic-addon1" />
                                                        </div>
                                                        <small className="text-danger">{flock_nameerr}</small>
                                                    </FormGroup>
                                                    <FormGroup>
                                                        <Label for="hatchdate">Hatch Date</Label>
                                                        <div className="input-group">
                                                            <input onChange={changeHatchdate} value={addData.hatch_date} name="hatchdate" placeholder="Hatch Date" type="date" max={currentDate} className="form-control" aria-label="hatchdate" aria-describedby="basic-addon1" />
                                                        </div>
                                                        <small className="text-danger">{hatch_dateerr}</small>
                                                    </FormGroup>
                                                    <FormGroup>
                                                        <Label for="flocksize">Flock Size</Label>
                                                        <div className="input-group">
                                                            <input onChange={changeFlocksize} name="flocksize" value={addData.flock_size || ""} placeholder="Flock Size" type="number" className="form-control" aria-label="flocksize" aria-describedby="basic-addon1" />
                                                        </div>
                                                        <small className="text-danger">{flock_sizeerr}</small>
                                                    </FormGroup>
                                                    <FormGroup>
                                                        <Label for="actualbirds">Actual birds</Label>
                                                        <div className="input-group">
                                                            <input onChange={changeActualbirds} name="actualbirds" value={addData.actual_birds || ""} placeholder="Actual birds" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                        </div>
                                                        <small className="text-danger">{actual_birdserr}</small>
                                                    </FormGroup>
                                                </>
                                            )}
                                            {flockStep === 2 && (
                                                <>
                                                    <FormGroup>
                                                        <Label for="farmselect">Chick Breed</Label>
                                                        <div className="input-group">
                                                            <Input onChange={changeBreed} value={addData.breed_public_id || "0"} id="chickbreed" name="chickbreed" type="select">
                                                                <option value="0" disabled>-Chick Breed</option>
                                                                {
                                                                    breeds.map((item) => {
                                                                        return (
                                                                            <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                                                        )
                                                                    })
                                                                }
                                                            </Input>
                                                        </div>
                                                        <small className="text-danger">{breed_public_iderr}</small>
                                                    </FormGroup>
                                                    <FormGroup>
                                                        <Label for="flockname">Hatchery</Label>
                                                        <div className="input-group">
                                                            <input onChange={changeHatchery} value={addData.hatchery_name} name="hatchery" placeholder="Hatchery" type="text" className="form-control" aria-label="hatchery" aria-describedby="basic-addon1" />
                                                        </div>
                                                        <small className="text-danger">{hatchery_nameerr}</small>
                                                    </FormGroup>
                                                    <FormGroup>
                                                        <Label for="farmselect">Integration?</Label>
                                                        <div className="input-group">
                                                            <Input onChange={changeIntrigation} value={addData.integration || "0"} id="integration" name="integration" type="select">
                                                                <option value={0} disabled>-Integration?</option>
                                                                <option value={1}>Yes</option>
                                                                <option value={2}>No</option>
                                                            </Input>
                                                        </div>
                                                        <small className="text-danger">{integrationerr}</small>
                                                    </FormGroup>
                                                    {
                                                        (integration === 1) ?
                                                            <FormGroup>
                                                                <Label for="flockname">Int Co.?</Label>
                                                                <div className="input-group">
                                                                    <Input onChange={changeIntco} value={addData.integrator_public_id || "0"} id="chickbreed" name="chickbreed" type="select">
                                                                        <option value="0" disabled>-Integ Co.</option>
                                                                        {
                                                                            intgcom.map((item) => {
                                                                                return (
                                                                                    <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                                                                )
                                                                            })
                                                                        }
                                                                    </Input>
                                                                </div>
                                                                <small className="text-danger">{integrator_public_iderr}</small>
                                                            </FormGroup> :
                                                            <FormGroup>
                                                                <Label for="flockname">Chicks Cost</Label>
                                                                <div className="input-group">
                                                                    <input onChange={changeChickcost} value={addData.chick_cost || ""} name="chickscost" placeholder="Total Chicks Cost" type="number" className="form-control" aria-label="chickscost" aria-describedby="basic-addon1" />
                                                                </div>
                                                                <small className="text-danger">{chick_costerr}</small>
                                                            </FormGroup>
                                                    }
                                                </>
                                            )}
                                            {flockStep === 3 && (
                                                <>
                                                    <FormGroup>
                                                        <Label for="flockname">Day1 Wt(gms)</Label>
                                                        <div className="input-group">
                                                            <input onChange={changeDayoneweight} value={addData.chick_weight || ""} name="weight" placeholder="Day1 Wt(gms)" type="text" className="form-control" aria-label="weight" aria-describedby="basic-addon1" />
                                                        </div>
                                                        <small className="text-danger">{chick_weighterr}</small>
                                                    </FormGroup>
                                                    <FormGroup>
                                                        <Label for="farmselect">EC Shed?</Label>
                                                        <div className="input-group">
                                                            <Input onChange={changeEcshed} value={String(addData.ec_shed ?? "0")} id="ecshed" name="ecshed" type="select">
                                                                <option disabled value="0">-EC Shed</option>
                                                                <option value={true}>Yes</option>
                                                                <option value={false}>No</option>
                                                            </Input>
                                                        </div>
                                                        <small className="text-danger">{ec_shederr}</small>
                                                    </FormGroup>
                                                    <FormGroup>
                                                        <Label for="farmselect">Feed Sys</Label>
                                                        <div className="input-group">
                                                            <Input onChange={changeFeedsys} value={addData.feed_sys || "0"} id="feedsys" name="feedsys" type="select">
                                                                <option disabled value="0">-Feed Sys?</option>
                                                                <option value="M">Manual</option>
                                                                <option value="A">Auto</option>
                                                            </Input>
                                                        </div>
                                                        <small className="text-danger">{feed_syserr}</small>
                                                    </FormGroup>
                                                    <FormGroup>
                                                        <Label for="flockname">Drinking Sys</Label>
                                                        <div className="input-group">
                                                            <Input onChange={changeDrinkingsys} value={addData.drinking_sys || "0"} id="drinkingsys" name="drinkingsys" type="select">
                                                                <option disabled value="0">-Drinking Sys</option>
                                                                <option value="M">Manual</option>
                                                                <option value="A">Auto</option>
                                                                <option value="B">Both</option>
                                                            </Input>
                                                        </div>
                                                        <small className="text-danger">{drinking_syserr}</small>
                                                    </FormGroup>
                                                </>
                                            )}
                                            {flockStep === 4 && (
                                                <div className="form-review-card">
                                                    <span>Review flock</span>
                                                    <dl>
                                                        <div><dt>Flock</dt><dd>{addData.flock_name || "Not added"}</dd></div>
                                                        <div><dt>Hatch date</dt><dd>{addData.hatch_date || "Not added"}</dd></div>
                                                        <div><dt>Birds</dt><dd>{addData.actual_birds || "Not added"} / {addData.flock_size || "Not added"}</dd></div>
                                                        <div><dt>Hatchery</dt><dd>{addData.hatchery_name || "Not added"}</dd></div>
                                                        <div><dt>Chick weight</dt><dd>{addData.chick_weight || "Not added"}</dd></div>
                                                        <div><dt>Chick cost</dt><dd>{addData.chick_cost || "Integrator flock"}</dd></div>
                                                    </dl>
                                                </div>
                                            )}
                                            <div className="form-wizard-actions">
                                                {flockStep > 0 && (
                                                    <Button className="btn" color="secondary" type="button" onClick={goPreviousStep}>Back</Button>
                                                )}
                                                {flockStep < flockSteps.length - 1 && (
                                                    <Button className="btn" color="danger" type="button" onClick={goNextStep} disabled={!hasFarmPrerequisite && flockStep === 0}>Next</Button>
                                                )}
                                                {flockStep === flockSteps.length - 1 && (
                                                    loading ?
                                                        <Button className="btn" color="danger" type="submit" disabled  >
                                                            Please wait...
                                                            <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                        </Button>
                                                        :
                                                        <Button className="btn" color="danger" type="submit" >Save</Button>
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

export default AddFlock;
