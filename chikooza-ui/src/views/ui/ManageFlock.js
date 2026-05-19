import { Alert, Row, Col, Table, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input, FormText, Nav, NavItem } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, config } from "../../Constants";
import Accordion from 'react-bootstrap/Accordion'
import { useState, useEffect } from "react";
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Modal from 'react-bootstrap/Modal';
import moment from "moment/moment";

const ManageFlock = () => {
    const [show, setShow] = useState(false);
    let [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    let [err, setErr] = useState('');
    let [farms, setFarms] = useState([]);
    let [showFlocks, setShowFlocks] = useState(0);
    let [flocks, setFlocks] = useState([]);
    let [showForm, setShowForm] = useState(0);
    let [breeds, setBreeds] = useState([]);
    let [intgcom, setIntgcom] = useState([]);
    useEffect(() => {
        let url = `${apiPath}farm/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            if (res.data.results.length == 0) {
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
            //setBreeds(res.data.results);
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
        chick_breed_public_id: null,
        hatchery_name: '',
        chick_weight: null,
        integration: null,
        integrator_public_id: null,
        chick_cost: null,
        ec_shed: null,
        feed_sys: null,
        drinking_sys: null,
        flock_public_id: null
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
    //let [farm_public_iderr ,setFarm_public_iderr] = useState(null);
    //let [flock_public_iderr ,setFlock_public_iderr] = useState(null);
    let [integration, setIntegration] = useState(2);

    const save = (e) => {
        e.preventDefault();
        setLoading(false);//console.log(addData.integration);
        let error = 0;
        //if(addData.farm_public_id == 0 || addData.farm_public_id == null){setFarm_public_iderr('Please select farm');error = 1;}else{setFarm_public_iderr('');}
        if (addData.integration == true) { addData.integration = 1; } else if (addData.integration == false) { addData.integration = 2; }
        if (addData.ec_shed == true) { addData.ec_shed = 1; } else if (addData.ec_shed == false) { addData.ec_shed = 2; }
        if (addData.hatch_date.trim() == '') { setHatch_dateerr('Hatch date is required'); error = 1; } else { setHatch_dateerr(''); }
        if (addData.flock_name.trim() == '') { setFlock_nameerr('Flock name is required'); error = 1; } else { setFlock_nameerr(''); }
        if (addData.flock_size <= 0 || addData.flock_size == null) { setFlock_sizeerr('Flock size is required'); error = 1; } else { setFlock_sizeerr(''); }
        if (addData.actual_birds <= 0 || addData.actual_birds == null) { setActual_birdserr('Flock Actual birds count is required'); error = 1; } else { setActual_birdserr(''); }
        if (addData.chick_breed_public_id == 0 || addData.chick_breed_public_id == null) { setBreed_public_iderr('Please select Breed'); error = 1; } else { setBreed_public_iderr(''); }
        if (addData.hatchery_name.trim() == '') { setHatchery_nameerr('Hatchery name is required'); error = 1; } else { setHatchery_nameerr(''); }
        if (addData.chick_weight <= 0 || addData.flock_size == null) { setChick_weighterr('Day one weight is required'); error = 1; } else { setChick_weighterr(''); }
        if (addData.ec_shed == 0 || addData.ec_shed == null) { setEc_shederr('Please select ec shed'); error = 1; } else { setEc_shederr(''); }
        if (addData.feed_sys == 0 || addData.feed_sys == null) { setFeed_syserr('Please select feed system'); error = 1; } else { setFeed_syserr(''); }
        if (addData.drinking_sys == 0 || addData.drinking_sys == null) { setDrinking_syserr('Please select Drinking System'); error = 1; } else { setDrinking_syserr(''); }
        if (addData.integration == 0 || addData.integration == null) {
            setIntegrationerr('Please select integration'); error = 1;
            if (addData.chick_cost <= 0 || addData.chick_cost == null) { console.log('1'); setChick_costerr('Chicks Cost is required'); error = 1; } else { setChick_costerr(''); }
        } else {
            setIntegrationerr('');
            if (addData.integration == 1) {
                if (addData.integrator_public_id == 0 || addData.integrator_public_id == null) { setIntegrator_public_iderr('Please select Intrigation company'); error = 1; } else { setIntegrator_public_iderr(''); }
            } else if (addData.integration == 2) {
                if (addData.chick_cost <= 0 || addData.chick_cost == null) { console.log(addData.chick_cost + '2'); setChick_costerr('Chicks Cost is required'); error = 1; } else { setChick_costerr(''); }
            }
        }
        if (error == 0) {
            setLoading(true);
            if (addData.ec_shed == 1) {
                addData.ec_shed = true;
            } else {
                addData.ec_shed = false;
            }
            let flock = {
                hatch_date: addData.hatch_date,
                flock_size: addData.flock_size,
                actual_birds: addData.actual_birds,
                flock_name: addData.flock_name,
                breed_public_id: addData.chick_breed_public_id,
                hatchery_name: addData.hatchery_name,
                chick_weight: addData.chick_weight,
                //integration:addData.integration,
                //integrator_public_id:addData.integrator_public_id,
                //chick_cost:addData.chick_cost,
                ec_shed: addData.ec_shed,
                feed_sys: addData.feed_sys,
                drinking_sys: addData.drinking_sys
            };
            if (addData.integration == 1) {
                flock.integration = true;
                flock.integrator_public_id = addData.integrator_public_id;
            } else {
                flock.integration = false;
                flock.chick_cost = addData.chick_cost;
            }
            console.log("bodyyyy", flock)
            let url = `${apiPath}flocks/${addData.flock_public_id}/`;
            console.log(config);
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.patch(url, flock, config).then((res) => {
                setShow(true);
                setLoading(false);
                setTimeout(successMsg, 3000);
                //setErr('Flock updated successfully');
                //setShowFlocks(0);
                //setShowForm(0);
                //setFarms([]);
                //setAddData({});
                // let newArray = flocks.slice();
                // let obj = newArray.find((o, i) => {
                //     if (o.public_id === addData.flock_public_id) {
                //        newArray[i] = { flock_name: addData.flock_name,flock_public_id: addData.flock_public_id};
                //        return true; // stop searching
                //     }
                // });
                // setFlocks(newArray);
            }).catch((err) => {
                setErr('Something went wrong. Please try again');
                setLoading(false);
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        } else {
            setErr('Validation error. Please check all fields.');
        }
    }

    let changeFarm = (e) => {
        //setAddData({...addData,farm_public_id:e.target.value});
        if (e.target.value == 0) {
            //setFarm_public_iderr('Please select farm');
        } else {
            //setFarm_public_iderr('');
            let url = `${apiPath}flocks/${e.target.value}/`;
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, config).then((res) => {
                setShowFlocks(1);
                setShowForm(0);
                if (res.data.results.total_records == 0) {
                    setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                } else {
                    setFlocks(res.data.results.flock_list);
                }
            }).catch((err) => {
                //setFlocks(err.data.results);
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }
    }
    let changeFlocks = (e) => {
        //setAddData({...addData,farm_public_id:e.target.value});
        if (e.target.value == 0) {
            //setFlock_public_iderr('Please select flocks');
        } else {
            //setFlock_public_iderr('');
            let url = `${apiPath}flocksDetail/${e.target.value}/`;
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, config).then((res) => {
                setShowForm(1);
                setAddData(res.data.results);
            }).catch((err) => {
                //setFlocks(err.data.results);
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }
    }
    let changeBreed = (e) => {
        setAddData({ ...addData, chick_breed_public_id: e.target.value });
        e.target.value == 0 ? setBreed_public_iderr('Please select Breed') : setBreed_public_iderr('');
    }
    //let changeIntrigation = (e) => {
      //  setAddData({ ...addData, integration: e.target.value });
       // e.target.value == 0 ? setIntegrationerr('Please select integration') : setIntegrationerr('');
       // if (e.target.value == 1) {
        //    setIntegration(1)
        //} else {
        //    setIntegration(2)
       // }
   // }

{/* AS-20-6-25 17-10 corrected Integration default value logic */}
   let changeIntrigation = (e) => {
    let value = e.target.value === "1" ? true : false;
    setAddData({ ...addData, integration: value });
    e.target.value == 0 ? setIntegrationerr('Please select integration') : setIntegrationerr('');
    setIntegration(value ? 1 : 2);
    }
{/* AS-20-6-25 17-10 change end */}

    let changeActualbirds = (e) => {
        setAddData({ ...addData, actual_birds: e.target.value });
        e.target.value <= 0 ? setActual_birdserr('Flock Actual birds count is required') : setActual_birdserr('');
    }
    let changeHatchery = (e) => {
        setAddData({ ...addData, hatchery_name: e.target.value });
        e.target.value == 0 ? setHatchery_nameerr('Hatchery name is required') : setHatchery_nameerr('');
    }
    let changeDayoneweight = (e) => {
        setAddData({ ...addData, chick_weight: e.target.value });
        e.target.value <= 0 ? setChick_weighterr('Day one weight is required') : setChick_weighterr('');
    }
    let changeChickcost = (e) => {
        if (addData.integration != 1) {
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
        e.target.value == 0 ? setDrinking_syserr('Please select Drinking System') : setDrinking_syserr('');
    }
    let changeFeedsys = (e) => {
        setAddData({ ...addData, feed_sys: e.target.value });
        e.target.value == 0 ? setFeed_syserr('Please select feed system') : setFeed_syserr('');
    }
    let changeFlockname = (e) => {
        setAddData({ ...addData, flock_name: e.target.value });
        e.target.value == 0 ? setFlock_nameerr('Flock name is required') : setFlock_nameerr('');
    }
    let changeHatchdate = (e) => {
        setAddData({ ...addData, hatch_date: e.target.value });
        e.target.value == 0 ? setHatch_dateerr('Hatch date is required') : setHatch_dateerr('');
    }
    let changeFlocksize = (e) => {
        setAddData({ ...addData, flock_size: e.target.value });
        e.target.value <= 0 ? setFlock_sizeerr('Flock size is required') : setFlock_sizeerr('');
    }
    let changeIntco = (e) => {
        if (addData.integration == 1) {
            setAddData({ ...addData, integrator_public_id: e.target.value });
            e.target.value == 0 ? setIntegrator_public_iderr('Please select Intrigation company') : setIntegrator_public_iderr('');
        }
    }
    function successMsg() {
        window.location.reload()
    }
    let closeAll = () => {
        setAddData({
            ...addData,
            hatch_date: '',
            flock_size: '',
            actual_birds: '',
            flock_name: '',
            chick_breed_public_id: '',
            hatchery_name: '',
            chick_weight: '',
            integration: '',
            integrator_public_id: '',
            chick_cost: '',
            ec_shed: '',
            feed_sys: '',
            drinking_sys: '',
            flock_public_id: ''
        });
        setFarms([]);
        window.location.reload();
    }
    var hatchdate = moment();
    var currentDate = hatchdate.format('YYYY-MM-DD');

    return (
        <Row>
            <Modal show={show} backdrop="static" keyboard={false} >
                <Modal.Header>
                </Modal.Header>
                <Modal.Body>
                    <Alert color="success">
                        Flock updated successfully
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
                    <CardTitle tag="h6" className="border-bottom p-3 mb-0">Manage Flock</CardTitle>
                    <CardBody>
                        <Row className="mt-3">
                            <Col sm="12" md={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        {(err != '') && <Alert color="danger">{err}</Alert>}
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
                                            </FormGroup>
                                            {(showFlocks == 1) ?
                                                <FormGroup>
                                                    <Label for="farmselect">Select Flocks</Label>
                                                    <div className="input-group">
                                                        <Input onChange={changeFlocks} id="farmSelect" defaultValue={"Select Flock"} name="farm" type="select">
                                                            <option selected={true} disabled defaultValue={0}>Select Flocks</option>
                                                            {
                                                                flocks.map((item) => {
                                                                    return (
                                                                        <option key={item.flock_public_id} value={item.flock_public_id}>{item.flock_name}</option>
                                                                    )
                                                                })
                                                            }
                                                        </Input>
                                                    </div>
                                                </FormGroup>
                                                : null}
                                            {(showForm == 1) ?
                                                <>
                                                    <Accordion defaultActiveKey="" className="mb-3">
                                                        <Accordion.Item eventKey="0">
                                                            <Accordion.Header>Flock Data - Main</Accordion.Header>
                                                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                                <FormGroup>
                                                                    <Label for="flockname">Flock Name</Label>
                                                                    <div className="input-group">
                                                                        <input value={addData.flock_name} onChange={changeFlockname} name="flockname" placeholder="Flock Name" type="text" className="form-control" aria-label="flockname" aria-describedby="basic-addon1" />
                                                                    </div>
                                                                    <small className="text-danger">{flock_nameerr}</small>
                                                                </FormGroup>
                                                                <FormGroup>
                                                                    <Label for="hatchdate">Hatch Date</Label>
                                                                    <div className="input-group">
                                                                        <input value={addData.hatch_date} onChange={changeHatchdate} name="hatchdate" max={currentDate} placeholder="Hatch Date" type="date" className="form-control" aria-label="hatchdate" aria-describedby="basic-addon1" />
                                                                    </div>
                                                                    <small className="text-danger">{hatch_dateerr}</small>
                                                                </FormGroup>
                                                                <FormGroup>
                                                                    <Label for="flocksize">Flock Size</Label>
                                                                    <div className="input-group">
                                                                        <input value={addData.flock_size} onChange={changeFlocksize} name="flocksize" placeholder="Flock Size" type="number" className="form-control" aria-label="flocksize" aria-describedby="basic-addon1" />
                                                                    </div>
                                                                    <small className="text-danger">{flock_sizeerr}</small>
                                                                </FormGroup>
                                                                <FormGroup>
                                                                    <Label for="actualbirds">Actual birds</Label>
                                                                    <div className="input-group">
                                                                        <input value={addData.actual_birds} onChange={changeActualbirds} name="actualbirds" placeholder="Actual birds" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
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
                                                                        <Input onChange={changeBreed} id="chickbreed" name="chickbreed" type="select">
                                                                            <option value="0" disabled>-Chick Breed</option>
                                                                            {
                                                                                breeds.map((item) => {
                                                                                    return (
                                                                                        <option selected={addData.chick_breed_public_id == item.public_id} key={item.public_id} value={item.public_id}>{item.name}</option>
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
                                                                        <input value={addData.hatchery_name} onChange={changeHatchery} name="hatchery" placeholder="Hatchery" type="text" className="form-control" aria-label="hatchery" aria-describedby="basic-addon1" />
                                                                    </div>
                                                                    <small className="text-danger">{hatchery_nameerr}</small>
                                                                </FormGroup>

                                                                {/* <FormGroup>
                                                                    <Label for="farmselect">Integration?</Label>
                                                                    <div className="input-group">
                                                                        <Input onChange={changeIntrigation} value={addData.integration} id="integration" name="integration" type="select">
                                                                            <option value="0" disabled>-Integration?</option>
                                                                            <option value="1" selected={addData.integration == true}>Yes</option>
                                                                            <option value="2" selected={addData.integration == false}>No</option>
                                                                        </Input>
                                                                    </div>
                                                                    <small className="text-danger">{integrationerr}</small>
                                                                </FormGroup> */}

{/* AS-20-6-25- 17-10 changed Integration display logic */}
                                                                 <FormGroup>
                                                                   <Label for="farmselect">Integration?</Label>
                                                                 <div className="input-group">
                                                                      <Input
                                                                       onChange={changeIntrigation}
                                                                        value={
                                                                         addData.integration === true
                                                                                  ? "1"
                                                                                  : addData.integration === false
                                                                                  ? "2"
                                                                                  : "0"
                                                                                       }
                                                                               id="integration"
                                                                               name="integration"
                                                                               type="select"
                                                                             >
                                                                              <option value="0" disabled>-Integration?</option>
                                                                              <option value="1">Yes</option>
                                                                              <option value="2">No</option>
                                                                              </Input>
                                                                              </div>
                                                                              <small className="text-danger">{integrationerr}</small>
                                                                </FormGroup>
{/* AS-20-6-25 17-10 change end */}

                                                                {
                                                                    (addData.integration == true) ?
                                                                        <FormGroup>
                                                                            <Label for="flockname">Int Co.?</Label>
                                                                            <div className="input-group">
                                                                                <Input onChange={changeIntco} value={addData.integrator_public_id} id="chickbreed" name="chickbreed" type="select">
                                                                                    <option value="0" disabled>-Integ Co.</option>
                                                                                    {
                                                                                        intgcom.map((item) => {
                                                                                            return (
                                                                                                <option selected={item.public_id == addData.integrator_public_id} key={item.public_id} value={item.public_id}>{item.name}</option>
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
                                                                                <input value={addData.chick_cost} onChange={changeChickcost} name="chickscost" placeholder="Chicks Cost" type="number" className="form-control" aria-label="chickscost" aria-describedby="basic-addon1" />
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
                                                                        <input value={addData.chick_weight} onChange={changeDayoneweight} name="weight" placeholder="Day1 Wt(gms)" type="number" className="form-control" aria-label="weight" aria-describedby="basic-addon1" />
                                                                    </div>
                                                                    <small className="text-danger">{chick_weighterr}</small>
                                                                </FormGroup>
                                                                <FormGroup>
                                                                    <Label for="farmselect">EC Shed?</Label>
                                                                    <div className="input-group">
                                                                        <Input onChange={changeEcshed} value={addData.ec_shed} id="ecshed" name="ecshed" type="select">
                                                                            <option disabled value="0">-EC Shed</option>
                                                                            <option value={true} selected={addData.ec_shed == true}>Yes</option>
                                                                            <option value={false} selected={addData.ec_shed == false}>No</option>
                                                                        </Input>
                                                                    </div>
                                                                    <small className="text-danger">{ec_shederr}</small>
                                                                </FormGroup>
                                                                <FormGroup>
                                                                    <Label for="farmselect">Feed Sys</Label>
                                                                    <div className="input-group">
                                                                        <Input onChange={changeFeedsys} value={addData.feed_sys} id="feedsys" name="feedsys" type="select">
                                                                            <option disabled value="0">-Feed Sys?</option>
                                                                            <option value="M" selected={addData.feed_sys == "M"}>Manual</option>
                                                                            <option value="A" selected={addData.feed_sys == "A"}>Auto</option>
                                                                        </Input>
                                                                    </div>
                                                                    <small className="text-danger">{feed_syserr}</small>
                                                                </FormGroup>
                                                                <FormGroup>
                                                                    <Label for="flockname">Drinking Sys</Label>
                                                                    <div className="input-group">
                                                                        <Input onChange={changeDrinkingsys} value={addData.drinking_sys} id="drinkingsys" name="drinkingsys" type="select">
                                                                            <option disabled value="0">-Drinking Sys</option>
                                                                            <option value="M" selected={addData.drinking_sys == "M"}>Manual</option>
                                                                            <option value="A" selected={addData.drinking_sys == "A"}>Auto</option>
                                                                            <option value="B" selected={addData.drinking_sys == "B"}>Both</option>
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
                                                        <Button className="btn ml-4" color="warning" type="button" onClick={closeAll}>Cancel</Button>
                                                    </div>
                                                </>
                                                : null
                                            }
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

export default ManageFlock;
