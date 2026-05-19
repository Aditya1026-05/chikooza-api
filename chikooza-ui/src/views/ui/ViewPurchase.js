import { Spinner, Alert, Row, Col, Table, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, config } from "../../Constants";
import { useState, useEffect } from "react";
import Accordion from 'react-bootstrap/Accordion'
import axios from 'axios';
import Modal from 'react-bootstrap/Modal';
import { useParams } from "react-router-dom";
import { useNavigate } from "react-router-dom";

const ViewPurchase = () => {
    let { flockPublicId, purchasePublicID } = useParams();
    let [loading, setLoading] = useState(false);
    const [show, setShow] = useState(false);
    const [flock, setFlock] = useState({});
    const [farm, setFarm] = useState({});
    const [purchase, setPurchase] = useState({});
    let [err, setErr] = useState('');
    let [remarkserr, setRemarkserr] = useState('');
    let [costerr, setCosterr] = useState('');
    let [dateerr, setDateerr] = useState('');
    let [company_nameerr, setCompany_nameerr] = useState('');
    let [item_nameerr, setItem_nameerr] = useState('');
    let [uniterr, setUniterr] = useState('');
    let [sizeerr, setSizeerr] = useState('');
    let [item_typeerr, setItem_typeerr] = useState('');
    let [quantityerr, setQuantityerr] = useState('');

    const navigate = useNavigate()


    useEffect(() => {
        let url = `${apiPath}flocksDetail/${flockPublicId}/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setFlock({ flock_public_id: res.data.results.flock_public_id, flock_name: res.data.results.flock_name });
            setFarm({ farm_public_id: res.data.results.farm_public_id, farm_name: res.data.results.farm_name });
        }).catch((err) => {
            setFlock({ flock_public_id: 0, flock_name: 'No flock available' });
            setFarm({ farm_public_id: 0, farm_name: 'No farm available' });
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    useEffect(() => {
        let url = `${apiPath}purchase/${purchasePublicID}/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setPurchase(res.data.results);
        }).catch((err) => {
            setPurchase();
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    const save = (e) => {
        e.preventDefault();
        setLoading(true);
        let error = 0;

        if (purchase.type === 'Feed') {
            if (purchase.cost < 0 || purchase.cost === '' || purchase.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (purchase.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (purchase.date === null || purchase.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
            if (purchase.company_name.trim()==='') { setCompany_nameerr('This fields is required'); error = 1; } else { setCompany_nameerr(''); }
            if (purchase.item_name.trim()==='') { setItem_nameerr('This fields is required'); error = 1; } else { setItem_nameerr(''); }
            if (purchase.unit<1) { setUniterr('This fields is required'); error = 1; } else { setUniterr(''); }
            //if (purchase.item_type.trim() === '' || purchase.item_type == null) { setItem_typeerr('This fields is required'); error = 1; } else { setItem_typeerr(''); }
            //if (purchase.size.trim() === '' || purchase.size == null) { setSizeerr('This fields is required'); error = 1; } else { setSizeerr(''); }
            //if (purchase.quantity < 0) { setQuantityerr('This fields is required'); error = 1; } else { setQuantityerr(''); }
        } else if (purchase.type === 'Medicine') {
            if (purchase.cost < 0 || purchase.cost === '' || purchase.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (purchase.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (purchase.date === null || purchase.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
            if (purchase.company_name.trim()==='') { setCompany_nameerr('This fields is required'); error = 1; } else { setCompany_nameerr(''); }
            if (purchase.item_name.trim()==='') { setItem_nameerr('This fields is required'); error = 1; } else { setItem_nameerr(''); }
            if (purchase.quantity < 0 || purchase.quantity === '') { setQuantityerr('This fields is required'); error = 1; } else { setQuantityerr(''); }
        } else if (purchase.type === 'Vaccination') {
            if (purchase.cost < 0 || purchase.cost === ''  || purchase.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (purchase.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (purchase.date === null || purchase.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
            if (purchase.company_name.trim()==='') { setCompany_nameerr('This fields is required'); error = 1; } else { setCompany_nameerr(''); }
            if (purchase.item_name.trim()==='') { setItem_nameerr('This fields is required'); error = 1; } else { setItem_nameerr(''); }
            if (purchase.quantity < 0 || purchase.quantity === '' || purchase.quantity === null) { setQuantityerr('This fields is required'); error = 1; } else { setQuantityerr(''); }
        } else if (purchase.type === 'Equipment') {
            if (purchase.cost < 0 || purchase.cost === ''  || purchase.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (purchase.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (purchase.date === null || purchase.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
            if (purchase.company_name.trim()==='') { setCompany_nameerr('This fields is required'); error = 1; } else { setCompany_nameerr(''); }
            if (purchase.item_name.trim()==='') { setItem_nameerr('This fields is required'); error = 1; } else { setItem_nameerr(''); }
            if (purchase.quantity < 0 || purchase.quantity === ''  || purchase.quantity === null) { setQuantityerr('This fields is required'); error = 1; } else { setQuantityerr(''); }
        } else if (purchase.type === 'Labour') {
            if (purchase.cost < 0 || purchase.cost === ''  || purchase.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (purchase.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (purchase.date === null || purchase.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
        } else if (purchase.type === 'Other') {
            if (purchase.cost < 0 || purchase.cost === ''  || purchase.cost === null) { setCosterr('This fields is not valid'); error = 1; } else { setCosterr(''); }
            if (purchase.remarks.trim() === '' ) { setRemarkserr('This fields is required'); error = 1; } else { setRemarkserr(''); }
            if (purchase.date === null || purchase.date === '') { setDateerr('This fields is required'); error = 1; } else { setDateerr(''); }
        }

        if (error == 0) {
            if (purchase.type == 'Other' || purchase.type == 'Labour') {
                purchase.item_name = '0';
                purchase.company_name = '0';
            }
            let url = `${apiPath}purchase/${purchase.public_id}/`;
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.patch(url, purchase, config).then((res) => {
                setShow(true);
                const myTimeout = setTimeout((() => {
                    setShow(false);
                }), 3000);
            }).catch((err) => {
                setErr('Something went wrong. Please try again');
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }
        setLoading(false);
    }
    let changeFeedCompany = (e) => {
        e.target.value.trim()==='' ? setCompany_nameerr('This fields is required') : setCompany_nameerr('');
        setPurchase({ ...purchase, company_name: e.target.value });
    }
    let changeCost = (e) => {
        setPurchase({ ...purchase, cost: e.target.value });
        e.target.value < 0 || e.target.value === '' ? setCosterr('This fields is required') : setCosterr('');
    }
    let changeFeedBrand = (e) => {
        e.target.value.trim()==='' ? setItem_nameerr('This fields is required') : setItem_nameerr('');
        setPurchase({ ...purchase, item_name: e.target.value });
    }
    let changeNumberOfBags = (e) => {
        e.target.value<1 || e.target.value === '' ? setUniterr('This fields is not valid') : setUniterr('');

        // setPurchase({ ...purchase, unit: e.target.value });

//MV-23-6-25- 17-10 set newUnit & newQuantity upon change in values
        const newUnit = e.target.value;
        let newQuantity = purchase.quantity;
        if (purchase.type === 'Feed' && newUnit > 0 && purchase.size > 0) {
            newQuantity = newUnit * purchase.size;
        }
        setPurchase({ ...purchase, unit: newUnit, quantity: newQuantity });
//MV-23-6-25- 17-10 change end

    }
    let changeBagsSize = (e) => {
        // setPurchase({ ...purchase, unit: e.target.value });

//MV-23-6-25- 17-10 set newSize & newQuantity upon change in values
        const newSize = e.target.value;
        let newQuantity = purchase.quantity;
        if (purchase.type === 'Feed' && purchase.unit > 0 && newSize > 0) {
            newQuantity = purchase.unit * newSize;
        }
        setPurchase({ ...purchase, size: newSize, quantity: newQuantity });
//MV-23-6-25- 17-10 change end

    }

    let changeRemarks = (e) => {
        setPurchase({ ...purchase, remarks: e.target.value });
        e.target.value.trim() == '' ? setRemarkserr('This fields is required') : setRemarkserr('');
    }
    let changeFeedType = (e) => {
        setPurchase({ ...purchase, item_type: e.target.value });
    }
    let changePurchaseDate = (e) => {
        setPurchase({ ...purchase, date: e.target.value });
        e.target.value.trim() == '' ? setDateerr('This fields is required') : setDateerr('');
    }
    let showQuantity = (e) => {
        setPurchase({ ...purchase, quantity: e.target.value });
        e.target.value < 0 || e.target.value === ''  ? setQuantityerr('This fields is not valid') : setQuantityerr('');
    }
    let cancel = () => {
        navigate("/listpurchase")

    }
    return (
        <Row>
            <Modal show={show} backdrop="static" keyboard={false} >
                <Modal.Header>
                </Modal.Header>
                <Modal.Body>
                    <Alert color="success">
                        Purchase Updated successfully
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
                        update Purchase
                    </CardTitle>
                    <CardBody>
                        <Row className="mt-3">
                            <Col sm="12" md={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        {(err != '') && <Alert color="danger">{err}</Alert>}
                                        <Form onSubmit={save}>
                                            <Label for="farmselect">Select Farm</Label>
                                            <FormGroup>
                                                <div className="input-group">
                                                    <Input id="farmSelect" name="farm" type="select">
                                                        <option defaultValue={farm.farm_public_id}>{farm.farm_name}</option>
                                                    </Input>
                                                </div>
                                            </FormGroup>
                                            <FormGroup>
                                                <Label for="farmselect">Select Flocks</Label>
                                                <div className="input-group">
                                                    <Input id="farmSelect" name="flock" type="select">
                                                        <option defaultValue={flock.flock_public_id}>{flock.flock_name}</option>
                                                    </Input>
                                                </div>
                                            </FormGroup>
                                            <Accordion defaultActiveKey="0" className="mb-3">
                                                <Accordion.Item eventKey="0">
                                                    <Accordion.Header>Purchase Details</Accordion.Header>
                                                    <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                        <Row>
                                                            <Col>
                                                                <Label for="purchaseDate" className="font-bold flex">Purchase Date</Label>
                                                                <Input defaultValue={purchase.date} onChange={changePurchaseDate} name="purchaseDate" type="date"></Input>
                                                                <small className="text-danger">{dateerr}</small>
                                                            </Col>
                                                            <Col>
                                                                <Label for="action" className="font-bold">Action</Label>
                                                                <Input name="selectAction" type="select">
                                                                    <option>{purchase.type}</option>
                                                                </Input>
                                                            </Col>
                                                        </Row>
                                                        {/* Feed Data */}
                                                        {
                                                            purchase.type == 'Feed' &&
                                                            <>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="feedCompany" className="font-bold flex">Feed Company</Label>
                                                                        <Input defaultValue={purchase.company_name} onChange={changeFeedCompany} name="feedCompany" type="text"></Input>
                                                                        <small className="text-danger">{company_nameerr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="feedBrand" className="font-bold flex">Feed Brand</Label>
                                                                        <Input defaultValue={purchase.item_name} onChange={changeFeedBrand} name="feedBrand" type="text">
                                                                        </Input>
                                                                        <small className="text-danger">{item_nameerr}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="numberOfBags" className="font-bold flex">No of Bags</Label>
                                                                        <Input defaultValue={purchase.unit} onChange={changeNumberOfBags} name="numberOfBags" type="number">
                                                                        </Input>
                                                                        <small className="text-danger">{uniterr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="bagsSize" className="font-bold">Bags Size</Label>
                                                                        <Input onChange={changeBagsSize} name="bagsSize" type="select">
                                                                            <option disabled={true} selected>Select</option>
                                                                            <option selected={purchase.size == 50} value="50">50 KG</option>
                                                                            <option selected={purchase.size == 100} value="100">100 KG</option>
                                                                        </Input>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="feedType" className="font-bold">Feed Type</Label>
                                                                        <Input onChange={changeFeedType} name="feedType" type="select">
                                                                            <option value='0' disabled selected>Select</option>
                                                                            <option selected={purchase.item_type == 100} value="100">Pre Starter</option>
                                                                            <option selected={purchase.item_type == 101} value="101">Starter</option>
                                                                            <option selected={purchase.item_type == 102} value="102">Finisher</option>
                                                                        </Input>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="cost" className="font-bold flex">Cost</Label>
                                                                        <Input defaultValue={purchase.cost} onChange={changeCost} name="cost" type="number"></Input>
                                                                        <small className="text-danger">{costerr}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                        <Input defaultValue={purchase.remarks} onChange={changeRemarks} id="remarks" name="remarks" type="text"></Input>
                                                                        <small className="text-danger">{remarkserr}</small>
                                                                    </Col>
                                                                </Row>
                                                            </>
                                                        }
                                                        {/* Feed Data */}

                                                        {/* Medicine Data */}
                                                        {
                                                            purchase.type == 'Medicine' &&
                                                            <>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="medicinecompany" className="font-bold flex">Medicine Company</Label>
                                                                        <Input defaultValue={purchase.company_name} onChange={changeFeedCompany} name="feedCompany" type="text"></Input>
                                                                        <small className="text-danger">{company_nameerr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="medicine" className="font-bold flex">Medicine</Label>
                                                                        <Input defaultValue={purchase.item_name} onChange={changeFeedBrand} name="feedBrand" type="text"></Input>
                                                                        <small className="text-danger">{item_nameerr}</small>
                                                                    </Col>
                                                                </Row>

                                                                <Row>
                                                                    <Col>
                                                                        <Label for="quantity" className="font-bold flex">Quantity</Label>
                                                                        <Input defaultValue={purchase.quantity} onChange={showQuantity} name="quantity" type="number"></Input>
                                                                        <small className="text-danger">{quantityerr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                        <Input defaultValue={purchase.cost} onChange={changeCost} name="cost" type="number"></Input>
                                                                        <small className="text-danger">{costerr}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                        <Input defaultValue={purchase.remarks} onChange={changeRemarks} id="remarks" name="remarks" type="text"></Input>
                                                                        <small className="text-danger">{remarkserr}</small>
                                                                    </Col>
                                                                </Row>
                                                            </>
                                                        }
                                                        {/* Medicine Data */}

                                                        {/* Vaccination Data */}
                                                        {
                                                            purchase.type == 'Vaccination' &&
                                                            <>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="vaccinationcompany" className="font-bold flex">Vaccination Company</Label>
                                                                        <Input defaultValue={purchase.company_name} onChange={changeFeedCompany} name="feedCompany" type="text"></Input>
                                                                        <small className="text-danger">{company_nameerr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="vaccination" className="font-bold flex">Vaccination</Label>
                                                                        <Input defaultValue={purchase.item_name} onChange={changeFeedBrand} name="feedBrand" type="text"></Input>
                                                                        <small className="text-danger">{item_nameerr}</small>
                                                                    </Col>
                                                                </Row>

                                                                <Row>
                                                                    <Col>
                                                                        <Label for="quantity" className="font-bold flex">Quantity</Label>
                                                                        <Input defaultValue={purchase.quantity} onChange={showQuantity} name="quantity" type="number"></Input>
                                                                        <small className="text-danger">{quantityerr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                        <Input defaultValue={purchase.cost} onChange={changeCost} name="cost" type="number"></Input>
                                                                        <small className="text-danger">{costerr}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                        <Input defaultValue={purchase.remarks} onChange={changeRemarks} id="remarks" name="remarks" type="text"></Input>
                                                                        <small className="text-danger">{remarkserr}</small>
                                                                    </Col>
                                                                </Row>
                                                            </>
                                                        }
                                                        {/* Vaccination Data */}
                                                        {
                                                            purchase.type == 'Equipment' &&
                                                            <>
                                                  z              {/* Equipment Data */}
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="equipmentcompany" className="font-bold flex">Equipment Company</Label>
                                                                        <Input defaultValue={purchase.company_name} onChange={changeFeedCompany} name="feedCompany" type="text"></Input>
                                                                        <small className="text-danger">{company_nameerr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="equipment" className="font-bold flex">Equipment</Label>
                                                                        <Input defaultValue={purchase.item_name} onChange={changeFeedBrand} name="feedBrand" type="text"></Input>
                                                                        <small className="text-danger">{item_nameerr}</small>
                                                                    </Col>
                                                                </Row>

                                                                <Row>
                                                                    <Col>
                                                                        <Label for="quantity" className="font-bold flex">Quantity</Label>
                                                                        <Input defaultValue={purchase.quantity} onChange={showQuantity} name="quantity" type="number"></Input>
                                                                        <small className="text-danger">{quantityerr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                        <Input defaultValue={purchase.cost} onChange={changeCost} name="cost" type="number"></Input>
                                                                        <small className="text-danger">{costerr}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                        <Input defaultValue={purchase.remarks} onChange={changeRemarks} id="remarks" name="remarks" type="text"></Input>
                                                                        <small className="text-danger">{remarkserr}</small>
                                                                    </Col>
                                                                </Row>
                                                            </>
                                                        }
                                                        {/* Equipment Data */}
                                                        {
                                                            purchase.type == 'Labour' &&
                                                            <>
                                                                {/* Labour Data */}
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                        <Input defaultValue={purchase.cost} onChange={changeCost} name="cost" type="number"></Input>
                                                                        <small className="text-danger">{costerr}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                        <Input defaultValue={purchase.remarks} onChange={changeRemarks} id="remarks" name="remarks" type="text"></Input>
                                                                        <small className="text-danger">{remarkserr}</small>
                                                                    </Col>
                                                                </Row>
                                                            </>
                                                        }
                                                        {/* Labour Data */}
                                                        {/* Other Data */}
                                                        {
                                                            purchase.type == 'Other' &&
                                                            <>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="Cost" className="font-bold flex">Cost</Label>
                                                                        <Input defaultValue={purchase.cost} onChange={changeCost} name="cost" type="number"></Input>
                                                                        <small className="text-danger">{costerr}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="remarks" className="font-bold flex">Remarks</Label>
                                                                        <Input defaultValue={purchase.remarks} onChange={changeRemarks} id="remarks" name="remarks" type="text"></Input>
                                                                        <small className="text-danger">{remarkserr}</small>
                                                                    </Col>
                                                                </Row>
                                                            </>
                                                        }
                                                        {/* Other Data */}

                                                    </Accordion.Body>
                                                </Accordion.Item>
                                            </Accordion>
                                            <div className="d-flex">
                                                {loading ?
                                                    <Button className="btn" color="danger" type="submit" disabled  >
                                                        Updateing...
                                                        <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                    </Button>
                                                    :
                                                    <Button className="btn" color="danger" type="submit">update</Button>
                                                }
                                                <Button className="btn ml-4" color="warning" type="button" onClick={cancel} >Cancel</Button>
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
export default ViewPurchase;