// import { Row, Col, Table, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input, FormText, Nav, NavItem } from "reactstrap";
import '../../assets/css/header.css';
import { Link } from "react-router-dom";
import { Tab, Tabs } from 'react-bootstrap';
import { Row, Col, Card, CardTitle, CardBody, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, config } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
import Chart from 'react-apexcharts';
import { useNavigate } from "react-router-dom";

const Member = () => {
  const [showFlock, setShowFlock] = useState(false);
  const [showForm, setShowForm] = useState(false);
  let [flocks, setFlocks] = useState([]);
  let [flock, setFlock] = useState([]);
  let [farms, setFarms] = useState([]);
  let [date, setDate] = useState([])
  let [currentCount, setCurrentCount] = useState([])
  let [mortality, setMortality] = useState([])
  let [week, setWeek] = useState([])
  let [weight, setWeight] = useState([])
  let [fcr, setFcr] = useState([])
  const navigate = useNavigate();

  useEffect(() => {
    getsetFlockData2()
    let url = `${apiPath}farm/`;
    config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
    axios.get(url, config).then((res) => {
      if (res.data.results.length === 0) {
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
  let changeFarm = (e) => {
    if (e.target.value === 0) {
      setShowFlock(false)
      setFlocks([]);
    } else {
      let url = `${apiPath}flocks/${e.target.value}/`;
      config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
      axios.get(url, config).then((res) => {
        if (res.data.results.total_records === 0) {
          setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
        } else {
          setFlocks(res.data.results.flock_list);
        }
        setShowFlock(true)
      }).catch((err) => {
        if (err.response.status === 401) {
          localStorage.clear();
          navigate("/login")
        }
      });
    }
  }
  let changeFlock = (e) => {
    if (e.target.value === 0) {
      setShowForm(false)
    } else {
      const user = flocks.find(u => u.flock_public_id === e.target.value);
      setShowForm(true)
      setFlock(user.flock_public_id)
    }
  }

  const getsetFlockData = () => {

    let url = `${apiPath}graph/${flock}/`

    const config = {
      headers: {
        "Authorization": `Bearer ${localStorage.getItem('token')}`
      }
    };

    axios.get(url, config)
      .then((res) => {
        setDate(res.data.results.date)
        setCurrentCount(res.data.results.current_bird_count)
        setMortality(res.data.results.mortality)
        setWeek(res.data.results.week)
        setWeight(res.data.results.average_weight)
        setFcr(res.data.results.fcr)
      }
      ).catch(err => {
        console.log(err)
        if (err.response.status === 401) {
          localStorage.clear();
          navigate("/login")
        }
      })
  }

  const getsetFlockData2 = () => {

    let url = `${apiPath}graph/1/`

    const config = {
      headers: {
        "Authorization": `Bearer ${localStorage.getItem('token')}`
      }
    };

    axios.get(url, config)
      .then((res) => {
        setDate(res.data.results.date)
        setCurrentCount(res.data.results.current_bird_count)
        setMortality(res.data.results.mortality)
        setWeek(res.data.results.week)
        setWeight(res.data.results.average_weight)
        setFcr(res.data.results.fcr)
      }
      ).catch(err => {
        console.log(err)
        if (err.response.status === 401) {
          localStorage.clear();
          navigate("/login")
        }
      })
  };

  return (
    <Row>
      <Col>
        {/* --------------------------------------------------------------------------------*/}
        {/* Card-1*/}
        {/* --------------------------------------------------------------------------------*/}
        <Card className="pb-4">
          <CardTitle tag="h6" className="border-bottom p-3 mb-0">
            <i className="bi bi-bell me-2"> </i>
            Farmer Dashboard
          </CardTitle>
          <CardBody>
            <Row className="mt-3">
              <Col sm="12" md={{ offset: 2, size: 8 }}>
                <div className={contentArea}>
                  <div className='gridmargin'>
                    <FormGroup>
                      <Label for="farmselect">Select Farm{JSON.stringify(showFlock)}</Label>
                      <div className="input-group">
                        <Input onChange={changeFarm} id="farmSelect" name="farm" type="select">
                          <option defaultValue={0}>Select Farm</option>
                          {
                            farms.map((item) => {
                              return (
                                <option key={item.public_id} value={item.public_id}>{item.name}</option>
                              )
                            })
                          }
                        </Input>
                      </div>
                      <small className="text-danger">{ }</small>
                    </FormGroup>

                    {
                      showFlock &&
                      <FormGroup>
                        <Label for="farmselect">Select Flock</Label>
                        <div className="input-group">
                          <Input onChange={changeFlock} defaultValue={'sdfs'} onClick={getsetFlockData} id="flockSelect" name="flock" type="select">
                            <option defaultValue={0}>Select Flocks</option>
                            {
                              flocks.map((item) => {
                                return (
                                  <option key={item.flock_public_id} value={item.flock_public_id}>{item.flock_name}</option>
                                )
                              })
                            }
                          </Input>
                        </div>
                        <small className="text-danger">{ }</small>
                      </FormGroup>
                    }
                    {
                      showForm &&
                      <>
                        <FormGroup className="mt-4 mb-4 block-example border border-light">
                          <Tabs defaultActiveKey="home" id="uncontrolled-tab-example" className="mb-3">
                            <Tab eventKey="home" title="Mortality">
                              <Chart
                                type='line'
                                className="chart-width"
                                height={550}

                                series={


                                  [
                                    {
                                      name: 'Current Bird Count',
                                      data: currentCount
                                    },
                                    {
                                      name: 'Mortality',
                                      data: mortality
                                    }

                                  ]
                                }
                                options={
                                  {

                                    title: {

                                      style: { fontSize: 20 }
                                    },
                                    colors: ["#FF1654", "#247BA0"],
                                    stroke: { width: 3, curve: 'straight' },
                                    fill: { opacity: 5 },

                                    xaxis: {
                                      title: {
                                        text: 'Data & Time ',
                                        style: { fontSize: 20 }
                                      },
                                      categories: date

                                    },

                                    yaxis: [
                                      {
                                        title: {
                                          text: "Current Bird Count"
                                        },
                                      },
                                      {
                                        opposite: true,
                                        title: {
                                          text: "Mortality"
                                        }
                                      }
                                    ],


                                  }
                                }>

                              </Chart>
                            </Tab>
                            <Tab eventKey="profile" title="Weight/FCR">
                              <Chart
                                type='line'
                                className="chart-width"
                                height={550}

                                series={

                                  [
                                    {
                                      name: 'Average Weight (In Grams)',
                                      data: weight
                                    },
                                    {
                                      name: 'FCR',
                                      data: fcr
                                    }

                                  ]
                                }
                                options={
                                  {
                                    title: {

                                      style: { fontSize: 20 }
                                    },
                                    colors: ["#FF1654", "#247BA0"],
                                    stroke: { width: 3, curve: 'straight' },
                                    fill: { opacity: 5 },

                                    xaxis: {
                                      title: {
                                        text: 'Week ',
                                        style: { fontSize: 20 }
                                      },
                                      categories: week

                                    },

                                    yaxis: [
                                      {
                                        title: {
                                          text: "Average Weight (In Grams)"
                                        },
                                      },
                                      {
                                        opposite: true,
                                        title: {
                                          text: "FCR"
                                        }
                                      }
                                    ],


                                  }
                                }>

                              </Chart>
                            </Tab>
                          </Tabs>
                        </FormGroup>
                      </>
                    }
                    {
                      !showForm &&
                      <>
                        <FormGroup className="mt-4 mb-4 block-example border border-light">
                          <Tabs defaultActiveKey="home" id="uncontrolled-tab-example" className="mb-3">
                            <Tab eventKey="home" title="Mortality">
                              <Chart
                                type='line'
                                className="chart-width"
                                height={550}

                                series={


                                  [
                                    {
                                      name: 'Current Bird Count',
                                      data: currentCount
                                    },
                                    {
                                      name: 'Mortality',
                                      data: mortality
                                    }

                                  ]
                                }
                                options={
                                  {

                                    title: {

                                      style: { fontSize: 20 }
                                    },
                                    colors: ["#FF1654", "#247BA0"],
                                    stroke: { width: 3, curve: 'straight' },
                                    fill: { opacity: 5 },

                                    xaxis: {
                                      title: {
                                        text: 'Data & Time ',
                                        style: { fontSize: 20 }
                                      },
                                      categories: date

                                    },

                                    yaxis: [
                                      {
                                        title: {
                                          text: "Current Bird Count"
                                        },
                                      },
                                      {
                                        opposite: true,
                                        title: {
                                          text: "Mortality"
                                        }
                                      }
                                    ],


                                  }
                                }>

                              </Chart>
                            </Tab>
                            <Tab eventKey="profile" title="Weight/FCR">
                              <Chart
                                type='line'
                                className="chart-width"
                                height={550}

                                series={

                                  [
                                    {
                                      name: 'Average Weight (In Grams)',
                                      data: weight
                                    },
                                    {
                                      name: 'FCR',
                                      data: fcr
                                    }

                                  ]
                                }
                                options={
                                  {
                                    title: {

                                      style: { fontSize: 20 }
                                    },
                                    colors: ["#FF1654", "#247BA0"],
                                    stroke: { width: 3, curve: 'straight' },
                                    fill: { opacity: 5 },

                                    xaxis: {
                                      title: {
                                        text: 'Week ',
                                        style: { fontSize: 20 }
                                      },
                                      categories: week

                                    },

                                    yaxis: [
                                      {
                                        title: {
                                          text: "Average Weight (In Grams)"
                                        },
                                      },
                                      {
                                        opposite: true,
                                        title: {
                                          text: "FCR"
                                        }
                                      }
                                    ],


                                  }
                                }>

                              </Chart>
                            </Tab>
                          </Tabs>
                        </FormGroup>
                      </>
                    }
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

export default Member;