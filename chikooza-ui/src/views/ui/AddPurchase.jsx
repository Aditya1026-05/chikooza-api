import { Spinner, Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import Accordion from 'react-bootstrap/Accordion'
import axios from 'axios';
import Modal from 'react-bootstrap/Modal';
import { Link, useLocation, useNavigate } from "react-router-dom";

const PURCHASE_DRAFT_KEY = "chikooza-add-purchase-draft";

const purchaseSteps = [
    { title: "Flock", helper: "Choose where this cost belongs" },
    { title: "Details", helper: "Enter purchase type and amount" },
    { title: "Review", helper: "Check and save" },
];

const emptyPurchaseData = {
    farm_public_id: '0',
    flock_public_id: '0',
    type: '',
    date: '',
    cost: '',
    remarks: '',
    company_name: '',
    item_name: '',
    unit: "",
    size: 50,
    item_type: 100,
    quantity: ''
};

const purchaseTypeLabels = {
    F: "Feed",
    M: "Medicine",
    V: "Vaccination",
    E: "Equipment",
    L: "Labour",
    O: "Other",
};

const readPurchaseDraft = () => {
    try {
        const draft = JSON.parse(localStorage.getItem(PURCHASE_DRAFT_KEY) || "{}");
        return {
            data: { ...emptyPurchaseData, ...(draft.data || {}) },
            showInputArea: draft.showInputArea || "0",
            purchaseStep: Number(draft.purchaseStep || 0),
        };
    } catch {
        return { data: emptyPurchaseData, showInputArea: "0", purchaseStep: 0 };
    }
};

const todayIso = () => new Date().toISOString().split("T")[0];

const AddPurchase = () => {
    const initialDraft = readPurchaseDraft();
    let [loading, setLoading] = useState(false);
    const [show, setShow] = useState(false);
    let [err, setErr] = useState('');
    let [farms, setFarms] = useState([]);
    let [showFlocks, setShowFlocks] = useState(0);
    let [flocks, setFlocks] = useState([]);
    let [showForm, setShowForm] = useState(0);
    // U: OLD: showInputArea used boolean false plus string action codes.
    // U: NEW: keep the select state as one consistent string value.
    const [showInputArea, setShowInputArea] = useState(initialDraft.showInputArea);
    const [purchaseStep, setPurchaseStep] = useState(initialDraft.purchaseStep);
    let [addData, setAddData] = useState(initialDraft.data);
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
    let [typeerr, setTypeerr] = useState('');
    let navigate = useNavigate()
    const location = useLocation();
    const prefillFarmId = String(location.state?.farmPublicId || "0");
    const prefillFlockId = String(location.state?.flockPublicId || "0");
    const hasFarmPrerequisite = farms.some((farm) => String(farm.public_id) !== "0");
    const hasFlockOptions = flocks.some((item) => String(item.flock_public_id) !== "0");

    useEffect(() => {
        // U: NEW: long purchase forms are draft-saved locally so a farmer can
        // U: leave the page and continue without retyping values.
        localStorage.setItem(PURCHASE_DRAFT_KEY, JSON.stringify({
            data: addData,
            showInputArea,
            purchaseStep,
        }));
    }, [addData, showInputArea, purchaseStep]);

    useEffect(() => {
        let cancelled = false;
        let url = `${apiPath}farm/`;
        // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, getAuthConfig()).then((res) => {
            if (cancelled) {
                return;
            }
            if (res.data.results.length === 0) {
                setFarms([{ public_id: 0, name: 'No farm available' }]);
            } else {
                setFarms(res.data.results);
            }

            if (prefillFarmId !== "0") {
                // U: NEW: when dashboard sends a selected flock here, preserve it
                // U: so farmers do not repeat farm/flock selection.
                setAddData((current) => ({
                    ...current,
                    farm_public_id: prefillFarmId,
                    flock_public_id: prefillFlockId,
                }));
                axios.get(`${apiPath}flocks/${prefillFarmId}/`, getAuthConfig()).then((flockRes) => {
                    if (cancelled) {
                        return;
                    }
                    setShowFlocks(1);
                    if (flockRes.data.results.total_records === 0) {
                        setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                        setShowForm(0);
                        return;
                    }
                    const flockList = flockRes.data.results.flock_list;
                    const hasPrefillFlock = flockList.some((item) => String(item.flock_public_id) === prefillFlockId);
                    setFlocks(flockList);
                    setShowForm(hasPrefillFlock ? 1 : 0);
                    setFlockerr(hasPrefillFlock ? '' : 'Please select a flock');
                    if (hasPrefillFlock) {
                        setPurchaseStep((currentStep) => Math.max(currentStep, 1));
                    }
                }).catch((err) => {
                    if (!cancelled) {
                        setFlocks([]);
                    }
                    handleUnauthorized(err, navigate);
                });
            }
        }).catch((err) => {
            if (cancelled) {
                return;
            }
            setFarms([{ public_id: 0, name: 'No farm available' }]);
            handleUnauthorized(err, navigate);
        });
        return () => {
            cancelled = true;
        };
    }, [navigate, prefillFarmId, prefillFlockId])
    let changeFarm = (e) => {
        setAddData({ ...addData, farm_public_id: e.target.value, flock_public_id: "0" });
        // U: OLD: e.target.value === 0 compared a string to a number.
        if (e.target.value === "0") {
            //setFarm_public_iderr('Please select farm');
            setShowFlocks(0);
            setShowForm(0);
            setFlocks([]);
        } else {
            let url = `${apiPath}flocks/${e.target.value}/`;
            axios.get(url, getAuthConfig()).then((res) => {
                setShowFlocks(1);
                setShowForm(0);
                if (res.data.results.total_records === 0) {
                    setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                } else {
                    setFlocks(res.data.results.flock_list);
                }
            }).catch((err) => {
                setFlocks([]);
                handleUnauthorized(err, navigate);
            });
        }
    }
    let changeFlocks = (e) => {
        if (e.target.value === "0") {
            setFlockerr('Flock is not valid');
            setAddData({ ...addData, flock_public_id: "0" });
            setShowForm(0);
        } else {
            setFlockerr('');
            setAddData({ ...addData, flock_public_id: e.target.value });
            setShowForm(1);
        }
    }
    const validateSelectionStep = () => {
        let valid = true;
        if (addData.farm_public_id === "0" || addData.farm_public_id === 0 || addData.farm_public_id === null) {
            setFlockerr('Select a farm and flock before adding a purchase.');
            valid = false;
        } else if (addData.flock_public_id === "0" || addData.flock_public_id === 0 || addData.flock_public_id === null) {
            setFlockerr('Select the flock this purchase belongs to.');
            valid = false;
        } else {
            setFlockerr('');
        }
        return valid;
    };

    const validatePurchaseDetails = () => {
        // U: OLD: validation was repeated per purchase type with vague "This fields" messages.
        // U: NEW: one path gives clear field-specific guidance and blocks future dates/bad values.
        let valid = true;
        const purchaseDate = addData.date || "";
        const needsItemFields = ["F", "M", "V", "E"].includes(showInputArea);
        const needsQuantity = ["M", "V", "E"].includes(showInputArea);

        if (showInputArea === "0" || addData.type === '') {
            setTypeerr('Select purchase type.');
            valid = false;
        } else {
            setTypeerr('');
        }
        if (!purchaseDate) {
            setDateerr('Purchase date is required.');
            valid = false;
        } else if (purchaseDate > todayIso()) {
            setDateerr('Purchase date cannot be in the future.');
            valid = false;
        } else {
            setDateerr('');
        }
        if (Number(addData.cost) <= 0 || addData.cost === null || addData.cost === '') {
            setCosterr('Cost must be greater than 0.');
            valid = false;
        } else {
            setCosterr('');
        }
        if ((addData.remarks || '').trim() === '') {
            setRemarkserr('Remarks are required.');
            valid = false;
        } else {
            setRemarkserr('');
        }
        if (needsItemFields && (addData.company_name || '').trim() === '') {
            setCompany_nameerr('Company name is required.');
            valid = false;
        } else {
            setCompany_nameerr('');
        }
        if (needsItemFields && (addData.item_name || '').trim() === '') {
            setItem_nameerr('Item name is required.');
            valid = false;
        } else {
            setItem_nameerr('');
        }
        if (showInputArea === "F" && Number(addData.unit) <= 0) {
            setUniterr('Number of bags must be greater than 0.');
            valid = false;
        } else {
            setUniterr('');
        }
        if (showInputArea === "F" && Number(addData.size) <= 0) {
            setSizeerr('Select a valid bag size.');
            valid = false;
        } else {
            setSizeerr('');
        }
        if (showInputArea === "F" && (addData.item_type === '' || addData.item_type === '0' || addData.item_type === null)) {
            setItem_typeerr('Select feed type.');
            valid = false;
        } else {
            setItem_typeerr('');
        }
        if (needsQuantity && Number(addData.quantity) <= 0) {
            setQuantityerr('Quantity must be greater than 0.');
            valid = false;
        } else {
            setQuantityerr('');
        }
        return valid;
    };

    const goNextStep = () => {
        if (purchaseStep === 0 && !validateSelectionStep()) {
            return;
        }
        if (purchaseStep === 1 && !validatePurchaseDetails()) {
            return;
        }
        setPurchaseStep((currentStep) => Math.min(currentStep + 1, purchaseSteps.length - 1));
    };

    const goPreviousStep = () => {
        setPurchaseStep((currentStep) => Math.max(currentStep - 1, 0));
    };

    const resetPurchaseForm = ({ keepSelection = false } = {}) => {
        const selection = keepSelection
            ? {
                farm_public_id: addData.farm_public_id,
                flock_public_id: addData.flock_public_id,
            }
            : {};
        setAddData({ ...emptyPurchaseData, ...selection });
        setShowInputArea("0");
        setPurchaseStep(keepSelection ? 1 : 0);
        setShowForm(keepSelection && addData.flock_public_id !== "0" ? 1 : 0);
        setErr('');
        localStorage.removeItem(PURCHASE_DRAFT_KEY);
    };

    const save = (e) => {
        e.preventDefault();
        setLoading(false);
        if (!validateSelectionStep()) {
            setPurchaseStep(0);
            return;
        }
        if (!validatePurchaseDetails()) {
            setPurchaseStep(1);
            return;
        }
        if (validateSelectionStep() && validatePurchaseDetails()) {
            setLoading(true)
            let url = `${apiPath}purchase/`;
            axios.post(url, addData, getAuthConfig()).then((res) => {
                setShow(true);
                setLoading(false);
                setTimeout((() => {
                    setShow(false);
                }), 3000);
                resetPurchaseForm({ keepSelection: true });
            }).catch((err) => {
                setLoading(false);
                setErr('Something went wrong. Please try again');
                handleUnauthorized(err, navigate);
            });
        }
    }
    const showInputs = (e) => {
        setShowInputArea(e.target.value);
        setTypeerr('');
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
        e.target.value.trim()==='' ? setCompany_nameerr('Company name is required.') : setCompany_nameerr('');
        setAddData({ ...addData, company_name: e.target.value });
    }
    let changeCost = (e) => {
        setAddData({ ...addData, cost: e.target.value });
        Number(e.target.value) <= 0 ? setCosterr('Cost must be greater than 0.') : setCosterr('');
    }
    let changeFeedBrand = (e) => {
        e.target.value.trim()==='' ? setItem_nameerr('Item name is required.') : setItem_nameerr('');
        setAddData({ ...addData, item_name: e.target.value });
    }
    let changeNumberOfBags = (e) => {
        Number(e.target.value) < 1 ? setUniterr('Number of bags must be greater than 0.') : setUniterr('');
        setAddData({ ...addData, unit: e.target.value });
    }
    let changeBagsSize = (e) => {
        setAddData({ ...addData, size: e.target.value });
    }
    let changeRemarks = (e) => {
        setAddData({ ...addData, remarks: e.target.value });
        e.target.value.trim() === '' ? setRemarkserr('Remarks are required.') : setRemarkserr('');
    }
    let changeFeedType = (e) => {
        setAddData({ ...addData, item_type: e.target.value });
    }
    let changePurchaseDate = (e) => {
        setAddData({ ...addData, date: e.target.value });
        if (e.target.value.trim() === '') {
            setDateerr('Purchase date is required.');
        } else if (e.target.value > todayIso()) {
            setDateerr('Purchase date cannot be in the future.');
        } else {
            setDateerr('');
        }
    }
    let showQuantity = (e) => {
        setAddData({ ...addData, quantity: e.target.value });
        Number(e.target.value) <= 0 ? setQuantityerr('Quantity must be greater than 0.') : setQuantityerr('');
    }
    let closeAll = () => {
        resetPurchaseForm();
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
                                        {!hasFarmPrerequisite && (
                                            <div className="form-prerequisite-card">
                                                <span>Farm required</span>
                                                <p>Add a farm and flock first. Purchases are saved against a flock so reports and Farmer AI can calculate costs correctly.</p>
                                                <Link to="/addfarm">Add farm first</Link>
                                            </div>
                                        )}
                                        <Form onSubmit={save}>
                                            <div className="form-stepper" aria-label="Purchase entry steps">
                                                {purchaseSteps.map((step, index) => (
                                                    <button
                                                        key={step.title}
                                                        type="button"
                                                        className={index === purchaseStep ? "is-active" : index < purchaseStep ? "is-complete" : ""}
                                                        onClick={() => setPurchaseStep(index)}
                                                    >
                                                        <span>{index + 1}</span>
                                                        <strong>{step.title}</strong>
                                                        <small>{step.helper}</small>
                                                    </button>
                                                ))}
                                            </div>
                                            {purchaseStep === 0 && (
                                                <>
                                                    <Label for="farmselect">Select Farm</Label>
                                                    <FormGroup>
                                                        <div className="input-group">
                                                            <Input onChange={changeFarm} value={addData.farm_public_id || "0"} id="farmSelect" name="farm" type="select">
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
                                                    </FormGroup>
                                                    {(showFlocks === 1) ?
                                                        <FormGroup>
                                                            <Label for="farmselect">Select Flocks</Label>
                                                            <div className="input-group">
                                                                <Input onChange={changeFlocks} value={addData.flock_public_id} id="farmSelect" name="flock" type="select">
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
                                                            <small className="text-danger">{flockerr}</small>
                                                        </FormGroup>
                                                        : null}
                                                    {(showFlocks === 1 && !hasFlockOptions) ?
                                                        <div className="form-prerequisite-card">
                                                            <span>Flock required</span>
                                                            <p>This farm does not have a flock yet. Add a flock before entering feed, medicine, equipment, labour, or other purchases.</p>
                                                            <Link to="/addflock">Add flock</Link>
                                                        </div>
                                                        : null}
                                                </>
                                            )}
                                            {(purchaseStep === 1 && showForm === 1) ?
                                                <>
                                                    <Accordion defaultActiveKey="0" className="mb-3">
                                                        <Accordion.Item eventKey="0">
                                                            <Accordion.Header>Purchase Details</Accordion.Header>
                                                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                                <Row>
                                                                    <Col>
                                                                        <Label for="purchaseDate" className="font-bold flex">Purchase Date</Label>
                                                                        <Input onChange={changePurchaseDate} value={addData.date || ""} name="purchaseDate" type="date" max={todayIso()}></Input>
                                                                        <small className="text-danger">{dateerr}</small>
                                                                    </Col>
                                                                    <Col>
                                                                        <Label for="action" className="font-bold">Action</Label>
                                                                        <Input value={showInputArea} onChange={showInputs} name="selectAction" type="select">
                                                                            <option value='0' disabled>Select</option>
                                                                            <option value="F">Feed</option>
                                                                            <option value="M">Medicine</option>
                                                                            <option value="V">Vaccination</option>
                                                                            <option value="E">Equipment</option>
                                                                            <option value="L">Labour</option>
                                                                            <option value="O">Other</option>
                                                                        </Input>
                                                                        <small className="text-danger">{typeerr}</small>
                                                                    </Col>
                                                                </Row>
                                                                {showInputArea === "0" && (
                                                                    <div className="form-helper-panel mt-3">
                                                                        <strong>Select purchase type</strong>
                                                                        <p>Choose feed, medicine, vaccination, equipment, labour, or other. The form will show only the fields required for that type.</p>
                                                                    </div>
                                                                )}

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
                                                                                    <option value="0" disabled>Select</option>
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
                                                                                    <option value='0' disabled>Select</option>
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
                                                </>
                                                : null}
                                            {purchaseStep === 1 && showForm !== 1 && (
                                                <div className="form-helper-panel">
                                                    <strong>Select farm and flock first</strong>
                                                    <p>Purchase records are saved against one flock. Complete the Flock step before adding purchase details.</p>
                                                </div>
                                            )}
                                            {purchaseStep === 2 && (
                                                <div className="form-review-card">
                                                    <span>Review purchase</span>
                                                    <dl>
                                                        <div><dt>Type</dt><dd>{addData.type || "Not selected"}</dd></div>
                                                        <div><dt>Date</dt><dd>{addData.date || "Not added"}</dd></div>
                                                        <div><dt>Company</dt><dd>{addData.company_name || "Not needed"}</dd></div>
                                                        <div><dt>Item</dt><dd>{addData.item_name || "Not needed"}</dd></div>
                                                        <div><dt>Quantity</dt><dd>{addData.quantity || addData.unit || "Not needed"}</dd></div>
                                                        <div><dt>Cost</dt><dd>{addData.cost ? `Rs. ${addData.cost}` : "Not added"}</dd></div>
                                                        <div><dt>Remarks</dt><dd>{addData.remarks || "Not added"}</dd></div>
                                                    </dl>
                                                </div>
                                            )}
                                            <div className="form-wizard-actions">
                                                {purchaseStep > 0 && (
                                                    <Button className="btn" color="secondary" type="button" onClick={goPreviousStep}>Back</Button>
                                                )}
                                                {purchaseStep < purchaseSteps.length - 1 && (
                                                    <Button className="btn" color="danger" type="button" onClick={goNextStep}>Next</Button>
                                                )}
                                                {purchaseStep === purchaseSteps.length - 1 && (
                                                    loading ?
                                                        <Button className="btn" color="danger" type="submit" disabled>
                                                            Please wait...
                                                            <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                        </Button>
                                                        :
                                                        <Button className="btn" color="danger" type="submit">Save</Button>
                                                )}
                                                <Button className="btn" color="warning" type="button" onClick={closeAll}>Cancel</Button>
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
export default AddPurchase;
