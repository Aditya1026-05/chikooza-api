import { Row, Col, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { useState, useEffect } from "react";
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import Modal from 'react-bootstrap/Modal'
import { Link } from "react-router-dom";
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const DAILY_SELECTOR_DRAFT_KEY = "chikooza-daily-selector-draft";

const dailySelectorSteps = [
    { title: "Select", helper: "Farm and flock" },
    { title: "Day", helper: "Choose week and date" },
];

const readDailySelectorDraft = () => {
    try {
        const draft = JSON.parse(localStorage.getItem(DAILY_SELECTOR_DRAFT_KEY) || "{}");
        return {
            selectedFarmId: draft.selectedFarmId || "0",
            selectedFlockId: draft.selectedFlockId || "0",
            selectorStep: Number(draft.selectorStep || 0),
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


    useEffect(() => {
        let url = `${apiPath}farm/`;
        // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
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

    useEffect(() => {
        localStorage.setItem(DAILY_SELECTOR_DRAFT_KEY, JSON.stringify({
            selectedFarmId,
            selectedFlockId,
            selectorStep,
        }));
    }, [selectedFarmId, selectedFlockId, selectorStep]);

    useEffect(() => {
        if (initialDraft.selectedFarmId === "0") {
            return;
        }
        axios.get(`${apiPath}flocks/${initialDraft.selectedFarmId}/`, getAuthConfig()).then((res) => {
            setShowFlock(true);
            if (res.data.results.total_records === 0) {
                setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
            } else {
                const flockList = res.data.results.flock_list;
                setFlocks(flockList);
                const selectedFlock = flockList.find((item) => String(item.flock_public_id) === initialDraft.selectedFlockId);
                if (selectedFlock) {
                    setFlock(selectedFlock);
                    setShowForm(true);
                }
            }
        }).catch((err) => {
            handleUnauthorized(err, navigate);
        });
    }, [initialDraft.selectedFarmId, initialDraft.selectedFlockId, navigate])
    let save = (e) => {
        e.preventDefault();
    }
    let changeFarm = (e) => {
        if (e.target.value === "0") {
            setShowFlock(false);
            setShowForm(false);
            setFlocks([]);
            setList([]);
            setSelectedFarmId("0");
            setSelectedFlockId("0");
            setSelectorStep(0);
            return;
        }
        setSelectedFarmId(e.target.value);
        setSelectedFlockId("0");
        let url = `${apiPath}flocks/${e.target.value}/`;
        // U: OLD: config.headers['Authorization'] was mutated before each request.
        axios.get(url, getAuthConfig()).then((res) => {
            setShowFlock(true);
            if (res.data.results.total_records === 0) {
                setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
            } else {
                setFlocks(res.data.results.flock_list);
            }
            setShowForm(false);
            setSelectorStep(0);
        }).catch((err) => {
            setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
            handleUnauthorized(err, navigate);
        });
    }
    let changeFlocks = (e) => {
        // U: OLD: e.target.value == 0 and numeric public_id comparisons were mixing strings and numbers.
        if (e.target.value === "0") {
            setShowForm(false);
            setList([]);
            setSelectedFlockId("0");
        } else {
            setSelectedFlockId(e.target.value);
            const selectedFlock = flocks.find((o) => String(o.flock_public_id) === e.target.value);
            if (!selectedFlock) {
                setShowForm(false);
                setList([]);
                return;
            }
            let url = `${apiPath}dailyDataDetail/?flock_public_id=${selectedFlock.flock_public_id}`;
            axios.get(url, getAuthConfig()).then((res) => {
                if (res.data.results.total_records > 0) {
                    setList(res.data.results.daily_data_list);
                } else {
                    setList([]);
                }
            }).catch((err) => {
                setList([]);
                handleUnauthorized(err, navigate);
            });
            setShowForm(true);
            setFlock(selectedFlock);
            setSelectorStep(1);
        }
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
    const recentDailyRecords = dailyRecords.slice(-6).reverse();
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
                    {days.map((number) => {
                        return (
                            (number <= list.length) ?
                                <Button color="success" className="ml-3 mt-3 mb-3" key={number}>
                                    <Link to={`/daydata/${flock.farm_public_id}/${flock.flock_public_id}/${getrealdate(flock.hatch_date, number)}`} className="linkdailydata">{getrealmonth(flock.hatch_date, number)}<br />Day {number}</Link>
                                </Button> :
                                (number === list.length + 1) ?
                                    <Button color="warning" className="ml-3 mt-3 mb-3" key={number}>
                                        <Link to={`/daydata/${flock.farm_public_id}/${flock.flock_public_id}/${getrealdate(flock.hatch_date, number)}`} className="linkdailydata">{getrealmonth(flock.hatch_date, number)}<br />Day {number}</Link>
                                    </Button> :
                                    <Button color="light" className="ml-3 mt-3 mb-3" key={number}>
                                        <span className="linkdailydata" style={{ cursor: 'default' }}>{getrealmonth(flock.hatch_date, number)}<br />Day {number}</span>
                                    </Button>
                        )
                    })}
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
                                            <div className="form-stepper" aria-label="Daily data selector steps">
                                                {dailySelectorSteps.map((step, index) => (
                                                    <button
                                                        key={step.title}
                                                        type="button"
                                                        className={index === selectorStep ? "is-active" : index < selectorStep ? "is-complete" : ""}
                                                        onClick={() => {
                                                            if (index === 0 || showForm) {
                                                                setSelectorStep(index);
                                                            }
                                                        }}
                                                    >
                                                        <span>{index + 1}</span>
                                                        <strong>{step.title}</strong>
                                                        <small>{step.helper}</small>
                                                    </button>
                                                ))}
                                            </div>
                                            {selectorStep === 0 && (
                                                <>
                                                    <FormGroup>
                                                        <Label for="farmselect">Select Farm</Label>
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
                                                            <Label for="farmselect">Select Flock</Label>
                                                            <div className="input-group">
                                                                <Input onChange={changeFlocks} value={selectedFlockId} id="flockSelect" name="flock" type="select">
                                                                    <option value="0" disabled>Select Flocks</option>
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
                                                    <div className="record-review-toolbar record-review-toolbar--compact">
                                                        <div>
                                                            <span>Daily data</span>
                                                            <strong>{flock.flock_name || "Selected flock"}</strong>
                                                            <p>{dailyRecords.length} day{dailyRecords.length === 1 ? "" : "s"} completed. Select a week below or record the next open day.</p>
                                                        </div>
                                                        {nextDailyDate && (
                                                            <Button tag={Link} to={`/daydata/${flock.farm_public_id}/${flock.flock_public_id}/${nextDailyDate}`} color="danger" type="button">
                                                                Record day {nextDailyDay}
                                                            </Button>
                                                        )}
                                                    </div>
                                                    {latestDailyRecord && (
                                                        <div className="record-summary-strip">
                                                            <strong>Latest entry:</strong> {latestDailyRecord.date}
                                                            <div className="record-summary-chips">
                                                                <span>Birds {latestDailyRecord.current_bird_count ?? "NA"}</span>
                                                                <span>Mortality {latestDailyRecord.mortality ?? 0}</span>
                                                                <span>Feed {latestDailyRecord.feed_consumed ?? latestDailyRecord.feed_intake ?? 0} kg</span>
                                                            </div>
                                                        </div>
                                                    )}
                                                    <div>
                                                        <MyVerticallyCenteredModal show={modalShow} onHide={() => setModalShow(false)} />
                                                        <Button className="flockdate" value="1" onClick={handleShow}>
                                                            Week 1
                                                        </Button>
                                                        <Button className="flockdate" value="2" onClick={handleShow}>
                                                            Week 2
                                                        </Button>
                                                        <Button className="flockdate" value="3" onClick={handleShow}>
                                                            Week 3
                                                        </Button>
                                                        <Button className="flockdate" value="4" onClick={handleShow}>
                                                            Week 4
                                                        </Button>
                                                        <Button className="flockdate" value="5" onClick={handleShow}>
                                                            Week 5
                                                        </Button>
                                                        <Button className="flockdate" value="6" onClick={handleShow}>
                                                            Week 6
                                                        </Button>
                                                        <Button className="flockdate" value="7" onClick={handleShow}>
                                                            Week 7
                                                        </Button>
                                                        <Button className="flockdate" value="8" onClick={handleShow}>
                                                            Week 8
                                                        </Button>
                                                        <Button className="flockdate" value="9" onClick={handleShow}>
                                                            Week 9
                                                        </Button>
                                                        <Button className="flockdate" value="10" onClick={handleShow}>
                                                            Week 10
                                                        </Button>
                                                        <Button className="flockdate" value="11" onClick={handleShow}>
                                                            Week 11
                                                        </Button>
                                                        <Button className="flockdate" value="12" onClick={handleShow}>
                                                            Week 12
                                                        </Button>
                                                    </div>
                                                    <div className="form-wizard-actions">
                                                        <Button type="button" color="secondary" outline onClick={() => setSelectorStep(0)}>Back</Button>
                                                        <Button type="button" color="secondary" outline onClick={() => {
                                                            setSelectedFarmId("0");
                                                            setSelectedFlockId("0");
                                                            setSelectorStep(0);
                                                            setShowForm(false);
                                                            localStorage.removeItem(DAILY_SELECTOR_DRAFT_KEY);
                                                        }}>Cancel</Button>
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
