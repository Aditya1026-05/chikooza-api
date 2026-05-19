import { Spinner, Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, config } from "../../Constants";
import { useState, useEffect } from "react";
import Accordion from 'react-bootstrap/Accordion'
import axios from 'axios';
import Modal from 'react-bootstrap/Modal';
import { useNavigate } from "react-router-dom";

const AddPurchase = () => {
    let [loading, setLoading] = useState(false);
    const [show, setShow] = useState(false);
    let [err, setErr] = useState('');
    let [farms, setFarms] = useState([]);
    let [showFlocks, setShowFlocks] = useState(0);
    let [flocks, setFlocks] = useState([]);
    let [showForm, setShowForm] = useState(0);
    const [showInputArea, setShowInputArea] = useState(false);
    let [addData, setAddData] = useState({
        flock_public_id: '',
        type: '',
        date: null,
        cost: null,
        remarks: '',
        company_name: '',
        item_name: '',
        unit: "",
        size: 50,
        item_type: 100,
        quantity: null
    });
    let [remarkserr, setRemarkserr] = useState('');
    let [costerr, setCosterr] = useState('');
    let [dateerr, setDateerr] = useState('');
    let [company_nameerr, setCompany_nameerr] = useState('');
    let [item_nameerr, setItem_nameerr] = useState('');
    let [uniterr, setUniterr] = useState('');
    let [sizeerr, setSizeerr] = useState('');
    let [item_typeerr, setItem_typeerr] = useState('');
    let [quantityerr, setQuantityerr] = useState('');
    let [flockerr, setFlockerr] = useState('');
    let navigate = useNavigate()

    useEffect(() => {
        let url = `${apiPath}farm/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
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
    let changeFarm = (e) => {
        setAddData({ ...addData, farm_public_id: e.target.value });
        if (e.target.value === 0) {
            //setFarm_public_iderr('Please select farm');
        } else {
            let url = `${apiPath}flocks/${e.target.value}/`;
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, config).then((res) => {
                setShowFlocks(1);
                setShowForm(0);
                if (res.data.results.total_records === 0) {
                    setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                } else {
                    setFlocks(res.data.results.flock_list);
                }
            }).catch((err) => {
                setFlocks(err.data.results);
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }
    }
    let changeFlocks = (e) => {
        if (e.target.value === 0) {
            setFlockerr('Flock is not valid');
            setShowForm(0);
        } else {
            setFlockerr('');
            setAddData({ ...addData, flock_public_id: e.target.value });
            setShowForm(1);
        }
    }
    const save = (e) => {
        e.preventDefault();
        setLoading(false);
        let error = 0;

        if (showInputArea === 'F') {
            if (addData.cost < 0 || addData.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (addData.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (addData.date === null || addData.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
            if (addData.company_name.trim()==='') { setCompany_nameerr('This fields is required'); error = 1; } else { setCompany_nameerr(''); }
            if (addData.item_name.trim()==='') { setItem_nameerr('This fields is required'); error = 1; } else { setItem_nameerr(''); }
            if (addData.unit<1) { setUniterr('This fields is required'); error = 1; } else { setUniterr(''); }
            //if (addData.item_type.trim() === '' || addData.item_type == null) { setItem_typeerr('This fields is required'); error = 1; } else { setItem_typeerr(''); }
            //if (addData.size.trim() === '' || addData.size == null) { setSizeerr('This fields is required'); error = 1; } else { setSizeerr(''); }
            if (addData.quantity < 0) { setQuantityerr('This fields is required'); error = 1; } else { setQuantityerr(''); }
        } else if (showInputArea === 'M') {
            if (addData.cost < 0 || addData.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (addData.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (addData.date === null || addData.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
            if (addData.company_name.trim()==='') { setCompany_nameerr('This fields is required'); error = 1; } else { setCompany_nameerr(''); }
            if (addData.item_name.trim()==='') { setItem_nameerr('This fields is required'); error = 1; } else { setItem_nameerr(''); }
            if (addData.quantity < 0 || addData.date === null) { setQuantityerr('This fields is required'); error = 1; } else { setQuantityerr(''); }
        } else if (showInputArea === 'V') {
            if (addData.cost < 0 || addData.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (addData.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (addData.date === null || addData.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
            if (addData.company_name.trim()==='') { setCompany_nameerr('This fields is required'); error = 1; } else { setCompany_nameerr(''); }
            if (addData.item_name.trim()==='') { setItem_nameerr('This fields is required'); error = 1; } else { setItem_nameerr(''); }
            if (addData.quantity < 0 || addData.date === null) { setQuantityerr('This fields is required'); error = 1; } else { setQuantityerr(''); }
        } else if (showInputArea === 'E') {
            if (addData.cost < 0 || addData.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (addData.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (addData.date === null || addData.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
            if (addData.company_name.trim()==='') { setCompany_nameerr('This fields is required'); error = 1; } else { setCompany_nameerr(''); }
            if (addData.item_name.trim()==='') { setItem_nameerr('This fields is required'); error = 1; } else { setItem_nameerr(''); }
            if (addData.quantity < 0 || addData.date === null) { setQuantityerr('This fields is required'); error = 1; } else { setQuantityerr(''); }
        } else if (showInputArea === 'L') {
            if (addData.cost < 0 || addData.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (addData.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (addData.date === null || addData.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
        } else if (showInputArea === 'O') {
            if (addData.cost < 0 || addData.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (addData.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (addData.date === null || addData.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
        }

        //console.log(error, addData.cost, addData.remarks, addData.date, addData.company_name, addData.item_name, addData.unit, addData.item_type, addData.size, addData.quantity);
        if (error === 0) {
            setLoading(true)
            let url = `${apiPath}purchase/`;
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.post(url, addData, config).then((res) => {
                setShow(true);
                setLoading(false);
                setTimeout((() => {
                    setShow(false);
                }), 3000);
                setAddData({
                    ...addData,
                    flock_public_id: '',
                    type: '',
                    date: null,
                    cost: null,
                    remarks: '',
                    company_name: '',
                    item_name: '',
                    unit: "",
                    size: 50,
                    item_type: 100,
                    quantity: null
                })
                setShowForm(0)
                setErr('');
                //setShowFlocks(0)
            }).catch((err) => {
                console.log(err);
                setLoading(false);
                setErr('Something went wrong. Please try again');
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }

    }
    const showInputs = (e) => {
        setShowInputArea(e.target.value);
        //console.log(addData);
        if (e.target.value === 'F') {
            setAddData({ ...addData, type: "Feed", quantity: 0 });
        } else if (e.target.value === 'M') {
            setAddData({ ...addData, type: "Medicine", unit: "", size: "" });
        } else if (e.target.value === 'V') {
            setAddData({ ...addData, type: "Vaccination", item_type: '', size: 0 });
        } else if (e.target.value === 'E') {
            setAddData({ ...addData, type: "Equipment", unit: "", size: "" });
        } else if (e.target.value === 'L') {
            setAddData({ ...addData, type: "Labour", item_type: '', unit: "", size: "" });
        } else if (e.target.value === 'O') {
            setAddData({ ...addData, type: "Other", item_type: '', unit: "", size: "", quantity: 0 });
        }
    }
    let changeFeedCompany = (e) => {
        e.target.value.trim()==='' ? setCompany_nameerr('This fields is required') : setCompany_nameerr('');
        setAddData({ ...addData, company_name: e.target.value });
    }
    let changeCost = (e) => {
        setAddData({ ...addData, cost: e.target.value });
        e.target.value < 0 ? setCosterr('This fields is not valid') : setCosterr('');
    }
    let changeFeedBrand = (e) => {
        e.target.value.trim()==='' ? setItem_nameerr('This fields is required') : setItem_nameerr('');
        setAddData({ ...addData, item_name: e.target.value });
    }
    let changeNumberOfBags = (e) => {
        e.target.value<1 ? setUniterr('This fields is not valid') : setUniterr('');
        setAddData({ ...addData, unit: e.target.value });
    }
    let changeBagsSize = (e) => {
        setAddData({ ...addData, size: e.target.value });
    }
    let changeRemarks = (e) => {
        setAddData({ ...addData, remarks: e.target.value });
        e.target.value.trim() === '' ? setRemarkserr('This fields is required') : setRemarkserr('');
    }
    let changeFeedType = (e) => {
        setAddData({ ...addData, item_type: e.target.value });
    }
    let changePurchaseDate = (e) => {
        setAddData({ ...addData, date: e.target.value });
        e.target.value.trim() === '' ? setDateerr('This fields is required') : setDateerr('');
    }
    let showQuantity = (e) => {
        setAddData({ ...addData, quantity: e.target.value });
        e.target.value < 0  ? setQuantityerr('This fields is not valid') : setQuantityerr('');
    }
    let closeAll = () => {
        setAddData({
            ...addData,
            flock_public_id: '',
            type: '',
            date: null,
            cost: null,
            remarks: '',
            company_name: '',
            item_name: '',
            unit: "",
            size: 50,
            item_type: 100,
            quantity: null
        })
        setShowForm(0)
        //setShowFlocks(0)
    }
    return (
        <Row>
            <Modal show={show} backdrop="static" keyboard={false} >
                <Modal.Header>
                </Modal.Header>
                <Modal.Body>
                    <Alert color="success">
                        Purchase added successfully
                    </Alert>
                    <Spinner animation="border" variant="primary" style={{ 'marginLeft': '45%' }} />
                </Modal.Body>
                <Modal.Footer>
                </Modal.Footer>
            </Modal>
            <Col>
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-1*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card className="pb-4">
                    <CardTitle tag="h6" className="border-bottom p-3 mb-0">
                        Add Purchase
                    </CardTitle>
                    <CardBody>
                        <Row className="mt-3">
                            <Col sm="12" md={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        {(err !== '') && <Alert color="danger">{err}</Alert>}
                                        <Form onSubmit={save}>
                                            <Label for="farmselect">Select Farm</Label>
                                            <FormGroup>
                                                <div className="input-group">
                                                    <Input onChange={changeFarm} defaultValue={'Select Farm'} id="farmSelect" name="farm" type="select">
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
                                            {(showFlocks === 1) ?
                                                <FormGroup>
                                                    <Label for="farmselect">Select Flocks</Label>
                                                    <div className="input-group">
                                                        <Input onChange={changeFlocks} value={addData.flock_public_id} id="farmSelect" name="flock" type="select">
                                                            <option selected value={0}>Select Flocks</option>
                                                            {
                                                                flocks.map((item) => {
                                                                    return (
                                                                        <option key={item.flock_public_id} value={item.flock_public_id}>{item.flock_name}</option>
                                                                    )
                                                                })
                                                            }
                                                        </Input>
                                                    </div>
                                                    <small className="text-danger">{flockerr}</small>
                                                </FormGroup>
                                                : null}
                                            {(showForm === 1) ?
                                                <>
                                                    <Accordion defaultActiveKey="0" className="mb-3">
                                                        <Accordion.Item eventKey="0">
                                                            <Accordion.Header>Purchase Details</Accordion.Header>
                                                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="purchaseDate" className="font-bold flex">Purchase Date</Label>
                                                                        <Input onChange={changePurchaseDate} value={addData.date} name="purchaseDate" type="date"></Input>
                                                                        <small className="text-danger">{dateerr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="action" className="font-bold">Action</Label>
                                                                        <Input defaultValue={0} onChange={showInputs} name="selectAction" type="select">
                                                                            <option value='0' disabled selected>Select</option>
                                                                            <option value="F">Feed</option>
                                                                            <option value="M">Medicine</option>
                                                                            <option value="V">Vaccination</option>
                                                                            <option value="E">Equipment</option>
                                                                            <option value="L">Labour</option>
                                                                            <option value="O">Other</option>
                                                                        </Input>
                                                                    </Col>
                                                                </Row>

                                                                {/* Feed Data */}
                                                                {
                                                                    showInputArea === 'F' &&
                                                                    <>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="feedCompany" className="font-bold flex">Feed Company</Label>
                                                                                <Input onChange={changeFeedCompany} value={addData.company_name} name="feedCompany" type="text"></Input>
                                                                                <small className="text-danger">{company_nameerr}</small>
                                                                            </Col>
                                                                            <Col>
                                                                                <Label for="feedBrand" className="font-bold flex">Feed Brand</Label>
                                                                                <Input onChange={changeFeedBrand} value={addData.item_name} name="feedBrand" type="text">
                                                                                </Input>
                                                                                <small className="text-danger">{item_nameerr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="numberOfBags" className="font-bold flex">No of Bags</Label>
                                                                                <Input onChange={changeNumberOfBags} value={addData.unit} name="numberOfBags" type="number">
                                                                                </Input>
                                                                                <small className="text-danger">{uniterr}</small>
                                                                            </Col>
                                                                            <Col>
                                                                                <Label for="bagsSize" className="font-bold">Bags Size</Label>
                                                                                <Input onChange={changeBagsSize} value={addData.size} name="bagsSize" type="select">
                                                                                    <option disabled={true} selected>Select</option>
                                                                                    <option value="50">50 KG</option>
                                                                                    <option value="100">100 KG</option>
                                                                                </Input>
                                                                                <small className="text-danger">{sizeerr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="feedType" className="font-bold">Feed Type</Label>
                                                                                <Input onChange={changeFeedType} value={addData.item_type} name="feedType" type="select">
                                                                                    <option value='0' disabled selected>Select</option>
                                                                                    <option value="100">Pre Starter</option>
                                                                                    <option value="101">Starter</option>
                                                                                    <option value="102">Finisher</option>
                                                                                </Input>
                                                                                <small className="text-danger">{item_typeerr}</small>
                                                                            </Col>
                                                                            <Col>
                                                                                <Label for="cost" className="font-bold flex">Cost</Label>
                                                                                <Input onChange={changeCost} value={addData.cost} name="cost" type="number"></Input>
                                                                                <small className="text-danger">{costerr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                                <Input onChange={changeRemarks} value={addData.remarks} id="remarks" name="remarks" type="text"></Input>
                                                                                <small className="text-danger">{remarkserr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                    </>
                                                                }
                                                                {/* Feed Data */}

                                                                {/* Medicine Data */}
                                                                {
                                                                    showInputArea === 'M' &&
                                                                    <>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="medicinecompany" className="font-bold flex">Medicine Company</Label>
                                                                                <Input onChange={changeFeedCompany} value={addData.company_name} name="feedCompany" type="text"></Input>
                                                                                <small className="text-danger">{company_nameerr}</small>
                                                                            </Col>
                                                                            <Col>
                                                                                <Label for="medicine" className="font-bold flex">Medicine</Label>
                                                                                <Input onChange={changeFeedBrand} value={addData.item_name} name="feedBrand" type="text"></Input>
                                                                                <small className="text-danger">{item_nameerr}</small>
                                                                            </Col>
                                                                        </Row>

                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="quantity" className="font-bold flex">Quantity</Label>
                                                                                <Input onChange={showQuantity} value={addData.quantity} name="quantity" type="number"></Input>
                                                                                <small className="text-danger">{quantityerr}</small>
                                                                            </Col>
                                                                            <Col>
                                                                                <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                                <Input onChange={changeCost} value={addData.cost} name="cost" type="number"></Input>
                                                                                <small className="text-danger">{costerr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                                <Input onChange={changeRemarks} value={addData.remarks} id="remarks" name="remarks" type="text"></Input>
                                                                                <small className="text-danger">{remarkserr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                    </>
                                                                }
                                                                {/* Medicine Data */}

                                                                {/* Vaccination Data */}
                                                                {
                                                                    showInputArea === 'V' &&
                                                                    <>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="vaccinationcompany" className="font-bold flex">Vaccination Company</Label>
                                                                                <Input onChange={changeFeedCompany} value={addData.company_name} name="feedCompany" type="text"></Input>
                                                                            </Col>
                                                                            <small className="text-danger">{company_nameerr}</small>
                                                                            <Col>
                                                                                <Label for="vaccination" className="font-bold flex">Vaccination</Label>
                                                                                <Input onChange={changeFeedBrand} value={addData.item_name} name="feedBrand" type="text"></Input>
                                                                                <small className="text-danger">{item_nameerr}</small>
                                                                            </Col>

                                                                        </Row>

                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="quantity" className="font-bold flex">Quantity</Label>
                                                                                <Input onChange={showQuantity} value={addData.quantity} name="quantity" type="number"></Input>
                                                                            </Col>
                                                                            <small className="text-danger">{quantityerr}</small>
                                                                            <Col>
                                                                                <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                                <Input onChange={changeCost} value={addData.cost} name="cost" type="number"></Input>
                                                                                <small className="text-danger">{costerr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                                <Input onChange={changeRemarks} value={addData.remarks} id="remarks" name="remarks" type="text"></Input>
                                                                                <small className="text-danger">{remarkserr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                    </>
                                                                }
                                                                {/* Vaccination Data */}
                                                                {
                                                                    showInputArea === 'E' &&
                                                                    <>
                                                                        {/* Equipment Data */}
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="equipmentcompany" className="font-bold flex">Equipment Company</Label>
                                                                                <Input onChange={changeFeedCompany} value={addData.company_name} name="feedCompany" type="text"></Input>
                                                                            </Col>
                                                                            <small className="text-danger">{company_nameerr}</small>
                                                                            <Col>
                                                                                <Label for="equipment" className="font-bold flex">Equipment</Label>
                                                                                <Input onChange={changeFeedBrand} value={addData.item_name} name="feedBrand" type="text"></Input>
                                                                                <small className="text-danger">{item_nameerr}</small>
                                                                            </Col>
                                                                        </Row>

                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="quantity" className="font-bold flex">Quantity</Label>
                                                                                <Input onChange={showQuantity} value={addData.quantity} name="quantity" type="number"></Input>
                                                                            </Col>
                                                                            <small className="text-danger">{quantityerr}</small>
                                                                            <Col>
                                                                                <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                                <Input onChange={changeCost} value={addData.cost} name="cost" type="number"></Input>
                                                                                <small className="text-danger">{costerr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                                <Input onChange={changeRemarks} id="remarks" name="remarks" type="text"></Input>
                                                                                <small className="text-danger">{remarkserr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                    </>
                                                                }
                                                                {/* Equipment Data */}
                                                                {
                                                                    showInputArea === 'L' &&
                                                                    <>
                                                                        {/* Labour Data */}
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                                <Input onChange={changeCost} value={addData.cost} name="cost" type="number"></Input>
                                                                                <small className="text-danger">{costerr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                                <Input onChange={changeRemarks} value={addData.remarks} id="remarks" name="remarks" type="text"></Input>
                                                                                <small className="text-danger">{remarkserr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                    </>
                                                                }
                                                                {/* Labour Data */}
                                                                {/* Other Data */}
                                                                {
                                                                    showInputArea === 'O' &&
                                                                    <>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                                <Input onChange={changeCost} value={addData.cost} name="cost" type="number"></Input>
                                                                                <small className="text-danger">{costerr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                        <Row>
                                                                            <Col>
                                                                                <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                                <Input onChange={changeRemarks} value={addData.remarks} id="remarks" name="remarks" type="text"></Input>
                                                                                <small className="text-danger">{remarkserr}</small>
                                                                            </Col>
                                                                        </Row>
                                                                    </>
                                                                }
                                                                {/* Other Data */}
                                                            </Accordion.Body>
                                                        </Accordion.Item>
                                                    </Accordion>
                                                    {showInputArea === false ? null :
                                                        <div className="d-flex">
                                                            {loading ?
                                                                <Button className="btn" color="danger" type="submit" disabled  >
                                                                    Please wait...
                                                                    <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                                </Button>
                                                                :
                                                                <Button className="btn" color="danger" type="submit">Save</Button>
                                                            }
                                                            <Button className="btn ml-4" color="warning" type="button" onClick={closeAll} >Cancel</Button>
                                                        </div>
                                                    }
                                                </>
                                                : null}
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
export default AddPurchase;