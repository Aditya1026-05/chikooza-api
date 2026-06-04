import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  Row,
  Col,
  Table,
  Card,
  CardBody,
  FormGroup,
  Label,
  Input,
} from "reactstrap";
import "../../assets/css/header.css";
import "../../assets/css/reports.css";
import { apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import {
  addPdfFooter,
  addPdfReportHeader,
  loadAutoTable,
  loadJsPDF,
} from "../../utils/pdf";
import {
  buildReportFilename,
  formatDate,
  formatNumber,
  getAgeInDays,
  sortByDate,
  summarizeDailyRows,
  todayIso,
  toNumber,
} from "../../utils/reporting";

const DAILY_SELECTOR_DRAFT_KEY = "chikooza-daily-selector-draft";

const readSelectorDraft = () => {
  try {
    return JSON.parse(localStorage.getItem(DAILY_SELECTOR_DRAFT_KEY) || "{}");
  } catch {
    return {};
  }
};

// U: OLD: this report used doc.html() on the DOM and exported "Daily Data Sheet.pdf".
// U: NEW: render filtered report rows once, then export the same rows through jsPDF tables.
const DailyDataSheet = () => {
  const [activeSelectorDraft] = useState(() => readSelectorDraft());
  const [farms, setFarms] = useState([]);
  const [flocks, setFlocks] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState("0");
  const [selectedFlockId, setSelectedFlockId] = useState("0");
  const [selectedFlock, setSelectedFlock] = useState(null);
  const [dailyDataList, setDailyDataList] = useState([]);
  const [isLoadingFlocks, setIsLoadingFlocks] = useState(false);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [reportError, setReportError] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const prefillFarmId = String(location.state?.farmPublicId || "0");
  const prefillFlockId = String(location.state?.flockPublicId || "0");

  const filteredRows = useMemo(() => {
    return sortByDate(dailyDataList);
  }, [dailyDataList]);

  const dailyTotals = useMemo(() => summarizeDailyRows(filteredRows), [filteredRows]);
  const hasSelectedFlock = selectedFlockId !== "0" && selectedFlock;
  const hasAnyDailyData = dailyDataList.length > 0;
  const hasFilteredRows = filteredRows.length > 0;

  const selectFlockForReport = (nextFlock) => {
    if (!nextFlock || String(nextFlock.flock_public_id) === "0") {
      setSelectedFlockId("0");
      setSelectedFlock(null);
      setDailyDataList([]);
      return;
    }

    setSelectedFarmId(String(nextFlock.farm_public_id || selectedFarmId));
    setSelectedFlockId(String(nextFlock.flock_public_id));
    setSelectedFlock(nextFlock);
    getDailyDataList(nextFlock.flock_public_id);
  };

  const loadFlocksForFarm = (farmPublicId, preferredFlockId = "0") => {
    if (!farmPublicId || String(farmPublicId) === "0") {
      setSelectedFarmId("0");
      setSelectedFlockId("0");
      setSelectedFlock(null);
      setDailyDataList([]);
      setFlocks([]);
      return;
    }

    setSelectedFarmId(String(farmPublicId));
    setSelectedFlockId("0");
    setSelectedFlock(null);
    setDailyDataList([]);
    setReportError("");
    setIsLoadingFlocks(true);
    axios
      .get(`${apiPath}flocks/${farmPublicId}/`, getAuthConfig())
      .then((res) => {
        if (!res.data.results.total_records) {
          setFlocks([]);
          return;
        }

        const flockList = res.data.results.flock_list || [];
        const nextFlock = flockList.find((item) => String(item.flock_public_id) === String(preferredFlockId)) || flockList[flockList.length - 1];
        setFlocks(flockList);
        selectFlockForReport(nextFlock);
      })
      .catch((err) => {
        setFlocks([]);
        handleUnauthorized(err, navigate);
      })
      .finally(() => setIsLoadingFlocks(false));
  };

  useEffect(() => {
    axios
      .get(`${apiPath}farm/`, getAuthConfig())
      .then((res) => {
        const farmList = res.data.results.length ? res.data.results : [];
        setFarms(farmList);

        if (!farmList.length) {
          return;
        }

        const selectorFarmId = String(activeSelectorDraft.selectedFarmId || "0");
        const selectorFlockId = String(activeSelectorDraft.selectedFlockId || "0");
        const latestFarm = farmList[farmList.length - 1];
        const requestedFarmId = prefillFarmId !== "0" ? prefillFarmId : selectorFarmId !== "0" ? selectorFarmId : latestFarm?.public_id;
        const selectedFarm = farmList.find((item) => String(item.public_id) === String(requestedFarmId)) || latestFarm;
        const targetFlockId = prefillFlockId !== "0" ? prefillFlockId : selectorFlockId;

        if (selectedFarm) {
          loadFlocksForFarm(selectedFarm.public_id, targetFlockId);
        }
      })
      .catch((err) => {
        setFarms([]);
        handleUnauthorized(err, navigate);
      });
  }, [activeSelectorDraft.selectedFarmId, activeSelectorDraft.selectedFlockId, navigate, prefillFarmId, prefillFlockId]);

  const changeFarm = (event) => {
    loadFlocksForFarm(event.target.value);
  };

  const changeFlock = (event) => {
    const flockPublicId = event.target.value;
    setReportError("");

    if (flockPublicId === "0") {
      setSelectedFlockId("0");
      setSelectedFlock(null);
      setDailyDataList([]);
      return;
    }

    const nextFlock = flocks.find((item) => String(item.flock_public_id) === flockPublicId);
    selectFlockForReport(nextFlock);
  };

  const getDailyDataList = (flockPublicId) => {
    setIsLoadingReport(true);
    axios
      .get(`${apiPath}dailyDataList/?flock_public_id=${flockPublicId}`, getAuthConfig())
      .then((res) => {
        setDailyDataList(res.data.results.daily_data_list || []);
      })
      .catch((err) => {
        setDailyDataList([]);
        setReportError("Could not load daily data for this flock.");
        handleUnauthorized(err, navigate);
      })
      .finally(() => setIsLoadingReport(false));
  };

  const dateRangeLabel = () => {
    if (!filteredRows.length) {
      return "No saved dates";
    }

    const firstDate = filteredRows[0]?.date;
    const lastDate = filteredRows[filteredRows.length - 1]?.date;
    if (!firstDate || !lastDate) {
      return "Saved daily records";
    }
    if (firstDate === lastDate) {
      return formatDate(firstDate);
    }
    return `${formatDate(firstDate)} to ${formatDate(lastDate)}`;
  };

  const buildPdfRows = () => {
    return filteredRows.map((item) => {
      const currentBirds = toNumber(item.current_bird_count);
      const cumFeedPerBird = currentBirds > 0
        ? (toNumber(item.total_feed) * 1000) / currentBirds
        : 0;

      return [
        formatDate(item.date),
        getAgeInDays(selectedFlock?.hatch_date, item.date),
        formatNumber(item.current_bird_count, 0),
        formatNumber(item.mortality, 0),
        `${formatNumber(item.cum_mort, 0)} (${formatNumber(item.total_mortality_percentage, 2)}%)`,
        formatNumber(item.feed_intake, 2),
        formatNumber(item.average_feed, 2),
        formatNumber(item.total_feed, 2),
        currentBirds > 0 ? formatNumber(cumFeedPerBird, 2) : "-",
        toNumber(item.average_bird_weight) > 0 ? formatNumber(item.average_bird_weight, 0) : "-",
        toNumber(item.average_bird_weight) > 0 ? formatNumber(item.fcr, 2) : "-",
        formatNumber(item.feed_stock, 2),
        item.remarks || "-",
      ];
    });
  };

  const downloadPdf = async () => {
    if (!hasFilteredRows || !selectedFlock) {
      return;
    }

    setIsExportingPdf(true);
    try {
      const [jsPDF, autoTable] = await Promise.all([loadJsPDF(), loadAutoTable()]);
      const doc = new jsPDF("landscape", "pt", "a4");
      const startY = addPdfReportHeader(doc, {
        title: "Daily Data Sheet",
        subtitle: "Saved operational records for mortality, feed, weight, FCR, and current bird count.",
        theme: "light",
        meta: [
          { label: "Farm", value: selectedFlock.farm_name || "-" },
          { label: "Flock", value: selectedFlock.flock_name || "-" },
          { label: "Report period", value: dateRangeLabel() },
          { label: "Generated", value: formatDate(todayIso()) },
        ],
      });

      autoTable(doc, {
        startY,
        head: [[
          "Date",
          "Age",
          "Birds",
          "Mort.",
          "Cum Mort.",
          "Feed Kg",
          "Feed/Bird",
          "Cum Feed",
          "Cum Feed/Bird",
          "Avg Wt",
          "FCR",
          "Feed Stock",
          "Remarks",
        ]],
        body: buildPdfRows(),
        foot: [[
          "Totals",
          "",
          formatNumber(dailyTotals.latestBirdCount, 0),
          formatNumber(dailyTotals.totalMortality, 0),
          "",
          formatNumber(dailyTotals.totalFeed, 2),
          "",
          "",
          "",
          "",
          formatNumber(dailyTotals.averageFcr, 2),
          formatNumber(dailyTotals.latestFeedStock, 2),
          `${dailyTotals.recordCount} records`,
        ]],
        styles: {
          cellPadding: 4,
          fontSize: 7.5,
          lineColor: [244, 214, 207],
          lineWidth: 0.35,
          overflow: "linebreak",
          textColor: [51, 33, 29],
        },
        headStyles: {
          fillColor: [255, 241, 235],
          fontStyle: "bold",
          lineColor: [230, 184, 174],
          textColor: [143, 35, 27],
        },
        footStyles: {
          fillColor: [255, 244, 238],
          fontStyle: "bold",
          lineColor: [230, 184, 174],
          textColor: [127, 29, 29],
        },
        alternateRowStyles: { fillColor: [255, 250, 247] },
        margin: { left: 28, right: 28 },
      });

      addPdfFooter(doc);
      doc.save(buildReportFilename("DailyDataSheet", selectedFlock.flock_name));
    } finally {
      setIsExportingPdf(false);
    }
  };

  return (
    <Row>
      <Col>
        <Card className="report-page report-page--daily-sheet">
          <div className="report-page__header">
            <div>
              <div className="report-page__eyebrow">Operations report</div>
              <h1 className="report-page__title">Daily Data Sheet</h1>
              <p className="report-page__subtitle">
                Select a farm and flock. The table and PDF use the same saved daily records and totals.
              </p>
            </div>
          </div>
          <CardBody className="report-page__body">
            <div className="report-filter-grid report-filter-grid--compact">
              <FormGroup>
                <Label for="farmSelect">Farm</Label>
                <Input id="farmSelect" type="select" value={selectedFarmId} onChange={changeFarm}>
                  <option value="0">Select farm</option>
                  {farms.map((item) => (
                    <option key={item.public_id} value={item.public_id}>
                      {item.name}
                    </option>
                  ))}
                </Input>
              </FormGroup>
              <FormGroup>
                <Label for="flockSelect">Flock</Label>
                <Input
                  disabled={selectedFarmId === "0" || isLoadingFlocks}
                  id="flockSelect"
                  type="select"
                  value={selectedFlockId}
                  onChange={changeFlock}
                >
                  <option value="0">{isLoadingFlocks ? "Loading flocks..." : "Select flock"}</option>
                  {flocks.map((item) => (
                    <option key={item.flock_public_id} value={item.flock_public_id}>
                      {item.flock_name}
                    </option>
                  ))}
                </Input>
              </FormGroup>
            </div>

            <div className="report-actions">
              <button
                type="button"
                className="report-export-button"
                onClick={downloadPdf}
                disabled={!hasFilteredRows || isExportingPdf}
              >
                {isExportingPdf ? "Exporting..." : "Export PDF"}
              </button>
            </div>

            {reportError && (
              <div className="report-empty-state">
                <strong>Report could not load</strong>
                {reportError}
              </div>
            )}

            {!hasSelectedFlock && (
              <div className="report-empty-state">
                <strong>Select a flock to view the report.</strong>
                Daily reports are built from saved daily flock records.
              </div>
            )}

            {hasSelectedFlock && !isLoadingReport && !hasAnyDailyData && (
              <div className="report-empty-state">
                <strong>Not enough data yet.</strong>
                Add daily data for this flock before exporting a daily data report.
              </div>
            )}

            {hasSelectedFlock && hasAnyDailyData && !hasFilteredRows && (
              <div className="report-empty-state">
                <strong>No daily records found.</strong>
                Add daily data for this flock before exporting the report.
              </div>
            )}

            {hasFilteredRows && (
              <>
                <div className="report-kpi-grid">
                  <div className="report-kpi">
                    <span>Records</span>
                    <strong>{dailyTotals.recordCount}</strong>
                  </div>
                  <div className="report-kpi">
                    <span>Total mortality</span>
                    <strong>{formatNumber(dailyTotals.totalMortality, 0)}</strong>
                  </div>
                  <div className="report-kpi">
                    <span>Feed used</span>
                    <strong>{formatNumber(dailyTotals.totalFeed, 2)} kg</strong>
                  </div>
                  <div className="report-kpi">
                    <span>Latest birds</span>
                    <strong>{formatNumber(dailyTotals.latestBirdCount, 0)}</strong>
                  </div>
                </div>

                <div className="report-section-card">
                  <div className="report-section-card__header">
                    <h3>{selectedFlock?.flock_name} daily records</h3>
                    <span className="report-muted">{dateRangeLabel()}</span>
                  </div>
                  <Table responsive className="report-table report-table--daily">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Age</th>
                        <th>Birds</th>
                        <th>Mort.</th>
                        <th>Cum Mort.</th>
                        <th>Feed Kg</th>
                        <th>Feed/Bird</th>
                        <th>Cum Feed</th>
                        <th>Cum Feed/Bird</th>
                        <th>Avg Wt</th>
                        <th>FCR</th>
                        <th>Feed Stock</th>
                        <th>Remarks</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRows.map((item) => {
                        const currentBirds = toNumber(item.current_bird_count);
                        const cumFeedPerBird = currentBirds > 0
                          ? (toNumber(item.total_feed) * 1000) / currentBirds
                          : 0;

                        return (
                          <tr key={item.public_id || `${item.flock_public_id}-${item.date}`}>
                            <td>{formatDate(item.date)}</td>
                            <td>{getAgeInDays(selectedFlock?.hatch_date, item.date)}</td>
                            <td>{formatNumber(item.current_bird_count, 0)}</td>
                            <td>{formatNumber(item.mortality, 0)}</td>
                            <td>{formatNumber(item.cum_mort, 0)} ({formatNumber(item.total_mortality_percentage, 2)}%)</td>
                            <td>{formatNumber(item.feed_intake, 2)}</td>
                            <td>{formatNumber(item.average_feed, 2)}</td>
                            <td>{formatNumber(item.total_feed, 2)}</td>
                            <td>{currentBirds > 0 ? formatNumber(cumFeedPerBird, 2) : "-"}</td>
                            <td>{toNumber(item.average_bird_weight) > 0 ? formatNumber(item.average_bird_weight, 0) : "-"}</td>
                            <td>{toNumber(item.average_bird_weight) > 0 ? formatNumber(item.fcr, 2) : "-"}</td>
                            <td>{formatNumber(item.feed_stock, 2)}</td>
                            <td>{item.remarks || "-"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td>Total</td>
                        <td></td>
                        <td>{formatNumber(dailyTotals.latestBirdCount, 0)}</td>
                        <td>{formatNumber(dailyTotals.totalMortality, 0)}</td>
                        <td></td>
                        <td>{formatNumber(dailyTotals.totalFeed, 2)}</td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td>{formatNumber(dailyTotals.averageFcr, 2)}</td>
                        <td>{formatNumber(dailyTotals.latestFeedStock, 2)}</td>
                        <td>{dailyTotals.recordCount} records</td>
                      </tr>
                    </tfoot>
                  </Table>
                </div>
              </>
            )}
          </CardBody>
        </Card>
      </Col>
    </Row>
  );
};

export default DailyDataSheet;
