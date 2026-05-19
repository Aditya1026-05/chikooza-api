import { Row, Col, Table, Card, CardTitle, CardBody, Alert, Button, Form, FormGroup, Label, Input, FormText, Nav, NavItem } from "reactstrap";
import '../../assets/css/header.css';
import { useState } from "react";
import { contentArea, apiPath, config } from "../../Constants";
import Accordion from 'react-bootstrap/Accordion'
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import Modal from 'react-bootstrap/Modal';
import Spinner from 'react-bootstrap/Spinner';
import { useNavigate } from "react-router-dom";



const EditSale = () => {
    let location = useLocation();
    console.log(location);
    let [show, setShow] = useState(false);
    let [loading, setLoading] = useState(false)
    let [modelShow, setModelShow] = useState(false);
    let [feed, setFeed] = useState([]);
    let [dataPopUp, setDataPopUp] = useState({
        totalfeed: 0
    });
    let [flock, setFlock] = useState([]);
    let [data, setData] = useState({
        date: location.state.item.date ? location.state.item.date : " ", dateerror: "",
        age: location.state.item.age ? location.state.item.age : " ", ageerror: '',
        lifting_count: location.state.item.lifting_count ? location.state.item.lifting_count : " ", lifting_counterror: '',
        total_weight: location.state.item.total_weight ? location.state.item.total_weight : " ", total_weighterror: '',
        cost: location.state.item.cost ? location.state.item.cost : " ", costerror: '',
        rate_per_kg: location.state.item.rate_per_kg ? location.state.item.rate_per_kg : " ", rate_per_kgerror: '',
        buyer: location.state.item.buyer ? location.state.item.buyer : " ", buyererror: '',
        buyer_address: location.state.item.buyer_address ? location.state.item.buyer_address : " ", buyer_addresserror: '',
        buyer_phone_no: location.state.item.buyer_phone_no ? location.state.item.buyer_phone_no : 0, buyer_phone_noerror: '',
        // buyer_email: location.state.item.buyer_email ? location.state.item.buyer_email : "",

//MV-23-6-25- 17-10 empty strng for email
        buyer_email: location.state.item.buyer_email ? location.state.item.buyer_email : "",
//MV-23-6-25- 17-10 change end

        buyer_emailerror: '',
        vehicle_no: location.state.item.vehicle_no ? location.state.item.vehicle_no : 0, vehicle_noerror: '',
        remarks: location.state.item.remarks ? location.state.item.remarks : 0, remarkserror: '',
        sales_type: location.state.item.sales_type ? location.state.item.sales_type : "partial_lifting",
        med: location.state.item.med_price ? location.state.item.med_price : 0,
        vac: location.state.item.vacc_price ? location.state.item.vacc_price : 0,
        ach: location.state.item.admin_charges ? location.state.item.admin_charges : 0,
        rc: location.state.item.rearing_charges ? location.state.item.rearing_charges : 0,
        pi: location.state.item.performance_incentives ? location.state.item.performance_incentives : 0,
        ri: location.state.item.rate_incentives ? location.state.item.rate_incentives : 0,
        ei: location.state.item.eef_incentives ? location.state.item.eef_incentives : 0,
        sri: location.state.item.sp_rate_incentives ? location.state.item.sp_rate_incentives : 0,
        pcr: location.state.item.production_cost_recovery ? location.state.item.production_cost_recovery : 0,
        stg: location.state.item.shortages ? location.state.item.shortages : 0,
        em: location.state.item.excess_mortality ? location.state.item.excess_mortality : 0,
        fr: location.state.item.fcr_recovery ? location.state.item.fcr_recovery : 0,
        ltds: location.state.item.less_tds ? location.state.item.less_tds : 0,
        lamct: location.state.item.less_amct ? location.state.item.less_amct : 0,
        ot: location.state.item.other_taxes ? location.state.item.other_taxes : 0
    });
    console.log(data);
    let navigate = useNavigate()
    function successMsg() {
        setShow(false);
    }
    // const [showFlock, setShowFlock] = useState(false);
    // const [showFlockSale, setShowFlockSale] = useState(false);
    // const [showForm, setShowForm] = useState(false);
    const save = (e) => {
        e.preventDefault();
        setLoading(false)
        let err = { status: 0, buyer: "" }
        if (data.buyer == null || data.buyer == '') { err.buyer = 'buyer is required.'; err.status = 1 } else { err.date = '' }
        setData({ ...data, buyererror: err.buyer })
        if (err.status === 0) {
            setLoading(true);
            let url = `${apiPath}sales/${location.state.item.public_id}/`;
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            let saleData = {
                date: data.date,
                lifting_count: data.lifting_count,
                total_weight: data.total_weight,
                rate_per_kg: data.rate_per_kg,
                buyer: data.buyer,
                vehicle_no: data.vehicle_no,
                remarks: data.remarks,
                buyer_phone_no: data.buyer_phone_no,
                buyer_address: data.buyer_address,
                vacc_price: data.vac,
                med_price: data.med,
                admin_charges: data.ach,
                rearing_charges: data.rc,
                performance_incentives: data.pi,
                rate_incentives: data.ri,
                eef_incentives: data.ei,
                sp_rate_incentives: data.sri,
                production_cost_recovery: data.pcr,
                shortages: data.stg,
                excess_mortality: data.em,
                fcr_recovery: data.fr,
                less_tds: data.ltds,
                less_amct: data.lamct,
                other_taxes: data.ot,
            };
            console.log(saleData);
            axios.patch(url, saleData, config).then((res) => {
                setLoading(false); setShow(true);
                setTimeout(successMsg, 3000);
                setData({ ...data, })

            }).catch((err) => {
                console.log(err);
                setLoading(false);
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }
    }
    let openModel = () => {
        setModelShow(true);
        let url = `${apiPath}purchase/?flock_public_id=${location.state.item.flock_public_id}&filter=feed`;
        const config = {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem('token')}`
            }
        };
        axios.get(url, config).then((res) => {//console.log(res.data.results);
            setFeed(res.data.results.purchase_list);
            let mid = 0;
            for (let i = 0; i < res.data.results.purchase_list.length; i++) {
                mid = mid + res.data.results.purchase_list[0].cost
            }
            setDataPopUp({ ...dataPopUp, totalfeed: mid });
        }).catch((err) => {//console.log('sachin',err);
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }
    // const displayFlock = () => {
    //     setShowFlock(true);
    // }
    // const displayForm = () => {
    //     setShowForm(true);
    // }
    // const closeForm = () => {
    //     setShowForm(false);
    // }
    // const displayFlockSale = () => {
    //     setShowFlockSale(true);
    // }
    // const CancelAll = () => {
    //     setShowForm(false);
    //     setShowFlockSale(false);
    //     setShowFlock(false);
    //     setFlock([]);
    // }
    return (
        <Row>
            <Modal show={show} backdrop="static" keyboard={false} >
                <Modal.Header>
                </Modal.Header>
                <Modal.Body>
                    <Alert color="success">
                        'Flock Sale Update Successfully.'
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
                                        <input disabled defaultValue={data.lifting_count} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                    </Col>
                                    <Col sm="6" md="3" lg="3">
                                        <Label for="flockname">Weight</Label>
                                        <input disabled defaultValue={data.total_weight} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                    </Col>
                                    <Col sm="6" md="3" lg="3">
                                        <Label for="flockname">Rate</Label>
                                        <input disabled defaultValue={data.rate_per_kg} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                    </Col>
                                    <Col sm="6" md="3" lg="3">
                                        <Label for="flockname">Cost</Label>
                                        <input disabled defaultValue={data.cost} className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
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
                                                <Row key={item.public_id}>
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
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.med} name="med" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="4" lg="4">
                                        <Label for="flockname">Vaccination</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.vac} name="vac" placeholder="0" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="4" lg="4">
                                        <Label for="flockname">Admin Charges</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.ach} name="ach" placeholder="0" type="text" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
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
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.rc} name="rc" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Performance Incentive</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.pi} name="pi" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Rate Incentive</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.ri} name="ri" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">EEF Incentive</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.ei} name="ei" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Sp. Rate Incentive</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.sri} name="sri" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Total</Label>
                                        <input defaultValue={data.rc + data.pi + data.ri + data.ei + data.sri} disabled name="totalicentive" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
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
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.pcr} name="pcr" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Shortages</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.stg} name="stg" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Excess Mortality</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.em} name="em" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">FCR Recovery</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.fr} name="fr" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Total</Label>
                                        <input defaultValue={data.pcr + data.stg + data.em + data.em + data.fr} disabled name="totalpnl" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
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
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.ltds} name="ltds" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Less AMCT</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.lamct} name="lamct" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                                <Row>
                                    <Col sm="6" md="6" lg="6">
                                        <Label for="flockname">Other Taxes</Label>
                                        <input onChange={(e) => setData({ ...data, [e.target.name]: e.target.value })} defaultValue={data.ot} name="ot" type="number" className="form-control" aria-label="actualbirds" aria-describedby="basic-addon1" />
                                        <small className="text-danger"></small>
                                    </Col>
                                </Row>
                            </Accordion.Body>
                        </Accordion.Item>
                    </Accordion>
                </Modal.Body>
                <Modal.Footer>
                    <Button color="danger" type="Update" onClick={() => setModelShow(false)} >Next</Button>
                </Modal.Footer>
            </Modal>
            <Col>
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-1*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card className="pb-4">
                    <CardTitle tag="h6" className="border-bottom p-3 mb-0">
                        Edit/ Flock Sale
                    </CardTitle>
                    <CardBody>
                        <Row className="mt-3">
                            <Col sm="12" md={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        <Form onSubmit={save}>

                                            <>
                                                <Row className="mt-3">
                                                    <Col>
                                                        <Label for="flockname " className="font-bold">Flock </Label>
                                                        <Alert color="danger" className="shadow-4">{location.state.item.flock_name

                                                        }</Alert>
                                                    </Col>
                                                    <Col>
                                                        <Label for="flockname" className="font-bold flex">Current Count</Label>
                                                        <Alert color="danger" className="shadow-4">{location.state.item.current_bird_count}</Alert>
                                                    </Col>


                                                </Row>

                                                <Accordion defaultActiveKey="0" className="mb-3">
                                                    <Accordion.Item eventKey="0">
                                                        <Accordion.Header>Flock Lifting Data</Accordion.Header>
                                                        <Accordion.Body style={{ backgroundColor: 'white' }} >
                                                            <Row>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="flockname"> Sale Date</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, date: e.target.value, dateerror: 'This field is not valid' }) :
                                                                                setData({ ...data, date: e.target.value, dateerror: '' })
                                                                        }} name="date" placeholder="Sale Date" type="date" className="form-control" aria-label="flockname" aria-describedby="basic-addon1" defaultValue={data.date} />
                                                                    </div>
                                                                    <small className="text-danger">{data.dateerror}</small>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="actualbirds">Age</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, age: e.target.value, ageerror: 'This field is not valid' }) :
                                                                                setData({ ...data, age: e.target.value, ageerror: '' })
                                                                        }} name="age" placeholder="0" defaultdefaultValue="371" type="number" className="form-control bg-red-100 " aria-label="actualbirds" aria-describedby="basic-addon1" defaultValue={data.age} />
                                                                    </div>
                                                                    <small className="text-danger">{data.ageerror}</small>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="hatchdate">Lifting Count</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, lifting_count: e.target.value, lifting_counterror: 'This field is not valid' }) :
                                                                                setData({ ...data, lifting_count: e.target.value, lifting_counterror: '' })
                                                                        }} name="lifting_count" placeholder="0" type="number" className="form-control" aria-label="hatchdate" aria-describedby="basic-addon1" defaultValue={data.lifting_count} />
                                                                    </div>
                                                                    <small className="text-danger">{data.lifting_counterror}</small>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="flocksize">Lifting Wt (kg).</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, total_weight: e.target.value, total_weighterror: 'This field is not valid' }) :
                                                                                setData({ ...data, total_weight: e.target.value, total_weighterror: '' })
                                                                        }} name="total_weight" placeholder="0" type="number" className="form-control" aria-label="flocksize" aria-describedby="basic-addon1" defaultValue={data.total_weight} />
                                                                    </div>
                                                                    <small className="text-danger">{data.total_weighterror}</small>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="actualbirds">Sale Amount</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, cost: e.target.value, costerror: 'This field is not valid' }) :
                                                                                setData({ ...data, cost: e.target.value, costerror: '' })
                                                                        }} name="cost" placeholder="0" type="number" className="form-control bg-red-100" aria-label="actualbirds" aria-describedby="basic-addon1" defaultValue={data.cost} />
                                                                    </div>
                                                                    <small className="text-danger">{data.costerror}</small>
                                                                </Col>

                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="actualbirds">Rate</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, rate_per_kg: e.target.value, rate_per_kgerror: 'This field is not valid' }) :
                                                                                setData({ ...data, rate_per_kg: e.target.value, rate_per_kgerror: '' })
                                                                        }} name="rate_per_kg" placeholder="0" defaultdefaultValue="200.00" type="number" className="form-control bg-red-100 " aria-label="actualbirds" aria-describedby="basic-addon1" defaultValue={data.rate_per_kg} />
                                                                    </div>
                                                                    <small className="text-danger">{data.rate_per_kgerror}</small>
                                                                </Col>
                                                            </Row>
                                                        </Accordion.Body>
                                                    </Accordion.Item>
                                                    <Accordion.Item eventKey="1">
                                                        <Accordion.Header>Buyer</Accordion.Header>
                                                        <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                            <Row>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="actualbirds">Name</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, buyer: e.target.value, buyererror: 'This field is not valid' }) :
                                                                                setData({ ...data, buyer: e.target.value, buyererror: '' })
                                                                        }} name="buyer" placeholder="Name" type="text" className="form-control  " aria-label="actualbirds" aria-describedby="basic-addon1" defaultValue={data.buyer} />
                                                                    </div>
                                                                    <small className="text-danger">{data.buyererror}</small>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="actualbirds">Address</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, buyer_address: e.target.value, buyer_addresserror: 'This field is not valid' }) :
                                                                                setData({ ...data, buyer_address: e.target.value, buyer_addresserror: '' })
                                                                        }} name="address" placeholder="Address" type="text" className="form-control  " aria-label="actualbirds" aria-describedby="basic-addon1" defaultValue={data.buyer_address} />
                                                                    </div>
                                                                    <small className="text-danger">{data.buyer_addresserror}</small>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="actualbirds">Phone</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, buyer_phone_no: e.target.value, buyer_phone_noerror: 'This field is not valid' }) :
                                                                                setData({ ...data, buyer_phone_no: e.target.value, buyer_phone_noerror: '' })
                                                                        }} name="phone" placeholder="0" type="number" className="form-control  " aria-label="actualbirds" aria-describedby="basic-addon1" defaultValue={data.buyer_phone_no} />
                                                                    </div>
                                                                    <small className="text-danger">{data.buyer_phone_noerror}</small>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="flockname">Email</Label>
                                                                    <div className="input-group">
                                                                    {/* <input onChange={(e) => {Add commentMore actions
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, buyer_email: e.target.value, buyer_emailerror: 'This field is not valid' }) :
                                                                                setData({ ...data, buyer_email: e.target.value, buyer_emailerror: '' })
                                                                        }} name="email" placeholder="Email" type="email" className="form-control" aria-label="hatchery" aria-describedby="basic-addon1" defaultValue={data.buyer_email} /> */}

{/* MV-16-6-25- 17-10 changed email logic */}
                                                                        <input
                                                                            onChange={(e) => {
                                                                                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                                                                                const emailValue = e.target.value;

                                                                                if (!emailValue || !emailRegex.test(emailValue)) {
                                                                                    setData({
                                                                                        ...data,
                                                                                        buyer_email: emailValue,
                                                                                        buyer_emailerror: 'Please enter a valid email address'
                                                                                    });
                                                                                } else {
                                                                                    setData({
                                                                                        ...data,
                                                                                        buyer_email: emailValue,
                                                                                        buyer_emailerror: ''
                                                                                    });
                                                                                }
                                                                            }}
                                                                            name="email"
                                                                            placeholder="Email"
                                                                            type="email"
                                                                            className="form-control"
                                                                            aria-label="hatchery"
                                                                            aria-describedby="basic-addon1"
                                                                            defaultValue={data.buyer_email || ""}
                                                                        />
{/* MV-16-6-25- 17-10 change end */}

                                                                    </div>
                                                                    <small className="text-danger">{data.buyer_emailerror}</small>
                                                                </Col>
                                                            </Row>
                                                        </Accordion.Body>
                                                    </Accordion.Item>
                                                    <Accordion.Item eventKey="2">
                                                        <Accordion.Header>Other Data</Accordion.Header>
                                                        <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                            <Row>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="actualbirds">Vehicle No.</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, vehicle_no: e.target.value, vehicle_noerror: 'This field is not valid' }) :
                                                                                setData({ ...data, vehicle_no: e.target.value, vehicle_noerror: '' })
                                                                        }} name="vehicle no" placeholder="Vehicle No." type="text" className="form-control  " aria-label="actualbirds" aria-describedby="basic-addon1" defaultValue={data.vehicle_no} />
                                                                    </div>
                                                                    <small className="text-danger">{data.vehicle_noerror}</small>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="actualbirds">Remarks</Label>
                                                                    <div className="input-group">
                                                                        <input onChange={(e) => {
                                                                            e.target.value === '' || e.target.value === null ?
                                                                                setData({ ...data, remarks: e.target.value, remarkserror: 'This field is not valid' }) :
                                                                                setData({ ...data, remarks: e.target.value, remarkserror: '' })
                                                                        }} name="remark" placeholder="remarks" type="text" className="form-control  " aria-label="actualbirds" aria-describedby="basic-addon1" defaultValue={data.remarks} />
                                                                    </div>
                                                                    <small className="text-danger">{data.remarkserror}</small>
                                                                </Col>
                                                            </Row>
                                                        </Accordion.Body>
                                                    </Accordion.Item>
                                                </Accordion>
                                                <div className="button-group">
                                                    {data.sales_type === 'final_lifting' &&
                                                        <div className="button-group">
                                                            <Button color="primary" type="button" onClick={openModel}>Add Integration Cost</Button>
                                                        </div>}
                                                    {loading ?
                                                        <Button className="btn" color="danger" type="submit" disabled  >
                                                            Saving...
                                                            <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                        </Button>
                                                        :
                                                        <Button className="btn" color="danger" type="submit" >save</Button>
                                                    }
                                                    <Link to="/viewsale" style={{ textDecoration: "none" }}> <Button color="warning" type="button" className="text-black" style={{ textDecoration: "none" }}  >Cancel</Button></Link>
                                                </div>

                                            </>

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

export default EditSale;
