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
  formatCurrency,
  formatDate,
  formatNumber,
  getAgeInDays,
  purchaseTypeTotals,
  sortByDate,
  summarizeCosts,
  summarizeSales,
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

// U: OLD: this report exported a DOM screenshot and showed only all-time backend totals.
// U: NEW: the screen and PDF use one filtered calculation path for purchases, sales, and daily rows.
const FlockSummary = () => {
  const [activeSelectorDraft] = useState(() => readSelectorDraft());
  const [farms, setFarms] = useState([]);
  const [flocks, setFlocks] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState("0");
  const [selectedFlockId, setSelectedFlockId] = useState("0");
  const [currentFlock, setCurrentFlock] = useState(null);
  const [flockData, setFlockData] = useState({});
  const [purchaseList, setPurchaseList] = useState([]);
  const [salesList, setSalesList] = useState([]);
  const [dailyDataList, setDailyDataList] = useState([]);
  const [isLoadingFlocks, setIsLoadingFlocks] = useState(false);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [reportError, setReportError] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const prefillFarmId = String(location.state?.farmPublicId || "0");
  const prefillFlockId = String(location.state?.flockPublicId || "0");

  const filteredPurchases = useMemo(() => {
    return sortByDate(purchaseList);
  }, [purchaseList]);

  const filteredSales = useMemo(() => {
    return sortByDate(salesList);
  }, [salesList]);

  const filteredDailyRows = useMemo(() => {
    return sortByDate(dailyDataList);
  }, [dailyDataList]);

  const purchaseTotals = useMemo(() => {
    return purchaseTypeTotals(filteredPurchases, currentFlock, "", "");
  }, [filteredPurchases, currentFlock]);

  const totalCost = useMemo(() => summarizeCosts(purchaseTotals), [purchaseTotals]);
  const salesTotals = useMemo(() => summarizeSales(filteredSales), [filteredSales]);
  const profitLoss = salesTotals.totalAmount - totalCost;
  const latestDailyRow = filteredDailyRows[filteredDailyRows.length - 1] || null;
  const hasSelectedFlock = selectedFlockId !== "0" && currentFlock;
  const hasAnyDailyData = dailyDataList.length > 0;
  const hasFilteredRows = filteredDailyRows.length || filteredPurchases.length || filteredSales.length;

  const selectFlockForReport = (nextFlock) => {
    if (!nextFlock || String(nextFlock.flock_public_id) === "0") {
      setSelectedFlockId("0");
      setCurrentFlock(null);
      setFlockData({});
      setPurchaseList([]);
      setSalesList([]);
      setDailyDataList([]);
      return;
    }

    setSelectedFarmId(String(nextFlock.farm_public_id || selectedFarmId));
    setSelectedFlockId(String(nextFlock.flock_public_id));
    setCurrentFlock(nextFlock);
    loadReportData(nextFlock.flock_public_id);
  };

  const loadFlocksForFarm = (farmPublicId, preferredFlockId = "0") => {
    if (!farmPublicId || String(farmPublicId) === "0") {
      setSelectedFarmId("0");
      setSelectedFlockId("0");
      setCurrentFlock(null);
      setFlockData({});
      setPurchaseList([]);
      setSalesList([]);
      setDailyDataList([]);
      setFlocks([]);
      return;
    }

    setSelectedFarmId(String(farmPublicId));
    setSelectedFlockId("0");
    setCurrentFlock(null);
    setFlockData({});
    setPurchaseList([]);
    setSalesList([]);
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
      setCurrentFlock(null);
      setFlockData({});
      setPurchaseList([]);
      setSalesList([]);
      setDailyDataList([]);
      return;
    }

    const nextFlock = flocks.find((item) => String(item.flock_public_id) === flockPublicId);
    selectFlockForReport(nextFlock);
  };

  const loadReportData = (flockPublicId) => {
    setIsLoadingReport(true);
    Promise.all([
      axios.get(`${apiPath}flockSummary/${flockPublicId}/`, getAuthConfig()),
      axios.get(`${apiPath}purchase/?flock_public_id=${flockPublicId}`, getAuthConfig()),
      axios.get(`${apiPath}dailyDataList/?flock_public_id=${flockPublicId}`, getAuthConfig()),
    ])
      .then(([summaryRes, purchaseRes, dailyRes]) => {
        const summary = summaryRes.data.results || {};
        setFlockData(summary);
        setSalesList(summary.sales_data || []);
        setPurchaseList(purchaseRes.data.results.purchase_list || []);
        setDailyDataList(dailyRes.data.results.daily_data_list || []);
      })
      .catch((err) => {
        setFlockData({});
        setPurchaseList([]);
        setSalesList([]);
        setDailyDataList([]);
        setReportError("Could not load the flock summary report.");
        handleUnauthorized(err, navigate);
      })
      .finally(() => setIsLoadingReport(false));
  };

  const dateRangeLabel = () => {
    const datedRows = [...filteredDailyRows, ...filteredPurchases, ...filteredSales]
      .map((row) => row?.date)
      .filter(Boolean)
      .sort((first, second) => String(first).localeCompare(String(second)));

    if (!datedRows.length) {
      return "No saved dates";
    }

    const firstDate = datedRows[0];
    const lastDate = datedRows[datedRows.length - 1];
    if (firstDate === lastDate) {
      return formatDate(firstDate);
    }
    return `${formatDate(firstDate)} to ${formatDate(lastDate)}`;
  };

  const pdfDateRangeLabel = () => {
    const datedRows = [...filteredDailyRows, ...filteredPurchases, ...filteredSales]
      .map((row) => row?.date)
      .filter(Boolean)
      .sort((first, second) => String(first).localeCompare(String(second)));

    if (!datedRows.length) {
      return "No saved dates";
    }

    const firstDate = datedRows[0];
    const lastDate = datedRows[datedRows.length - 1];
    if (firstDate === lastDate) {
      return formatDate(firstDate);
    }

    const first = new Date(`${firstDate}T00:00:00`);
    const last = new Date(`${lastDate}T00:00:00`);
    if (!Number.isNaN(first.getTime()) && !Number.isNaN(last.getTime()) && first.getFullYear() === last.getFullYear()) {
      const firstCompact = first.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
      });
      return `${firstCompact} - ${formatDate(lastDate)}`;
    }

    return `${formatDate(firstDate)} - ${formatDate(lastDate)}`;
  };

  const costRows = () => {
    return [
      ["Chick cost", formatCurrency(purchaseTotals.Chick)],
      ["Feed", formatCurrency(purchaseTotals.Feed)],
      ["Medicine", formatCurrency(purchaseTotals.Medicine)],
      ["Vaccination", formatCurrency(purchaseTotals.Vaccination)],
      ["Equipment", formatCurrency(purchaseTotals.Equipment)],
      ["Labour", formatCurrency(purchaseTotals.Labour)],
      ["Other", formatCurrency(purchaseTotals.Other)],
    ];
  };

  const salesRows = () => {
    return filteredSales.map((sale) => [
      formatDate(sale.date),
      sale.sales_type || "-",
      formatNumber(sale.lifting_count, 0),
      formatNumber(sale.total_weight, 2),
      formatNumber(sale.average_weight, 2),
      formatNumber(sale.rate_per_kg, 2),
      formatCurrency(sale.cost),
    ]);
  };

  const downloadPDFWithjsPDF = async () => {
    if (!hasSelectedFlock || !hasFilteredRows) {
      return;
    }

    setIsExportingPdf(true);
    try {
      const [jsPDF, autoTable] = await Promise.all([loadJsPDF(), loadAutoTable()]);
      const doc = new jsPDF("portrait", "pt", "a4");
      let startY = addPdfReportHeader(doc, {
        title: "Flock Summary",
        subtitle: "Saved flock performance, cost, sales, and profit/loss report.",
        theme: "light",
        meta: [
          { label: "Farm", value: flockData.farm_name || currentFlock?.farm_name || "-" },
          { label: "Flock", value: flockData.flock_name || currentFlock?.flock_name || "-" },
          { label: "Report period", value: pdfDateRangeLabel() },
          { label: "Generated", value: formatDate(todayIso()) },
        ],
      });

      autoTable(doc, {
        startY,
        head: [["Metric", "Value", "Metric", "Value"]],
        body: [
          ["Status", flockData.status || "-", "Hatch date", formatDate(flockData.hatch_date || currentFlock?.hatch_date)],
          ["Starting birds", formatNumber(flockData.actual_birds || currentFlock?.actual_birds, 0), "Current birds", latestDailyRow ? formatNumber(latestDailyRow.current_bird_count, 0) : formatNumber(flockData.current_bird_count, 0)],
          ["Mortality", latestDailyRow ? formatNumber(latestDailyRow.cum_mort, 0) : formatNumber(flockData.cum_mort, 0), "FCR", latestDailyRow ? formatNumber(latestDailyRow.fcr, 2) : String(flockData.fcr || "-")],
          ["Total cost", formatCurrency(totalCost), "Total sales", formatCurrency(salesTotals.totalAmount)],
          ["Profit/Loss", formatCurrency(profitLoss), "Records", `${filteredDailyRows.length} daily / ${filteredPurchases.length} purchases / ${filteredSales.length} sales`],
        ],
        styles: { cellPadding: 5, fontSize: 9, lineColor: [244, 214, 207], lineWidth: 0.35, textColor: [51, 33, 29] },
        headStyles: { fillColor: [255, 241, 235], lineColor: [230, 184, 174], textColor: [143, 35, 27] },
        alternateRowStyles: { fillColor: [255, 250, 247] },
        margin: { left: 36, right: 36 },
      });

      startY = doc.lastAutoTable.finalY + 18;
      autoTable(doc, {
        startY,
        head: [["Cost type", "Amount"]],
        body: costRows(),
        foot: [["Total cost", formatCurrency(totalCost)]],
        styles: { cellPadding: 5, fontSize: 9, lineColor: [244, 214, 207], lineWidth: 0.35, textColor: [51, 33, 29] },
        headStyles: { fillColor: [255, 241, 235], lineColor: [230, 184, 174], textColor: [143, 35, 27] },
        footStyles: { fillColor: [255, 244, 238], fontStyle: "bold", lineColor: [230, 184, 174], textColor: [127, 29, 29] },
        margin: { left: 36, right: 36 },
      });

      startY = doc.lastAutoTable.finalY + 18;
      autoTable(doc, {
        startY,
        head: [["Date", "Type", "Birds", "Weight", "Avg Wt", "Rate/Kg", "Amount"]],
        body: salesRows().length ? salesRows() : [["No sales saved", "", "", "", "", "", ""]],
        foot: [["Total", "", formatNumber(salesTotals.totalBirds, 0), formatNumber(salesTotals.totalWeight, 2), formatNumber(salesTotals.averageWeight, 2), formatNumber(salesTotals.averageRate, 2), formatCurrency(salesTotals.totalAmount)]],
        styles: { cellPadding: 4, fontSize: 8, lineColor: [244, 214, 207], lineWidth: 0.35, textColor: [51, 33, 29] },
        headStyles: { fillColor: [255, 241, 235], lineColor: [230, 184, 174], textColor: [143, 35, 27] },
        footStyles: { fillColor: [255, 244, 238], fontStyle: "bold", lineColor: [230, 184, 174], textColor: [127, 29, 29] },
        margin: { left: 36, right: 36 },
      });

      addPdfFooter(doc);
      doc.save(buildReportFilename("FlockSummary", flockData.flock_name || currentFlock?.flock_name));
    } finally {
      setIsExportingPdf(false);
    }
  };

  return (
    <Row>
      <Col>
        <Card className="report-page report-page--flock-summary">
          <div className="report-page__header">
            <div>
              <div className="report-page__eyebrow">Performance report</div>
              <h1 className="report-page__title">Flock Summary</h1>
              <p className="report-page__subtitle">
                Review flock performance, purchase cost, sales, and profit/loss from saved farm records.
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
                onClick={downloadPDFWithjsPDF}
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
                Flock summary uses saved daily data, purchases, and sales for the selected flock.
              </div>
            )}

            {hasSelectedFlock && !isLoadingReport && !hasAnyDailyData && (
              <div className="report-empty-state">
                <strong>Not enough data yet.</strong>
                Add daily data before using performance metrics like FCR, current birds, and mortality trend.
              </div>
            )}

            {hasSelectedFlock && !isLoadingReport && hasAnyDailyData && !hasFilteredRows && (
              <div className="report-empty-state">
                <strong>No report records found.</strong>
                Add daily data, purchases, or sales before exporting this report.
              </div>
            )}

            {hasSelectedFlock && hasFilteredRows && (
              <>
                <div className="report-kpi-grid">
                  <div className="report-kpi">
                    <span>Current birds</span>
                    <strong>{latestDailyRow ? formatNumber(latestDailyRow.current_bird_count, 0) : formatNumber(flockData.current_bird_count, 0)}</strong>
                  </div>
                  <div className="report-kpi">
                    <span>Total cost</span>
                    <strong>{formatCurrency(totalCost)}</strong>
                  </div>
                  <div className="report-kpi">
                    <span>Total sales</span>
                    <strong>{formatCurrency(salesTotals.totalAmount)}</strong>
                  </div>
                  <div className="report-kpi">
                    <span>Profit/Loss</span>
                    <strong className={profitLoss >= 0 ? "report-profit-positive" : "report-profit-negative"}>
                      {formatCurrency(profitLoss)}
                    </strong>
                  </div>
                </div>

                <div className="report-section-card">
                  <div className="report-section-card__header">
                    <h3>Flock details</h3>
                    <span className="report-muted">{dateRangeLabel()}</span>
                  </div>
                  <Table responsive className="report-table report-table--soft">
                    <tbody>
                      <tr>
                        <th>Farm</th>
                        <td>{flockData.farm_name || currentFlock?.farm_name || "-"}</td>
                        <th>Flock</th>
                        <td>{flockData.flock_name || currentFlock?.flock_name || "-"}</td>
                      </tr>
                      <tr>
                        <th>Hatch date</th>
                        <td>{formatDate(flockData.hatch_date || currentFlock?.hatch_date)}</td>
                        <th>Age today</th>
                        <td>{getAgeInDays(currentFlock?.hatch_date, todayIso())}</td>
                      </tr>
                      <tr>
                        <th>Breed</th>
                        <td>{flockData.chick_breed || currentFlock?.chick_breed || "-"}</td>
                        <th>Status</th>
                        <td>{flockData.status || "-"}</td>
                      </tr>
                      <tr>
                        <th>Starting birds</th>
                        <td>{formatNumber(flockData.actual_birds || currentFlock?.actual_birds, 0)}</td>
                        <th>Latest FCR</th>
                        <td>{latestDailyRow ? formatNumber(latestDailyRow.fcr, 2) : String(flockData.fcr || "-")}</td>
                      </tr>
                    </tbody>
                  </Table>
                </div>

                <div className="report-section-card">
                  <div className="report-section-card__header">
                    <h3>Cost breakdown</h3>
                    <span className="report-muted">{filteredPurchases.length} purchase records</span>
                  </div>
                  <Table responsive className="report-table report-table--soft">
                    <thead>
                      <tr>
                        <th>Cost type</th>
                        <th>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {costRows().map(([label, value]) => (
                        <tr key={label}>
                          <td>{label}</td>
                          <td>{value}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td>Total cost</td>
                        <td>{formatCurrency(totalCost)}</td>
                      </tr>
                    </tfoot>
                  </Table>
                </div>

                <div className="report-section-card">
                  <div className="report-section-card__header">
                    <h3>Sales</h3>
                    <span className="report-muted">{filteredSales.length} sale records</span>
                  </div>
                  <Table responsive className="report-table report-table--soft">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Birds</th>
                        <th>Total weight</th>
                        <th>Avg weight</th>
                        <th>Rate/Kg</th>
                        <th>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSales.length ? (
                        filteredSales.map((sale) => (
                          <tr key={sale.public_id || `${sale.date}-${sale.sales_type}`}>
                            <td>{formatDate(sale.date)}</td>
                            <td>{sale.sales_type || "-"}</td>
                            <td>{formatNumber(sale.lifting_count, 0)}</td>
                            <td>{formatNumber(sale.total_weight, 2)}</td>
                            <td>{formatNumber(sale.average_weight, 2)}</td>
                            <td>{formatNumber(sale.rate_per_kg, 2)}</td>
                            <td>{formatCurrency(sale.cost)}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="7">No sales saved for this flock.</td>
                        </tr>
                      )}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td>Total</td>
                        <td></td>
                        <td>{formatNumber(salesTotals.totalBirds, 0)}</td>
                        <td>{formatNumber(salesTotals.totalWeight, 2)}</td>
                        <td>{formatNumber(salesTotals.averageWeight, 2)}</td>
                        <td>{formatNumber(salesTotals.averageRate, 2)}</td>
                        <td>{formatCurrency(salesTotals.totalAmount)}</td>
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

export default FlockSummary;
