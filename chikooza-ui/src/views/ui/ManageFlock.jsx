import { Alert, Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom';
import Modal from 'react-bootstrap/Modal';
import moment from "moment/moment";

const MANAGE_FLOCK_DRAFT_KEY = "chikooza-manage-flock-draft";

const manageFlockSteps = [
    { title: "Select", helper: "Farm and flock" },
    { title: "Main", helper: "Name, date, birds" },
    { title: "Breed", helper: "Breed and source" },
    { title: "Systems", helper: "Shed and equipment" },
    { title: "Review", helper: "Check and save" },
];

const emptyManageFlockData = {
    hatch_date: '',
    flock_size: '',
    actual_birds: '',
    flock_name: '',
    chick_breed_public_id: "0",
    hatchery_name: '',
    chick_weight: '',
    integration: null,
    integrator_public_id: "0",
    chick_cost: '',
    ec_shed: null,
    feed_sys: "0",
    drinking_sys: "0",
    flock_public_id: null
};

const readManageFlockDraft = () => {
    try {
        const draft = JSON.parse(localStorage.getItem(MANAGE_FLOCK_DRAFT_KEY) || "{}");
        return {
            data: { ...emptyManageFlockData, ...(draft.data || {}) },
            selectedFarmId: draft.selectedFarmId || "0",
            selectedFlockId: draft.selectedFlockId || "0",
            flockStep: Number(draft.flockStep || 0),
        };
    } catch {
        return { data: emptyManageFlockData, selectedFarmId: "0", selectedFlockId: "0", flockStep: 0 };
    }
};

const ManageFlock = () => {
    const [initialDraft] = useState(() => readManageFlockDraft());
    const [show, setShow] = useState(false);
    let [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const routeFarmId = String(location.state?.farmPublicId || "0");
    const routeFlockId = String(location.state?.flockPublicId || "0");
    const startingFarmId = routeFarmId !== "0" ? routeFarmId : initialDraft.selectedFarmId;
    const startingFlockId = routeFlockId !== "0" ? routeFlockId : initialDraft.selectedFlockId;
    let [err, setErr] = useState('');
    let [farms, setFarms] = useState([]);
    let [showFlocks, setShowFlocks] = useState(startingFarmId !== "0" ? 1 : 0);
    let [flocks, setFlocks] = useState([]);
    let [showForm, setShowForm] = useState(routeFlockId === "0" && initialDraft.data.flock_public_id ? 1 : 0);
    let [breeds, setBreeds] = useState([]);
    let [intgcom, setIntgcom] = useState([]);
    const [selectedFarmId, setSelectedFarmId] = useState(startingFarmId);
    const [selectedFlockId, setSelectedFlockId] = useState(startingFlockId);
    const [flockStep, setFlockStep] = useState(initialDraft.flockStep);
    let [addData, setAddData] = useState(initialDraft.data);
    const farmList = farms.filter((item) => String(item.public_id) !== "0");

    function loadFlockForEdit(flockId, nextStep = 0) {
        if (String(flockId) === "0") {
            //setFlock_public_iderr('Please select flocks');
            setShowForm(0);
            setSelectedFlockId("0");
        } else {
            //setFlock_public_iderr('');
            setSelectedFlockId(String(flockId));
            let url = `${apiPath}flocksDetail/${flockId}/`;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, getAuthConfig()).then((res) => {
                setShowForm(1);
                setAddData({ ...emptyManageFlockData, ...res.data.results });
                setFlockStep(nextStep);
                setErr('');
            }).catch((err) => {
                //setFlocks(err.data.results);
                handleUnauthorized(err, navigate);
            });
        }
    }

    useEffect(() => {
        let url = `${apiPath}farm/`;
        // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
        // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, getAuthConfig()).then((res) => {
            if (res.data.results.length === 0) {
                setFarms([{ public_id: 0, name: 'No farm available' }]);
            } else {
                const farmResults = res.data.results;
                const requestedFarmId = routeFarmId !== "0" ? routeFarmId : initialDraft.selectedFarmId;
                const activeFarm = farmResults.find((item) => String(item.public_id) === String(requestedFarmId)) || farmResults[farmResults.length - 1];
                const activeFarmId = String(activeFarm.public_id);
                setFarms(farmResults);
                setSelectedFarmId(activeFarmId);
                axios.get(`${apiPath}flocks/${activeFarmId}/`, getAuthConfig()).then((flockRes) => {
                    setShowFlocks(1);
                    if (flockRes.data.results.total_records === 0) {
                        setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                        setSelectedFlockId("0");
                        setShowForm(0);
                        setFlockStep(0);
                    } else {
                        const flockResults = flockRes.data.results.flock_list || [];
                        const requestedFlockId = routeFlockId !== "0" ? routeFlockId : initialDraft.selectedFlockId;
                        const activeFlock = flockResults.find((item) => String(item.flock_public_id) === String(requestedFlockId)) || flockResults[flockResults.length - 1];
                        setFlocks(flockResults);
                        loadFlockForEdit(activeFlock.flock_public_id, initialDraft.flockStep > 0 ? initialDraft.flockStep : 0);
                    }
                }).catch((err) => {
                    handleUnauthorized(err, navigate);
                });
            }
        }).catch((err) => {
            console.log(err)
            setFarms([{ public_id: 0, name: 'No farm available' }]);
            handleUnauthorized(err, navigate);
        });
    }, [initialDraft.selectedFarmId, initialDraft.selectedFlockId, initialDraft.flockStep, navigate, routeFarmId, routeFlockId])
    useEffect(() => {
        let url = `${apiPath}breeds/`;
        axios.get(url, getAuthConfig()).then((res) => {
            setBreeds(res.data.results);
        }).catch((err) => {
            //setBreeds(res.data.results);
            handleUnauthorized(err, navigate);
        });
    }, [navigate])
    useEffect(() => {
        let url = `${apiPath}integrators/`;
        axios.get(url, getAuthConfig()).then((res) => {
            setIntgcom(res.data.results);
        }).catch((err) => {
            //setIntgcom(res.data.results);
            handleUnauthorized(err, navigate);
        });
    }, [navigate])

    useEffect(() => {
        if (!showForm) {
            return;
        }
        // U: NEW: manage-flock edits are draft-saved locally while the farmer
        // U: moves through the longer step flow.
        localStorage.setItem(MANAGE_FLOCK_DRAFT_KEY, JSON.stringify({
            data: addData,
            selectedFarmId,
            selectedFlockId,
            flockStep,
        }));
    }, [addData, selectedFarmId, selectedFlockId, flockStep, showForm]);

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
    let [, setIntegration] = useState(2);

    const validateManageFlock = () => {
        let valid = true;
        const normalizedIntegration = addData.integration === true ? 1 : addData.integration === false ? 2 : Number(addData.integration);
        const normalizedEcShed = addData.ec_shed === true ? 1 : addData.ec_shed === false ? 2 : Number(addData.ec_shed);
        const hatchDate = addData.hatch_date || "";
        const flockSize = Number(addData.flock_size);
        const actualBirds = Number(addData.actual_birds);

        if (!hatchDate) { setHatch_dateerr('Hatch date is required'); valid = false; }
        else if (moment(hatchDate).isAfter(moment(), "day")) { setHatch_dateerr('Hatch date cannot be in the future'); valid = false; }
        else { setHatch_dateerr(''); }
        if ((addData.flock_name || '').trim() === '') { setFlock_nameerr('Flock name is required'); valid = false; } else { setFlock_nameerr(''); }
        if (!flockSize || flockSize <= 0) { setFlock_sizeerr('Flock size must be greater than 0'); valid = false; } else { setFlock_sizeerr(''); }
        if (addData.actual_birds === '' || addData.actual_birds === null) { setActual_birdserr('Actual birds is required'); valid = false; }
        else if (actualBirds < 0) { setActual_birdserr('Actual birds cannot be negative'); valid = false; }
        else if (flockSize > 0 && actualBirds > flockSize) { setActual_birdserr('Actual birds cannot exceed flock size'); valid = false; }
        else { setActual_birdserr(''); }
        if (String(addData.chick_breed_public_id || "0") === "0") { setBreed_public_iderr('Please select breed'); valid = false; } else { setBreed_public_iderr(''); }
        if ((addData.hatchery_name || '').trim() === '') { setHatchery_nameerr('Hatchery name is required'); valid = false; } else { setHatchery_nameerr(''); }
        if (Number(addData.chick_weight) <= 0) { setChick_weighterr('Day one weight must be greater than 0'); valid = false; } else { setChick_weighterr(''); }
        if (normalizedEcShed === 0 || addData.ec_shed === null) { setEc_shederr('Please select EC shed'); valid = false; } else { setEc_shederr(''); }
        if (String(addData.feed_sys || "0") === "0") { setFeed_syserr('Please select feed system'); valid = false; } else { setFeed_syserr(''); }
        if (String(addData.drinking_sys || "0") === "0") { setDrinking_syserr('Please select drinking system'); valid = false; } else { setDrinking_syserr(''); }
        if (normalizedIntegration === 0 || addData.integration === null) {
            setIntegrationerr('Please select integration');
            valid = false;
        } else if (normalizedIntegration === 1 && String(addData.integrator_public_id || "0") === "0") {
            setIntegrationerr('');
            setIntegrator_public_iderr('Please select integration company');
            valid = false;
        } else if (normalizedIntegration === 2 && Number(addData.chick_cost) <= 0) {
            setIntegrationerr('');
            setChick_costerr('Chicks cost must be greater than 0');
            valid = false;
        } else {
            setIntegrationerr('');
            setIntegrator_public_iderr('');
            setChick_costerr('');
        }
        return valid;
    };

    const validateMainStep = () => {
        let valid = true;
        const hatchDate = addData.hatch_date || "";
        const flockSize = Number(addData.flock_size);
        const actualBirds = Number(addData.actual_birds);

        if (!hatchDate) { setHatch_dateerr('Hatch date is required'); valid = false; }
        else if (moment(hatchDate).isAfter(moment(), "day")) { setHatch_dateerr('Hatch date cannot be in the future'); valid = false; }
        else { setHatch_dateerr(''); }
        if ((addData.flock_name || '').trim() === '') { setFlock_nameerr('Flock name is required'); valid = false; } else { setFlock_nameerr(''); }
        if (!flockSize || flockSize <= 0) { setFlock_sizeerr('Flock size must be greater than 0'); valid = false; } else { setFlock_sizeerr(''); }
        if (addData.actual_birds === '' || addData.actual_birds === null) { setActual_birdserr('Actual birds is required'); valid = false; }
        else if (actualBirds < 0) { setActual_birdserr('Actual birds cannot be negative'); valid = false; }
        else if (flockSize > 0 && actualBirds > flockSize) { setActual_birdserr('Actual birds cannot exceed flock size'); valid = false; }
        else { setActual_birdserr(''); }
        return valid;
    };

    const validateBreedStep = () => {
        let valid = true;
        const normalizedIntegration = addData.integration === true ? 1 : addData.integration === false ? 2 : Number(addData.integration);

        if (String(addData.chick_breed_public_id || "0") === "0") { setBreed_public_iderr('Please select breed'); valid = false; } else { setBreed_public_iderr(''); }
        if ((addData.hatchery_name || '').trim() === '') { setHatchery_nameerr('Hatchery name is required'); valid = false; } else { setHatchery_nameerr(''); }
        if (normalizedIntegration === 0 || addData.integration === null) {
            setIntegrationerr('Please select integration');
            valid = false;
        } else if (normalizedIntegration === 1 && String(addData.integrator_public_id || "0") === "0") {
            setIntegrationerr('');
            setIntegrator_public_iderr('Please select integration company');
            valid = false;
        } else if (normalizedIntegration === 2 && Number(addData.chick_cost) <= 0) {
            setIntegrationerr('');
            setChick_costerr('Chicks cost must be greater than 0');
            valid = false;
        } else {
            setIntegrationerr('');
            setIntegrator_public_iderr('');
            setChick_costerr('');
        }
        return valid;
    };

    const validateSystemsStep = () => {
        let valid = true;
        const normalizedEcShed = addData.ec_shed === true ? 1 : addData.ec_shed === false ? 2 : Number(addData.ec_shed);

        if (Number(addData.chick_weight) <= 0) { setChick_weighterr('Day one weight must be greater than 0'); valid = false; } else { setChick_weighterr(''); }
        if (normalizedEcShed === 0 || addData.ec_shed === null) { setEc_shederr('Please select EC shed'); valid = false; } else { setEc_shederr(''); }
        if (String(addData.feed_sys || "0") === "0") { setFeed_syserr('Please select feed system'); valid = false; } else { setFeed_syserr(''); }
        if (String(addData.drinking_sys || "0") === "0") { setDrinking_syserr('Please select drinking system'); valid = false; } else { setDrinking_syserr(''); }
        return valid;
    };

    const validateStepBeforeMove = (step) => {
        if (step === 0) {
            if (!showForm) {
                setErr('Select a farm and flock first.');
                return false;
            }
            setErr('');
            return true;
        }
        if (step === 1) {
            return validateMainStep();
        }
        if (step === 2) {
            return validateBreedStep();
        }
        if (step === 3) {
            return validateSystemsStep();
        }
        return true;
    };

    const goNextFlockStep = () => {
        if (flockStep === 0 && !showForm) {
            setErr('Select a farm and flock first.');
            return;
        }
        if (!validateStepBeforeMove(flockStep)) {
            return;
        }
        setErr('');
        setFlockStep((currentStep) => Math.min(currentStep + 1, manageFlockSteps.length - 1));
    };

    const goToManageFlockStep = (targetStep) => {
        if (targetStep <= flockStep) {
            setFlockStep(targetStep);
            return;
        }

        for (let step = flockStep; step < targetStep; step += 1) {
            if (!validateStepBeforeMove(step)) {
                return;
            }
        }
        setErr('');
        setFlockStep(targetStep);
    };

    const goPreviousFlockStep = () => {
        setFlockStep((currentStep) => Math.max(currentStep - 1, 0));
    };

    const save = (e) => {
        e.preventDefault();
        setLoading(false);//console.log(addData.integration);
        if (!validateManageFlock()) {
            setErr('Validation error. Please check all fields.');
            setFlockStep(1);
            return;
        }
        let error = 0;
        //if(addData.farm_public_id == 0 || addData.farm_public_id == null){setFarm_public_iderr('Please select farm');error = 1;}else{setFarm_public_iderr('');}
        // U: Replaced direct addData mutation with local normalized values for validation/payload.
        const normalizedIntegration = addData.integration === true ? 1 : addData.integration === false ? 2 : Number(addData.integration);
        const normalizedEcShed = addData.ec_shed === true ? 1 : addData.ec_shed === false ? 2 : Number(addData.ec_shed);
        if ((addData.hatch_date || '').trim() === '') { setHatch_dateerr('Hatch date is required'); error = 1; } else { setHatch_dateerr(''); }
        if ((addData.flock_name || '').trim() === '') { setFlock_nameerr('Flock name is required'); error = 1; } else { setFlock_nameerr(''); }
        if (addData.flock_size <= 0 || addData.flock_size === null) { setFlock_sizeerr('Flock size is required'); error = 1; } else { setFlock_sizeerr(''); }
        if (addData.actual_birds === '' || addData.actual_birds === null) { setActual_birdserr('Actual birds is required'); error = 1; }
        else if (Number(addData.actual_birds) < 0) { setActual_birdserr('Actual birds cannot be negative'); error = 1; }
        else if (Number(addData.flock_size) > 0 && Number(addData.actual_birds) > Number(addData.flock_size)) { setActual_birdserr('Actual birds cannot exceed flock size'); error = 1; }
        else { setActual_birdserr(''); }
        if (String(addData.chick_breed_public_id) === "0" || addData.chick_breed_public_id === null) { setBreed_public_iderr('Please select Breed'); error = 1; } else { setBreed_public_iderr(''); }
        if ((addData.hatchery_name || '').trim() === '') { setHatchery_nameerr('Hatchery name is required'); error = 1; } else { setHatchery_nameerr(''); }
        if (addData.chick_weight <= 0 || addData.chick_weight === null) { setChick_weighterr('Day one weight is required'); error = 1; } else { setChick_weighterr(''); }
        if (normalizedEcShed === 0 || addData.ec_shed === null) { setEc_shederr('Please select ec shed'); error = 1; } else { setEc_shederr(''); }
        if (String(addData.feed_sys) === "0" || addData.feed_sys === null) { setFeed_syserr('Please select feed system'); error = 1; } else { setFeed_syserr(''); }
        if (String(addData.drinking_sys) === "0" || addData.drinking_sys === null) { setDrinking_syserr('Please select Drinking System'); error = 1; } else { setDrinking_syserr(''); }
        if (normalizedIntegration === 0 || addData.integration === null) {
            setIntegrationerr('Please select integration'); error = 1;
            if (addData.chick_cost <= 0 || addData.chick_cost === null) { setChick_costerr('Chicks Cost is required'); error = 1; } else { setChick_costerr(''); }
        } else {
            setIntegrationerr('');
            if (normalizedIntegration === 1) {
                if (String(addData.integrator_public_id) === "0" || addData.integrator_public_id === null) { setIntegrator_public_iderr('Please select Intrigation company'); error = 1; } else { setIntegrator_public_iderr(''); }
            } else if (normalizedIntegration === 2) {
                if (addData.chick_cost <= 0 || addData.chick_cost === null) { setChick_costerr('Chicks Cost is required'); error = 1; } else { setChick_costerr(''); }
            }
        }
        if (error === 0) {
            setLoading(true);
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
                ec_shed: normalizedEcShed === 1,
                feed_sys: addData.feed_sys,
                drinking_sys: addData.drinking_sys
            };
            if (normalizedIntegration === 1) {
                flock.integration = true;
                flock.integrator_public_id = addData.integrator_public_id;
            } else {
                flock.integration = false;
                flock.chick_cost = addData.chick_cost;
            }
            let url = `${apiPath}flocks/${addData.flock_public_id}/`;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.patch(url, flock, getAuthConfig()).then((res) => {
                setShow(true);
                setLoading(false);
                setTimeout(successMsg, 3000);
                setFlocks((currentFlocks) => currentFlocks.map((item) => (
                    String(item.flock_public_id) === String(addData.flock_public_id) ? { ...item, ...addData, flock_name: addData.flock_name } : item
                )));
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
                handleUnauthorized(err, navigate);
            });
        } else {
            setErr('Validation error. Please check all fields.');
        }
    }

    let changeFarm = (e) => {
        //setAddData({...addData,farm_public_id:e.target.value});
        if (e.target.value === "0") {
            //setFarm_public_iderr('Please select farm');
            setShowFlocks(0);
            setShowForm(0);
            setFlocks([]);
            setSelectedFarmId("0");
            setSelectedFlockId("0");
            setFlockStep(0);
        } else {
            //setFarm_public_iderr('');
            setSelectedFarmId(e.target.value);
            setSelectedFlockId("0");
            let url = `${apiPath}flocks/${e.target.value}/`;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, getAuthConfig()).then((res) => {
                setShowFlocks(1);
                setShowForm(0);
                setFlockStep(0);
                if (res.data.results.total_records === 0) {
                    setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                    setSelectedFlockId("0");
                    setShowForm(0);
                } else {
                    const flockResults = res.data.results.flock_list || [];
                    const latestFlock = flockResults[flockResults.length - 1];
                    setFlocks(flockResults);
                    loadFlockForEdit(latestFlock.flock_public_id, 0);
                }
            }).catch((err) => {
                //setFlocks(err.data.results);
                handleUnauthorized(err, navigate);
            });
        }
    }
    let changeFlocks = (e) => {
        loadFlockForEdit(e.target.value, 0);
    }
    let changeBreed = (e) => {
        setAddData({ ...addData, chick_breed_public_id: e.target.value });
        e.target.value === "0" ? setBreed_public_iderr('Please select Breed') : setBreed_public_iderr('');
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

// AS-20-6-25 17-10 corrected Integration default value logic
   let changeIntrigation = (e) => {
    let value = e.target.value === "1" ? true : false;
    setAddData({ ...addData, integration: value });
    e.target.value === "0" ? setIntegrationerr('Please select integration') : setIntegrationerr('');
    setIntegration(value ? 1 : 2);
    }
// AS-20-6-25 17-10 change end

    let changeActualbirds = (e) => {
        setAddData({ ...addData, actual_birds: e.target.value });
        if (e.target.value === "") {
            setActual_birdserr('Actual birds is required');
        } else if (Number(e.target.value) < 0) {
            setActual_birdserr('Actual birds cannot be negative');
        } else if (Number(addData.flock_size) > 0 && Number(e.target.value) > Number(addData.flock_size)) {
            setActual_birdserr('Actual birds cannot exceed flock size');
        } else {
            setActual_birdserr('');
        }
    }
    let changeHatchery = (e) => {
        setAddData({ ...addData, hatchery_name: e.target.value });
        e.target.value.trim() === "" ? setHatchery_nameerr('Hatchery name is required') : setHatchery_nameerr('');
    }
    let changeDayoneweight = (e) => {
        setAddData({ ...addData, chick_weight: e.target.value });
        e.target.value <= 0 ? setChick_weighterr('Day one weight is required') : setChick_weighterr('');
    }
    let changeChickcost = (e) => {
        if (addData.integration !== true) {
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
        e.target.value.trim() === "" ? setFlock_nameerr('Flock name is required') : setFlock_nameerr('');
    }
    let changeHatchdate = (e) => {
        setAddData({ ...addData, hatch_date: e.target.value });
        if (e.target.value === "") {
            setHatch_dateerr('Hatch date is required');
        } else if (moment(e.target.value).isAfter(moment(), "day")) {
            setHatch_dateerr('Hatch date cannot be in the future');
        } else {
            setHatch_dateerr('');
        }
    }
    let changeFlocksize = (e) => {
        setAddData({ ...addData, flock_size: e.target.value });
        Number(e.target.value) <= 0 ? setFlock_sizeerr('Flock size must be greater than 0') : setFlock_sizeerr('');
    }
    let changeIntco = (e) => {
        if (addData.integration === true) {
            setAddData({ ...addData, integrator_public_id: e.target.value });
            e.target.value === "0" ? setIntegrator_public_iderr('Please select Intrigation company') : setIntegrator_public_iderr('');
        }
    }
    function successMsg() {
        setShow(false);
        setFlockStep(0);
        localStorage.removeItem(MANAGE_FLOCK_DRAFT_KEY);
    }
    let closeAll = () => {
        localStorage.removeItem(MANAGE_FLOCK_DRAFT_KEY);
        navigate('/member');
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
                                        {(err !== '') && <Alert color="danger">{err}</Alert>}
                                        <Form onSubmit={save}>
                                            {flockStep > 0 && (
                                                <div className="form-stepper form-stepper--four" aria-label="Manage flock steps">
                                                    {manageFlockSteps.slice(1).map((step, index) => {
                                                        const actualStep = index + 1;
                                                        return (
                                                            <button
                                                                key={step.title}
                                                                type="button"
                                                                className={actualStep === flockStep ? "is-active" : actualStep < flockStep ? "is-complete" : ""}
                                                                onClick={() => goToManageFlockStep(actualStep)}
                                                            >
                                                                <span>{index + 1}</span>
                                                                <strong>{step.title}</strong>
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                            {flockStep === 0 && (
                                                <>
                                                    <FormGroup>
                                                        <Label for="farmselect">Select Farm</Label>
                                                        <div className="input-group">
                                                            <Input onChange={changeFarm} id="farmSelect" value={selectedFarmId} name="farm" type="select">
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
                                                    {(showFlocks === 1) ?
                                                        <FormGroup>
                                                            <Label for="farmselect">Select Flock</Label>
                                                            <div className="input-group">
                                                                <Input onChange={changeFlocks} id="flockSelect" value={selectedFlockId} name="flock" type="select">
                                                                    <option value="0">Select Flock</option>
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
                                                </>
                                            )}
                                            {(showForm === 1) ?
                                                <>
                                                    <div className="mb-3">
                                                        {flockStep === 1 && (
                                                        <div>
                                                            <div>
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
                                                            </div>
                                                        </div>
                                                        )}
                                                        {flockStep === 2 && (
                                                        <div>
                                                            <div>
                                                                <FormGroup>
                                                                    <Label for="farmselect">Chick Breed</Label>
                                                                    <div className="input-group">
                                                                        <Input onChange={changeBreed} value={addData.chick_breed_public_id || "0"} id="chickbreed" name="chickbreed" type="select">
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
                                                                    (addData.integration === true) ?
                                                                        <FormGroup>
                                                                            <Label for="flockname">Int Co.?</Label>
                                                                            <div className="input-group">
                                                                                <Input onChange={changeIntco} value={addData.integrator_public_id} id="chickbreed" name="chickbreed" type="select">
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
                                                                                <input value={addData.chick_cost} onChange={changeChickcost} name="chickscost" placeholder="Chicks Cost" type="number" className="form-control" aria-label="chickscost" aria-describedby="basic-addon1" />
                                                                            </div>
                                                                            <small className="text-danger">{chick_costerr}</small>
                                                                        </FormGroup>
                                                                }
                                                            </div>
                                                        </div>
                                                        )}
                                                        {flockStep === 3 && (
                                                        <div>
                                                            <div>
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
                                                                        <Input
                                                                            onChange={changeEcshed}
                                                                            value={addData.ec_shed === true ? "true" : addData.ec_shed === false ? "false" : "0"}
                                                                            id="ecshed"
                                                                            name="ecshed"
                                                                            type="select"
                                                                        >
                                                                            <option disabled value="0">-EC Shed</option>
                                                                            <option value="true">Yes</option>
                                                                            <option value="false">No</option>
                                                                        </Input>
                                                                    </div>
                                                                    <small className="text-danger">{ec_shederr}</small>
                                                                </FormGroup>
                                                                <FormGroup>
                                                                    <Label for="farmselect">Feed Sys</Label>
                                                                    <div className="input-group">
                                                                        <Input onChange={changeFeedsys} value={addData.feed_sys} id="feedsys" name="feedsys" type="select">
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
                                                                        <Input onChange={changeDrinkingsys} value={addData.drinking_sys} id="drinkingsys" name="drinkingsys" type="select">
                                                                            <option disabled value="0">-Drinking Sys</option>
                                                                            <option value="M">Manual</option>
                                                                            <option value="A">Auto</option>
                                                                            <option value="B">Both</option>
                                                                        </Input>
                                                                    </div>
                                                                    <small className="text-danger">{drinking_syserr}</small>
                                                                </FormGroup>
                                                            </div>
                                                        </div>
                                                        )}
                                                    </div>
                                                    {flockStep === 4 && (
                                                        <div className="form-review-card">
                                                            <span>Review flock update</span>
                                                            <dl>
                                                                <div><dt>Flock</dt><dd>{addData.flock_name || "Missing"}</dd></div>
                                                                <div><dt>Hatch date</dt><dd>{addData.hatch_date || "Missing"}</dd></div>
                                                                <div><dt>Flock size</dt><dd>{addData.flock_size || "Missing"}</dd></div>
                                                                <div><dt>Actual birds</dt><dd>{addData.actual_birds || "Missing"}</dd></div>
                                                                <div><dt>Hatchery</dt><dd>{addData.hatchery_name || "Missing"}</dd></div>
                                                                <div><dt>Integration</dt><dd>{addData.integration === true ? "Yes" : addData.integration === false ? "No" : "Missing"}</dd></div>
                                                                <div><dt>Feed system</dt><dd>{addData.feed_sys || "Missing"}</dd></div>
                                                                <div><dt>Drinking system</dt><dd>{addData.drinking_sys || "Missing"}</dd></div>
                                                            </dl>
                                                        </div>
                                                    )}
                                                    <div className="form-wizard-actions manage-flock-actions">
                                                        {flockStep > 0 && <Button className="manage-flock-back-action" type="button" color="secondary" outline onClick={goPreviousFlockStep}>Back</Button>}
                                                        {flockStep < manageFlockSteps.length - 1 && <Button className="manage-flock-next-action" type="button" color="danger" onClick={goNextFlockStep}>Next</Button>}
                                                        {flockStep === manageFlockSteps.length - 1 && (loading ?
                                                            <Button className="btn manage-flock-save-action" color="danger" type="submit" disabled>
                                                                Please wait...
                                                                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                            </Button>
                                                            :
                                                            <Button className="btn manage-flock-save-action" color="danger" type="submit">Save</Button>
                                                        )}
                                                        <Button className="btn manage-flock-cancel-action" color="secondary" outline type="button" onClick={closeAll}>Cancel</Button>
                                                        <Button className="btn manage-flock-add-action" color="danger" outline type="button" onClick={() => navigate("/addflock")}>Add another flock</Button>
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
