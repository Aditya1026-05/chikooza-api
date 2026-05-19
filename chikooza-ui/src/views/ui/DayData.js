import { Row, Col, Card, CardTitle, CardBody, Alert, Button, Form, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { useState, useEffect } from "react";
import { contentArea, apiPath, config } from "../../Constants";
import Accordion from 'react-bootstrap/Accordion';
import { Link, useParams } from "react-router-dom";
import axios from 'axios';
import Modal from 'react-bootstrap/Modal';
import Spinner from 'react-bootstrap/Spinner';
import { useNavigate } from "react-router-dom";
import moment from "moment";


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
        if (public_id == "") {
            formValues.splice(i, 1)
            // console.log(formValues.splice(i, 1));
            setFormValues([...formValues])
        } else {
            let url = `${apiPath}flockVaccination/${public_id}/`;
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.delete(url, config).then((res) => {
                let newFormValues = [...formValues];
                newFormValues.splice(i, 1);
                setFormValues(newFormValues)
            }).catch((err) => {//console.log(err);
                if (err.response.status === 404) {
                    let newFormValues = [...formValues];
                    newFormValues.splice(i, 1);
                    setFormValues(newFormValues)
                }
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }
    }

    let handleSubmit = (event) => {
        event.preventDefault();
        let error = 0;
        setLoading(true);
        let midData = 0;
        if (addData.darkness_time_public_id === 0) { setDarknessError('This fields is not a valid.'); error = 1; } else { setDarknessError(''); }
        if (addData.feed_availability_public_id === 0) { setFeedAvaibilityError('This fields is not a valid.'); error = 1; } else { setFeedAvaibilityError(''); }
        if (oldValues.current_bird_count == null) { midData = flockDetails.actual_birds; } else { midData = oldValues.current_bird_count; }
        // console.log(addData.mortality + " > " + midData);
        if (addData.mortality === null || addData.mortality == '' || addData.mortality < 0 || addData.mortality >= midData) { setMortalityError('This fields is not a valid.'); error = 1; } else { setMortalityError(''); }
        midData = 0;
        if (oldValues.feed_stock === 0) { midData = oldValues.initial_total_feed; } else { midData = oldValues.feed_stock; }
        if (addData.feed_intake === null || addData.feed_intake == '' || addData.feed_intake <= 0 || addData.feed_intake > midData) { setFeedintakeError('This fields is not a valid.'); error = 1; } else { setFeedintakeError(''); }
        let midWeight = 0;
        if (addData.average_bird_weight == null || addData.feed_intake == '') {
            midWeight = 0;
        } else {
            midWeight = addData.average_bird_weight;
        }

        //console.log(error);
        if (error == 0) {
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
            if (updation == true) {
                formValues.map((item, index) => {//console.log(item);
                    if ((item.vaccine_public_id != '') && (item.status != '')) {
                        mid = 0;
                        if (item.public_id != '') {
                            dailyDataVaccination.flock_vaccination.flock_vaccination_public_id.push(item.public_id);
                        } else {
                            dailyDataVaccination.flock_vaccination.flock_vaccination_public_id.push(0);
                        }
                        dailyDataVaccination.flock_vaccination.vaccine_public_id.push(item.vaccine_public_id);
                        dailyDataVaccination.flock_vaccination.status.push(item.status);
                    }
                });//console.log(dailyDataVaccination);
                if (mid == 1) {
                    //  console.log(dailyData);
                    let url = `${apiPath}dailyData/${dailyDataPublicID}/`;
                    config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
                    axios.patch(url, dailyData, config).then((res) => {
                        //setErr('Form created successfully');
                        setShow(true);
                        const myTimeout = setTimeout(successMsg, 3000);
                    }).catch((err) => {
                        //  console.log(err);
                        setErr('Something went wrong. Please try again');
                        setLoading(false);
                        if (err.response.status === 401) {
                            localStorage.clear();
                            navigate("/login")
                        }

                    });
                } else {
                    //console.log(dailyDataVaccination);
                    let url = `${apiPath}dailyData/${dailyDataPublicID}/`;
                    config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
                    axios.patch(url, dailyDataVaccination, config).then((res) => {
                        //setErr('Form created successfully');
                        setShow(true);
                        const myTimeout = setTimeout(successMsg, 3000);
                    }).catch((err) => {
                        //console.log(err);
                        setErr('Something went wrong. Please try again');
                        setLoading(false);
                        if (err.response.status === 401) {
                            localStorage.clear();
                            navigate("/login")
                        }
                    });
                }
            } else {
                formValues.map((item) => {
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
                if (mid == 1) {
                    // console.log(dailyData);
                    let url = `${apiPath}dailyData/`;
                    config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
                    axios.post(url, dailyData, config).then((res) => {
                        //setErr('Form created successfully');
                        setAddData({ ...addData, mortality: null, feed_intake: null, average_bird_weight: null })
                        setShow(true);
                        const myTimeout = setTimeout(successMsg, 3000);
                    }).catch((err) => {
                        // console.log(err);
                        setErr('Something went wrong. Please try again');
                        setLoading(false);
                        if (err.response.status === 401) {
                            localStorage.clear();
                            navigate("/login")
                        }
                    });
                } else {
                    // console.log(dailyDataVaccination);
                    let url = `${apiPath}dailyData/`;
                    config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
                    axios.post(url, dailyDataVaccination, config).then((res) => {
                        //setErr('Form created successfully');
                        setAddData({ ...addData, mortality: null, feed_intake: null, average_bird_weight: null })
                        setShow(true);
                        const myTimeout = setTimeout(successMsg, 3000);
                    }).catch((err) => {
                        // console.log(err);
                        setErr('Something went wrong. Please try again');
                        setLoading(false);
                        if (err.response.status === 401) {
                            localStorage.clear();
                            navigate("/login")
                        }
                    });
                }
            }
        } else {
            setLoading(false);
        }
    }
    function successMsg() {
        //setAddData({...addData,mortality:null,feed_intake:null,average_bird_weight:null})
        setShow(false);
        setLastInsertDate(date);
        //setNxtLink(false);
        setLoading(false);
        window.location.reload();
    }
    useEffect(() => {
        setFormValues([{ public_id: "", vaccine_public_id: "", status: "" }]);
        let day = new Array();
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        let dt = new Date(date);
        let textday = `${dt.getDate()}`;
        if (textday.length == 1) {
            textday = `0${textday}`;
        }
        day.push(`${textday} ${monthNames[dt.getMonth()]} ${dt.getFullYear()}`);

        dt.setDate(dt.getDate() + 1);
        textday = `${dt.getDate()}`;
        if (textday.length == 1) {
            textday = `0${textday}`;
        }
        day.push(`${textday} ${monthNames[dt.getMonth()]} ${dt.getFullYear()}`);

        dt.setDate(dt.getDate() - 2);
        textday = `${dt.getDate()}`;
        if (textday.length == 1) {
            textday = `0${textday}`;
        }
        day.push(`${textday} ${monthNames[dt.getMonth()]} ${dt.getFullYear()}`);

        dt.setDate(dt.getDate());
        textday = `${dt.getDate()}`;
        if (textday.length == 1) {
            textday = `0${textday}`;
        }

        let text = `${new Date(dt).getMonth() + 1}`;
        if (text.length == 1) {
            text = `0${text}`;
        }
        day.push(`${dt.getFullYear()}-${text}-${textday}`);

        dt.setDate(dt.getDate() + 2);
        textday = `${dt.getDate()}`;
        if (textday.length == 1) {
            textday = `0${textday}`;
        }
        text = `${new Date(dt).getMonth() + 1}`;
        if (text.length == 1) {
            text = `0${text}`;
        }
        day.push(`${dt.getFullYear()}-${text}-${textday}`);
        console.log("dayyyyyyyyYYYY>>>>>>>>>>>>>>>>>>>", day)
        setTodayDate(day);
    }, [date])
    let changeFormat = (dt) => {
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        let textday = `${new Date(dt).getDate()}`;
        if (textday.length == 1) {
            textday = `0${textday}`;
        }
        return `${textday}-${monthNames[new Date(dt).getMonth()]}-${new Date(dt).getFullYear()}`;
    }
    let datCompare = (hd, td) => {
        var hd = new Date(hd);
        var td = new Date(td);
        if (hd.getTime() < td.getTime()) {
            return false;
        } else {
            return true;
        }
    }
    let datCompareSame = (hd, td) => {
        //  console.log(hd, td)
        var hd = new Date(hd);
        var td = new Date(td);
        if (hd.getTime() == td.getTime()) {
            return true;
        } else {
            return false;
        }
    }
    //For flock details
    useEffect(() => {
        let url = `${apiPath}flocksDetail/${flockid}/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setFlockDetails(res.data.results);
            //console.log(res.data.results);
            //setAddData(addData.current_bird_count=res.data.results.actual_birds);
        }).catch((err) => {
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    //For daily data
    useEffect(() => {
        //For total feed
        let url = `${apiPath}quantity/?date=${date}&flock_public_id=${flockid}`; //console.log(url);
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res1) => {
            setOldValues({ ...oldValues, initial_total_feed: res1.data.results.quantity });
            //setAddData({...addData,feed_stock:res.data.results.quantity,total_feed:0});

            url = `${apiPath}dailyData/?flock_public_id=${flockid}&date=${date}`;
            axios.get(url, config).then((res) => {
                // console.log(res.data.results.yesterday_daily_data.mort, "nkjnj");
                if (res.data.results.number_of_days === 1 && res.data.results.daily_data.current_bird_count === undefined) {
                    setUpdation(false);
                    setAddData({ ...addData, type: 'Save', feed_stock: res1.data.results.quantity });
                    setOldValues({ ...oldValues, feed_stock: res1.data.results.quantity });
                    // console.log("first day first time");
                } else if (res.data.results.daily_data.current_bird_count === undefined) {
                    // console.log("first time");
                    setUpdation(false);
                    // setAddData({ ...addData, type: 'Save', cooling: false, heating: false, medicine: false, seek: false, darkness_time_public_id: 0, feed_availability_public_id: 0, mortality: null, feed_intake: null, average_bird_weight: null, mortalityPer: res.data.results.yesterday_daily_data.total_mort, current_bird_count: res.data.results.yesterday_daily_data.current_bird_count, feed_stock: res1.data.results.quantity - res.data.results.yesterday_daily_data.total_feed, total_feed: res.data.results.yesterday_daily_data.total_feed, avg_feed_per_bird: res.data.results.yesterday_daily_data.average_feed, total_fcr: res.data.results.yesterday_daily_data.total_fcr, fcr: res.data.results.yesterday_daily_data.fcr, mort: res.data.results.yesterday_daily_data.mort });

//MV-23-6-25- 17-10 added cum_mort and total_mortality_percentage
                    setAddData({ ...addData, type: 'Save', cooling: false, heating: false, medicine: false, seek: false, darkness_time_public_id: 0, feed_availability_public_id: 0, mortality: null, feed_intake: null, average_bird_weight: null, mortalityPer: res.data.results.yesterday_daily_data.total_mort, current_bird_count: res.data.results.yesterday_daily_data.current_bird_count, feed_stock: res1.data.results.quantity - res.data.results.yesterday_daily_data.total_feed, total_feed: res.data.results.yesterday_daily_data.total_feed, avg_feed_per_bird: res.data.results.yesterday_daily_data.average_feed, total_fcr: res.data.results.yesterday_daily_data.total_fcr, fcr: res.data.results.yesterday_daily_data.fcr, mort: res.data.results.yesterday_daily_data.mort ,cum_mort: res.data.results.yesterday_daily_data.cum_mort ,total_mortality_percentage: res.data.results.yesterday_daily_data.total_mortality_percentage  });
//MV-23-6-25- 17-10 change end

                    setOldValues({ ...oldValues, current_bird_count: res.data.results.yesterday_daily_data.current_bird_count, feed_stock: res1.data.results.quantity - res.data.results.yesterday_daily_data.total_feed, total_feed: res.data.results.yesterday_daily_data.total_feed })
                } else {
                    //console.log("updation");
                    setDailyDataPublicID(res.data.results.daily_data.public_id);
                    setUpdation(true);
                    // setAddData({ ...addData, type: 'Update', cooling: res.data.results.daily_data.cooling, heating: res.data.results.daily_data.heating, medicine: res.data.results.daily_data.medicine, seek: res.data.results.daily_data.seek, darkness_time_public_id: res.data.results.daily_data.darkness_time_public_id, feed_availability_public_id: res.data.results.daily_data.feed_availability_public_id, mortality: res.data.results.daily_data.mortality, feed_intake: res.data.results.daily_data.feed_intake, average_bird_weight: res.data.results.daily_data.average_bird_weight, mort: res.data.results.daily_data.mort, mortalityPer: res.data.results.daily_data.total_mort, current_bird_count: res.data.results.daily_data.current_bird_count, feed_stock: res1.data.results.quantity - res.data.results.daily_data.total_feed, total_feed: res.data.results.daily_data.total_feed, avg_feed_per_bird: res.data.results.daily_data.average_feed, total_fcr: res.data.results.daily_data.total_fcr, cum_mort: res.data.results.daily_data.cum_mort, fcr: res.data.results.daily_data.fcr, total_mortality_percentage: res.data.results.daily_data.total_mortality_percentage });

//MV-23-6-25- 17-10 added cum_mort & total_mortality_percentage
                    setAddData({ ...addData, type: 'Update', cooling: res.data.results.daily_data.cooling, heating: res.data.results.daily_data.heating, medicine: res.data.results.daily_data.medicine, seek: res.data.results.daily_data.seek, darkness_time_public_id: res.data.results.daily_data.darkness_time_public_id, feed_availability_public_id: res.data.results.daily_data.feed_availability_public_id, mortality: res.data.results.daily_data.mortality, feed_intake: res.data.results.daily_data.feed_intake, average_bird_weight: res.data.results.daily_data.average_bird_weight, mort: res.data.results.daily_data.mort, mortalityPer: res.data.results.daily_data.total_mort, current_bird_count: res.data.results.daily_data.current_bird_count, feed_stock: res1.data.results.quantity - res.data.results.daily_data.total_feed, total_feed: res.data.results.daily_data.total_feed, avg_feed_per_bird: res.data.results.daily_data.average_feed, total_fcr: res.data.results.daily_data.total_fcr, cum_mort: res.data.results.daily_data.cum_mort, fcr: res.data.results.daily_data.fcr, total_mortality_percentage: res.data.results.daily_data.total_mortality_percentage });
//MV-23-6-25- 17-10 change end

                    if (res.data.results.yesterday_daily_data.current_bird_count === undefined) {
                        setOldValues({ ...oldValues, feed_stock: res1.data.results.quantity });
                    } else {
                        setOldValues({ ...oldValues, current_bird_count: res.data.results.yesterday_daily_data.current_bird_count, feed_stock: res1.data.results.quantity - res.data.results.yesterday_daily_data.total_feed, total_feed: res.data.results.yesterday_daily_data.total_feed })
                    }
                    if (res.data.results.daily_data.flock_vaccination.length > 0) {
                        let midvar = [];
                        res.data.results.daily_data.flock_vaccination.map((item) => {
                            midvar.push({ public_id: item.public_id, vaccine_public_id: item.vaccine_public_id, status: item.status });
                        });
                        setFormValues(midvar);
                    }
                }
                setDaysCount(res.data.results.number_of_days);

            }).catch((err) => {
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }).catch((err) => {
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
        //For total feed
    }, [date])
    useEffect(() => {
        let url = `${apiPath}vaccines/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setVaccines(res.data.results.vaccines_list);
        }).catch((err) => {
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    useEffect(() => {
        let url = `${apiPath}dailyDataLastDate/${flockid}/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setLastInsertDate(res.data.results.last_date);
        }).catch((err) => {
            setLastInsertDate(null);
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [date])
    //For Select Darkness Time
    useEffect(() => {
        let url = `${apiPath}darknessTime/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setDarkNess(res.data.results.darkness_time_list);
        }).catch((err) => {
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    //Select Feed Availability Time
    useEffect(() => {
        let url = `${apiPath}feedAvailability/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setFeedAvaibility(res.data.results.feed_availability_list);
            // console.log()
        }).catch((err) => {
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    let mortalityData = (e) => {
        let midData = 0;
        if (oldValues.current_bird_count == null) { midData = flockDetails.actual_birds; } else { midData = oldValues.current_bird_count; }
        if (e.target.value != null && e.target.value != '' && e.target.value >= 0) {
            if (e.target.value <= midData - 1) {
                setMortalityError('');
                let current = 0;
                if (oldValues.current_bird_count == null) {
                    current = flockDetails.actual_birds - e.target.value;
                } else {
                    current = oldValues.current_bird_count - e.target.value;
                }
                let url = `${apiPath}dailyDataMortality/?current_bird_count=${current}&actual_birds=${flockDetails.actual_birds}`;
                config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
                axios.get(url, config).then((res) => {
                    setAddData({ ...addData, current_bird_count: current, mortality: e.target.value, mortalityCount: res.data.results.total_mort_value, mortalityPer: res.data.results.total_mort_percent });
                }).catch((err) => {
                    setAddData({ ...addData, mortality: e.target.value });
                    if (err.response.status === 401) {
                        localStorage.clear();
                        navigate("/login")
                    }
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
        let midData = 0;
        if (oldValues.feed_stock == 0) { midData = oldValues.initial_total_feed; } else { midData = oldValues.feed_stock; }
        if (e.target.value != '' && e.target.value > 0) {
            if (e.target.value <= midData) {
                setFeedintakeError('');
                let url = `${apiPath}dailyDataAvgFeed/?current_bird_count=${addData.current_bird_count}&date=${date}&feed_intake=${e.target.value}&flock_public_id=${flockid}`;
                config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
                axios.get(url, config).then((res) => {
                    // console.log(url); console.log(res.data.results);
                    setAddData({ ...addData, feed_intake: e.target.value, avg_feed_per_bird: res.data.results.avg_feed_per_bird, total_feed: Number(oldValues.total_feed) + Number(e.target.value), feed_stock: oldValues.feed_stock - e.target.value });
                }).catch((err) => {
                    setAddData({ ...addData, feed_intake: e.target.value });
                    if (err.response.status === 401) {
                        localStorage.clear();
                        navigate("/login")
                    }
                });
            } else {
                setAddData({ ...addData, feed_intake: e.target.value });
                setFeedintakeError('Feed Intake cannot be more than the Feed Stock.');
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
            config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, config).then((res) => {
                setAddData({ ...addData, average_bird_weight: e.target.value, fcr: res.data.results.fcr, total_fcr: res.data.results.total_fcr })
            }).catch((err) => {
                setAddData({ ...addData, average_bird_weight: e.target.value });
                if (err.response.status === 401) {
                    localStorage.clear();
                    navigate("/login")
                }
            });
        }

        // else {
        //     setAddData(addData.average_bird_weight = e.target.value);
        //     setAverageBirdError('This fields is not a valid.');
        // }
    }
    let closeAll = () => {
        navigate("/flockdailydata")

    }
    // console.log(formValues, "lhgfdfgh");
    return (
        <Row>

            <Modal show={show} backdrop="static" keyboard={false} >
                <Modal.Header>
                </Modal.Header>
                <Modal.Body>
                    <Alert color="success">
                        {(updation == true) ? `Daily data successfully updated` : `Daily data successfully added`}
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
                                        {(err != '') && <Alert color="danger">{err}</Alert>}
                                        <Row className="mt-0 mb-6 ml-4">
                                            {datCompare(flockDetails.hatch_date, todayDate[3]) ? null :
                                                <Col sm="6" md="4" lg="4" className="mt-6">
                                                    <Link to={`/daydata/${farmid}/${flockid}/${todayDate[3]}`} className="linkgroup" style={{ backgroundColor: '#d66f73', color: '#fff' }}>« {todayDate[2]}</Link>
                                                </Col>
                                            }
                                            <Col sm="6" md="4" lg="4" className="mt-6">
                                                <span className="linkgroup" style={{ color: '#000' }}>Today: {moment(todayDate[0]).format("DD MMM")}</span>
                                            </Col>
                                            <Col sm="6" md="4" lg="4" className="mt-6">
                                                {datCompareSame(lastInsertDate, todayDate[3]) || lastInsertDate === '' || lastInsertDate === null ?
                                                    <span className="linkgroup" style={{ color: '#000' }}>{moment(todayDate[1]).format("DD MMM")}</span> :
                                                    <Link to={`/daydata/${farmid}/${flockid}/${todayDate[4]}`} className="linkgroup" style={{ backgroundColor: '#d66f73', color: '#fff' }}>{todayDate[1]} »</Link>
                                                }
                                            </Col>
                                        </Row>
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
                                            <Accordion defaultActiveKey="0" className="mb-3">
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
                                                                <Alert color="secondary" style={{ color: '#000' }}>{addData.current_bird_count == null ? 0 : addData.current_bird_count}</Alert>
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
                                                                <Alert color="danger" style={{ color: '#000' }}>{addData.feed_stock == null ? oldValues.initial_total_feed : addData.feed_stock}</Alert>
                                                            </Col>
                                                        </Row>
                                                        <Row>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname " className="font-bold">Avg. Feed/Birds</Label>
                                                                <Alert color="danger" style={{ color: '#000' }}>{addData.avg_feed_per_bird}</Alert>
                                                            </Col>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname" className="font-bold flex">Avg. Bird Wt.(gm)</Label>
                                                                <input onBlur={getFcr} name="avgbirdweight" defaultValue={addData.average_bird_weight} placeholder="Avg. Bird Wt.(gm)" type="number" className="form-control" aria-label="avgcount" aria-describedby="basic-addon1" />
                                                                <small className="text-danger">{averageBirdError}</small>
                                                            </Col>
                                                            <Col sm="6" md="4" lg="4">
                                                                <Label for="flockname" className="font-bold">FCR/Total FCR</Label>
                                                                <Alert color="danger" style={{ color: '#000' }}>{`${addData.fcr ? addData.fcr : "-"}/${addData.total_fcr ? addData.total_fcr : "-"}`}</Alert>
                                                            </Col>
                                                        </Row>
                                                    </Accordion.Body>
                                                </Accordion.Item>
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
                                                                    <Input id="exampleSelect" name="vaccine_public_id" type="select" onChange={e => handleChange(index, e)}>
                                                                        <option value="" selected={true}>Select Vaccination</option>
                                                                        {
                                                                            vaccines.map((item) => {
                                                                                return (
                                                                                    <option selected={element.vaccine_public_id == item.public_id} key={item.public_id} value={item.public_id}>{item.full_name}</option>
                                                                                )
                                                                            })
                                                                        }
                                                                    </Input>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4">
                                                                    <Label for="exampleSelect">&nbsp;</Label>
                                                                    <Input id="exampleSelect" name="status" type="select" onChange={e => handleChange(index, e)}>
                                                                        <option value='' selected={true}>Select Status</option>
                                                                        <option selected={element.status == 'Start'} value='Start'>Started</option>
                                                                        <option selected={element.status == 'Continue'} value='Continue'>Continue</option>
                                                                        <option selected={element.status == 'Complete'} value='Complete'>Completed</option>
                                                                    </Input>
                                                                </Col>
                                                                <Col sm="6" md="4" lg="4"><Label>&nbsp;</Label><br />
                                                                    {
                                                                        index ?
                                                                            <Button className="btn" color="danger" type="button" onClick={() => removeFormFields(index, element.public_id)}>- Remove</Button>
                                                                            : element.status != "" ? <Button className="btn" color="success" type="button" onClick={() => addFormFields()} >+ Add More</Button> : <Button className="btn" color="success" type="button" onClick={() => alert('Please select vaccination and status')}>+ Add More</Button>
                                                                    }
                                                                </Col>
                                                            </Row>
                                                        ))}
                                                    </Accordion.Body>
                                                </Accordion.Item>
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
                                                <Accordion.Item eventKey="3">
                                                    <Accordion.Header>Darkness / Feed Availability</Accordion.Header>
                                                    <Accordion.Body style={{ backgroundColor: 'white' }}>
                                                        <Row>
                                                            <Col sm="6" md="6" lg="6">
                                                                <Label for="darkness">Darkness Time</Label>
                                                                <Input id="darkness" name="darkness" type="select" onChange={(e) => { (setAddData({ ...addData, darkness_time_public_id: e.target.value })) }}>
                                                                    <option value="0" selected={true}>Select Darkness Time</option>
                                                                    {
                                                                        darkNess.map((item) => {
                                                                            return (
                                                                                <option selected={addData.darkness_time_public_id == item.public_id} key={item.public_id} value={item.public_id}>{item.name}</option>
                                                                            )
                                                                        })
                                                                    }
                                                                </Input>
                                                                <small className="text-danger">{darknessError}</small>
                                                            </Col>
                                                            <Col sm="6" md="6" lg="6">
                                                                <Label for="feedavailability">Feed Availability Time</Label>
                                                                <Input id="feedavailability" name="feedavailability" type="select" onChange={(e) => { (setAddData({ ...addData, feed_availability_public_id: e.target.value })) }}>
                                                                    <option value="0" selected={true}>Select Feed Availability Time</option>
                                                                    {
                                                                        feedAvaibility.map((item) => {
                                                                            return (
                                                                                <option selected={addData.feed_availability_public_id == item.public_id} key={item.public_id} value={item.public_id}>{item.name}</option>
                                                                            )
                                                                        })
                                                                    }
                                                                </Input>
                                                                <small className="text-danger">{feedAvaibilityError}</small>
                                                            </Col>
                                                        </Row>
                                                    </Accordion.Body>
                                                </Accordion.Item>
                                            </Accordion>
                                            <div className="button-group">
                                                {loading ?
                                                    <Button className="btn" color="danger" type="submit"   >
                                                        Please wait...
                                                        <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                                    </Button>
                                                    :
                                                    <Button className="btn" color="danger" type="submit" >{addData.type}</Button>
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

export default DaywiseData;