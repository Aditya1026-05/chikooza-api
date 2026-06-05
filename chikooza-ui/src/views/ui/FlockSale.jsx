import { Row, Col, Card, CardTitle, CardBody, Alert, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
import Accordion from 'react-bootstrap/Accordion';
// U: OLD: import Moment from 'react-moment';
// U: NEW: use the existing moment dependency directly to avoid the abandoned React wrapper.
import Modal from 'react-bootstrap/Modal';
import Spinner from 'react-bootstrap/Spinner';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import moment from "moment";

const getFlockAgeInDays = (hatchDate) => {
    if (!hatchDate) {
        return "";
    }

    const age = moment().diff(moment(hatchDate), "days");
    return Number.isFinite(age) ? Math.max(age, 0) : "";
};

const SALE_DRAFT_KEY = "chikooza-flock-sale-draft";
const DAILY_SELECTOR_DRAFT_KEY = "chikooza-daily-selector-draft";

const saleSteps = [
    { title: "Flock", helper: "Choose farm and flock" },
    { title: "Sale", helper: "Select lifting type" },
    { title: "Details", helper: "Add sale and buyer data" },
    { title: "Review", helper: "Check and save" },
];

const emptySaleData = {
    farm: null,
    flock: null,
    selType: null,
    date: '',
    sellcount: '',
    selltwt: '',
    sellrate: '',
    sellamount: '',
    sellavgweight: 0,
    totalCost: 0,
    buyername: "",
    buyeraddress: "",
    buyerphone: "",
    buyeremail: "",
    buyervehicle: "",
    buyerremarks: "",
};

const emptySalePopupData = {
    totalfeed: 0,
    med: 0,
    vac: 0,
    ach: 0,
    rc: 0,
    pi: 0,
    ri: 0,
    ei: 0,
    sri: 0,
    totalicentive: 0,
    pcr: 0,
    stg: 0,
    em: 0,
    fr: 0,
    totalpnl: 0,
    ltds: 0,
    lamct: 0,
    ot: 0,
};

const readSaleDraft = () => {
    try {
        const draft = JSON.parse(localStorage.getItem(SALE_DRAFT_KEY) || "{}");
        return {
            data: { ...emptySaleData, ...(draft.data || {}) },
            dataPopUp: { ...emptySalePopupData, ...(draft.dataPopUp || {}) },
            saleStep: Number(draft.saleStep || 0),
        };
    } catch {
        return { data: emptySaleData, dataPopUp: emptySalePopupData, saleStep: 0 };
    }
};

const readSelectorDraft = () => {
    try {
        return JSON.parse(localStorage.getItem(DAILY_SELECTOR_DRAFT_KEY) || "{}");
    } catch {
        return {};
    }
};

const getSaleTypeLabel = (saleType) => {
    if (saleType === "partial_lifting") {
        return "Partial Lifting";
    }
    if (saleType === "final_lifting") {
        return "Final Lifting";
    }
    return "Not selected";
};

const FlockSale = () => {
    const [initialDraft] = useState(() => readSaleDraft());
    let [show, setShow] = useState(false);
    let [modelShow, setModelShow] = useState(false);
    let [farms, setFarms] = useState([]);
    let [flocks, setFlocks] = useState([]);
    let [flock, setFlock] = useState([]);
    let [feed, setFeed] = useState([]);
    let [showForm, setShowForm] = useState(initialDraft.saleStep >= 2);
    let [showFlocks, setShowFlocks] = useState(Boolean(initialDraft.data.farm));
    let [showFlockSale, setShowFlockSale] = useState(Boolean(initialDraft.data.flock));
    let [showButton, setShowButton] = useState(Boolean(initialDraft.data.selType && initialDraft.data.selType !== "0"));
    const [existingSales, setExistingSales] = useState([]);
    const [saleReviewLoading, setSaleReviewLoading] = useState(false);
    const [saleStep, setSaleStep] = useState(initialDraft.saleStep);
    // let [data, setData] = useState({ farm: null, flock: null, selType: null, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 });

//MV-16-6-25- 17-10 added buyeremail
    let [data, setData] = useState(initialDraft.data);
//MV-16-6-25- 17-10 change end

    let [dataPopUp, setDataPopUp] = useState(initialDraft.dataPopUp);
    const [activeSelectorDraft] = useState(() => readSelectorDraft());
    let [error, setError] = useState({});
    let [totalChickCount, setTotalChickCount] = useState(0);
    let [submitError, setSubmitError] = useState('');
    let [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const prefillFarmId = String(location.state?.farmPublicId || "0");
    const prefillFlockId = String(location.state?.flockPublicId || "0");
    const hasFarmPrerequisite = farms.some((farm) => String(farm.public_id) !== "0");
    const hasFlockOptions = flocks.some((item) => String(item.flock_public_id) !== "0");
    const saleReviewTotal = existingSales.reduce((total, item) => total + Number(item.cost || 0), 0);

    const loadExistingSales = (flockPublicId) => {
        if (!flockPublicId || String(flockPublicId) === "0") {
            setExistingSales([]);
            return;
        }

        setSaleReviewLoading(true);
        axios.get(`${apiPath}sales/?flock_public_id=${flockPublicId}`, getAuthConfig()).then((res) => {
            setExistingSales(res.data.results.sales_list || []);
        }).catch((err) => {
            setExistingSales([]);
            handleUnauthorized(err, navigate);
        }).finally(() => {
            setSaleReviewLoading(false);
        });
    };

    const loadCurrentBirdCount = (selectedFlock) => {
        if (!selectedFlock?.flock_public_id) {
            setTotalChickCount(0);
            return;
        }

        axios.get(`${apiPath}dailyDataLastDate/${selectedFlock.flock_public_id}/`, getAuthConfig()).then((dailyRes) => {
            setTotalChickCount(dailyRes.data.results.current_bird_count);
        }).catch((err) => {
            setTotalChickCount(selectedFlock.actual_birds);
            handleUnauthorized(err, navigate);
        });
    };

    const selectFlockForSale = (selectedFlock, { resetSaleFields = false, nextStep = 0 } = {}) => {
        if (!selectedFlock || String(selectedFlock.flock_public_id) === "0") {
            setFlock([]);
            setShowFlockSale(false);
            setShowForm(false);
            setShowButton(false);
            setData((current) => ({ ...emptySaleData, farm: current.farm || null }));
            setExistingSales([]);
            setTotalChickCount(0);
            setSaleStep(0);
            return;
        }

        setData((current) => ({
            ...(resetSaleFields ? emptySaleData : current),
            farm: selectedFlock.farm_public_id || current.farm,
            flock: selectedFlock.flock_public_id,
            ...(resetSaleFields
                ? {
                    selType: null,
                    date: '',
                    sellcount: '',
                    selltwt: '',
                    sellrate: '',
                    sellamount: '',
                }
                : {}),
        }));
        setFlock(selectedFlock);
        setShowFlockSale(true);
        setShowForm(resetSaleFields ? false : nextStep >= 2);
        setShowButton(resetSaleFields ? false : Boolean(data.selType && data.selType !== "0"));
        if (resetSaleFields) {
            setDataPopUp(emptySalePopupData);
        }
        setError({});
        setSubmitError("");
        setSaleStep(nextStep);
        loadExistingSales(selectedFlock.flock_public_id);
        loadCurrentBirdCount(selectedFlock);
    };

    function successMsg() {
        setShow(false);
    }

    useEffect(() => {
        // U: NEW: sale forms contain flock, buyer and cost fields, so keep a
        // U: local draft instead of losing the farmer's work on navigation.
        localStorage.setItem(SALE_DRAFT_KEY, JSON.stringify({
            data,
            dataPopUp,
            saleStep,
            updatedAt: Date.now(),
        }));
    }, [data, dataPopUp, saleStep]);

    const validateSaleSelection = () => {
        if (!data.farm || data.farm === "0") {
            setSubmitError("Select a farm before recording sale data.");
            return false;
        }
        if (!data.flock || data.flock === "0") {
            setSubmitError("Select the flock being sold.");
            return false;
        }
        setSubmitError("");
        return true;
    };

    const validateSaleType = () => {
        if (!data.selType || data.selType === "0") {
            setSubmitError("Select whether this is partial lifting or final lifting.");
            return false;
        }
        setSubmitError("");
        return true;
    };

    const validateSaleDetails = () => {
        // U: OLD: sale validation lived inside save and allowed several bad
        // U: values to reach the final button. NEW: the same checks guard the
        // U: wizard step and final submit.
        let validationError = { status: 0, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', phone: '', email: '' };
        const liftingCount = Number(data.sellcount);
        const availableBirds = Number(totalChickCount || 0);
        const saleDate = data.date || "";

        if (!data.flock) {
            validationError.sellcount = 'Please select flock first.';
            validationError.status = 1;
        }
        if (!data.selType || data.selType === "0") {
            validationError.sellcount = 'Please select sale type.';
            validationError.status = 1;
        }
        if (!saleDate) {
            validationError.date = 'Date is required.';
            validationError.status = 1;
        } else if (moment(saleDate).isAfter(moment(), "day")) {
            validationError.date = 'Sale date cannot be in the future.';
            validationError.status = 1;
        } else if (flock.hatch_date && moment(saleDate).isBefore(moment(flock.hatch_date), "day")) {
            validationError.date = 'Sale date cannot be before hatch date.';
            validationError.status = 1;
        }
        if (data.sellcount === null || data.sellcount === '' || liftingCount <= 0) {
            validationError.sellcount = 'Lifting count must be greater than 0.';
            validationError.status = 1;
        } else if (availableBirds > 0 && liftingCount > availableBirds) {
            validationError.sellcount = `Lifting count cannot exceed current birds (${availableBirds}).`;
            validationError.status = 1;
        }
        if (data.selltwt === null || data.selltwt === '' || Number(data.selltwt) <= 0) {
            validationError.selltwt = 'Total weight must be greater than 0.';
            validationError.status = 1;
        }
        if (data.sellrate === null || data.sellrate === '' || Number(data.sellrate) <= 0) {
            validationError.sellrate = 'Rate must be greater than 0.';
            validationError.status = 1;
        }
        if (data.buyerphone && !/^\d{10}$/.test(data.buyerphone)) {
            validationError.phone = 'Buyer phone must be 10 digits.';
            validationError.status = 1;
        }
        if (data.buyeremail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.buyeremail)) {
            validationError.email = 'Enter a valid buyer email.';
            validationError.status = 1;
        }

        setError({
            ...error,
            date: validationError.date,
            sellcount: validationError.sellcount,
            selltwt: validationError.selltwt,
            sellrate: validationError.sellrate,
            sellamount: validationError.sellamount,
            phone: validationError.phone,
            email: validationError.email,
        });
        return validationError.status === 0;
    };

    const goNextSaleStep = () => {
        if (saleStep === 0 && !validateSaleSelection()) {
            return;
        }
        if (saleStep === 1 && !validateSaleType()) {
            return;
        }
        if (saleStep === 2 && !validateSaleDetails()) {
            return;
        }
        setShowForm(saleStep + 1 >= 2);
        setSaleStep((currentStep) => Math.min(currentStep + 1, saleSteps.length - 1));
    };

    const goPreviousSaleStep = () => {
        setSaleStep((currentStep) => Math.max(currentStep - 1, 0));
    };

    const resetSaleForm = ({ keepSelection = false } = {}) => {
        const selection = keepSelection
            ? {
                farm: data.farm,
                flock: data.flock,
            }
            : {};
        setData({ ...emptySaleData, ...selection });
        setDataPopUp(emptySalePopupData);
        setError({});
            setSubmitError("");
            setSaleStep(keepSelection ? 1 : 0);
            setShowForm(false);
            setShowButton(false);
            setShowFlockSale(Boolean(keepSelection && data.flock));
            if (!keepSelection) {
                setExistingSales([]);
            }
            if (!keepSelection) {
                setFlock([]);
                setFlocks([]);
            setShowFlocks(false);
        }
        localStorage.removeItem(SALE_DRAFT_KEY);
    };

    const save = (e) => {
        setLoading(false)
        e.preventDefault();
        if (!validateSaleSelection()) {
            setSaleStep(0);
            return;
        }
        if (!validateSaleType()) {
            setSaleStep(1);
            return;
        }
        if (!validateSaleDetails()) {
            setSaleStep(2);
            return;
        }
        if (validateSaleSelection() && validateSaleType() && validateSaleDetails()) {
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
            const savedFlockPublicId = data.flock;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.post(url, saleData, getAuthConfig()).then((res) => {
                setShow(true);
                setLoading(false)
                setTimeout(successMsg, 3000);
                resetSaleForm({ keepSelection: true });
                loadExistingSales(savedFlockPublicId);
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
        // U: OLD: window.location.reload() refreshed the whole app and lost
        // U: context. NEW: reset only this form state.
        resetSaleForm();
    }
    useEffect(() => {
        let cancelled = false;
        let url = `${apiPath}farm/`;
        // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
        // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, getAuthConfig()).then((res) => {
            if (cancelled) {
                return;
            }
            if (res.data.results.length === 0) {
                setFarms([{ public_id: 0, name: 'No farm available' }]);
            } else {
                setFarms(res.data.results);
            }

            const draftFarmId = String(initialDraft.data.farm || "0");
            const draftFlockId = String(initialDraft.data.flock || "0");
            const selectorFarmId = String(activeSelectorDraft.selectedFarmId || "0");
            const selectorFlockId = String(activeSelectorDraft.selectedFlockId || "0");
            const latestFarm = res.data.results[res.data.results.length - 1];
            const requestedFarmId = prefillFarmId !== "0"
                ? prefillFarmId
                : draftFarmId !== "0"
                    ? draftFarmId
                    : selectorFarmId !== "0"
                        ? selectorFarmId
                        : latestFarm?.public_id;
            const targetFarm = res.data.results.find((item) => String(item.public_id) === String(requestedFarmId)) || latestFarm;
            const targetFarmId = targetFarm?.public_id;
            const targetFlockId = prefillFlockId !== "0"
                ? prefillFlockId
                : draftFlockId !== "0"
                    ? draftFlockId
                    : selectorFlockId;
            const shouldResumeSaleDraft = draftFlockId !== "0" && prefillFlockId === "0";

            if (targetFarmId !== "0") {
                // U: NEW: dashboard prefill and locally saved drafts both
                // U: restore the selected farm/flock without forcing a reload.
                setData((current) => ({ ...current, farm: targetFarmId }));
                axios.get(`${apiPath}flocks/${targetFarmId}/`, getAuthConfig()).then((flockRes) => {
                    if (cancelled) {
                        return;
                    }
                    setShowFlocks(true);
                    if (flockRes.data.results.total_records === 0) {
                        setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                        setShowFlockSale(false);
                        return;
                    }

                    const flockList = flockRes.data.results.flock_list;
                    const selected = flockList.find((item) => String(item.flock_public_id) === String(targetFlockId)) || flockList[flockList.length - 1];
                    setFlocks(flockList);
                    if (!selected) {
                        setShowFlockSale(false);
                        return;
                    }

                    setData((current) => ({
                        ...current,
                        farm: selected.farm_public_id || targetFarmId,
                        flock: selected.flock_public_id,
                        ...(!shouldResumeSaleDraft
                            ? {
                                selType: null,
                                date: '',
                                sellcount: '',
                                selltwt: '',
                                sellrate: '',
                                sellamount: '',
                            }
                            : {}),
                    }));
                    setFlock(selected);
                    setShowFlockSale(true);
                    setShowButton(Boolean(shouldResumeSaleDraft && initialDraft.data.selType && initialDraft.data.selType !== "0"));
                    setShowForm(Boolean(shouldResumeSaleDraft && initialDraft.saleStep >= 2));
                    setSaleStep(prefillFlockId !== "0" ? 1 : shouldResumeSaleDraft ? initialDraft.saleStep : 0);
                    setError({});
                    loadExistingSales(selected.flock_public_id);

                    loadCurrentBirdCount(selected);
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
    }, [activeSelectorDraft.selectedFarmId, activeSelectorDraft.selectedFlockId, navigate, prefillFarmId, prefillFlockId])
    let changeFarm = (e) => {
        if (e.target.value === "0") {
            setFlocks([]);
            setFlock([]);
            setShowForm(false);
            setShowFlocks(false);
            setShowFlockSale(false);
            setShowButton(false);
            setData(emptySaleData);
            setError({});
            setSubmitError("");
            setSaleStep(0);
            setExistingSales([]);
        } else {
            let url = `${apiPath}flocks/${e.target.value}/`;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, getAuthConfig()).then((res) => {
                if (res.data.results.total_records === 0) {
                    setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                    setData({ ...emptySaleData, farm: e.target.value });
                    setFlock([]);
                    setShowForm(false);
                    setShowFlockSale(false);
                    setShowButton(false);
                    setError({});
                    setSubmitError("");
                    setSaleStep(0);
                    setExistingSales([]);
                } else {
                    const flockList = res.data.results.flock_list;
                    const selected = flockList[flockList.length - 1];
                    setFlocks(flockList);
                    selectFlockForSale(selected, { resetSaleFields: true, nextStep: 0 });
                }
                setShowFlocks(true);
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
            setData({ ...emptySaleData, farm: data.farm });
            setError({});
            setSubmitError("");
            setSaleStep(0);
            setExistingSales([]);
        } else {
            const user = flocks.find(u => String(u.flock_public_id) === e.target.value);
            if (!user) {
                setShowForm(false);
                setShowFlockSale(false);
                setShowButton(false);
                return;
            }
            setShowForm(false);
            setShowButton(false);
            selectFlockForSale(user, { resetSaleFields: true, nextStep: 0 });
        }
    }
    let changeFlockSale = (e) => {
        if (e.target.value === "0") {
            setShowButton(false);
            setShowForm(false);
            setData({ ...data, selType: e.target.value, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 });
            setError({});
            setSubmitError("");
            setSaleStep(1);
        } else {
            setShowButton(true);
            setShowForm(false);
            e.target.value === "partial_lifting" ?
                setData({ ...data, selType: e.target.value, date: '', sellcount: '', selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 })
                : setData({ ...data, selType: e.target.value, date: '', sellcount: totalChickCount, selltwt: '', sellrate: '', sellamount: '', sellavgweight: 0, totalCost: 0 })
            setError({});
            setSubmitError("");
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
    const flockAgeInDays = getFlockAgeInDays(flock.hatch_date);
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
                                            {submitError && <Alert color="danger">{submitError}</Alert>}
                                            {!hasFarmPrerequisite && (
                                                <div className="form-prerequisite-card">
                                                    <span>Farm required</span>
                                                    <p>Add a farm and flock before recording sales. Sales are linked to a flock for profit/loss reports.</p>
                                                    <Link to="/addfarm">Add farm first</Link>
                                                </div>
                                            )}
                                            {saleStep > 0 && (
                                                <div className="form-stepper" aria-label="Flock sale steps">
                                                    {saleSteps.slice(1).map((step, index) => {
                                                        const actualStep = index + 1;
                                                        return (
                                                            <button
                                                                key={step.title}
                                                                type="button"
                                                                className={actualStep === saleStep ? "is-active" : actualStep < saleStep ? "is-complete" : ""}
                                                                onClick={() => {
                                                                    setSaleStep(actualStep);
                                                                    setShowForm(actualStep >= 2);
                                                                }}
                                                            >
                                                                <span>{index + 1}</span>
                                                                <strong>{step.title}</strong>
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                            {saleStep === 0 && (
                                                <>
                                                    <FormGroup>
                                                        <Label for="farmselect">Select Farm</Label>
                                                        <div className="input-group">
                                                            <Input onChange={changeFarm} value={data.farm || "0"} id="farmSelect" name="farm" type="select">
                                                                <option value="0">Select Farm</option>
                                                                {farms.map((item) => (
                                                                    <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                                                ))}
                                                            </Input>
                                                        </div>
                                                    </FormGroup>
                                                    {showFlocks && (
                                                        <FormGroup>
                                                            <Label for="flockSelect">Select Flock</Label>
                                                            <div className="input-group">
                                                                <Input onChange={changeFlock} value={data.flock || "0"} id="flockSelect" name="flock" type="select">
                                                                    <option value="0">Select Flocks</option>
                                                                    {flocks.map((item) => (
                                                                        <option key={item.flock_public_id} value={item.flock_public_id}>{item.flock_name}</option>
                                                                    ))}
                                                                </Input>
                                                            </div>
                                                        </FormGroup>
                                                    )}
                                                    {showFlocks && !hasFlockOptions && (
                                                        <div className="form-prerequisite-card">
                                                            <span>Flock required</span>
                                                            <p>This farm does not have a flock yet. Add a flock before recording partial or final lifting sales.</p>
                                                            <Link to="/addflock">Add flock</Link>
                                                        </div>
                                                    )}
                                                </>
                                            )}
                                            {saleStep === 1 && (
                                                <>
                                                    {!showFlockSale ? (
                                                        <div className="form-helper-panel">
                                                            <strong>Select a flock first</strong>
                                                            <p>Sales must be attached to a flock so reports can calculate bird count and profit correctly.</p>
                                                        </div>
                                                    ) : (
                                                        <FormGroup>
                                                            <Label for="saleSelect">Select Sale Type</Label>
                                                            <div className="input-group">
                                                                <Input onChange={changeFlockSale} value={data.selType || "0"} id="saleSelect" name="sale" type="select">
                                                                    <option value="0">Select Sale Type</option>
                                                                    <option value="partial_lifting">Partial Lifting</option>
                                                                    <option value="final_lifting">Final Lifting</option>
                                                                </Input>
                                                            </div>
                                                        </FormGroup>
                                                    )}
                                                    {showFlockSale && Number(totalChickCount || 0) <= 0 && (
                                                        <div className="form-prerequisite-card">
                                                            <span>Current birds missing</span>
                                                            <p>The selected flock has no current bird count. Add daily data first so sales cannot exceed available birds.</p>
                                                            <Link to="/flockdailydata">Add daily data</Link>
                                                        </div>
                                                    )}
                                                </>
                                            )}
                                            {saleStep === 2 && (
                                                <>
                                                    <Row className="mt-3">
                                                        <Col>
                                                            <Label for="flockname" className="font-bold">Flock</Label>
                                                            <Alert color="danger" className="shadow-4">{flock.flock_name || "Selected flock"}</Alert>
                                                        </Col>
                                                        <Col>
                                                            <Label for="currentCount" className="font-bold flex">Current Count</Label>
                                                            <Alert color="danger" className="shadow-4">{totalChickCount}</Alert>
                                                        </Col>
                                                        <Col>
                                                            <Label for="flockAge" className="font-bold">Age</Label>
                                                            <Alert color="danger" className="shadow-4">
                                                                {/* U: OLD: <Moment diff={flock.hatch_date} unit="days">{new Date()}</Moment> */}
                                                                {flockAgeInDays}
                                                            </Alert>
                                                        </Col>
                                                    </Row>
                                                    <Accordion defaultActiveKey="0" className="mb-3">
                                                        <Accordion.Item eventKey="0">
                                                            <Accordion.Header>Flock Data</Accordion.Header>
                                                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                                <Row>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="saleDate">Date</Label>
                                                                        <input
                                                                            onChange={(e) => {
                                                                                const value = e.target.value;
                                                                                setData({ ...data, date: value });
                                                                                if (!value) {
                                                                                    setError({ ...error, date: 'Date is required.' });
                                                                                } else if (moment(value).isAfter(moment(), "day")) {
                                                                                    setError({ ...error, date: 'Sale date cannot be in the future.' });
                                                                                } else {
                                                                                    setError({ ...error, date: '' });
                                                                                }
                                                                            }}
                                                                            value={data.date || ""}
                                                                            name="date"
                                                                            placeholder="Sale Date"
                                                                            min={flock.hatch_date || ""}
                                                                            max={currentDate}
                                                                            type="date"
                                                                            className="form-control"
                                                                            aria-label="sale date"
                                                                            aria-describedby="basic-addon1"
                                                                        />
                                                                        <small className="text-danger">{error.date}</small>
                                                                    </Col>
                                                                    {data.selType === "partial_lifting" ? (
                                                                        <Col sm="6" md="4" lg="4">
                                                                            <Label for="sellcount">Lifting Count</Label>
                                                                            <input
                                                                                onBlur={totalWeight}
                                                                                onChange={(e) => {
                                                                                    const value = e.target.value;
                                                                                    const liftingCount = Number(value);
                                                                                    if (!value || liftingCount <= 0) {
                                                                                        setError({ ...error, sellcount: 'Lifting count must be greater than 0.' });
                                                                                    } else if (Number(totalChickCount || 0) > 0 && liftingCount > Number(totalChickCount || 0)) {
                                                                                        setError({ ...error, sellcount: `Lifting count cannot exceed current birds (${totalChickCount}).` });
                                                                                    } else {
                                                                                        setError({ ...error, sellcount: '' });
                                                                                    }
                                                                                    setData({ ...data, sellcount: value });
                                                                                }}
                                                                                value={data.sellcount || ""}
                                                                                name="sellcount"
                                                                                placeholder="0"
                                                                                type="number"
                                                                                min="1"
                                                                                max={totalChickCount || undefined}
                                                                                className="form-control"
                                                                                aria-label="lifting count"
                                                                                aria-describedby="basic-addon1"
                                                                            />
                                                                            <small className="text-danger">{error.sellcount}</small>
                                                                        </Col>
                                                                    ) : data.selType === "final_lifting" && (
                                                                        <Col sm="6" md="4" lg="4">
                                                                            <Label for="sellcount">Lifting Count</Label>
                                                                            <input disabled value={data.sellcount || totalChickCount || ""} name="sellcount" placeholder="0" type="number" className="form-control" aria-label="lifting count" aria-describedby="basic-addon1" />
                                                                            <small className="text-danger">{error.sellcount}</small>
                                                                        </Col>
                                                                    )}
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="selltwt">Total Wt.</Label>
                                                                        <input
                                                                            onBlur={totalWeight}
                                                                            onChange={(e) => {
                                                                                const value = e.target.value;
                                                                                setData({ ...data, selltwt: value });
                                                                                Number(value) <= 0 ? setError({ ...error, selltwt: 'Total weight must be greater than 0.' }) : setError({ ...error, selltwt: '' });
                                                                            }}
                                                                            value={data.selltwt || ""}
                                                                            name="selltwt"
                                                                            placeholder="0"
                                                                            type="number"
                                                                            min="0"
                                                                            className="form-control"
                                                                            aria-label="total weight"
                                                                            aria-describedby="basic-addon1"
                                                                        />
                                                                        <small className="text-danger">{error.selltwt}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="sellavgwt">Avg. Wt(kg)</Label>
                                                                        <input value={data.sellavgweight || 0} disabled name="sellavgwt" placeholder="0" type="number" className="form-control" aria-label="average weight" aria-describedby="basic-addon1" />
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="sellrate">Rate/kg</Label>
                                                                        <input
                                                                            onBlur={totalCost}
                                                                            onChange={(e) => {
                                                                                const value = e.target.value;
                                                                                setData({ ...data, sellrate: value });
                                                                                Number(value) <= 0 ? setError({ ...error, sellrate: 'Rate must be greater than 0.' }) : setError({ ...error, sellrate: '' });
                                                                            }}
                                                                            value={data.sellrate || ""}
                                                                            name="sellrate"
                                                                            placeholder="0"
                                                                            type="number"
                                                                            min="0"
                                                                            className="form-control"
                                                                            aria-label="rate per kg"
                                                                            aria-describedby="basic-addon1"
                                                                        />
                                                                        <small className="text-danger">{error.sellrate}</small>
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="sellcost">Cost</Label>
                                                                        <input value={data.totalCost || 0} disabled name="sellcost" placeholder="0" type="number" className="form-control" aria-label="sale cost" aria-describedby="basic-addon1" />
                                                                    </Col>
                                                                </Row>
                                                            </Accordion.Body>
                                                        </Accordion.Item>
                                                        <Accordion.Item eventKey="1">
                                                            <Accordion.Header>Buyer Data</Accordion.Header>
                                                            <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                                <Row>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="buyername">Buyer Name</Label>
                                                                        <input onChange={(e) => { setData({ ...data, [e.target.name]: e.target.value }); }} value={data.buyername || ""} name="buyername" placeholder="Buyer Name" type="text" className="form-control" aria-label="buyer name" aria-describedby="basic-addon1" />
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="buyeraddress">Buyer Address</Label>
                                                                        <input onChange={(e) => { setData({ ...data, [e.target.name]: e.target.value }); }} value={data.buyeraddress || ""} name="buyeraddress" placeholder="Buyer Address" type="text" className="form-control" aria-label="buyer address" aria-describedby="basic-addon1" />
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="buyerphone">Buyer Phone</Label>
                                                                        <input
                                                                            maxLength={10}
                                                                            onChange={(e) => {
                                                                                const value = e.target.value;
                                                                                if (value === "" || /^\d{0,10}$/.test(value)) {
                                                                                    setData({ ...data, buyerphone: value });
                                                                                    setError({ ...error, phone: value && value.length !== 10 ? 'Buyer phone must be 10 digits.' : '' });
                                                                                }
                                                                            }}
                                                                            value={data.buyerphone || ""}
                                                                            name="buyerphone"
                                                                            placeholder="Buyer Phone"
                                                                            type="text"
                                                                            className="form-control"
                                                                            aria-label="buyer phone"
                                                                            aria-describedby="basic-addon1"
                                                                        />
                                                                        <small className="text-danger">{error.phone}</small>
                                                                    </Col>
                                                                </Row>
                                                                <Row>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="buyeremail">Buyer Email</Label>
                                                                        <input
                                                                            onChange={(e) => {
                                                                                const value = e.target.value;
                                                                                const isValidEmail = value === "" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
                                                                                setData({ ...data, buyeremail: value });
                                                                                setError({ ...error, email: isValidEmail ? '' : 'Enter a valid buyer email.' });
                                                                            }}
                                                                            name="buyeremail"
                                                                            value={data.buyeremail || ""}
                                                                            placeholder="Buyer Email"
                                                                            type="email"
                                                                            className="form-control"
                                                                            aria-label="buyer email"
                                                                            aria-describedby="basic-addon1"
                                                                        />
                                                                        <small className="text-danger">{error.email}</small>
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="buyervehicle">Vehicle No.</Label>
                                                                        <input onChange={(e) => { setData({ ...data, [e.target.name]: e.target.value }); }} value={data.buyervehicle || ""} name="buyervehicle" placeholder="Vehicle No." type="text" className="form-control" aria-label="vehicle number" aria-describedby="basic-addon1" />
                                                                    </Col>
                                                                    <Col sm="6" md="4" lg="4">
                                                                        <Label for="buyerremarks">Remarks</Label>
                                                                        <input onChange={(e) => { setData({ ...data, [e.target.name]: e.target.value }); }} value={data.buyerremarks || ""} name="buyerremarks" placeholder="" type="text" className="form-control" aria-label="remarks" aria-describedby="basic-addon1" />
                                                                    </Col>
                                                                </Row>
                                                            </Accordion.Body>
                                                        </Accordion.Item>
                                                    </Accordion>
                                                    {flock.integration === true && data.selType === 'final_lifting' && (
                                                        <div className="button-group">
                                                            <Button color="primary" type="button" onClick={openModel}>Add Integration Cost</Button>
                                                        </div>
                                                    )}
                                                </>
                                            )}
                                            {saleStep === 3 && (
                                                <div className="form-review-card">
                                                    <span>Review sale entry</span>
                                                    <dl>
                                                        <div><dt>Flock</dt><dd>{flock.flock_name || data.flock || "Not selected"}</dd></div>
                                                        <div><dt>Sale type</dt><dd>{getSaleTypeLabel(data.selType)}</dd></div>
                                                        <div><dt>Date</dt><dd>{data.date || "Missing"}</dd></div>
                                                        <div><dt>Lifting count</dt><dd>{data.sellcount || 0}</dd></div>
                                                        <div><dt>Total weight</dt><dd>{data.selltwt || 0} kg</dd></div>
                                                        <div><dt>Rate/kg</dt><dd>Rs. {data.sellrate || 0}</dd></div>
                                                        <div><dt>Total sale</dt><dd>Rs. {data.totalCost || 0}</dd></div>
                                                        <div><dt>Buyer</dt><dd>{data.buyername || "Not added"}</dd></div>
                                                    </dl>
                                                </div>
                                            )}
                                            <div className="form-wizard-actions">
                                                {saleStep > 0 && <Button type="button" color="secondary" outline onClick={goPreviousSaleStep}>Back</Button>}
                                                {saleStep < saleSteps.length - 1 && <Button type="button" color="danger" onClick={goNextSaleStep}>Next</Button>}
                                                {saleStep === saleSteps.length - 1 && (
                                                    loading ? (
                                                        <Button className="btn" color="danger" type="submit" disabled>
                                                            Saving...
                                                            <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                        </Button>
                                                    ) : (
                                                        <Button className="btn" color="danger" type="submit">Save</Button>
                                                    )
                                                )}
                                                <Button color="secondary" outline type="button" onClick={closeAll}>Cancel</Button>
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

export default FlockSale;
