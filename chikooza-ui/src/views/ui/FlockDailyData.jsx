import { Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { useState, useEffect } from "react";
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import Modal from 'react-bootstrap/Modal'
import { Link } from "react-router-dom";
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const DAILY_SELECTOR_DRAFT_KEY = "chikooza-daily-selector-draft";

const readDailySelectorDraft = () => {
    try {
        const draft = JSON.parse(localStorage.getItem(DAILY_SELECTOR_DRAFT_KEY) || "{}");
        return {
            selectedFarmId: draft.selectedFarmId || "0",
            selectedFlockId: draft.selectedFlockId || "0",
            selectorStep: 0,
        };
    } catch {
        return { selectedFarmId: "0", selectedFlockId: "0", selectorStep: 0 };
    }
};

const ManageFlock = () => {
    const [initialDraft] = useState(() => readDailySelectorDraft());

    let [farms, setFarms] = useState([]);
    let [flocks, setFlocks] = useState([]);
    let [list, setList] = useState([]);
    let [flock, setFlock] = useState({});
    let [showFlock, setShowFlock] = useState(false);
    let [showForm, setShowForm] = useState(false);
    const navigate = useNavigate();
    const [selectedFarmId, setSelectedFarmId] = useState(initialDraft.selectedFarmId);
    const [selectedFlockId, setSelectedFlockId] = useState(initialDraft.selectedFlockId);
    const [selectorStep, setSelectorStep] = useState(initialDraft.selectorStep);

    function loadDailyDataForFlock(selectedFlock, nextStep = 0) {
        if (!selectedFlock || String(selectedFlock.flock_public_id) === "0") {
            setFlock({});
            setShowForm(false);
            setList([]);
            setSelectedFlockId("0");
            return;
        }

        setSelectedFlockId(String(selectedFlock.flock_public_id));
        setFlock(selectedFlock);
        setShowForm(true);
        setSelectorStep(nextStep);

        axios.get(`${apiPath}dailyDataDetail/?flock_public_id=${selectedFlock.flock_public_id}`, getAuthConfig()).then((res) => {
            if (res.data.results.total_records > 0) {
                setList(res.data.results.daily_data_list);
            } else {
                setList([]);
            }
        }).catch((err) => {
            setList([]);
            handleUnauthorized(err, navigate);
        });
    }

    function loadFlocksForFarm(farmId, preferredFlockId = "0", nextStep = 0) {
        if (String(farmId) === "0") {
            setShowFlock(false);
            setShowForm(false);
            setFlocks([]);
            setList([]);
            setSelectedFarmId("0");
            setSelectedFlockId("0");
            setSelectorStep(0);
            return;
        }

        setSelectedFarmId(String(farmId));
        axios.get(`${apiPath}flocks/${farmId}/`, getAuthConfig()).then((res) => {
            setShowFlock(true);
            if (res.data.results.total_records === 0) {
                setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                setSelectedFlockId("0");
                setFlock({});
                setShowForm(false);
                setList([]);
                setSelectorStep(0);
                return;
            }

            const flockList = res.data.results.flock_list;
            const selectedFlock = flockList.find((item) => String(item.flock_public_id) === String(preferredFlockId)) || flockList[flockList.length - 1];
            setFlocks(flockList);
            loadDailyDataForFlock(selectedFlock, nextStep);
        }).catch((err) => {
            setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
            setShowForm(false);
            setList([]);
            handleUnauthorized(err, navigate);
        });
    }

    useEffect(() => {
        let url = `${apiPath}farm/`;
        // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, getAuthConfig()).then((res) => {
            if (res.data.results.length === 0) {
                setFarms([{ public_id: 0, name: 'No farm available' }]);
            } else {
                const farmList = res.data.results;
                const selectedFarm = farmList.find((item) => String(item.public_id) === String(initialDraft.selectedFarmId)) || farmList[farmList.length - 1];
                setFarms(farmList);
                loadFlocksForFarm(selectedFarm.public_id, initialDraft.selectedFlockId);
            }
        }).catch((err) => {
            setFarms([{ public_id: 0, name: 'No farm available' }]);
            handleUnauthorized(err, navigate);
        });
    }, [navigate])

    useEffect(() => {
        localStorage.setItem(DAILY_SELECTOR_DRAFT_KEY, JSON.stringify({
            selectedFarmId,
            selectedFlockId,
            selectorStep,
        }));
    }, [selectedFarmId, selectedFlockId, selectorStep]);

    let save = (e) => {
        e.preventDefault();
    }
    let changeFarm = (e) => {
        loadFlocksForFarm(e.target.value, "0", 0);
    }
    let changeFlocks = (e) => {
        // U: OLD: selecting a flock did not share one loader with draft restore.
        const selectedFlock = flocks.find((o) => String(o.flock_public_id) === e.target.value);
        if (!selectedFlock) {
            setShowForm(false);
            setList([]);
            setSelectedFlockId("0");
            return;
        }
        loadDailyDataForFlock(selectedFlock, 0);
    }
    let [modalShow, setModalShow] = useState(false);
    let [week, setWeek] = useState(null);
    let [days, setDays] = useState([]);
    const hasFarmPrerequisite = farms.some((farm) => String(farm.public_id) !== "0");
    const hasFlockOptions = flocks.some((item) => String(item.flock_public_id) !== "0");
    let handleShow = (e) => {
        // U: OLD: a long loose-equality if/else block manually listed every week.
        const selectedWeek = Number(e.target.value);
        const firstDay = ((selectedWeek - 1) * 7) + 1;
        setDays(Array.from({ length: 7 }, (_, index) => firstDay + index));
        setWeek(selectedWeek);
        setModalShow(true)
    }
    let getrealdate = (dt, num) => {
        let dt1 = new Date(dt);
        dt1.setDate(dt1.getDate() + num);
        let text = `${new Date(dt1).getMonth() + 1}`;
        if (text.length === 1) {
            text = `0${text}`;
        }
        let textday = `${dt1.getDate()}`;
        if (textday.length === 1) {
            textday = `0${textday}`;
        }
        return `${new Date(dt1).getFullYear()}-${text}-${textday}`;
    }
    let getrealmonth = (dt, num) => {
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        let dt1 = new Date(dt);
        dt1.setDate(dt1.getDate() + num);
        return (`${dt1.getDate()} ${monthNames[dt1.getMonth()]}`);
    }
    const dailyRecords = Array.isArray(list) ? list : [];
    const latestDailyRecord = dailyRecords[dailyRecords.length - 1];
    const nextDailyDay = dailyRecords.length + 1;
    const nextDailyDate = showForm && flock.hatch_date ? getrealdate(flock.hatch_date, nextDailyDay) : "";
    const latestEntryDate = latestDailyRecord?.date || "";
    const summaryBirds = latestDailyRecord?.birds_count ?? latestDailyRecord?.current_bird_count ?? "NA";
    const summaryMortality = latestDailyRecord?.cum_mort ?? latestDailyRecord?.total_mort ?? latestDailyRecord?.mortality ?? 0;
    const summaryFeed = latestDailyRecord?.total_feed_consumed ?? latestDailyRecord?.total_feed ?? latestDailyRecord?.feed_intake ?? 0;
    const summaryFcr = latestDailyRecord?.total_fcr ?? latestDailyRecord?.fcr ?? "-";
    const summaryWeight = latestDailyRecord?.average_bird_weight ?? "NA";
    const completedWeeks = Math.floor(dailyRecords.length / 7);
    const activeWeek = Math.max(1, Math.min(12, Math.ceil(nextDailyDay / 7)));
    const weekNumbers = Array.from({ length: 12 }, (_, index) => index + 1);
    function MyVerticallyCenteredModal(props) {
        return (
            <Modal
                {...props}
                size="lg"
                aria-labelledby="contained-modal-title-vcenter"
                centered
            >
                <Modal.Header closeButton>
                    <Modal.Title id="contained-modal-title-vcenter">
                        Please click on date to enter daily data for Week {week}
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <div className="daily-day-grid">
                        {days.map((number) => {
                            return (
                                (number <= list.length) ?
                                    <Button color="light" className="daily-day-button is-complete" key={number}>
                                        <Link to={`/daydata/${flock.farm_public_id}/${flock.flock_public_id}/${getrealdate(flock.hatch_date, number)}`} className="linkdailydata">{getrealmonth(flock.hatch_date, number)}<br />Day {number}</Link>
                                    </Button> :
                                    (number === list.length + 1) ?
                                        <Button color="light" className="daily-day-button is-current" key={number}>
                                            <Link to={`/daydata/${flock.farm_public_id}/${flock.flock_public_id}/${getrealdate(flock.hatch_date, number)}`} className="linkdailydata">{getrealmonth(flock.hatch_date, number)}<br />Day {number}</Link>
                                        </Button> :
                                        <Button color="light" className="daily-day-button is-disabled" key={number}>
                                            <span className="linkdailydata" style={{ cursor: 'default' }}>{getrealmonth(flock.hatch_date, number)}<br />Day {number}</span>
                                        </Button>
                            )
                        })}
                    </div>
                    {/* {
                days.map((item) =>{
                    return(
                        {item}
                    )
                })
            } */}
                </Modal.Body>
                <Modal.Footer>
                    {/* <Button onClick={props.onHide}>Close</Button> */}
                </Modal.Footer>
            </Modal>
        );
    }

    return (
        <Row>
            <Col>
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-1*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card className="pb-4">
                    <CardTitle tag="h6" className="border-bottom p-3 mb-0">
                        Flock Days
                    </CardTitle>
                    <CardBody>
                        <Row className="mt-3">
                            <Col sm="12" md={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        {!hasFarmPrerequisite && (
                                            <div className="form-prerequisite-card">
                                                <span>Farm required</span>
                                                <p>Add a farm and flock before entering daily data. Daily data powers mortality, FCR, reports, and Farmer AI answers.</p>
                                                <Link to="/addfarm">Add farm first</Link>
                                            </div>
                                        )}
                                        <Form onSubmit={save}>
                                            {selectorStep === 0 && (
                                                <>
                                                    <FormGroup>
                                                        <Label for="farmSelect">Select Farm</Label>
                                                        <div className="input-group">
                                                            <Input onChange={changeFarm} value={selectedFarmId} id="farmSelect" name="farm" type="select">
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
                                                    {
                                                        showFlock &&
                                                        <FormGroup>
                                                            <Label for="flockSelect">Select Flock</Label>
                                                            <div className="input-group">
                                                                <Input onChange={changeFlocks} value={selectedFlockId} id="flockSelect" name="flock" type="select">
                                                                    <option value="0" disabled>Select Flock</option>
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
                                                    <div className="form-wizard-actions">
                                                        <Button type="button" color="danger" onClick={() => setSelectorStep(1)} disabled={!showForm || selectedFlockId === "0"}>Next</Button>
                                                        <Button type="button" color="secondary" outline onClick={() => navigate("/member")}>Cancel</Button>
                                                    </div>
                                                </>
                                            )}
                                            {showFlock && !hasFlockOptions && (
                                                <div className="form-prerequisite-card">
                                                    <span>Flock required</span>
                                                    <p>This farm does not have a flock yet. Create a flock before recording daily mortality, bird count, feed, weight, and FCR.</p>
                                                    <Link to="/addflock">Add flock</Link>
                                                </div>
                                            )}
                                            {
                                                showForm && selectorStep === 1 &&
                                                <>
                                                    <div className="record-review-toolbar record-review-toolbar--compact daily-data-summary-card">
                                                        <div>
                                                            <span>Daily data</span>
                                                            <p>
                                                                {dailyRecords.length} day{dailyRecords.length === 1 ? "" : "s"} completed{latestEntryDate ? ", latest entry " : ""}
                                                                {latestEntryDate && <b className="daily-latest-date">{latestEntryDate}</b>}. Choose a week or go to the next open day.
                                                            </p>
                                                        </div>
                                                        {nextDailyDate && (
                                                            <Button tag={Link} to={`/daydata/${flock.farm_public_id}/${flock.flock_public_id}/${nextDailyDate}`} color="danger" type="button">
                                                                Go to day {nextDailyDay} →
                                                            </Button>
                                                        )}
                                                    </div>
                                                    <div className="daily-data-metric-strip" aria-label="Daily data summary">
                                                        <strong><span>Birds</span><b>{summaryBirds}</b></strong>
                                                        <strong><span>Mortality</span><b>{summaryMortality}</b></strong>
                                                        <strong><span>Feed</span><b>{summaryFeed} kg</b></strong>
                                                        <strong><span>Avg. Bird Wt.</span><b>{summaryWeight} gm</b></strong>
                                                        <strong><span>FCR{latestEntryDate ? ` (${latestEntryDate})` : ""}</span><b>{summaryFcr}</b></strong>
                                                    </div>
                                                    <div className="daily-week-grid" aria-label="Daily data weeks">
                                                        <MyVerticallyCenteredModal show={modalShow} onHide={() => setModalShow(false)} />
                                                        {weekNumbers.map((weekNumber) => (
                                                            <Button
                                                                key={weekNumber}
                                                                className={`flockdate ${weekNumber <= completedWeeks ? "is-complete" : ""} ${weekNumber === activeWeek ? "is-current" : ""}`}
                                                                value={weekNumber}
                                                                onClick={handleShow}
                                                            >
                                                                Week {weekNumber}
                                                            </Button>
                                                        ))}
                                                    </div>
                                                    <div className="form-wizard-actions">
                                                        <Button type="button" color="secondary" outline onClick={() => setSelectorStep(0)}>Back</Button>
                                                        <Button type="button" color="secondary" outline onClick={() => navigate("/member")}>Cancel</Button>
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

export default ManageFlock;
