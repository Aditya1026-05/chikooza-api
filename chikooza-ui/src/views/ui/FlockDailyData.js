import { Row, Col, Badge, Table, Card, CardTitle, CardBody, CardText, Button, Form, FormGroup, Label, Input, FormText, Nav, NavItem } from "reactstrap";
import '../../assets/css/header.css';
import { useState, useEffect } from "react";
import { contentArea, apiPath, config } from "../../Constants";
import Modal from 'react-bootstrap/Modal'
import { Link } from "react-router-dom";
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const ManageFlock = () => {

    let [farms, setFarms] = useState([]);
    let [flocks, setFlocks] = useState([]);
    let [list, setList] = useState([]);
    let [flock, setFlock] = useState({});
    let [showFlock, setShowFlock] = useState(false);
    let [showForm, setShowForm] = useState(false);
    const navigate = useNavigate();


    useEffect(() => {
        let url = `${apiPath}farm/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            if (res.data.results.length == 0) {
                setFarms([{ public_id: 0, name: 'No farm available' }]);
            } else {
                setFarms(res.data.results);
            }
        }).catch((err) => {
            setFarms([{ public_id: 0, name: 'No farm available' }]);
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }, [])
    let save = (e) => {
        e.preventDefault();
    }
    let changeFarm = (e) => {
        let url = `${apiPath}flocks/${e.target.value}/`;
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, config).then((res) => {
            setShowFlock(true);
            if (res.data.results.total_records == 0) {
                setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
            } else {
                setFlocks(res.data.results.flock_list);
            }
            setShowForm(false);
        }).catch((err) => {
            setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
            if (err.response.status === 401) {
                localStorage.clear();
                navigate("/login")
            }
        });
    }
    let changeFlocks = (e) => {
        if (e.target.value == 0) {
            setShowForm(false);
        } else {
            let newArray = flocks.slice();
            newArray.find((o, i) => {
                if (o.flock_public_id === e.target.value) {
                    let url = `${apiPath}dailyDataDetail/?flock_public_id=${o.flock_public_id}`;
                    config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
                    axios.get(url, config).then((res) => {
                        if (res.data.results.total_records > 0) {
                            setList(res.data.results.daily_data_list);
                        } else {
                            setList([]);
                        }
                    }).catch((err) => {
                        setList([]);
                        if (err.response.status === 401) {
                            localStorage.clear();
                            navigate("/login")
                        }
                    });
                    setShowForm(true);
                    setFlock(o);
                }
            });
        }
    }
    let [modalShow, setModalShow] = useState(false);
    let [week, setWeek] = useState(null);
    let [days, setDays] = useState([]);
    let handleShow = (e) => {
        let day = new Array();
        if (e.target.value == 1) {
            day = [1, 2, 3, 4, 5, 6, 7];
            setDays(day);
        } else if (e.target.value == 2) {
            day = [8, 9, 10, 11, 12, 13, 14];
            setDays(day);
        } else if (e.target.value == 3) {
            day = [15, 16, 17, 18, 19, 20, 21];
            setDays(day);
        } else if (e.target.value == 4) {
            day = [22, 23, 24, 25, 26, 27, 28];
            setDays(day);
        } else if (e.target.value == 5) {
            day = [29, 30, 31, 32, 33, 34, 35];
            setDays(day);
        } else if (e.target.value == 6) {
            day = [36, 37, 38, 39, 40, 41, 42];
            setDays(day);
        } else if (e.target.value == 7) {
            day = [43, 44, 45, 46, 47, 48, 49];
            setDays(day);
        } else if (e.target.value == 8) {
            day = [50, 51, 52, 53, 54, 55, 56];
            setDays(day);
        } else if (e.target.value == 9) {
            day = [57, 58, 59, 60, 61, 62, 63];
            setDays(day);
        } else if (e.target.value == 10) {
            day = [64, 65, 66, 67, 68, 69, 70];
            setDays(day);
        } else if (e.target.value == 11) {
            day = [71, 72, 73, 74, 75, 76, 77];
            setDays(day);
        } else {
            day = [78, 79, 80, 81, 82, 83, 84];
            setDays(day);
        }
        setWeek(e.target.value);
        setModalShow(true)
    }
    let getrealdate = (dt, num) => {
        let dt1 = new Date(dt);
        dt1.setDate(dt1.getDate() + num);
        let text = `${new Date(dt1).getMonth() + 1}`;
        if (text.length == 1) {
            text = `0${text}`;
        }
        let textday = `${dt1.getDate()}`;
        if (textday.length == 1) {
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
                                (number == list.length + 1) ?
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
                                        <Form onSubmit={save}>
                                            <FormGroup>
                                                <Label for="farmselect">Select Farm</Label>
                                                <div className="input-group">
                                                    <Input onChange={changeFarm} defaultValue={0} id="farmSelect" name="farm" type="select">
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
                                                        <Input onChange={changeFlocks} id="farmSelect" name="flock" type="select">
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
                                                </FormGroup>
                                            }
                                            {
                                                showForm &&
                                                <>
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
