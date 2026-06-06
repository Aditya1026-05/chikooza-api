import { Row, Col, Card, CardTitle, CardBody, Alert, Button, Form, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { useState, useEffect } from "react";
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import Accordion from 'react-bootstrap/Accordion';
import { Link, useParams } from "react-router-dom";
import axios from 'axios';
import Modal from 'react-bootstrap/Modal';
import Spinner from 'react-bootstrap/Spinner';
import { useNavigate } from "react-router-dom";

const dailyDataSteps = [
    { title: "Flock", helper: "Mortality and feed" },
    { title: "Vaccines", helper: "Vaccination status" },
    { title: "Checks", helper: "Heating, cooling, sick" },
    { title: "Timing", helper: "Darkness and feed" },
    { title: "Review", helper: "Check and save" },
];

const DaywiseData = () => {
    const navigate = useNavigate();
    let [dailyDataPublicID, setDailyDataPublicID] = useState(0);
    let [err, setErr] = useState('');
    const [show, setShow] = useState(false);
    let [updation, setUpdation] = useState(false);
    let [loading, setLoading] = useState(false);
    let [feedAvaibility, setFeedAvaibility] = useState([]);
    let [darkNess, setDarkNess] = useState([]);
    // let [addData, setAddData] = useState({
    //     date: null, flock_public_id: null, mortality: null, mort: null, feed_intake: null, current_bird_count: null,
    //     average_bird_weight: null, heating: false, cooling: false, seek: false, medicine: false, darkness_time_public_id: 0, feed_availability_public_id: 0,
    //     mortalityCount: 0, mortalityPer: 0, avg_feed_per_bird: 0, total_feed: 0, feed_stock: null, fcr: null, total_fcr: null, type: 'Save'
    // });

//MV-23-6-25- 17-10 added cum_mort & total_mortality_percentage
    let [addData, setAddData] = useState({
        date: null, flock_public_id: null, mortality: null, mort: null, feed_intake: null, current_bird_count: null,
        average_bird_weight: null, heating: false, cooling: false, seek: false, medicine: false, darkness_time_public_id: 0, feed_availability_public_id: 0, cum_mort:0,total_mortality_percentage:0,
        mortalityCount: 0, mortalityPer: 0, avg_feed_per_bird: 0, total_feed: 0, feed_stock: null, fcr: null, total_fcr: null, type: 'Save'
    });
//MV-23-6-25- 17-10 change end

    let [oldValues, setOldValues] = useState({ current_bird_count: null, initial_total_feed: null, total_feed: 0, feed_stock: 0, fcr: null, total_fcr: null });
    let [vaccines, setVaccines] = useState([{}]);
    let [formValues, setFormValues] = useState([{ public_id: "", vaccine_public_id: "", status: "" }])
    let [mortalityError, setMortalityError] = useState(null);
    let [feedintakeError, setFeedintakeError] = useState(null);
    let [averageBirdError, setAverageBirdError] = useState(null);
    let { farmid, flockid, date } = useParams();
    let [todayDate, setTodayDate] = useState([]);
    let [flockDetails, setFlockDetails] = useState({});
    let [daysCount, setDaysCount] = useState(0);
    let [lastInsertDate, setLastInsertDate] = useState(null);
    let [darknessError, setDarknessError] = useState('');
    let [feedAvaibilityError, setFeedAvaibilityError] = useState('');
    const [dailyStep, setDailyStep] = useState(0);
    const dailyDraftKey = `chikooza-day-data-draft-${flockid}-${date}`;
    const FEED_STOCK_ERROR = "Feed intake is greater than available feed stock. Add a feed purchase for this flock first.";

    const getAvailableFeedStock = () => Number(oldValues.feed_stock ?? oldValues.initial_total_feed ?? 0);
    const getDisplayFeedStock = () => {
        if (addData.feed_stock === null || addData.feed_stock === undefined) {
            return getAvailableFeedStock();
        }
        return Number(addData.feed_stock || 0);
    };
    const getApiErrorMessage = (error) => {
        const payload = error?.response?.data || {};
        const result = payload.results || payload.result || {};
        const resultValues = Object.values(result || {});
        const firstResultValue = resultValues.length > 0
            ? (Array.isArray(resultValues[0]) ? resultValues[0][0] : resultValues[0])
            : "";
        return firstResultValue || payload.message || payload.error || "Something went wrong. Please try again";
    };
    const handleSaveError = (error) => {
        const message = getApiErrorMessage(error);
        setErr(message);
        if (String(message).toLowerCase().includes("feed")) {
            setFeedintakeError(message);
        }
        setLoading(false);
        handleUnauthorized(error, navigate);
    };

    useEffect(() => {
        // U: NEW: daily data is a long multi-section form, so keep a local
        // U: draft while the farmer moves across steps.
        localStorage.setItem(dailyDraftKey, JSON.stringify({
            addData,
            formValues,
            dailyStep,
        }));
    }, [addData, formValues, dailyStep, dailyDraftKey]);

    let handleChange = (i, e) => {
        let newFormValues = [...formValues];
        newFormValues[i][e.target.name] = e.target.value;
        setFormValues(newFormValues);
    }

    let addFormFields = () => {
        setFormValues([...formValues, { public_id: "", vaccine_public_id: "", status: "" }])
    }
    // console.log("sdvf", formValues);
    let removeFormFields = (i, public_id) => {
        if (public_id === "") {
            formValues.splice(i, 1)
            // console.log(formValues.splice(i, 1));
            setFormValues([...formValues])
        } else {
            let url = `${apiPath}flockVaccination/${public_id}/`;
            // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.delete(url, getAuthConfig()).then(() => {
                let newFormValues = [...formValues];
                newFormValues.splice(i, 1);
                setFormValues(newFormValues)
            }).catch((err) => {//console.log(err);
                if (err?.response?.status === 404) {
                    let newFormValues = [...formValues];
                    newFormValues.splice(i, 1);
                    setFormValues(newFormValues)
                }
                handleUnauthorized(err, navigate);
            });
        }
    }

    let handleSubmit = (event) => {
        event.preventDefault();
        let error = 0;
        setLoading(true);
        let midData = 0;
        if (addData.darkness_time_public_id === 0 || addData.darkness_time_public_id === "0") { setDarknessError('This fields is not a valid.'); error = 1; } else { setDarknessError(''); }
        if (addData.feed_availability_public_id === 0 || addData.feed_availability_public_id === "0") { setFeedAvaibilityError('This fields is not a valid.'); error = 1; } else { setFeedAvaibilityError(''); }
        if (oldValues.current_bird_count === null) { midData = flockDetails.actual_birds; } else { midData = oldValues.current_bird_count; }
        // console.log(addData.mortality + " > " + midData);
        if (addData.mortality === null || addData.mortality === '' || addData.mortality < 0 || addData.mortality >= midData) { setMortalityError('This fields is not a valid.'); error = 1; } else { setMortalityError(''); }
        midData = getAvailableFeedStock();
        if (addData.feed_intake === null || addData.feed_intake === '' || Number(addData.feed_intake) <= 0 || Number(addData.feed_intake) > midData) { setFeedintakeError(FEED_STOCK_ERROR); error = 1; } else { setFeedintakeError(''); }
        let midWeight = 0;
        if (addData.average_bird_weight === null || addData.feed_intake === '') {
            midWeight = 0;
        } else {
            midWeight = addData.average_bird_weight;
        }

        //console.log(error);
        if (error === 0) {
            let mid = 1;
            let dailyData = {
                flock_public_id: flockid,
                date: date,
                mortality: addData.mortality,
                average_bird_weight: midWeight,
                feed_intake: addData.feed_intake,
                heating: addData.heating,
                cooling: addData.cooling,

//MV-23-6-25- 17-10 added cum_mort & total_mortality_percentage
                cum_mort: addData.cum_mort,
                total_mortality_percentage: addData.total_mortality_percentage,
//MV-16-6-25- 17-10 change end

                seek: addData.seek,
                darkness_time_public_id: addData.darkness_time_public_id,
                feed_availability_public_id: addData.feed_availability_public_id,
                medicine: addData.medicine
            };
            let dailyDataVaccination = {
                flock_public_id: flockid,
                date: date,
                mortality: addData.mortality,
                average_bird_weight: midWeight,
                feed_intake: addData.feed_intake,
                heating: addData.heating,
                cooling: addData.cooling,
                seek: addData.seek,
                darkness_time_public_id: addData.darkness_time_public_id,
                feed_availability_public_id: addData.feed_availability_public_id,
                medicine: addData.medicine,
                flock_vaccination: {
                    flock_vaccination_public_id: [],
                    vaccine_public_id: [],
                    status: [],
                }
            }; //console.log(dailyData);
            if (updation === true) {
                // U: OLD: map() was used for side effects and returned nothing.
                formValues.forEach((item) => {//console.log(item);
                    if ((item.vaccine_public_id !== '') && (item.status !== '')) {
                        mid = 0;
                        if (item.public_id !== '') {
                            dailyDataVaccination.flock_vaccination.flock_vaccination_public_id.push(item.public_id);
                        } else {
                            dailyDataVaccination.flock_vaccination.flock_vaccination_public_id.push(0);
                        }
                        dailyDataVaccination.flock_vaccination.vaccine_public_id.push(item.vaccine_public_id);
                        dailyDataVaccination.flock_vaccination.status.push(item.status);
                    }
                });//console.log(dailyDataVaccination);
                if (mid === 1) {
                    //  console.log(dailyData);
                    let url = `${apiPath}dailyData/${dailyDataPublicID}/`;
                    // U: OLD: config.headers['Authorization'] was mutated before each save request.
                    axios.patch(url, dailyData, getAuthConfig()).then(() => {
                        //setErr('Form created successfully');
                        setShow(true);
                        setTimeout(successMsg, 3000);
                    }).catch(handleSaveError);
                } else {
                    //console.log(dailyDataVaccination);
                    let url = `${apiPath}dailyData/${dailyDataPublicID}/`;
                    axios.patch(url, dailyDataVaccination, getAuthConfig()).then(() => {
                        //setErr('Form created successfully');
                        setShow(true);
                        setTimeout(successMsg, 3000);
                    }).catch(handleSaveError);
                }
            } else {
                formValues.forEach((item) => {
                    if (item.vaccine_public_id.length > 0) {
                        mid = 0;
                        dailyDataVaccination.flock_vaccination.vaccine_public_id.push(item.vaccine_public_id);
                        if (item.type === undefined) {
                            dailyDataVaccination.flock_vaccination.status.push(item.status);
                        } else {
                            dailyDataVaccination.flock_vaccination.status.push(item.type);
                        }
                    }
                })
                if (mid === 1) {
                    // console.log(dailyData);
                    let url = `${apiPath}dailyData/`;
                    axios.post(url, dailyData, getAuthConfig()).then(() => {
                        //setErr('Form created successfully');
                        setAddData({ ...addData, mortality: null, feed_intake: null, average_bird_weight: null })
                        setShow(true);
                        setTimeout(successMsg, 3000);
                    }).catch(handleSaveError);
                } else {
                    // console.log(dailyDataVaccination);
                    let url = `${apiPath}dailyData/`;
                    axios.post(url, dailyDataVaccination, getAuthConfig()).then(() => {
                        //setErr('Form created successfully');
                        setAddData({ ...addData, mortality: null, feed_intake: null, average_bird_weight: null })
                        setShow(true);
                        setTimeout(successMsg, 3000);
                    }).catch(handleSaveError);
                }
            }
        } else {
            setLoading(false);
        }
    }
    function successMsg() {
        setShow(false);
        setLastInsertDate(date);
        setLoading(false);
        localStorage.removeItem(dailyDraftKey);
    }
    useEffect(() => {
        setFormValues([{ public_id: "", vaccine_public_id: "", status: "" }]);
        const day = [];
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        let dt = new Date(date);
        let textday = `${dt.getDate()}`;
        if (textday.length === 1) {
            textday = `0${textday}`;
        }
        day.push(`${textday} ${monthNames[dt.getMonth()]} ${dt.getFullYear()}`);

        dt.setDate(dt.getDate() + 1);
        textday = `${dt.getDate()}`;
        if (textday.length === 1) {
            textday = `0${textday}`;
        }
        day.push(`${textday} ${monthNames[dt.getMonth()]} ${dt.getFullYear()}`);

        dt.setDate(dt.getDate() - 2);
        textday = `${dt.getDate()}`;
        if (textday.length === 1) {
            textday = `0${textday}`;
        }
        day.push(`${textday} ${monthNames[dt.getMonth()]} ${dt.getFullYear()}`);

        dt.setDate(dt.getDate());
        textday = `${dt.getDate()}`;
        if (textday.length === 1) {
            textday = `0${textday}`;
        }

        let text = `${new Date(dt).getMonth() + 1}`;
        if (text.length === 1) {
            text = `0${text}`;
        }
        day.push(`${dt.getFullYear()}-${text}-${textday}`);

        dt.setDate(dt.getDate() + 2);
        textday = `${dt.getDate()}`;
        if (textday.length === 1) {
            textday = `0${textday}`;
        }
        text = `${new Date(dt).getMonth() + 1}`;
        if (text.length === 1) {
            text = `0${text}`;
        }
        day.push(`${dt.getFullYear()}-${text}-${textday}`);
        setTodayDate(day);
    }, [date])
    let changeFormat = (dt) => {
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        let textday = `${new Date(dt).getDate()}`;
        if (textday.length === 1) {
            textday = `0${textday}`;
        }
        return `${textday}-${monthNames[new Date(dt).getMonth()]}-${new Date(dt).getFullYear()}`;
    }
    let datCompare = (hd, td) => {
        const hatchDate = new Date(hd);
        const targetDate = new Date(td);
        return hatchDate.getTime() >= targetDate.getTime();
    }
    let datCompareSame = (hd, td) => {
        //  console.log(hd, td)
        const hatchDate = new Date(hd);
        const targetDate = new Date(td);
        return hatchDate.getTime() === targetDate.getTime();
    }
    //For flock details
    useEffect(() => {
        let url = `${apiPath}flocksDetail/${flockid}/`;
        // U: OLD: config.headers['Authorization'] was mutated before each request.
        axios.get(url, getAuthConfig()).then((res) => {
            setFlockDetails(res.data.results);
            //console.log(res.data.results);
            //setAddData(addData.current_bird_count=res.data.results.actual_birds);
        }).catch((err) => {
            handleUnauthorized(err, navigate);
        });
    }, [flockid, navigate])
    //For daily data
    useEffect(() => {
        //For total feed
        let url = `${apiPath}quantity/?date=${date}&flock_public_id=${flockid}`; //console.log(url);
        const authConfig = getAuthConfig();
        axios.get(url, authConfig).then((res1) => {
            const initialQuantity = res1.data.results.quantity;
            setOldValues((current) => ({ ...current, initial_total_feed: initialQuantity }));
            //setAddData({...addData,feed_stock:res.data.results.quantity,total_feed:0});

            url = `${apiPath}dailyData/?flock_public_id=${flockid}&date=${date}`;
            axios.get(url, authConfig).then((res) => {
                const results = res.data.results;
                const dailyData = results.daily_data;
                const yesterdayData = results.yesterday_daily_data;
                // console.log(res.data.results.yesterday_daily_data.mort, "nkjnj");
                if (results.number_of_days === 1 && dailyData.current_bird_count === undefined) {
                    setUpdation(false);
                    setAddData((current) => ({ ...current, type: 'Save', feed_stock: initialQuantity }));
                    setOldValues((current) => ({ ...current, feed_stock: initialQuantity }));
                    // console.log("first day first time");
                } else if (dailyData.current_bird_count === undefined) {
                    // console.log("first time");
                    setUpdation(false);
                    // setAddData({ ...addData, type: 'Save', cooling: false, heating: false, medicine: false, seek: false, darkness_time_public_id: 0, feed_availability_public_id: 0, mortality: null, feed_intake: null, average_bird_weight: null, mortalityPer: res.data.results.yesterday_daily_data.total_mort, current_bird_count: res.data.results.yesterday_daily_data.current_bird_count, feed_stock: res1.data.results.quantity - res.data.results.yesterday_daily_data.total_feed, total_feed: res.data.results.yesterday_daily_data.total_feed, avg_feed_per_bird: res.data.results.yesterday_daily_data.average_feed, total_fcr: res.data.results.yesterday_daily_data.total_fcr, fcr: res.data.results.yesterday_daily_data.fcr, mort: res.data.results.yesterday_daily_data.mort });

//MV-23-6-25- 17-10 added cum_mort and total_mortality_percentage
                    setAddData((current) => ({ ...current, type: 'Save', cooling: false, heating: false, medicine: false, seek: false, darkness_time_public_id: 0, feed_availability_public_id: 0, mortality: null, feed_intake: null, average_bird_weight: null, mortalityPer: yesterdayData.total_mort, current_bird_count: yesterdayData.current_bird_count, feed_stock: initialQuantity - yesterdayData.total_feed, total_feed: yesterdayData.total_feed, avg_feed_per_bird: yesterdayData.average_feed, total_fcr: yesterdayData.total_fcr, fcr: yesterdayData.fcr, mort: yesterdayData.mort, cum_mort: yesterdayData.cum_mort, total_mortality_percentage: yesterdayData.total_mortality_percentage }));
//MV-23-6-25- 17-10 change end

                    setOldValues((current) => ({ ...current, current_bird_count: yesterdayData.current_bird_count, feed_stock: initialQuantity - yesterdayData.total_feed, total_feed: yesterdayData.total_feed }))
                } else {
                    //console.log("updation");
                    setDailyDataPublicID(dailyData.public_id);
                    setUpdation(true);
                    // setAddData({ ...addData, type: 'Update', cooling: res.data.results.daily_data.cooling, heating: res.data.results.daily_data.heating, medicine: res.data.results.daily_data.medicine, seek: res.data.results.daily_data.seek, darkness_time_public_id: res.data.results.daily_data.darkness_time_public_id, feed_availability_public_id: res.data.results.daily_data.feed_availability_public_id, mortality: res.data.results.daily_data.mortality, feed_intake: res.data.results.daily_data.feed_intake, average_bird_weight: res.data.results.daily_data.average_bird_weight, mort: res.data.results.daily_data.mort, mortalityPer: res.data.results.daily_data.total_mort, current_bird_count: res.data.results.daily_data.current_bird_count, feed_stock: res1.data.results.quantity - res.data.results.daily_data.total_feed, total_feed: res.data.results.daily_data.total_feed, avg_feed_per_bird: res.data.results.daily_data.average_feed, total_fcr: res.data.results.daily_data.total_fcr, cum_mort: res.data.results.daily_data.cum_mort, fcr: res.data.results.daily_data.fcr, total_mortality_percentage: res.data.results.daily_data.total_mortality_percentage });

//MV-23-6-25- 17-10 added cum_mort & total_mortality_percentage
                    setAddData((current) => ({ ...current, type: 'Update', cooling: dailyData.cooling, heating: dailyData.heating, medicine: dailyData.medicine, seek: dailyData.seek, darkness_time_public_id: dailyData.darkness_time_public_id, feed_availability_public_id: dailyData.feed_availability_public_id, mortality: dailyData.mortality, feed_intake: dailyData.feed_intake, average_bird_weight: dailyData.average_bird_weight, mort: dailyData.mort, mortalityPer: dailyData.total_mort, current_bird_count: dailyData.current_bird_count, feed_stock: initialQuantity - dailyData.total_feed, total_feed: dailyData.total_feed, avg_feed_per_bird: dailyData.average_feed, total_fcr: dailyData.total_fcr, cum_mort: dailyData.cum_mort, fcr: dailyData.fcr, total_mortality_percentage: dailyData.total_mortality_percentage }));
//MV-23-6-25- 17-10 change end

                    if (yesterdayData.current_bird_count === undefined) {
                        setOldValues((current) => ({ ...current, feed_stock: initialQuantity }));
                    } else {
                        setOldValues((current) => ({ ...current, current_bird_count: yesterdayData.current_bird_count, feed_stock: initialQuantity - yesterdayData.total_feed, total_feed: yesterdayData.total_feed }))
                    }
                    if (dailyData.flock_vaccination.length > 0) {
                        const midvar = dailyData.flock_vaccination.map((item) => ({ public_id: item.public_id, vaccine_public_id: item.vaccine_public_id, status: item.status }));
                        setFormValues(midvar);
                    }
                }
                setDaysCount(results.number_of_days);

            }).catch((err) => {
                handleUnauthorized(err, navigate);
            });
        }).catch((err) => {
            handleUnauthorized(err, navigate);
        });
        //For total feed
    }, [date, flockid, navigate])
    useEffect(() => {
        let url = `${apiPath}vaccines/`;
        axios.get(url, getAuthConfig()).then((res) => {
            setVaccines(res.data.results.vaccines_list);
        }).catch((err) => {
            handleUnauthorized(err, navigate);
        });
    }, [navigate])
    useEffect(() => {
        let url = `${apiPath}dailyDataLastDate/${flockid}/`;
        axios.get(url, getAuthConfig()).then((res) => {
            setLastInsertDate(res.data.results.last_date);
        }).catch((err) => {
            setLastInsertDate(null);
            handleUnauthorized(err, navigate);
        });
    }, [date, flockid, navigate])
    //For Select Darkness Time
    useEffect(() => {
        let url = `${apiPath}darknessTime/`;
        axios.get(url, getAuthConfig()).then((res) => {
            setDarkNess(res.data.results.darkness_time_list);
        }).catch((err) => {
            handleUnauthorized(err, navigate);
        });
    }, [navigate])
    //Select Feed Availability Time
    useEffect(() => {
        let url = `${apiPath}feedAvailability/`;
        axios.get(url, getAuthConfig()).then((res) => {
            setFeedAvaibility(res.data.results.feed_availability_list);
            // console.log()
        }).catch((err) => {
            handleUnauthorized(err, navigate);
        });
    }, [navigate])
    let mortalityData = (e) => {
        let midData = 0;
        if (oldValues.current_bird_count === null) { midData = flockDetails.actual_birds; } else { midData = oldValues.current_bird_count; }
        if (e.target.value !== null && e.target.value !== '' && e.target.value >= 0) {
            if (e.target.value <= midData - 1) {
                setMortalityError('');
                let current = 0;
                if (oldValues.current_bird_count === null) {
                    current = flockDetails.actual_birds - e.target.value;
                } else {
                    current = oldValues.current_bird_count - e.target.value;
                }
                let url = `${apiPath}dailyDataMortality/?current_bird_count=${current}&actual_birds=${flockDetails.actual_birds}`;
                axios.get(url, getAuthConfig()).then((res) => {
                    setAddData({ ...addData, current_bird_count: current, mortality: e.target.value, mortalityCount: res.data.results.total_mort_value, mortalityPer: res.data.results.total_mort_percent });
                }).catch((err) => {
                    setAddData({ ...addData, mortality: e.target.value });
                    handleUnauthorized(err, navigate);
                });
            } else {
                setAddData({ ...addData, mortality: e.target.value });
                setMortalityError('Mortality cannot be more than the bird count.');
            }
        } else {
            setAddData({ ...addData, mortality: e.target.value });
            setMortalityError('This fields is not a valid.');
        }
    }
    let feedData = (e) => {
        const feedIntake = Number(e.target.value);
        const availableFeedStock = getAvailableFeedStock();
        if (e.target.value !== '' && feedIntake > 0) {
            if (feedIntake <= availableFeedStock) {
                setFeedintakeError('');
                let url = `${apiPath}dailyDataAvgFeed/?current_bird_count=${addData.current_bird_count}&date=${date}&feed_intake=${e.target.value}&flock_public_id=${flockid}`;
                axios.get(url, getAuthConfig()).then((res) => {
                    // console.log(url); console.log(res.data.results);
                    setAddData({ ...addData, feed_intake: e.target.value, avg_feed_per_bird: res.data.results.avg_feed_per_bird, total_feed: Number(oldValues.total_feed) + feedIntake, feed_stock: availableFeedStock - feedIntake });
                }).catch((err) => {
                    setAddData({ ...addData, feed_intake: e.target.value });
                    handleUnauthorized(err, navigate);
                });
            } else {
                setAddData({ ...addData, feed_intake: e.target.value });
                setFeedintakeError(FEED_STOCK_ERROR);
            }
        } else {
            setAddData({ ...addData, feed_intake: e.target.value });
            setFeedintakeError('This fields is not a valid.');
        }
    }
    let getFcr = (e) => {
        if (e.target.value > 0) {
            setAverageBirdError('')
            let url = `${apiPath}dailyDataFCR/?date=${date}&flock_public_id=${flockid}&average_feed=${addData.avg_feed_per_bird}&average_bird_weight=${e.target.value}`;
            axios.get(url, getAuthConfig()).then((res) => {
                setAddData({ ...addData, average_bird_weight: e.target.value, fcr: res.data.results.fcr, total_fcr: res.data.results.total_fcr })
            }).catch((err) => {
                setAddData({ ...addData, average_bird_weight: e.target.value });
                handleUnauthorized(err, navigate);
            });
        }

        // else {
        //     setAddData(addData.average_bird_weight = e.target.value);
        //     setAverageBirdError('This fields is not a valid.');
        // }
    }
    let closeAll = () => {
        localStorage.removeItem(dailyDraftKey);
        navigate("/flockdailydata")

    }
    const validateDailyStep = () => {
        let valid = true;
        if (dailyStep === 0) {
            let midData = oldValues.current_bird_count === null ? flockDetails.actual_birds : oldValues.current_bird_count;
            let feedStock = getAvailableFeedStock();
            if (addData.mortality === null || addData.mortality === '' || Number(addData.mortality) < 0 || Number(addData.mortality) >= Number(midData || 0)) {
                setMortalityError('Mortality must be 0 or more and less than current bird count.');
                valid = false;
            }
            if (addData.feed_intake === null || addData.feed_intake === '' || Number(addData.feed_intake) <= 0 || Number(addData.feed_intake) > Number(feedStock || 0)) {
                setFeedintakeError(FEED_STOCK_ERROR);
                valid = false;
            }
            if (addData.average_bird_weight !== null && addData.average_bird_weight !== '' && Number(addData.average_bird_weight) <= 0) {
                setAverageBirdError('Average bird weight must be greater than 0.');
                valid = false;
            }
        }
        if (dailyStep === 3) {
            if (addData.darkness_time_public_id === 0 || addData.darkness_time_public_id === "0") {
                setDarknessError('Select darkness time.');
                valid = false;
            }
            if (addData.feed_availability_public_id === 0 || addData.feed_availability_public_id === "0") {
                setFeedAvaibilityError('Select feed availability time.');
                valid = false;
            }
        }
        return valid;
    };
    const goNextDailyStep = () => {
        if (!validateDailyStep()) {
            return;
        }
        setDailyStep((currentStep) => Math.min(currentStep + 1, dailyDataSteps.length - 1));
    };
    const goPreviousDailyStep = () => {
        setDailyStep((currentStep) => Math.max(currentStep - 1, 0));
    };
    const displayFeedStock = getDisplayFeedStock();
    // console.log(formValues, "lhgfdfgh");
    return (
        <Row>

            <Modal show={show} backdrop="static" keyboard={false} >
                <Modal.Header>
                </Modal.Header>
                <Modal.Body>
                    <Alert color="success">
                        {(updation === true) ? `Daily data successfully updated` : `Daily data successfully added`}
                    </Alert>
                    <Spinner animation="border" variant="success" style={{ 'marginLeft': '45%' }} />
                </Modal.Body>
                <Modal.Footer>
                </Modal.Footer>
            </Modal>
            <Col>
                <Card className="pb-4">
                    <CardTitle tag="h6" className="border-bottom p-3 mb-0">
                        Flock Daily Data
                    </CardTitle>
                    <CardBody>
                        <Row className="mt-0">
                            <Col sm="12" md='12' lg={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        {(err !== '') && <Alert color="danger">{err}</Alert>}
                                        <Row className="mt-0 mb-6 ml-4">
                                            {datCompare(flockDetails.hatch_date, todayDate[3]) ? null :
                                                <Col sm="6" md="4" lg="4" className="mt-6">
                                                    <Link to={`/daydata/${farmid}/${flockid}/${todayDate[3]}`} className="linkgroup" style={{ backgroundColor: '#d66f73', color: '#fff' }}>Previous: {todayDate[2]}</Link>
                                                </Col>
                                            }
                                            <Col sm="6" md="4" lg="4" className="mt-6">
                                                {/* U: OLD: this said "Today" even when the farmer opened an older flock day.
                                                    U: NEW: label it as the selected entry date. */}
                                                <span className="linkgroup" style={{ color: '#000' }}>Entry date: {todayDate[0]}</span>
                                            </Col>
                                            <Col sm="6" md="4" lg="4" className="mt-6">
                                                {datCompareSame(lastInsertDate, todayDate[3]) || lastInsertDate === '' || lastInsertDate === null ?
                                                    <span className="linkgroup" style={{ color: '#000' }}>Next: {todayDate[1]}</span> :
                                                    <Link to={`/daydata/${farmid}/${flockid}/${todayDate[4]}`} className="linkgroup" style={{ backgroundColor: '#d66f73', color: '#fff' }}>Next: {todayDate[1]}</Link>
                                                }
                                            </Col>
                                        </Row>
                                        <div className="form-stepper" aria-label="Daily data steps">
                                            {dailyDataSteps.map((step, index) => (
                                                <button
                                                    key={step.title}
                                                    type="button"
                                                    className={index === dailyStep ? "is-active" : index < dailyStep ? "is-complete" : ""}
                                                    onClick={() => setDailyStep(index)}
                                                >
                                                    <span>{index + 1}</span>
                                                    <strong>{step.title}</strong>
                                                    <small>{step.helper}</small>
                                                </button>
                                            ))}
                                        </div>
                                        <Form onSubmit={handleSubmit}>
                                            <Row className="mt-3">
                                                <Col sm="6" md="4" lg="4">
                                                    <Label for="flockname " className="font-bold">Flock </Label>
                                                    <Alert color="danger" style={{ color: '#000' }}>{flockDetails.flock_name}</Alert>
                                                </Col>
                                                <Col sm="6" md="4" lg="4">
                                                    <Label for="flockname" className="font-bold flex">Hatch Date(Age)</Label>
                                                    <Alert color="danger" style={{ color: '#000' }}>{changeFormat(flockDetails.hatch_date)}({daysCount})</Alert>
                                                </Col>
                                                <Col sm="6" md="4" lg="4">
                                                    <Label for="flockname" className="font-bold">Intial Bird Count</Label>
                                                    <Alert color="danger" style={{ color: '#000' }}>{flockDetails.flock_bird}</Alert>
                                                </Col>
                                            </Row>
                                            <Accordion activeKey={String(dailyStep)} className="mb-3">
                                                {dailyStep === 0 && (
                                                <Accordion.Item eventKey="0">
                                                    <Accordion.Header>Flock Data</Accordion.Header>
                                                    <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                        <Row>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="Mortality" className="font-bold">Mortality</Label>
                                                                <input type="number" onBlur={mortalityData} name="mortality" defaultValue={addData.mortality} placeholder="Mortality count" className="form-control" aria-label="Mortality" aria-describedby="basic-addon1" />
                                                                <small className="text-danger">{mortalityError}</small>
                                                            </Col>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname" className="font-bold flex">Total Mort(%)</Label>
                                                                <Alert color="secondary" style={{ color: '#000' }}>
                                                                    {/* {addData.mort}
                                                                    {`(${addData.mortalityPer}%)`} */}

{/* MV-23-6-25- 17-10 display updated values */}
                                                                    {addData.cum_mort}
                                                                    {`(${addData.total_mortality_percentage}%)`}
{/* MV-23-6-25- 17-10 change end */}

                                                                </Alert>
                                                            </Col>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname" className="font-bold">Current Bird Cnt</Label>
                                                                {/* <Alert color="secondary" style={{ color: '#000' }}>{addData.current_bird_count == null ? flockDetails.actual_birds : addData.current_bird_count}</Alert> */}

{/* MV-23-6-25- 17-10 0 displayed when null count */}
                                                                <Alert color="secondary" style={{ color: '#000' }}>{addData.current_bird_count === null ? 0 : addData.current_bird_count}</Alert>
{/* MV-23-6-25- 17-10 change end */}

                                                            </Col>
                                                        </Row>
                                                        <Row>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname " className="font-bold">Feed Intake(Kgs)</Label>
                                                                <input onBlur={feedData} name="feedintake" defaultValue={addData.feed_intake} placeholder="Feed Intake(Kgs)" type="number" className="form-control" aria-label="feedintake" aria-describedby="basic-addon1" />
                                                                <small className="text-danger">{feedintakeError}</small>
                                                            </Col>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname" className="font-bold flex">Total Feed(Kgs)</Label>
                                                                <Alert color="secondary" style={{ color: '#000' }}>{addData.total_feed}</Alert>
                                                            </Col>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname" className="font-bold">Feed Stock(Kgs)</Label>
                                                                <Alert color={displayFeedStock <= 0 ? "warning" : "secondary"} style={{ color: '#000' }}>{displayFeedStock}</Alert>
                                                                {displayFeedStock <= 0 && (
                                                                    <div className="form-helper-panel mt-2">
                                                                        <strong>No feed stock available</strong>
                                                                        <p>Add a feed purchase for this flock before recording feed consumed.</p>
                                                                        <Button
                                                                            color="danger"
                                                                            outline
                                                                            type="button"
                                                                            onClick={() => navigate("/addpurchase", { state: { farmPublicId: farmid, flockPublicId: flockid } })}
                                                                        >
                                                                            Add feed purchase
                                                                        </Button>
                                                                    </div>
                                                                )}
                                                            </Col>
                                                        </Row>
                                                        <Row>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname " className="font-bold">Avg. Feed/Birds</Label>
                                                                <Alert color="danger" style={{ color: '#000' }}>{addData.avg_feed_per_bird}</Alert>
                                                            </Col>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname" className="font-bold flex">Avg. Bird Wt.(gm) (optional)</Label>
                                                                <input onBlur={getFcr} name="avgbirdweight" defaultValue={addData.average_bird_weight} placeholder="Avg. Bird Wt.(gm)" type="number" className="form-control" aria-label="avgcount" aria-describedby="basic-addon1" />
                                                                <small className="text-danger">{averageBirdError}</small>
                                                            </Col>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname" className="font-bold">FCR/Total FCR ({date})</Label>
                                                                <Alert color="danger" style={{ color: '#000' }}>{`${addData.fcr ? addData.fcr : "-"}/${addData.total_fcr ? addData.total_fcr : "-"}`}</Alert>
                                                            </Col>
                                                        </Row>
                                                    </Accordion.Body>
                                                </Accordion.Item>
                                                )}
                                                {dailyStep === 1 && (
                                                <Accordion.Item eventKey="1">
                                                    <Accordion.Header>Vaccinations</Accordion.Header>
                                                    <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                        {formValues.map((element, index) => (
                                                            <Row key={index}>
                                                                <Col sm="6" md="4" lg="4">
                                                                    {
                                                                        index ? <Label>&nbsp;</Label>
                                                                            : <Label for="exampleSelect">Vaccination Today?</Label>
                                                                    }
                                                                    {/* U: OLD: option-level selected props mixed strings and numbers; React expects select value/defaultValue. */}
                                                                    <Input id="exampleSelect" name="vaccine_public_id" type="select" value={element.vaccine_public_id || ""} onChange={e => handleChange(index, e)}>
                                                                        <option value="">Select Vaccination</option>
                                                                        {
                                                                            vaccines.map((item) => {
                                                                                return (
                                                                                    <option key={item.public_id} value={item.public_id}>{item.full_name}</option>
                                                                                )
                                                                            })
                                                                        }
                                                                    </Input>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="exampleSelect">&nbsp;</Label>
                                                                    <Input id="exampleSelect" name="status" type="select" value={element.status || ""} onChange={e => handleChange(index, e)}>
                                                                        <option value=''>Select Status</option>
                                                                        <option value='Start'>Started</option>
                                                                        <option value='Continue'>Continue</option>
                                                                        <option value='Complete'>Completed</option>
                                                                    </Input>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4"><Label>&nbsp;</Label><br />
                                                                    {
                                                                        index ?
                                                                            <Button className="btn" color="danger" type="button" onClick={() => removeFormFields(index, element.public_id)}>- Remove</Button>
                                                                            : element.status !== "" ? <Button className="btn" color="success" type="button" onClick={() => addFormFields()} >+ Add More</Button> : <Button className="btn" color="success" type="button" onClick={() => alert('Please select vaccination and status')}>+ Add More</Button>
                                                                    }
                                                                </Col>
                                                            </Row>
                                                        ))}
                                                    </Accordion.Body>
                                                </Accordion.Item>
                                                )}
                                                {dailyStep === 2 && (
                                                <Accordion.Item eventKey="2">
                                                    <Accordion.Header>More Data</Accordion.Header>
                                                    <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                        <Row>{/*heating:false,:false,:false,:false*/}
                                                            <Col sm="3" md="3" lg="3">
                                                                <Input type="checkbox" checked={addData.heating} onChange={(e) => { (e.target.checked ? setAddData({ ...addData, heating: true }) : setAddData({ ...addData, heating: false })) }} name="heating" /> Heating?
                                                            </Col>
                                                            <Col sm="3" md="3" lg="3">
                                                                <Input type="checkbox" checked={addData.seek} name="seek" onChange={(e) => { (e.target.checked ? setAddData({ ...addData, seek: true }) : setAddData({ ...addData, seek: false })) }} /> Sick?
                                                            </Col>
                                                            <Col sm="3" md="3" lg="3">
                                                                <Input type="checkbox" checked={addData.cooling} name="cooling" onChange={(e) => { (e.target.checked ? setAddData({ ...addData, cooling: true }) : setAddData({ ...addData, cooling: false })) }} /> Cooling?
                                                            </Col>
                                                            <Col sm="3" md="3" lg="3">
                                                                <Input type="checkbox" checked={addData.medicine} name="medicine" onChange={(e) => { (e.target.checked ? setAddData({ ...addData, medicine: true }) : setAddData({ ...addData, medicine: false })) }} /> Meds?
                                                            </Col>
                                                        </Row>
                                                    </Accordion.Body>
                                                </Accordion.Item>
                                                )}
                                                {dailyStep === 3 && (
                                                <Accordion.Item eventKey="3">
                                                    <Accordion.Header>Darkness / Feed Availability</Accordion.Header>
                                                    <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                        <Row>
                                                            <Col sm="6" md="6" lg="6">
                                                                <Label for="darkness">Darkness Time</Label>
                                                                <Input id="darkness" name="darkness" type="select" value={addData.darkness_time_public_id || "0"} onChange={(e) => { (setAddData({ ...addData, darkness_time_public_id: e.target.value })) }}>
                                                                    <option value="0">Select Darkness Time</option>
                                                                    {
                                                                        darkNess.map((item) => {
                                                                            return (
                                                                                <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                                                            )
                                                                        })
                                                                    }
                                                                </Input>
                                                                <small className="text-danger">{darknessError}</small>
                                                            </Col>
                                                            <Col sm="6" md="6" lg="6">
                                                                <Label for="feedavailability">Feed Availability Time</Label>
                                                                <Input id="feedavailability" name="feedavailability" type="select" value={addData.feed_availability_public_id || "0"} onChange={(e) => { (setAddData({ ...addData, feed_availability_public_id: e.target.value })) }}>
                                                                    <option value="0">Select Feed Availability Time</option>
                                                                    {
                                                                        feedAvaibility.map((item) => {
                                                                            return (
                                                                                <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                                                            )
                                                                        })
                                                                    }
                                                                </Input>
                                                                <small className="text-danger">{feedAvaibilityError}</small>
                                                            </Col>
                                                        </Row>
                                                    </Accordion.Body>
                                                </Accordion.Item>
                                                )}
                                            </Accordion>
                                            {dailyStep === 4 && (
                                                <div className="form-review-card">
                                                    <span>Review daily data</span>
                                                    <dl>
                                                        <div><dt>Mortality</dt><dd>{addData.mortality ?? "Missing"}</dd></div>
                                                        <div><dt>Feed intake</dt><dd>{addData.feed_intake ?? "Missing"} kg</dd></div>
                                                        <div><dt>Current birds</dt><dd>{addData.current_bird_count ?? "Missing"}</dd></div>
                                                        <div><dt>Average weight</dt><dd>{addData.average_bird_weight ?? "Not added"} gm</dd></div>
                                                        <div><dt>FCR</dt><dd>{addData.fcr || "-"}</dd></div>
                                                        <div><dt>Vaccination rows</dt><dd>{formValues.filter((item) => item.vaccine_public_id).length}</dd></div>
                                                        <div><dt>Darkness</dt><dd>{addData.darkness_time_public_id || "Missing"}</dd></div>
                                                        <div><dt>Feed availability</dt><dd>{addData.feed_availability_public_id || "Missing"}</dd></div>
                                                    </dl>
                                                </div>
                                            )}
                                            <div className="form-wizard-actions">
                                                {dailyStep > 0 && <Button type="button" color="secondary" outline onClick={goPreviousDailyStep}>Back</Button>}
                                                {dailyStep < dailyDataSteps.length - 1 && <Button type="button" color="danger" onClick={goNextDailyStep}>Next</Button>}
                                                {dailyStep === dailyDataSteps.length - 1 && (loading ?
                                                    <Button className="btn" color="danger" type="submit">
                                                        Please wait...
                                                        <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                    </Button>
                                                    :
                                                    <Button className="btn" color="danger" type="submit">{addData.type}</Button>
                                                )}
                                                <Button className="btn" color="secondary" outline type="button" onClick={closeAll}>Cancel</Button>
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

export default DaywiseData;
