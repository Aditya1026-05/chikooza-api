import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, config } from "../../Constants";
import Accordion from 'react-bootstrap/Accordion'
import { useState, useEffect } from "react";
import axios from 'axios';
import Modal from 'react-bootstrap/Modal';
import { useNavigate } from 'react-router-dom';
import moment from "moment";

const AddFlock = () => {
    let [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    let [err, setErr] = useState('');
    const [show, setShow] = useState(false);
    let [farms, setFarms] = useState([]);
    let [breeds, setBreeds] = useState([]);
    let [intgcom, setIntgcom] = useState([]);

    var hatchdate = moment();
    var currentDate = hatchdate.format('YYYY-MM-DD');

    useEffect(() => {
        let url = `${apiPath}farm/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            console.log("farms list-----", res.data.results)
            if (res.data.results.length === 0) {
                setFarms([{ public_id: 0, name: 'No farm available' }]);
            } else {
                setFarms(res.data.results);
            }
        }).catch((err) => {
            console.log(err)
            setFarms([{ public_id: 0, name: 'No farm available' }]);
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    useEffect(() => {
        let url = `${apiPath}breeds/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setBreeds(res.data.results);
        }).catch((err) => {
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    useEffect(() => {
        let url = `${apiPath}integrators/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setIntgcom(res.data.results);
        }).catch((err) => {
            //setIntgcom(res.data.results);
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    let [addData, setAddData] = useState({
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
    });
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

    const save = (e) => {
        e.preventDefault();
        setLoading(false);
        let error = 0;
        if (addData.farm_public_id === 0 || addData.farm_public_id == null) { setFarm_public_iderr('Please select farm'); error = 1; } else { setFarm_public_iderr(''); }
        if (addData.hatch_date.trim() === '') { setHatch_dateerr('Hatch date is required'); error = 1; } else { setHatch_dateerr(''); }
        if (addData.flock_name.trim() === '') { setFlock_nameerr('Flock name is required'); error = 1; } else { setFlock_nameerr(''); }
        if (addData.flock_size <= 0 || addData.flock_size == null) { setFlock_sizeerr('Flock size is required'); error = 1; } else { setFlock_sizeerr(''); }
        if (addData.actual_birds <= 0 || addData.actual_birds == null) { setActual_birdserr('Flock Actual birds count is required'); error = 1; } else { setActual_birdserr(''); }
        if (addData.breed_public_id === 0 || addData.breed_public_id == null) { setBreed_public_iderr('Please select Breed'); error = 1; } else { setBreed_public_iderr(''); }
        if (addData.hatchery_name.trim() === '') { setHatchery_nameerr('Hatchery name is required'); error = 1; } else { setHatchery_nameerr(''); }
        if (addData.chick_weight <= 0 || addData.flock_size == null) { setChick_weighterr('Day one weight is required'); error = 1; } else { setChick_weighterr(''); }
        if (addData.ec_shed === 0 || addData.ec_shed == null) { setEc_shederr('Please select ec shed'); error = 1; } else { setEc_shederr(''); }
        if (addData.feed_sys === 0 || addData.feed_sys == null) { setFeed_syserr('Please select feed system'); error = 1; } else { setFeed_syserr(''); }
        if (addData.drinking_sys === 0 || addData.drinking_sys == null) { setDrinking_syserr('Please select Drinking System'); error = 1; } else { setDrinking_syserr(''); }
        if (addData.integration === 0 || addData.integration == null) {
            setIntegrationerr('Please select integration'); error = 1;
            if (addData.chick_cost <= 0 || addData.chick_cost == null) { setChick_costerr('Chicks Cost is required'); error = 1; } else { setChick_costerr(''); }
        } else {
            setIntegrationerr('');
            if (addData.integration == 1) {
                if (addData.integrator_public_id == 0 || addData.integrator_public_id == null) { setIntegrator_public_iderr('Please select Drinking System'); error = 1; } else { setIntegrator_public_iderr(''); }
            } else if (addData.integration == 2) {
                if (addData.chick_cost <= 0 || addData.chick_cost == null) { setChick_costerr('Chicks Cost is required'); error = 1; } else { setChick_costerr(''); }
            }
        }
        if (error === 0) {
            setLoading(true)
            // if (addData.integration === 1) {
            //     addData.integration = true;
            //     //addData.chick_cost=1;
            // } else {
            //     addData.integration = false;
            //     //addData.integrator_public_id=1;
            // }
            if (addData.ec_shed === 1) {
                addData.ec_shed = true;
            } else {
                addData.ec_shed = false;
            }
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
                ec_shed: addData.ec_shed,
                feed_sys: addData.feed_sys,
                drinking_sys: addData.drinking_sys,
                farm_public_id: addData.farm_public_id
            };
            if (addData.integration == 1) {
                flock.integration = true;
                flock.integrator_public_id = addData.integrator_public_id;
            } else {
                flock.integration = false;
                flock.chick_cost = addData.chick_cost;
            }
            let url = `${apiPath}flocks/`;
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.post(url, flock, config).then((res) => {
                console.log(res)
                //setErr('Form created successfully');
                setShow(true);
                setLoading(false);
                setTimeout(successMsg, 3000);
            }).catch((err) => {
                console.log(err)
                setErr(err.response.data.message);
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }
    }
    let changeFarm = (e) => {
        setAddData({ ...addData, farm_public_id: e.target.value });
        e.target.value === 0 ? setFarm_public_iderr('Please select farm') : setFarm_public_iderr('');
    }
    let changeBreed = (e) => {
        setAddData({ ...addData, breed_public_id: e.target.value });
        e.target.value === 0 ? setBreed_public_iderr('Please select Breed') : setBreed_public_iderr('');
    }
    let changeIntrigation = (e) => {
        setAddData({ ...addData, integration: e.target.value });
        e.target.value == 0 ? setIntegrationerr('Please select integration') : setIntegrationerr('');
        if (e.target.value == 1) {
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
        e.target.value === 0 ? setHatchery_nameerr('Hatchery name is required') : setHatchery_nameerr('');
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
        e.target.value === 0 ? setDrinking_syserr('Please select Drinking System') : setDrinking_syserr('');
    }
    let changeFeedsys = (e) => {
        setAddData({ ...addData, feed_sys: e.target.value });
        e.target.value === 0 ? setFeed_syserr('Please select feed system') : setFeed_syserr('');
    }
    let changeFlockname = (e) => {
        setAddData({ ...addData, flock_name: e.target.value });
        e.target.value === 0 ? setFlock_nameerr('Flock name is required') : setFlock_nameerr('');
    }
    let changeHatchdate = (e) => {
        setAddData({ ...addData, hatch_date: e.target.value });
        e.target.value === 0 ? setHatch_dateerr('Hatch date is required') : setHatch_dateerr('');
    }
    let changeFlocksize = (e) => {
        setAddData({ ...addData, flock_size: e.target.value });
        e.target.value <= 0 ? setFlock_sizeerr('Flock size is required') : setFlock_sizeerr('');
    }
    let changeIntco = (e) => {
        if (integration === 1) {
            setAddData({ ...addData, integrator_public_id: e.target.value });
            e.target.value === 0 ? setIntegrator_public_iderr('Please select Intrigation company') : setIntegrator_public_iderr('');
        }
    }
    function successMsg() {
        navigate("/manageflock");
    }
    let closeAll = () => {
        setAddData({
            ...addData, hatch_date: '',
            flock_size: "",
            actual_birds: "",
            flock_name: '',
            breed_public_id: "",
            hatchery_name: '',
            chick_weight: "",
            integration: "",
            integrator_public_id: "",
            chick_cost: "",
            ec_shed: "",
            feed_sys: "",
            drinking_sys: "",
            farm_public_id: ""
        })
        setFarms([]);
    }
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
                                        <Form onSubmit={save}>
                                            <FormGroup>
                                                <Label for="farmselect">Select Farm</Label>
                                                <div className="input-group">
                                                    <Input onChange={changeFarm} id="farmSelect" defaultValue={'Select Farm'} name="farm" type="select">
                                                        <option disabled defaultValue={-1}>Select Farm</option>
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
                                            <Accordion defaultActiveKey="" className="mb-3">
                                                <Accordion.Item eventKey="0">
                                                    <Accordion.Header>Flock Data - Main</Accordion.Header>
                                                    <Accordion.Body style={{ backgroundColor: 'white' }}>
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
                                                                <input onChange={changeFlocksize} name="flocksize" value={addData.flock_size} placeholder="Flock Size" type="number" className="form-control" aria-label="flocksize" aria-describedby="basic-addon1" />
                                                            </div>
                                                            <small className="text-danger">{flock_sizeerr}</small>
                                                        </FormGroup>
                                                        <FormGroup>
                                                            <Label for="actualbirds">Actual birds</Label>
                                                            <div className="input-group">
                                                                <input onChange={changeActualbirds} name="actualbirds" value={addData.actual_birds} placeholder="Actual birds" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                            </div>
                                                            <small className="text-danger">{actual_birdserr}</small>
                                                        </FormGroup>
                                                    </Accordion.Body>
                                                </Accordion.Item>
                                                <Accordion.Item eventKey="1">
                                                    <Accordion.Header>Breed Data</Accordion.Header>
                                                    <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                        <FormGroup>
                                                            <Label for="farmselect">Chick Breed</Label>
                                                            <div className="input-group">
                                                                <Input onChange={changeBreed} defaultValue={0} id="chickbreed" name="chickbreed" type="select">
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
                                                                <Input onChange={changeIntrigation} defaultValue={0} id="integration" name="integration" type="select">
                                                                    <option value={0} disabled>-Integration?</option>
                                                                    <option value={1}>Yes</option>
                                                                    <option value={2}>No</option>
                                                                </Input>
                                                            </div>
                                                            <small className="text-danger"></small>
                                                        </FormGroup>
                                                        {
                                                            (integration == 1) ?
                                                                <FormGroup>
                                                                    <Label for="flockname">Int Co.?</Label>
                                                                    <div className="input-group">
                                                                        <Input onChange={changeIntco} defaultValue={0} id="chickbreed" name="chickbreed" type="select">
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
                                                                        <input onChange={changeChickcost} value={addData.chick_cost} name="chickscost" placeholder="Total Chicks Cost" type="number" className="form-control" aria-label="chickscost" aria-describedby="basic-addon1" />
                                                                    </div>
                                                                    <small className="text-danger">{chick_costerr}</small>
                                                                </FormGroup>
                                                        }
                                                    </Accordion.Body>
                                                </Accordion.Item>
                                                <Accordion.Item eventKey="2">
                                                    <Accordion.Header>More Flock Data</Accordion.Header>
                                                    <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                        <FormGroup>
                                                            <Label for="flockname">Day1 Wt(gms)</Label>
                                                            <div className="input-group">
                                                                <input onChange={changeDayoneweight} value={addData.chick_weight} name="weight" placeholder="Day1 Wt(gms)" type="text" className="form-control" aria-label="weight" aria-describedby="basic-addon1" />
                                                            </div>
                                                            <small className="text-danger">{chick_weighterr}</small>
                                                        </FormGroup>
                                                        <FormGroup>
                                                            <Label for="farmselect">EC Shed?</Label>
                                                            <div className="input-group">
                                                                <Input onChange={changeEcshed} defaultValue={0} id="ecshed" name="ecshed" type="select">
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
                                                                <Input onChange={changeFeedsys} defaultValue={0} id="feedsys" name="feedsys" type="select">
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
                                                                <Input onChange={changeDrinkingsys} defaultValue={0} id="drinkingsys" name="drinkingsys" type="select">
                                                                    <option disabled value="0">-Drinking Sys</option>
                                                                    <option value="M">Manual</option>
                                                                    <option value="A">Auto</option>
                                                                    <option value="B">Both</option>
                                                                </Input>
                                                            </div>
                                                            <small className="text-danger">{drinking_syserr}</small>
                                                        </FormGroup>
                                                    </Accordion.Body>
                                                </Accordion.Item>
                                            </Accordion>
                                            <div className="button-group">
                                                {loading ?
                                                    <Button className="btn" color="danger" type="submit" disabled  >
                                                        Please wait...
                                                        <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                    </Button>
                                                    :
                                                    <Button className="btn" color="danger" type="submit" >Save</Button>
                                                }
                                                <Button className="btn ml-4" color="warning" type="button" onClick={closeAll} >Cancel</Button>
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
