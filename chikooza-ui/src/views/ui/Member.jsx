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
import {
  isValidWorkspaceId,
  readInitialWorkspace,
  resolveWorkspaceFarm,
  resolveWorkspaceFlock,
  writeCurrentWorkspace,
} from "../../utils/currentWorkspace";

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
  feedPurchaseCount: 0,
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
  const [totalFlockCount, setTotalFlockCount] = useState(0);
  const [showWorkflow, setShowWorkflow] = useState(false);
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
      const feedPurchaseCount = purchaseList.filter((item) => item.type === "Feed").length;
      const latestDailyData = dailyList[dailyList.length - 1];
      const failed =
        dailyResult.status === "rejected" ||
        purchaseResult.status === "rejected" ||
        saleResult.status === "rejected";

      setRecordStatus({
        dailyCount: dailyList.length,
        feedPurchaseCount,
        salesCount: salesList.length,
        lastDailyDate: latestDailyData?.date || "",
        currentBirdCount: latestDailyData?.birds_count ?? latestDailyData?.current_bird_count ?? null,
        loading: false,
        error: failed ? "Some saved-record checks could not be loaded." : "",
      });
    });
  }, [navigate]);

  const loadTotalFlockCount = useCallback((farmList) => {
    const validFarms = farmList.filter((farm) => String(farm.public_id) !== "0");
    if (validFarms.length === 0) {
      setTotalFlockCount(0);
      return;
    }

    // U: NEW: dashboard header needs the farmer's total flock count across
    // U: all farms, while the chart selector still loads only the active farm.
    Promise.allSettled(
      validFarms.map((farm) => axios.get(`${apiPath}flocks/${farm.public_id}/`, getAuthConfig()))
    ).then((results) => {
      const total = results.reduce((count, result) => {
        if (result.status === "rejected") {
          handleUnauthorized(result.reason, navigate);
          return count;
        }
        const records = result.value.data?.results;
        return count + Number(records?.total_records || records?.flock_list?.length || 0);
      }, 0);
      setTotalFlockCount(total);
    });
  }, [navigate]);

  const loadFlocksForFarm = useCallback((farmId, options = {}) => {
    const {
      preferredFlockId = "0",
      persistCurrent = false,
      source = "dashboard",
    } = options;

    if (!isValidWorkspaceId(farmId)) {
      setShowFlock(false);
      setShowForm(false);
      setFlocks([]);
      setSelectedFarm("0");
      setSelectedFlock("0");
      if (persistCurrent) {
        writeCurrentWorkspace({ farmPublicId: "0", flockPublicId: "0", source });
      }
      return;
    }

    const resolvedFarmId = String(farmId);
    setSelectedFarm(resolvedFarmId);

    axios.get(`${apiPath}flocks/${resolvedFarmId}/`, getAuthConfig()).then((flockRes) => {
      if (flockRes.data.results.total_records === 0) {
        setFlocks([{ flock_public_id: 0, flock_name: "No flock available" }]);
        setSelectedFlock("0");
        setShowForm(false);
        if (persistCurrent) {
          writeCurrentWorkspace({ farmPublicId: resolvedFarmId, flockPublicId: "0", source });
        }
      } else {
        const flockList = flockRes.data.results.flock_list;
        const resolvedFlock = resolveWorkspaceFlock(flockList, preferredFlockId);
        const resolvedFlockId = String(resolvedFlock.flock_public_id);

        getsetFlockData2(resolvedFlockId);
        setSelectedFlock(resolvedFlockId);
        setFlocks(flockList);
        setShowForm(true);
        if (persistCurrent) {
          writeCurrentWorkspace({ farmPublicId: resolvedFarmId, flockPublicId: resolvedFlockId, source });
        }
      }
      setShowFlock(true);
    }).catch((err) => {
      handleUnauthorized(err, navigate);
    });
  }, [getsetFlockData2, navigate]);

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
        setTotalFlockCount(0);
        writeCurrentWorkspace({ farmPublicId: "0", flockPublicId: "0", source: "dashboard_empty" });
      } else {
        const farmList = res.data.results;
        const savedWorkspace = readInitialWorkspace();
        const resolvedFarm = resolveWorkspaceFarm(farmList, savedWorkspace.farmPublicId);
        setFarms(farmList);
        loadTotalFlockCount(farmList);
        loadFlocksForFarm(resolvedFarm.public_id, {
          preferredFlockId: savedWorkspace.flockPublicId,
          persistCurrent: true,
          source: "dashboard_init",
        });
      }
    }).catch((err) => {
      setFarms([{ public_id: 0, name: "No farm available" }]);
      setSelectedFarm("0");
      setTotalFlockCount(0);
      handleUnauthorized(err, navigate);
    });
  }, [loadFlocksForFarm, loadTotalFlockCount, navigate]);

  const changeFarm = (event) => {
    // U: OLD: e.target.value === 0 compared a string to a number.
    if (event.target.value === "0") {
      setShowFlock(false);
      setShowForm(false);
      setFlocks([]);
      setSelectedFarm("0");
      setSelectedFlock("0");
      writeCurrentWorkspace({ farmPublicId: "0", flockPublicId: "0", source: "dashboard_manual_farm" });
      return;
    }

    loadFlocksForFarm(event.target.value, {
      preferredFlockId: "0",
      persistCurrent: true,
      source: "dashboard_manual_farm",
    });
  };

  const selectFlockRecord = (flock, options = {}) => {
    const { persistCurrent = false, farmId = selectedFarm, source = "dashboard_manual_flock" } = options;
    if (!flock || String(flock.flock_public_id) === "0") {
      setShowForm(false);
      setSelectedFlock("0");
      if (persistCurrent) {
        writeCurrentWorkspace({ farmPublicId: farmId, flockPublicId: "0", source });
      }
      return;
    }

    // U: NEW: use one selection path for dropdowns and the visible flock chips.
    getsetFlockData2(flock.flock_public_id);
    setShowForm(true);
    setSelectedFlock(String(flock.flock_public_id));
    if (persistCurrent) {
      writeCurrentWorkspace({ farmPublicId: farmId, flockPublicId: flock.flock_public_id, source });
    }
  };

  const changeFlock = (event) => {
    const flock = flocks.find((item) => String(item.flock_public_id) === event.target.value);
    selectFlockRecord(flock, { persistCurrent: true });
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

  const availableFlocks = useMemo(() => {
    return flocks.filter((flock) => String(flock.flock_public_id) !== "0");
  }, [flocks]);

  const flockCount = useMemo(() => {
    return availableFlocks.length;
  }, [availableFlocks]);

  const hasMortalityData = currentCount.length > 0 || mortality.length > 0;
  const hasWeightData = weight.length > 0 || fcr.length > 0;
  const hasChartData = showForm && (hasMortalityData || hasWeightData);
  const hasDailyData = recordStatus.dailyCount > 0;
  const hasFeedPurchase = recordStatus.feedPurchaseCount > 0;
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
        complete: hasFarm,
        href: hasFarm ? "/managefarm" : "/addfarm",
        action: hasFarm ? "Review farms" : "Add farm",
      },
      {
        title: "Add flock",
        complete: hasFlock,
        href: hasFarm ? "/addflock" : "/addfarm",
        action: hasFarm ? "Add flock" : "Add farm first",
      },
      {
        title: "Add feed purchase",
        complete: hasFeedPurchase,
        href: hasFeedPurchase ? "/listpurchase" : hasFlock ? "/addpurchase" : "/addflock",
        state: selectedRecordState,
        action: hasFeedPurchase ? "Review feed purchases" : hasFlock ? "Add feed purchase" : "Add flock first",
      },
      {
        title: "Record daily data",
        complete: hasDailyData,
        href: hasFeedPurchase ? "/flockdailydata" : hasFlock ? "/addpurchase" : "/addflock",
        state: selectedRecordState,
        action: hasDailyData ? "Review daily data" : hasFeedPurchase ? "Add daily data" : hasFlock ? "Add feed first" : "Add flock first",
      },
      {
        title: "Record sales",
        complete: hasSales,
        href: hasSales ? "/viewsale" : hasFlock ? "/flocksale" : "/addflock",
        state: selectedRecordState,
        action: hasSales ? "Review sales" : hasFlock ? "Add sale" : "Add flock first",
      },
      {
        title: "Review reports",
        complete: reportsReady,
        href: reportsReady ? "/dailydatasheet" : "/flockdailydata",
        action: reportsReady ? "Open reports" : "Add daily data first",
      },
    ];
  }, [farmCount, flockCount, hasDailyData, hasFeedPurchase, hasSales, reportsReady, selectedRecordState]);

  const nextSetupStep = setupSteps.find((step) => !step.complete) || setupSteps[setupSteps.length - 1];
  const continueDraft = useMemo(() => {
    return findContinueDraft(selectedFarm, selectedFlock);
  }, [selectedFarm, selectedFlock]);
  const continueAction = continueDraft || {
    title: nextSetupStep.title,
    action: nextSetupStep.action,
    href: nextSetupStep.href,
    state: nextSetupStep.state,
  };
  const continueActionLabel = continueDraft ? "Continue where you left off" : "Recommended next action";

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
    if (!hasFeedPurchase) {
      return {
        title: "Add feed stock first",
        body: "Feed purchases create the feed stock used by daily data. Add a feed purchase before recording feed consumed.",
        href: "/addpurchase",
        action: "Add feed purchase",
        state: selectedRecordState,
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
  }, [farmCount, flockCount, hasFeedPurchase, recordStatus.dailyCount, selectedRecordState]);

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
          <h1>FLOCK PERFORMANCE<br />AT A GLANCE</h1>
        </div>
        <div className="member-dashboard-summary" aria-label="Dashboard record summary">
          <article>
            <span>Farms</span>
            <strong>{farmCount}</strong>
          </article>
          <article>
            <span>Flocks</span>
            <strong>{totalFlockCount}</strong>
          </article>
          <article className="member-dashboard-select-card">
            <label htmlFor="currentFarmSelect">Current farm</label>
            <Input value={selectedFarm} onChange={changeFarm} id="currentFarmSelect" name="currentFarm" type="select">
              <option value="0" disabled>Select Farm</option>
              {farms.map((item) => (
                <option key={item.public_id} value={item.public_id}>{item.name}</option>
              ))}
            </Input>
          </article>
          <article className="member-dashboard-select-card">
            <label htmlFor="currentFlockSelect">Current flock</label>
            <Input value={selectedFlock} onChange={changeFlock} id="currentFlockSelect" name="currentFlock" type="select" disabled={!showFlock}>
              <option value="0" disabled>Select Flock</option>
              {flocks.map((item) => (
                <option key={item.flock_public_id} value={item.flock_public_id}>{item.flock_name}</option>
              ))}
            </Input>
          </article>
        </div>
      </section>

      <section className="member-continue-card">
        <div>
          <strong>{continueActionLabel}: {continueAction.title}</strong>
        </div>
        <div className="member-continue-actions">
          <button type="button" onClick={() => setShowWorkflow((current) => !current)}>
            {showWorkflow ? "Hide workflow" : "View workflow"}
          </button>
          <Link to={continueAction.href} state={continueAction.state}>{continueAction.action}</Link>
        </div>
      </section>

      {showWorkflow && (
        <section className="member-workflow-card member-workflow-panel">
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
                  <Link to={step.href} state={step.state}>{step.action}</Link>
                </div>
              </article>
            ))}
          </div>
          {recordStatus.loading && <p className="member-card-note">Checking saved flock records...</p>}
          {!recordStatus.loading && recordStatus.error && <p className="member-card-note is-error">{recordStatus.error}</p>}
        </section>
      )}

      <section className="member-chart-card member-chart-card-wide">
        <div className="member-chart-top">
          <div className="member-card-heading">
            <span>Performance charts</span>
            <strong>{selectedFlockLabel}</strong>
          </div>
          <div className="member-chart-controls">
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
          </div>
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
            <Link to={chartEmptyState.href} state={chartEmptyState.state}>{chartEmptyState.action}</Link>
          </div>
        )}
      </section>
    </main>
  );
};

export default Member;
