import "../../assets/css/header.css";
import { Tab, Tabs } from "react-bootstrap";
import { FormGroup, Label, Input } from "reactstrap";
import { apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
// U: OLD: import Chart from 'react-apexcharts';
// U: NEW: use the lazy chart wrapper so ApexCharts is split out of this route chunk.
import Chart from "../../components/ApexChart";
import { Link, useNavigate } from "react-router-dom";

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

const emptyRecordStatus = {
  dailyCount: 0,
  purchaseCount: 0,
  salesCount: 0,
  lastDailyDate: "",
  currentBirdCount: null,
  loading: false,
  error: "",
};

const readDashboardDraft = (key) => {
  try {
    return JSON.parse(localStorage.getItem(key) || "{}");
  } catch {
    return {};
  }
};

const hasAnyValue = (record, keys) => {
  return keys.some((key) => {
    const value = record?.[key];
    return value !== undefined && value !== null && value !== "" && value !== "0" && value !== 0;
  });
};

const findContinueDraft = (selectedFarm, selectedFlock) => {
  // U: NEW: form autosave is useful only if the dashboard gives farmers a
  // U: direct way to return to meaningful unfinished work.
  const storageKeys = Object.keys(localStorage);
  const dayDataKey = storageKeys.find((key) => {
    if (!key.startsWith("chikooza-day-data-draft-")) {
      return false;
    }
    const draft = readDashboardDraft(key);
    return Number(draft.dailyStep || 0) > 0 || hasAnyValue(draft.addData, ["mortality", "feed_intake", "average_bird_weight"]);
  });

  if (dayDataKey) {
    const match = dayDataKey.match(/^chikooza-day-data-draft-(\d+)-(\d{4}-\d{2}-\d{2})$/);
    if (match && selectedFarm !== "0") {
      return {
        title: "Continue daily data entry",
        helper: "Your unfinished flock-day record is saved locally.",
        action: "Resume daily data",
        href: `/daydata/${selectedFarm}/${match[1]}/${match[2]}`,
      };
    }
    return {
      title: "Continue daily data entry",
      helper: "Choose the saved flock and day to finish your daily record.",
      action: "Resume daily data",
      href: "/flockdailydata",
    };
  }

  const saleDraft = readDashboardDraft("chikooza-flock-sale-draft");
  if (Number(saleDraft.saleStep || 0) > 0 || hasAnyValue(saleDraft.data, ["selType", "date", "sellcount", "selltwt", "sellrate"])) {
    return {
      title: "Continue flock sale",
      helper: "Your unfinished sale and buyer details are saved locally.",
      action: "Resume sale",
      href: "/flocksale",
      state: selectedFlock !== "0" ? { farmPublicId: selectedFarm, flockPublicId: selectedFlock } : undefined,
    };
  }

  const purchaseDraft = readDashboardDraft("chikooza-add-purchase-draft");
  if (Number(purchaseDraft.purchaseStep || 0) > 0 || hasAnyValue(purchaseDraft.data, ["type", "date", "cost", "remarks"])) {
    return {
      title: "Continue purchase entry",
      helper: "Your unfinished purchase details are saved locally.",
      action: "Resume purchase",
      href: "/addpurchase",
      state: selectedFlock !== "0" ? { farmPublicId: selectedFarm, flockPublicId: selectedFlock } : undefined,
    };
  }

  const flockDraft = readDashboardDraft("chikooza-add-flock-draft");
  if (hasAnyValue(flockDraft, ["farm_public_id", "flock_name", "hatch_date", "flock_size", "actual_birds"])) {
    return {
      title: "Continue flock setup",
      helper: "Your unfinished flock details are saved locally.",
      action: "Resume flock",
      href: "/addflock",
    };
  }

  const farmDraft = readDashboardDraft("chikooza-add-farm-draft");
  if (hasAnyValue(farmDraft, ["farmname", "address", "cityorvillage", "pincode", "numberofsheds"])) {
    return {
      title: "Continue farm setup",
      helper: "Your unfinished farm details are saved locally.",
      action: "Resume farm",
      href: "/addfarm",
    };
  }

  const dailySelectorDraft = readDashboardDraft("chikooza-daily-selector-draft");
  if (String(dailySelectorDraft.selectedFlockId || "0") !== "0") {
    return {
      title: "Continue daily data",
      helper: "Return to your previously selected flock and choose the next day.",
      action: "Resume daily data",
      href: "/flockdailydata",
    };
  }

  return null;
};

const formatDashboardDate = (value) => {
  if (!value) {
    return "Not recorded";
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
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
  const [recordStatus, setRecordStatus] = useState(emptyRecordStatus);
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

  const loadRecordStatus = useCallback((flockId) => {
    if (!flockId || flockId === "0") {
      setRecordStatus(emptyRecordStatus);
      return;
    }

    setRecordStatus((current) => ({ ...current, loading: true, error: "" }));

    // U: OLD: dashboard inferred daily completion from chart availability and
    // U: only checked purchase/sale booleans. NEW: load real saved-record counts.
    Promise.allSettled([
      axios.get(`${apiPath}dailyDataDetail/?flock_public_id=${flockId}`, getAuthConfig()),
      axios.get(`${apiPath}purchase/?flock_public_id=${flockId}`, getAuthConfig()),
      axios.get(`${apiPath}sales/?flock_public_id=${flockId}`, getAuthConfig()),
    ]).then(([dailyResult, purchaseResult, saleResult]) => {
      if (dailyResult.status === "rejected") {
        handleUnauthorized(dailyResult.reason, navigate);
      }
      if (purchaseResult.status === "rejected") {
        handleUnauthorized(purchaseResult.reason, navigate);
      }
      if (saleResult.status === "rejected") {
        handleUnauthorized(saleResult.reason, navigate);
      }

      const dailyList =
        dailyResult.status === "fulfilled"
          ? dailyResult.value.data?.results?.daily_data_list || []
          : [];
      const purchaseList =
        purchaseResult.status === "fulfilled"
          ? purchaseResult.value.data?.results?.purchase_list || []
          : [];
      const salesList =
        saleResult.status === "fulfilled"
          ? saleResult.value.data?.results?.sales_list || []
          : [];
      const latestDailyData = dailyList[dailyList.length - 1];
      const failed =
        dailyResult.status === "rejected" ||
        purchaseResult.status === "rejected" ||
        saleResult.status === "rejected";

      setRecordStatus({
        dailyCount: dailyList.length,
        purchaseCount: purchaseList.length,
        salesCount: salesList.length,
        lastDailyDate: latestDailyData?.date || "",
        currentBirdCount: latestDailyData?.birds_count ?? latestDailyData?.current_bird_count ?? null,
        loading: false,
        error: failed ? "Some saved-record checks could not be loaded." : "",
      });
    });
  }, [navigate]);

  useEffect(() => {
    loadRecordStatus(selectedFlock);
  }, [loadRecordStatus, selectedFlock]);

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

  const selectedFarmRecord = useMemo(() => {
    return farms.find((farm) => String(farm.public_id) === selectedFarm);
  }, [farms, selectedFarm]);

  const selectedFlockRecord = useMemo(() => {
    return flocks.find((flock) => String(flock.flock_public_id) === selectedFlock);
  }, [flocks, selectedFlock]);

  const selectedFarmLabel = selectedFarmRecord?.name || "No farm selected";
  const selectedFlockLabel = selectedFlockRecord?.flock_name || "No flock selected";

  const farmCount = useMemo(() => {
    return farms.filter((farm) => String(farm.public_id) !== "0").length;
  }, [farms]);

  const flockCount = useMemo(() => {
    return flocks.filter((flock) => String(flock.flock_public_id) !== "0").length;
  }, [flocks]);

  const hasMortalityData = currentCount.length > 0 || mortality.length > 0;
  const hasWeightData = weight.length > 0 || fcr.length > 0;
  const hasChartData = showForm && (hasMortalityData || hasWeightData);
  const hasDailyData = recordStatus.dailyCount > 0;
  const hasPurchases = recordStatus.purchaseCount > 0;
  const hasSales = recordStatus.salesCount > 0;
  const reportsReady = hasDailyData;
  const selectedRecordState = selectedFlock !== "0"
    ? { farmPublicId: selectedFarm, flockPublicId: selectedFlock }
    : undefined;

  const setupSteps = useMemo(() => {
    const hasFarm = farmCount > 0;
    const hasFlock = flockCount > 0;

    return [
      {
        title: "Create farm",
        helper: "Add farm location and shed details first.",
        complete: hasFarm,
        href: hasFarm ? "/managefarm" : "/addfarm",
        action: hasFarm ? "Review farms" : "Add farm",
      },
      {
        title: "Add flock",
        helper: "Connect a broiler batch to the farm.",
        complete: hasFlock,
        href: hasFarm ? "/addflock" : "/addfarm",
        action: hasFarm ? "Add flock" : "Add farm first",
      },
      {
        title: "Record daily data",
        helper: "Enter bird count, mortality, weight, feed, and FCR.",
        complete: hasDailyData,
        href: hasFlock ? "/flockdailydata" : "/addflock",
        action: hasFlock ? "Add daily data" : "Add flock first",
      },
      {
        title: "Add purchases",
        helper: "Track feed, medicine, labour, equipment, and other costs.",
        complete: hasPurchases,
        href: hasPurchases ? "/listpurchase" : hasFlock ? "/addpurchase" : "/addflock",
        state: selectedRecordState,
        action: hasPurchases ? "Review purchases" : hasFlock ? "Add purchase" : "Add flock first",
      },
      {
        title: "Record sales",
        helper: "Add partial or final lifting details for profit reports.",
        complete: hasSales,
        href: hasSales ? "/viewsale" : hasFlock ? "/flocksale" : "/addflock",
        state: selectedRecordState,
        action: hasSales ? "Review sales" : hasFlock ? "Add sale" : "Add flock first",
      },
      {
        title: "Review reports",
        helper: "Open daily and flock reports once daily records exist.",
        complete: reportsReady,
        href: reportsReady ? "/dailydatasheet" : "/flockdailydata",
        action: reportsReady ? "Open reports" : "Add daily data first",
      },
    ];
  }, [farmCount, flockCount, hasDailyData, hasPurchases, hasSales, reportsReady, selectedRecordState]);

  const nextSetupStep = setupSteps.find((step) => !step.complete) || setupSteps[setupSteps.length - 1];
  const continueDraft = useMemo(() => {
    return findContinueDraft(selectedFarm, selectedFlock);
  }, [selectedFarm, selectedFlock]);
  const continueAction = continueDraft || {
    title: `Next recommended step: ${nextSetupStep.title}`,
    helper: nextSetupStep.helper,
    action: nextSetupStep.action,
    href: nextSetupStep.href,
    state: nextSetupStep.state,
  };

  const chartEmptyState = useMemo(() => {
    if (farmCount === 0) {
      return {
        title: "Create your first farm",
        body: "The dashboard starts showing flock charts after a farm, flock, and daily data are added.",
        href: "/addfarm",
        action: "Add farm",
      };
    }
    if (flockCount === 0) {
      return {
        title: "Add a flock under this farm",
        body: "A flock connects daily data, purchases, sales, reports, and Farmer AI answers.",
        href: "/addflock",
        action: "Add flock",
      };
    }
    if (recordStatus.dailyCount === 1) {
      return {
        title: "Add one more daily entry",
        body: "Your first daily record is saved. Add the next day to unlock trend charts for bird count, mortality, weight, and FCR.",
        href: "/flockdailydata",
        action: "Add next daily data",
      };
    }
    return {
      title: "No daily chart data yet",
      body: "Add daily flock data to view mortality, bird count, weight, and FCR charts here.",
      href: "/flockdailydata",
      action: "Add daily data",
    };
  }, [farmCount, flockCount, recordStatus.dailyCount]);

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
          U: NEW: workspace layout with a compact page header, planner, and chart area. */}
      <section className="member-dashboard-hero">
        <div>
          <span>Farmer dashboard</span>
          <h1>Flock performance at a glance.</h1>
          <p>Select a farm and flock to review bird count, mortality, weight, and FCR trends. If you are starting fresh, follow the workflow below.</p>
        </div>
      </section>

      <section className="member-continue-card">
        <div>
          <span>{continueDraft ? "Continue where you left off" : "Recommended next action"}</span>
          <strong>{continueAction.title}</strong>
          <p>{continueAction.helper}</p>
        </div>
        <Link to={continueAction.href} state={continueAction.state}>{continueAction.action}</Link>
      </section>

      <section className="member-context-grid">
        <article className="member-context-card">
          <div className="member-card-heading">
            <span>Selected farm</span>
            <strong>{selectedFarmLabel}</strong>
          </div>
          {selectedFarmRecord ? (
            <>
              <dl>
                <div><dt>Location</dt><dd>{[selectedFarmRecord.city, selectedFarmRecord.state_name].filter(Boolean).join(", ") || "Not added"}</dd></div>
                <div><dt>Sheds</dt><dd>{selectedFarmRecord.shed_count ?? "Not added"}</dd></div>
                <div><dt>Status</dt><dd>{selectedFarmRecord.status ? "Active" : "Inactive"}</dd></div>
                <div><dt>Flocks</dt><dd>{flockCount}</dd></div>
              </dl>
              <Link to="/managefarm">Manage farm</Link>
            </>
          ) : (
            <div className="member-context-empty">
              <p>Add a farm first so flocks, purchases, sales, reports, and Farmer AI can connect to it.</p>
              <Link to="/addfarm">Add farm</Link>
            </div>
          )}
        </article>

        <article className="member-context-card">
          <div className="member-card-heading">
            <span>Selected flock</span>
            <strong>{selectedFlockLabel}</strong>
          </div>
          {selectedFlockRecord ? (
            <>
              <dl>
                <div><dt>Breed</dt><dd>{selectedFlockRecord.chick_breed || "Not added"}</dd></div>
                <div><dt>Hatch date</dt><dd>{formatDashboardDate(selectedFlockRecord.hatch_date)}</dd></div>
                <div><dt>Initial birds</dt><dd>{selectedFlockRecord.actual_birds ?? "Not added"}</dd></div>
                <div><dt>Current birds</dt><dd>{recordStatus.currentBirdCount ?? selectedFlockRecord.actual_birds ?? "Not recorded"}</dd></div>
              </dl>
              <Link to="/manageflock">Manage flock</Link>
            </>
          ) : (
            <div className="member-context-empty">
              <p>Add or select a flock to unlock daily data, charts, purchases, sales, and reports.</p>
              <Link to={farmCount > 0 ? "/addflock" : "/addfarm"}>{farmCount > 0 ? "Add flock" : "Add farm first"}</Link>
            </div>
          )}
        </article>
      </section>

      <section className="member-workflow-card">
        <div className="member-card-heading">
          <span>Recommended steps</span>
          <strong>Next: {nextSetupStep.title}</strong>
        </div>
        <div className="member-workflow-steps" aria-label="Recommended farmer setup workflow">
          {setupSteps.map((step, index) => (
            <article key={step.title} className={step.complete ? "is-complete" : ""}>
              <div className="member-workflow-index">{step.complete ? "OK" : index + 1}</div>
              <div>
                <h2>{step.title}</h2>
                <p>{step.helper}</p>
                <Link to={step.href} state={step.state}>{step.action}</Link>
              </div>
            </article>
          ))}
        </div>
        {recordStatus.loading && <p className="member-card-note">Checking saved flock records...</p>}
        {!recordStatus.loading && recordStatus.error && <p className="member-card-note is-error">{recordStatus.error}</p>}
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
              <strong>{farmCount}</strong>
            </div>
            <div>
              <span>Flocks</span>
              <strong>{flockCount}</strong>
            </div>
            <div>
              <span>Daily entries</span>
              <strong>{recordStatus.dailyCount}</strong>
            </div>
            <div>
              <span>Purchases</span>
              <strong>{recordStatus.purchaseCount}</strong>
            </div>
            <div>
              <span>Sales</span>
              <strong>{recordStatus.salesCount}</strong>
            </div>
          </div>
          <div className="member-record-status" role="status">
            {recordStatus.loading && "Checking saved daily data, purchases, and sales..."}
            {!recordStatus.loading && recordStatus.error && recordStatus.error}
            {!recordStatus.loading && !recordStatus.error && selectedFlock !== "0" && (
              `Latest daily entry: ${formatDashboardDate(recordStatus.lastDailyDate)}.`
            )}
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
              <span>{chartEmptyState.title}</span>
              <p>{chartEmptyState.body}</p>
              <Link to={chartEmptyState.href}>{chartEmptyState.action}</Link>
            </div>
          )}
        </section>
      </section>
    </main>
  );
};

export default Member;
