import { Row, Col, Card, CardTitle, CardBody, Alert, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
import Accordion from 'react-bootstrap/Accordion';
import Moment from 'react-moment';
import Modal from 'react-bootstrap/Modal';
import Spinner from 'react-bootstrap/Spinner';
import { useNavigate } from 'react-router-dom';
import moment from "moment";

const FlockSale = () => {
    let [show, setShow] = useState(false);
    let [modelShow, setModelShow] = useState(false);
    let [farms, setFarms] = useState([]);
    let [flocks, setFlocks] = useState([]);
    let [flock, setFlock] = useState([]);
    let [feed, setFeed] = useState([]);
    let [showForm, setShowForm] = useState(false);
    let [showFlocks, setShowFlocks] = useState(false);
    let [showFlockSale, setShowFlockSale] = useState(false);
    let [showButton, setShowButton] = useState(false);
    // let [data, setData] = useState({ farm: null, flock: null, selType: null, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 });

//MV-16-6-25- 17-10 added buyeremail
    let [data, setData] = useState({ farm: null, flock: null, selType: null, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 ,buyeremail: "", });
//MV-16-6-25- 17-10 change end

    let [dataPopUp, setDataPopUp] = useState({
        totalfeed: 0, med: 0, vac: 0, ach: 0, rc: 0, pi: 0, ri: 0, ei: 0, sri: 0, totalicentive: 0, pcr: 0, stg: 0, em: 0, fr: 0, totalpnl: 0,
        ltds: 0, lamct: 0, ot: 0
    });
    let [error, setError] = useState({});
    let [totalChickCount, setTotalChickCount] = useState(0);
    let [submitError, setSubmitError] = useState('');
    let [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    function successMsg() {
        setShow(false);
    }
    const save = (e) => {
        setLoading(false)
        e.preventDefault();
        let error = { status: 0, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '' };
        if (data.date === null || data.date === '') { error.date = 'Date is required.'; error.status = 1 } else { error.date = '' }
        if (data.sellcount === null || Number(data.sellcount) < 0 || data.sellcount === '') { error.sellcount = 'Lifting Count is required.'; error.status = 1 } else { error.sellcount = '' }
        if (data.selltwt === null || Number(data.selltwt) < 0 || data.selltwt === '') { error.selltwt = 'Total weight is required.'; error.status = 1 } else { error.selltwt = '' }
        if (data.sellrate === null || Number(data.sellrate) < 0 || data.sellrate === '') { error.sellrate = 'Rate is required.'; error.status = 1 } else { error.sellrate = '' }
        setError({ ...error, date: error.date, sellcount: error.sellcount, selltwt: error.selltwt, sellrate: error.sellrate, sellamount: error.sellamount });
        if (error.status === 0) {
            setLoading(true)
            setSubmitError('');
            let saleData = {
                flock_public_id: data.flock,
                sales_type: data.selType,
                date: data.date,
                lifting_count: data.sellcount,
                total_weight: data.selltwt,
                rate_per_kg: data.sellrate,
                buyer: data.buyername,
                vehicle_no: data.buyervehicle,
                remarks: data.buyerremarks,
                buyer_phone_no: data.buyerphone,

//MV-16-6-25- 17-10 added buyeremail
                buyer_email: data.buyeremail,
//MV-16-6-25- 17-10 change end

                buyer_address: data.buyeraddress,
                feed_total: dataPopUp.totalfeed,
                vacc_price: dataPopUp.vac,
                med_price: dataPopUp.med,
                admin_charges: dataPopUp.ach,
                rearing_charges: dataPopUp.rc,
                performance_incentives: dataPopUp.pi,
                rate_incentives: dataPopUp.ri,
                eef_incentives: dataPopUp.ei,
                sp_rate_incentives: dataPopUp.sri,
                production_cost_recovery: dataPopUp.pcr,
                shortages: dataPopUp.stg,
                excess_mortality: dataPopUp.em,
                fcr_recovery: dataPopUp.fr,
                less_tds: dataPopUp.ltds,
                less_amct: dataPopUp.lamct,
                other_taxes: dataPopUp.ot,
            };
            let url = `${apiPath}sales/`;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.post(url, saleData, getAuthConfig()).then((res) => {
                setShow(true);
                setLoading(false)
                setTimeout(successMsg, 3000);
                setShowFlocks(false);
                setShowForm(false);
                setShowButton(false)
                setShowFlockSale(false)
            }).catch((err) => {
                console.log(err);
                setSubmitError('Something went wrong. Please try again');
                setLoading(false);
                handleUnauthorized(err, navigate);
            });
            // feed_rate:
            // feed_quantity:
            // chicks_rate:
            // chicks_quantity:

        } else {
            console.log('else');
        }
    }
    const closeAll = () => {
        //setFarms([]);
        setFlocks([]);
        setFlock([]);
        setShowForm(false);
        setShowFlocks(false);
        setShowFlockSale(false);
        setShowButton(false);
        setData({ farm: null, flock: null, selType: null, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 });
        setError({});
        window.location.reload();
    }
    useEffect(() => {
        let url = `${apiPath}farm/`;
        // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
        // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
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
    let changeFarm = (e) => {
        if (e.target.value === "0") {
            setFlocks([]);
            setFlock([]);
            setShowForm(false);
            setShowFlocks(false);
            setShowFlockSale(false);
            setShowButton(false);
            setData({ farm: null, flock: null, selType: null, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 });
            setError({});
        } else {
            let url = `${apiPath}flocks/${e.target.value}/`;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, getAuthConfig()).then((res) => {
                if (res.data.results.total_records === 0) {
                    setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                } else {
                    //setData({...data,farm:e.target.value,flock:null,seltype:null});
                    setFlocks(res.data.results.flock_list);
                }
                setShowFlocks(true);
                setFlock([]);
                setShowForm(false);
                setShowFlockSale(false);
                setShowButton(false);
                setData({ flock: null, selType: null, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '' });
                setError({});
            }).catch((err) => {
                //setFormError('No Flock available.');
                handleUnauthorized(err, navigate);
            });
        }
    }
    let changeFlock = (e) => {
        if (e.target.value === "0") {
            setShowForm(false);
            setShowFlockSale(false);
            setShowButton(false);
            setData({ flock: null, selType: null, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '' });
            setError({});
        } else {
            const user = flocks.find(u => String(u.flock_public_id) === e.target.value);
            if (!user) {
                setShowForm(false);
                setShowFlockSale(false);
                setShowButton(false);
                return;
            }
            let url = `${apiPath}dailyDataLastDate/${e.target.value}/`;
            axios.get(url, getAuthConfig()).then((res) => {
                setTotalChickCount(res.data.results.current_bird_count);
            }).catch((err) => {
                setTotalChickCount(user.actual_birds);
                handleUnauthorized(err, navigate);
            });
            setData({ ...data, farm: user.farm_public_id, flock: user.flock_public_id, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '' });
            setFlock(user);
            setShowFlockSale(true);
            setShowForm(false);
            //setShowButton(false);
            setError({});
        }
    }
    let changeFlockSale = (e) => {
        if (e.target.value === "0") {
            setShowButton(false);
            setShowForm(false);
            setData({ ...data, selType: e.target.value, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 });
            setError({});
        } else {
            setShowButton(true);
            setShowForm(false);
            e.target.value === "partial_lifting" ?
                setData({ ...data, selType: e.target.value, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 })
                : setData({ ...data, selType: e.target.value, date: '', sellcount: totalChickCount, selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 })
            setError({});
        }
    }
    let openModel = () => {
        setModelShow(true);
        let url = `${apiPath}purchase/?flock_public_id=${flock.flock_public_id}&filter=feed`;
        axios.get(url, getAuthConfig()).then((res) => {//console.log(res.data.results);
            const purchaseList = res.data.results.purchase_list;
            setFeed(purchaseList);
            // U: Replaced repeated first-item cost addition with a real total over all feed purchases.
            // for (let i = 0; i < res.data.results.purchase_list.length; i++) { mid = mid + res.data.results.purchase_list[0].cost }
            const totalFeedCost = purchaseList.reduce((total, item) => total + Number(item.cost || 0), 0);
            setDataPopUp({ ...dataPopUp, totalfeed: totalFeedCost });
        }).catch((err) => {
            //console.log('sachin',err);
            handleUnauthorized(err, navigate);
        });
    }
    let totalWeight = (e) => {
        if ((data.sellcount === null || Number(data.sellcount) < 0 || data.sellcount === '')) {
            setError({ ...error, sellcount: 'Lifting count is required.' });
            setData({ ...data, selltwt: 0 });
        } else {
            if ((data.selltwt === null || Number(data.selltwt) < 0 || data.selltwt === '')) {
                setError({ ...error, selltwt: 'Total weight is required.' });
                setData({ ...data, selltwt: 0 });
            } else {
                let mid = data.selltwt / data.sellcount; mid = mid.toFixed(2)
                setData({ ...data, sellavgweight: mid });
            }
        }
    }
    let totalCost = (e) => {
        if ((data.selltwt === null || Number(data.selltwt) < 0 || data.selltwt === '')) {
            setError({ ...error, selltwt: 'Total weight is required.' });
            setData({ ...data, selltwt: 0 });
        } else {
            if ((data.sellrate === null || Number(data.sellrate) < 0 || data.sellrate === '')) {
                setError({ ...error, sellrate: 'Rate is required.' });
                setData({ ...data, selltwt: 0 });
            } else {
                setData({ ...data, totalCost: data.selltwt * data.sellrate });
            }
        }
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
                        'Flock Sale Added Successfully.'
                    </Alert>
                    <Spinner animation="border" variant="success" style={{ 'marginLeft': '45%' }} />
                </Modal.Body>
                <Modal.Footer>
                </Modal.Footer>
            </Modal>
            <Modal size="lg" show={modelShow} onHide={() => setModelShow(false)} >
                <Modal.Header closeButton>
                    <Modal.Title>Add Integration Cost</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <Accordion defaultActiveKey="0">
                        <Accordion.Item eventKey="0">
                            <Accordion.Header>Cost</Accordion.Header>
                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                <Row><Col><b>Chicks</b></Col></Row>
                                <Row>
                                    <Col sm="6" md="3" lg="3">
                                        <Label for="flockname">Qty</Label>
                                        <input disabled defaultValue={data.sellcount} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                    </Col>
                                    <Col sm="6" md="3" lg="3">
                                        <Label for="flockname">Weight</Label>
                                        <input disabled defaultValue={data.selltwt} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                    </Col>
                                    <Col sm="6" md="3" lg="3">
                                        <Label for="flockname">Rate</Label>
                                        <input disabled defaultValue={data.sellrate} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                    </Col>
                                    <Col sm="6" md="3" lg="3">
                                        <Label for="flockname">Cost</Label>
                                        <input disabled defaultValue={data.totalCost} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                    </Col>
                                </Row>
                                <Row><Col><b>Feed</b></Col></Row>
                                {
                                    feed.length > 0 &&
                                    <Row>
                                        <Col sm="6" md="3" lg="3">
                                            <Label for="flockname">Name</Label>
                                        </Col>
                                        <Col sm="6" md="3" lg="3">
                                            <Label for="flockname">Date</Label>
                                        </Col>
                                        <Col sm="6" md="3" lg="3">
                                            <Label for="flockname">Quantity</Label>
                                        </Col>
                                        <Col sm="6" md="3" lg="3">
                                            <Label for="flockname">Rate</Label>
                                        </Col>
                                    </Row>
                                }
                                {
                                    feed.length > 0 ?
                                        feed.map((item) => {
                                            return (
                                                <Row>
                                                    <Col sm="6" md="3" lg="3">
                                                        <input disabled defaultValue={item.item_name} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                    </Col>
                                                    <Col sm="6" md="3" lg="3">
                                                        <input disabled defaultValue={`${item.date.split('-')[2]}/${item.date.split('-')[1]}/${item.date.split('-')[0]}`} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                    </Col>
                                                    <Col sm="6" md="3" lg="3">
                                                        <input disabled defaultValue={item.quantity} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                    </Col>
                                                    <Col sm="6" md="3" lg="3">
                                                        <input disabled defaultValue={item.cost} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                    </Col>
                                                </Row>
                                            )
                                        }) :
                                        <Row><Col>No feed purchase yet.</Col></Row>
                                }
                                <Row><Col><b>Total Feed Cost:- </b>{dataPopUp.totalfeed}</Col></Row>
                                <Row>
                                    <Col sm="6" md="4" lg="4">
                                        <Label for="flockname">Medicine</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="med" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="4" lg="4">
                                        <Label for="flockname">Vaccination</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="vac" defaultValue="0" placeholder="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="4" lg="4">
                                        <Label for="flockname">Admin Charges</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="ach" defaultValue="0" placeholder="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                            </Accordion.Body>
                        </Accordion.Item>
                        <Accordion.Item eventKey="1">
                            <Accordion.Header>Incentives</Accordion.Header>
                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Rearing Charges</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="rc" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Performance Incentive</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="pi" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Rate Incentive</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="ri" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">EEF Incentive</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="ei" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Sp. Rate Incentive</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="sri" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Total</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} disabled name="totalicentive" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                            </Accordion.Body>
                        </Accordion.Item>
                        <Accordion.Item eventKey="2">
                            <Accordion.Header>Penalties</Accordion.Header>
                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Production Cost Recovery</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="pcr" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Shortages</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="stg" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Excess Mortality</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="em" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">FCR Recovery</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="fr" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Total</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="totalpnl" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                            </Accordion.Body>
                        </Accordion.Item>
                        <Accordion.Item eventKey="3">
                            <Accordion.Header>Taxes</Accordion.Header>
                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Less TDS</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="ltds" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Less AMCT</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="lamct" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Other Taxes</Label>
                                        <input onChange={(e) => setDataPopUp({ ...dataPopUp, [e.target.name]: e.target.value })} name="ot" defaultValue="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                            </Accordion.Body>
                        </Accordion.Item>
                    </Accordion>
                </Modal.Body>
                <Modal.Footer>
                    <Button color="danger" type="Update" onClick={() => setModelShow(false)} >Next</Button>
                    <Button color="warning" type="submit" className="text-black" onClick={() => setModelShow(false)} >Close</Button>
                </Modal.Footer>
            </Modal>
            <Col>
                <Card className="pb-4">
                    <CardTitle tag="h6" className="border-bottom p-3 mb-0">
                        FLock Sale
                    </CardTitle>
                    <CardBody>
                        <Row className="mt-3">
                            <Col sm="12" md={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        <Form onSubmit={save}>
                                            <FormGroup>
                                                <Label for="farmselect">Select Farm</Label>
                                                <div className="input-group">
                                                    <Input onChange={changeFarm} id="farmSelect" name="farm" type="select" defaultValue="0">
                                                        <option value="0">Select Farm</option>
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
                                            {
                                                showFlocks &&
                                                <FormGroup>
                                                    <Label for="farmselect">Select Flock</Label>
                                                    <div className="input-group">
                                                        <Input onChange={changeFlock} id="flockSelect" name="flock" type="select" defaultValue="0">
                                                            <option value="0">Select Flocks</option>
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
                                            }
                                            {
                                                showFlockSale &&
                                                <FormGroup>
                                                    <Label for="farmselect">Select Sale Type</Label>
                                                    <div className="input-group">
                                                        <Input onChange={changeFlockSale} id="saleSelect" name="sale" type="select" defaultValue="0">
                                                            <option value="0">Select Sale Type</option>
                                                            <option value="partial_lifting">Partial Lifting</option>
                                                            <option value="final_lifting">Final Lifting</option>
                                                        </Input>
                                                    </div>
                                                </FormGroup>
                                            }
                                            {
                                                showButton &&
                                                <div className="button-group mt-2">
                                                    <Button color="danger" onClick={() => {
                                                        setShowForm(true);
                                                        setData({ ...data, date: '', selltwt: '', sellrate: '', sellamount: '' });
                                                        setError({});
                                                    }} className="btn" type="button">Proceed to next step</Button>
                                                    {/* <Button color="warning" type="button" className="text-black">Cancel</Button> */}
                                                </div>
                                            }
                                            {
                                                showForm &&
                                                <>
                                                    <Row className="mt-3">
                                                        <Col>
                                                            <Label for="flockname " className="font-bold">Flock </Label>
                                                            <Alert color="danger" className="shadow-4">{flock.flock_name}</Alert>
                                                        </Col>
                                                        <Col>
                                                            <Label for="flockname" className="font-bold flex">Current Count</Label>
                                                            <Alert color="danger" className="shadow-4">{totalChickCount}</Alert>
                                                        </Col>
                                                        <Col>
                                                            <Label for="flockname" className="font-bold">Age</Label>
                                                            <Alert color="danger" className="shadow-4">
                                                                <Moment diff={flock.hatch_date} unit="days">{new Date()}</Moment></Alert>
                                                        </Col>

                                                    </Row>
                                                    <Accordion defaultActiveKey="0" className="mb-3">
                                                        <Accordion.Item eventKey="0">
                                                            <Accordion.Header>Flock Data</Accordion.Header>
                                                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                                <Row>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Date</Label>
                                                                        <input onChange={(e) => {
                                                                            if (e.target.value === null || e.target.value.trim() === '') {
                                                                                setError({ ...error, date: 'Date is required.' }); setData({ ...data, date: e.target.value });
                                                                            } else {
                                                                                setError({ ...error, date: '' }); setData({ ...data, date: e.target.value });
                                                                            }
                                                                        }} name="date" placeholder="Sale Date" min={currentDate} type="date" className="form-control" aria-label="flockname" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{error.date}</small>
                                                                    </Col>
                                                                    {data.selType === "partial_lifting" ?
                                                                        <Col sm="6" md="4" lg="4">
                                                                            <Label for="flockname">Lifting Count</Label>
                                                                            <input onBlur={totalWeight} onChange={(e) => {
                                                                                if (e.target.value === null || Number(e.target.value) < 0 || e.target.value === '') {
                                                                                    setError({ ...error, sellcount: 'Lifting Count is required.' }); setData({ ...data, sellcount: e.target.value });
                                                                                } else {
                                                                                    setError({ ...error, sellcount: '' }); setData({ ...data, sellcount: e.target.value });
                                                                                }
                                                                            }} name="sellcount" placeholder="0" type="number" className="form-control" aria-label="hatchdate" aria-describedby="basic-addon1" />
                                                                            <small className="text-danger">{error.sellcount}</small>
                                                                        </Col>
                                                                        : data.selType === "final_lifting" &&
                                                                        <Col sm="6" md="4" lg="4">
                                                                            <Label for="flockname">Lifting Count</Label>
                                                                            <input disabled defaultValue={totalChickCount} name="sellcount" placeholder="0" type="number" className="form-control" aria-label="hatchdate" aria-describedby="basic-addon1" />
                                                                        </Col>
                                                                    }
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Total Wt.</Label>
                                                                        <input onBlur={totalWeight} onChange={(e) => {
                                                                            if (e.target.value === null || Number(e.target.value) < 0 || e.target.value === '') {
                                                                                setError({ ...error, selltwt: 'Total weight is required.' }); setData({ ...data, selltwt: e.target.value });
                                                                            } else {
                                                                                setError({ ...error, selltwt: '' }); setData({ ...data, selltwt: e.target.value });
                                                                            }
                                                                        }} name="selltwt" placeholder="0" type="number" className="form-control" aria-label="flocksize" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{error.selltwt}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Avg. Wt(kg)</Label>
                                                                        <input value={data.sellavgweight} disabled name="sellavgwt" placeholder="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger"></small>
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Rate/kg</Label>
                                                                        <input onBlur={totalCost} onChange={(e) => {
                                                                            if (e.target.value === null || Number(e.target.value) < 0 || e.target.value === '') {
                                                                                setError({ ...error, sellrate: 'Rate is required.' }); setData({ ...data, sellrate: e.target.value });
                                                                            } else {
                                                                                setError({ ...error, sellrate: '' }); setData({ ...data, sellrate: e.target.value });
                                                                            }
                                                                        }} name="sellrate" placeholder="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{error.sellrate}</small>
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Cost</Label>
                                                                        <input value={data.totalCost} disabled name="sellcost" placeholder="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{ }</small>
                                                                    </Col>
                                                                </Row>
                                                            </Accordion.Body>
                                                        </Accordion.Item>
                                                        <Accordion.Item eventKey="1">
                                                            <Accordion.Header>Buyer Data</Accordion.Header>
                                                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                                <Row>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Buyer Name</Label>
                                                                        <input onChange={(e) => { setData({ ...data, [e.target.name]: e.target.value }); }} name="buyername" placeholder="Buyer Name" type="text" className="form-control" aria-label="flockname" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{ }</small>
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Buyer Address</Label>
                                                                        <input onChange={(e) => { setData({ ...data, [e.target.name]: e.target.value }); }} name="buyeraddress" placeholder="Buyer Address" type="text" className="form-control" aria-label="hatchdate" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{ }</small>
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Buyer Phone</Label>
                                                                        <input maxLength={10} onChange={(e) => {
                                                                            if (e.target.value === "" || e.target.value.match(/^[0-9]*$/)) {
                                                                                setError({ ...error, phone: '' });
                                                                                setData({ ...data, [e.target.name]: e.target.value });
                                                                            } else {
                                                                                setError({ ...error, phone: 'Phone is not right format.' });
                                                                                setData({ ...data, [e.target.name]: e.target.value });
                                                                            }
                                                                        }} name="buyerphone" placeholder="Buyer Phone" type="text" className="form-control" aria-label="flocksize" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{error.phone}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col sm="6" md="4" lg="4">
                                                                    {/* <Label for="flockname">Buyer Email</Label>Add commentMore actions
                                                                        <input onChange={(e) => {
                                                                            if (e.target.value == "" || RegExp(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,15}/g).test(e.target.value.trim())) {
                                                                                setError({ ...error, email: '' });
                                                                                setData({ ...data, [e.target.name]: e.target.value });
                                                                            } else {
                                                                                setError({ ...error, email: 'Email is not right format.' });
                                                                                setData({ ...data, [e.target.name]: e.target.value });
                                                                            }
                                                                        }} name="buyeremail" placeholder="Buyer Email" type="text" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{error.email}</small> */}

{/* MV-16-6-25- 17-10 changed Email logic */}
                                                                    <Label for="flockname">Buyer Email</Label>
                                                                    <input
                                                                        onChange={(e) => {
                                                                        const value = e.target.value;
                                                                        const isValidEmail = value === "" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

                                                                        setData(prev => ({
                                                                            ...prev,
                                                                            buyeremail: value
                                                                        }));

                                                                        if (isValidEmail) {
                                                                            setError(prev => ({...prev, email: ''}));
                                                                        } else {
                                                                            setError(prev => ({...prev, email: 'Email is not right format.'}));
                                                                        }
                                                                        }}
                                                                        name="buyeremail"
                                                                        value={data.buyeremail}
                                                                        placeholder="Buyer Email"
                                                                        type="email"
                                                                        className="form-control"
                                                                        aria-label="actualbirds"
                                                                        aria-describedby="basic-addon1"
                                                                    />
                                                                    <small className="text-danger">{error.email}</small>
{/* MV-16-6-25- 17-10 change end */}


                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Vehicle No.</Label>
                                                                        <input onChange={(e) => { setData({ ...data, [e.target.name]: e.target.value }); }} name="buyervehicle" placeholder="Vehicle No." type="text" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{ }</small>
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="flockname">Remarks</Label>
                                                                        <input onChange={(e) => { setData({ ...data, [e.target.name]: e.target.value }); }} name="buyerremarks" placeholder="" type="text" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                                                        <small className="text-danger">{ }</small>
                                                                    </Col>
                                                                </Row>
                                                            </Accordion.Body>
                                                        </Accordion.Item>
                                                    </Accordion>
                                                    {flock.integration === true && data.selType === 'final_lifting' &&
                                                        <div className="button-group">
                                                            <Button color="primary" type="button" onClick={openModel}>Add Integration Cost</Button>
                                                        </div>}
                                                    <div className="button-group">
                                                        {submitError && <Alert color="danger">{submitError}</Alert>}
                                                        {loading ?
                                                            <Button className="btn" color="danger" type="submit" disabled  >
                                                                Saving...
                                                                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                            </Button>
                                                            :
                                                            <Button className="btn" color="danger" type="submit" >Save</Button>
                                                        }                                                        <Button color="warning" type="submit" className="text-black" onClick={closeAll} >Cancel</Button>
                                                    </div>
                                                </>
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

export default FlockSale;
