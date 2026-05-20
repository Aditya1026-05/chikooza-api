import "../../assets/css/header.css";
import { Tab, Tabs } from "react-bootstrap";
import { FormGroup, Label, Input } from "reactstrap";
import { apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
// U: OLD: import Chart from 'react-apexcharts';
// U: NEW: use the lazy chart wrapper so ApexCharts is split out of this route chunk.
import Chart from "../../components/ApexChart";
import { useNavigate } from "react-router-dom";

const chartPalette = ["#b42318", "#2563eb"];

const baseChartOptions = {
  chart: {
    toolbar: { show: false },
    zoom: { enabled: false },
  },
  colors: chartPalette,
  dataLabels: { enabled: false },
  grid: {
    borderColor: "#f0ddd8",
    strokeDashArray: 4,
  },
  legend: {
    labels: { colors: "#67504c" },
  },
  stroke: {
    curve: "smooth",
    width: 3,
  },
  tooltip: {
    theme: "light",
  },
};

const Member = () => {
  const [graphError, setGraphError] = useState("");
  const [showFlock, setShowFlock] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [flocks, setFlocks] = useState([]);
  // U: OLD: let [flock, setFlock] = useState([]) was only written to, never read.
  const [selectedFarm, setSelectedFarm] = useState("0");
  const [selectedFlock, setSelectedFlock] = useState("0");
  const [farms, setFarms] = useState([]);
  const [date, setDate] = useState([]);
  const [currentCount, setCurrentCount] = useState([]);
  const [mortality, setMortality] = useState([]);
  const [week, setWeek] = useState([]);
  const [weight, setWeight] = useState([]);
  const [fcr, setFcr] = useState([]);
  const navigate = useNavigate();

  const getsetFlockData2 = useCallback((flockId) => {
    const url = `${apiPath}graph/${flockId}/`;

    // U: OLD: this screen created/mutated request config objects inline for auth headers.
    // U: NEW: use a fresh authenticated config object per request.
    axios.get(url, getAuthConfig())
      .then((res) => {
        setGraphError("");
        setDate(res.data.results.date);
        setCurrentCount(res.data.results.current_bird_count);
        setMortality(res.data.results.mortality);
        setWeek(res.data.results.week);
        setWeight(res.data.results.average_weight);
        setFcr(res.data.results.fcr);
      })
      .catch((err) => {
        setGraphError(err?.response?.data?.message || "Unable to load flock graph data");
        setDate([]);
        setCurrentCount([]);
        setMortality([]);
        setWeek([]);
        setWeight([]);
        setFcr([]);
        handleUnauthorized(err, navigate);
      });
  }, [navigate]);

  useEffect(() => {
    let url = `${apiPath}farm/`;
    // U: OLD: config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
    axios.get(url, getAuthConfig()).then((res) => {
      if (res.data.results.length === 0) {
        setFarms([{ public_id: 0, name: "No farm available" }]);
        setSelectedFarm("0");
      } else {
        setFarms(res.data.results);
        const latestFarm = res.data.results[res.data.results.length - 1];
        setSelectedFarm(String(latestFarm.public_id));
        url = `${apiPath}flocks/${latestFarm.public_id}/`;
        axios.get(url, getAuthConfig()).then((flockRes) => {
          if (flockRes.data.results.total_records === 0) {
            setFlocks([{ flock_public_id: 0, flock_name: "No flock available" }]);
            setSelectedFlock("0");
            setShowForm(false);
          } else {
            const flockList = flockRes.data.results.flock_list;
            const latestFlock = flockList[flockList.length - 1];
            getsetFlockData2(latestFlock.flock_public_id);
            setSelectedFlock(String(latestFlock.flock_public_id));
            setFlocks(flockList);
            setShowForm(true);
          }
          setShowFlock(true);
        }).catch((err) => {
          handleUnauthorized(err, navigate);
        });
      }
    }).catch((err) => {
      setFarms([{ public_id: 0, name: "No farm available" }]);
      setSelectedFarm("0");
      handleUnauthorized(err, navigate);
    });
  }, [getsetFlockData2, navigate]);

  const changeFarm = (event) => {
    // U: OLD: e.target.value === 0 compared a string to a number.
    if (event.target.value === "0") {
      setShowFlock(false);
      setShowForm(false);
      setFlocks([]);
      setSelectedFarm("0");
      setSelectedFlock("0");
      return;
    }

    setSelectedFarm(event.target.value);
    const url = `${apiPath}flocks/${event.target.value}/`;
    axios.get(url, getAuthConfig()).then((res) => {
      if (res.data.results.total_records === 0) {
        setFlocks([{ flock_public_id: 0, flock_name: "No flock available" }]);
        setSelectedFlock("0");
        setShowForm(false);
      } else {
        const flockList = res.data.results.flock_list;
        const latestFlock = flockList[flockList.length - 1];
        getsetFlockData2(latestFlock.flock_public_id);
        setSelectedFlock(String(latestFlock.flock_public_id));
        setFlocks(flockList);
        setShowForm(true);
      }
      setShowFlock(true);
    }).catch((err) => {
      handleUnauthorized(err, navigate);
    });
  };

  const changeFlock = (event) => {
    if (event.target.value === "0") {
      setShowForm(false);
      setSelectedFlock("0");
      return;
    }

    getsetFlockData2(event.target.value);
    const flock = flocks.find((item) => String(item.flock_public_id) === event.target.value);
    if (!flock) {
      setShowForm(false);
      setSelectedFlock("0");
      return;
    }
    setShowForm(true);
    setSelectedFlock(String(flock.flock_public_id));
  };

  const selectedFarmLabel = useMemo(() => {
    return farms.find((farm) => String(farm.public_id) === selectedFarm)?.name || "No farm selected";
  }, [farms, selectedFarm]);

  const selectedFlockLabel = useMemo(() => {
    return flocks.find((flock) => String(flock.flock_public_id) === selectedFlock)?.flock_name || "No flock selected";
  }, [flocks, selectedFlock]);

  const hasMortalityData = currentCount.length > 0 || mortality.length > 0;
  const hasWeightData = weight.length > 0 || fcr.length > 0;
  const hasChartData = showForm && (hasMortalityData || hasWeightData);

  const mortalityOptions = {
    ...baseChartOptions,
    xaxis: {
      categories: date,
      labels: { style: { colors: "#67504c" } },
      title: { text: "Date", style: { color: "#67504c" } },
    },
    yaxis: [
      {
        title: { text: "Current Bird Count", style: { color: "#67504c" } },
        labels: { style: { colors: "#67504c" } },
      },
      {
        opposite: true,
        title: { text: "Mortality", style: { color: "#67504c" } },
        labels: { style: { colors: "#67504c" } },
      },
    ],
  };

  const weightOptions = {
    ...baseChartOptions,
    xaxis: {
      categories: week,
      labels: { style: { colors: "#67504c" } },
      title: { text: "Week", style: { color: "#67504c" } },
    },
    yaxis: [
      {
        title: { text: "Average Weight (grams)", style: { color: "#67504c" } },
        labels: { style: { colors: "#67504c" } },
      },
      {
        opposite: true,
        title: { text: "FCR", style: { color: "#67504c" } },
        labels: { style: { colors: "#67504c" } },
      },
    ],
  };

  return (
    <main className="member-dashboard">
      {/* U: OLD: dashboard was a centered legacy card with duplicated chart markup.
          U: NEW: workspace layout with a page header, selector panel, and one chart area. */}
      <section className="member-dashboard-hero">
        <div>
          <span>Farmer dashboard</span>
          <h1>Flock performance at a glance.</h1>
          <p>Select a farm and flock to review bird count, mortality, weight, and FCR trends.</p>
        </div>
        <div className="member-dashboard-summary">
          <div>
            <span>Selected farm</span>
            <strong>{selectedFarmLabel}</strong>
          </div>
          <div>
            <span>Selected flock</span>
            <strong>{selectedFlockLabel}</strong>
          </div>
        </div>
      </section>

      <section className="member-dashboard-grid">
        <aside className="member-selector-card">
          <div className="member-card-heading">
            <span>Choose records</span>
            <strong>Farm and flock</strong>
          </div>
          <FormGroup>
            <Label for="farmSelect">Select Farm</Label>
            <Input value={selectedFarm} onChange={changeFarm} id="farmSelect" name="farm" type="select">
              <option value="0" disabled>Select Farm</option>
              {farms.map((item) => (
                <option key={item.public_id} value={item.public_id}>{item.name}</option>
              ))}
            </Input>
          </FormGroup>

          {showFlock && (
            <FormGroup>
              <Label for="flockSelect">Select Flock</Label>
              <Input value={selectedFlock} onChange={changeFlock} id="flockSelect" name="flock" type="select">
                <option value="0" disabled>Select Flock</option>
                {flocks.map((item) => (
                  <option key={item.flock_public_id} value={item.flock_public_id}>{item.flock_name}</option>
                ))}
              </Input>
            </FormGroup>
          )}

          <div className="member-mini-stats">
            <div>
              <span>Farms</span>
              <strong>{farms.filter((farm) => String(farm.public_id) !== "0").length}</strong>
            </div>
            <div>
              <span>Flocks</span>
              <strong>{flocks.filter((flock) => String(flock.flock_public_id) !== "0").length}</strong>
            </div>
          </div>
        </aside>

        <section className="member-chart-card">
          <div className="member-card-heading">
            <span>Performance charts</span>
            <strong>{selectedFlockLabel}</strong>
          </div>

          {graphError && (
            <div className="member-dashboard-alert">{graphError}</div>
          )}

          {hasChartData ? (
            <Tabs defaultActiveKey="mortality" id="member-performance-tabs" className="member-tabs">
              <Tab eventKey="mortality" title="Mortality">
                <Chart
                  type="line"
                  className="chart-width"
                  height={430}
                  series={[
                    { name: "Current Bird Count", data: currentCount },
                    { name: "Mortality", data: mortality },
                  ]}
                  options={mortalityOptions}
                />
              </Tab>
              <Tab eventKey="weight" title="Weight / FCR">
                <Chart
                  type="line"
                  className="chart-width"
                  height={430}
                  series={[
                    { name: "Average Weight (grams)", data: weight },
                    { name: "FCR", data: fcr },
                  ]}
                  options={weightOptions}
                />
              </Tab>
            </Tabs>
          ) : (
            <div className="member-empty-state">
              <span>No chart data yet</span>
              <p>Add daily flock data to view mortality, bird count, weight, and FCR charts here.</p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
};

export default Member;
