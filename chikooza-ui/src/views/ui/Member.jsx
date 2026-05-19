// import { Row, Col, Table, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input, FormText, Nav, NavItem } from "reactstrap";
import '../../assets/css/header.css';
import { Tab, Tabs } from 'react-bootstrap';
import { Row, Col, Card, CardTitle, CardBody, FormGroup, Label, Input } from "reactstrap";
// U: OLD duplicate header.css import removed.
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect, useCallback } from "react";
import axios from 'axios';
// U: OLD: import Chart from 'react-apexcharts';
// U: NEW: use the lazy chart wrapper so ApexCharts is split out of this route chunk.
import Chart from '../../components/ApexChart';
import { useNavigate } from "react-router-dom";

const Member = () => {
  let [graphError, setGraphError] = useState('');
  const [showFlock, setShowFlock] = useState(false);
  const [showForm, setShowForm] = useState(false);
  let [flocks, setFlocks] = useState([]);
  // U: OLD: let [flock, setFlock] = useState([]) was only written to, never read.
  const [selectedFarm, setSelectedFarm] = useState("0");
  const [selectedFlock, setSelectedFlock] = useState("0");
  let [farms, setFarms] = useState([]);
  let [date, setDate] = useState([])
  let [currentCount, setCurrentCount] = useState([])
  let [mortality, setMortality] = useState([])
  let [week, setWeek] = useState([])
  let [weight, setWeight] = useState([])
  let [fcr, setFcr] = useState([])
  const navigate = useNavigate();

  const getsetFlockData2 = useCallback((flock_id) => {
    let url = `${apiPath}graph/${flock_id}/`

    // U: OLD: this screen created/mutated request config objects inline for auth headers.
    // U: NEW: use a fresh authenticated config object per request.
    axios.get(url, getAuthConfig())
      .then((res) => {
        setGraphError('');
        setDate(res.data.results.date)
        setCurrentCount(res.data.results.current_bird_count)
        setMortality(res.data.results.mortality)
        setWeek(res.data.results.week)
        setWeight(res.data.results.average_weight)
        setFcr(res.data.results.fcr)
      }
      ).catch(err => {
        setGraphError(err?.response?.data?.message || 'Unable to load flock graph data');
        setDate([])
        setCurrentCount([])
        setMortality([])
        setWeek([])
        setWeight([])
        setFcr([])
        handleUnauthorized(err, navigate);
      })
  }, [navigate]);

  useEffect(() => {
    //getsetFlockData2()
    let url = `${apiPath}farm/`;
    // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
    axios.get(url, getAuthConfig()).then((res) => {
      if (res.data.results.length === 0) {
        setFarms([{ public_id: 0, name: 'No farm available' }]);
        setSelectedFarm("0");
      } else {
        setFarms(res.data.results);
        //setlatId(res.data.results[res.data.results.length - 1].public_id);
        const latestFarm = res.data.results[res.data.results.length - 1];
        setSelectedFarm(String(latestFarm.public_id));
        url = `${apiPath}flocks/${latestFarm.public_id}/`;
        axios.get(url, getAuthConfig()).then((res) => {
          if (res.data.results.total_records === 0) {
            setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
            setSelectedFlock("0");
            setShowForm(false);
          } else {
            const flockList = res.data.results.flock_list;
            const latestFlock = flockList[flockList.length - 1];
            getsetFlockData2(latestFlock.flock_public_id)
            setSelectedFlock(String(latestFlock.flock_public_id));
            setFlocks(flockList);
            setShowForm(true);
          }
          setShowFlock(true)
        }).catch((err) => {
          handleUnauthorized(err, navigate);
        });
      }
    }).catch((err) => {
      setFarms([{ public_id: 0, name: 'No farm available' }]);
      setSelectedFarm("0");
      handleUnauthorized(err, navigate);
    });
  }, [getsetFlockData2, navigate])
  let changeFarm = (e) => {
    // U: OLD: e.target.value === 0 compared a string to a number.
    if (e.target.value === "0") {
      setShowFlock(false)
      setShowForm(false)
      setFlocks([]);
      setSelectedFarm("0");
      setSelectedFlock("0");
    } else {
      setSelectedFarm(e.target.value);
      let url = `${apiPath}flocks/${e.target.value}/`;
      axios.get(url, getAuthConfig()).then((res) => {
        if (res.data.results.total_records === 0) {
          setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
          setSelectedFlock("0");
          setShowForm(false);
        } else {
          const flockList = res.data.results.flock_list;
          const latestFlock = flockList[flockList.length - 1];
          getsetFlockData2(latestFlock.flock_public_id)
          setSelectedFlock(String(latestFlock.flock_public_id));
          setFlocks(flockList);
          setShowForm(true);
        }
        setShowFlock(true)
      }).catch((err) => {
        handleUnauthorized(err, navigate);
      });
    }
  }
  let changeFlock = (e) => {
    if (e.target.value === "0") {
      setShowForm(false)
      setSelectedFlock("0");
    } else {
      getsetFlockData2(e.target.value)
      const user = flocks.find(u => String(u.flock_public_id) === e.target.value);
      if (!user) {
        setShowForm(false);
        setSelectedFlock("0");
        return;
      }
      setShowForm(true)
      setSelectedFlock(String(user.flock_public_id))
    }
  }

  // const getsetFlockData = () => {

  //   let url = `${apiPath}graph/${flock}/`

  //   const config = {
  //     headers: {
  //       "Authorization": `Bearer ${localStorage.getItem('token')}`
  //     }
  //   };

  //   axios.get(url, config)
  //     .then((res) => {
  //       setDate(res.data.results.date)
  //       setCurrentCount(res.data.results.current_bird_count)
  //       setMortality(res.data.results.mortality)
  //       setWeek(res.data.results.week)
  //       setWeight(res.data.results.average_weight)
  //       setFcr(res.data.results.fcr)
  //     }
  //     ).catch(err => {
  //       console.log(err)
  //       if (err.response.status === 401) {
  //         localStorage.clear();
  //         navigate("/login")
  //       }
  //     })
  // }

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
                      <Label for="farmselect">Select Farm</Label>
                      <div className="input-group">
                        <Input value={selectedFarm} onChange={changeFarm} id="farmSelect" name="farm" type="select">
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
                      <small className="text-danger">{ }</small>
                    </FormGroup>

                    {
                      showFlock &&
                      <FormGroup>
                        <Label for="farmselect">Select Flock</Label>
                        <div className="input-group">
                          <Input value={selectedFlock} onChange={changeFlock} id="flockSelect" name="flock" type="select">
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
                        <small className="text-danger">{ }</small>
                      </FormGroup>
                    }
                    <small className="text-danger">{graphError}</small>
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
