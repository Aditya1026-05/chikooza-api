import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
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
  filterRowsByDate,
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

// U: OLD: this report exported a DOM screenshot and showed only all-time backend totals.
// U: NEW: the screen and PDF use one filtered calculation path for purchases, sales, and daily rows.
const FlockSummary = () => {
  const [farms, setFarms] = useState([]);
  const [flocks, setFlocks] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState("0");
  const [selectedFlockId, setSelectedFlockId] = useState("0");
  const [currentFlock, setCurrentFlock] = useState(null);
  const [flockData, setFlockData] = useState({});
  const [purchaseList, setPurchaseList] = useState([]);
  const [salesList, setSalesList] = useState([]);
  const [dailyDataList, setDailyDataList] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isLoadingFlocks, setIsLoadingFlocks] = useState(false);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [reportError, setReportError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    axios
      .get(`${apiPath}farm/`, getAuthConfig())
      .then((res) => setFarms(res.data.results.length ? res.data.results : []))
      .catch((err) => {
        setFarms([]);
        handleUnauthorized(err, navigate);
      });
  }, [navigate]);

  const filteredPurchases = useMemo(() => {
    return sortByDate(filterRowsByDate(purchaseList, startDate, endDate));
  }, [purchaseList, startDate, endDate]);

  const filteredSales = useMemo(() => {
    return sortByDate(filterRowsByDate(salesList, startDate, endDate));
  }, [salesList, startDate, endDate]);

  const filteredDailyRows = useMemo(() => {
    return sortByDate(filterRowsByDate(dailyDataList, startDate, endDate));
  }, [dailyDataList, startDate, endDate]);

  const purchaseTotals = useMemo(() => {
    return purchaseTypeTotals(filteredPurchases, currentFlock, startDate, endDate);
  }, [filteredPurchases, currentFlock, startDate, endDate]);

  const totalCost = useMemo(() => summarizeCosts(purchaseTotals), [purchaseTotals]);
  const salesTotals = useMemo(() => summarizeSales(filteredSales), [filteredSales]);
  const profitLoss = salesTotals.totalAmount - totalCost;
  const latestDailyRow = filteredDailyRows[filteredDailyRows.length - 1] || null;
  const hasSelectedFlock = selectedFlockId !== "0" && currentFlock;
  const hasAnyDailyData = dailyDataList.length > 0;
  const hasFilteredRows = filteredDailyRows.length || filteredPurchases.length || filteredSales.length;

  const changeFarm = (event) => {
    const farmPublicId = event.target.value;
    setSelectedFarmId(farmPublicId);
    setSelectedFlockId("0");
    setCurrentFlock(null);
    setFlockData({});
    setPurchaseList([]);
    setSalesList([]);
    setDailyDataList([]);
    setFlocks([]);
    setReportError("");

    if (farmPublicId === "0") {
      return;
    }

    setIsLoadingFlocks(true);
    axios
      .get(`${apiPath}flocks/${farmPublicId}/`, getAuthConfig())
      .then((res) => setFlocks(res.data.results.total_records ? res.data.results.flock_list : []))
      .catch((err) => {
        setFlocks([]);
        handleUnauthorized(err, navigate);
      })
      .finally(() => setIsLoadingFlocks(false));
  };

  const changeFlock = (event) => {
    const flockPublicId = event.target.value;
    setSelectedFlockId(flockPublicId);
    setReportError("");

    if (flockPublicId === "0") {
      setCurrentFlock(null);
      setFlockData({});
      setPurchaseList([]);
      setSalesList([]);
      setDailyDataList([]);
      return;
    }

    const nextFlock = flocks.find((item) => String(item.flock_public_id) === flockPublicId);
    setCurrentFlock(nextFlock || null);
    if (nextFlock) {
      loadReportData(nextFlock.flock_public_id);
    }
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

  const resetFilters = () => {
    setStartDate("");
    setEndDate("");
  };

  const dateRangeLabel = () => {
    if (!startDate && !endDate) {
      return "All dates";
    }
    return `${startDate ? formatDate(startDate) : "Start"} to ${endDate ? formatDate(endDate) : "Today"}`;
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
        subtitle: "Filtered flock performance, cost, sales, and profit/loss report.",
        meta: [
          { label: "Farm", value: flockData.farm_name || currentFlock?.farm_name || "-" },
          { label: "Flock", value: flockData.flock_name || currentFlock?.flock_name || "-" },
          { label: "Date range", value: dateRangeLabel() },
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
        styles: { fontSize: 9, cellPadding: 5 },
        headStyles: { fillColor: [65, 16, 13], textColor: [255, 250, 245] },
        alternateRowStyles: { fillColor: [255, 250, 245] },
        margin: { left: 36, right: 36 },
      });

      startY = doc.lastAutoTable.finalY + 18;
      autoTable(doc, {
        startY,
        head: [["Cost type", "Amount"]],
        body: costRows(),
        foot: [["Total cost", formatCurrency(totalCost)]],
        styles: { fontSize: 9, cellPadding: 5 },
        headStyles: { fillColor: [65, 16, 13], textColor: [255, 250, 245] },
        footStyles: { fillColor: [255, 247, 237], textColor: [65, 16, 13], fontStyle: "bold" },
        margin: { left: 36, right: 36 },
      });

      startY = doc.lastAutoTable.finalY + 18;
      autoTable(doc, {
        startY,
        head: [["Date", "Type", "Birds", "Weight", "Avg Wt", "Rate/Kg", "Amount"]],
        body: salesRows().length ? salesRows() : [["No sales in selected range", "", "", "", "", "", ""]],
        foot: [["Total", "", formatNumber(salesTotals.totalBirds, 0), formatNumber(salesTotals.totalWeight, 2), formatNumber(salesTotals.averageWeight, 2), formatNumber(salesTotals.averageRate, 2), formatCurrency(salesTotals.totalAmount)]],
        styles: { fontSize: 8, cellPadding: 4 },
        headStyles: { fillColor: [65, 16, 13], textColor: [255, 250, 245] },
        footStyles: { fillColor: [255, 247, 237], textColor: [65, 16, 13], fontStyle: "bold" },
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
        <Card className="report-page">
          <div className="report-page__header">
            <div>
              <div className="report-page__eyebrow">Performance report</div>
              <h1 className="report-page__title">Flock Summary</h1>
              <p className="report-page__subtitle">
                Review flock performance, purchase cost, sales, and profit/loss for a selected date range.
              </p>
            </div>
          </div>
          <CardBody className="report-page__body">
            <div className="report-filter-grid">
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
              <FormGroup>
                <Label for="summaryStartDate">From date</Label>
                <Input id="summaryStartDate" type="date" value={startDate} max={endDate || todayIso()} onChange={(event) => setStartDate(event.target.value)} />
              </FormGroup>
              <FormGroup>
                <Label for="summaryEndDate">To date</Label>
                <Input id="summaryEndDate" type="date" value={endDate} min={startDate || undefined} max={todayIso()} onChange={(event) => setEndDate(event.target.value)} />
              </FormGroup>
            </div>

            <div className="report-actions">
              <button type="button" className="report-reset-button" onClick={resetFilters}>
                Clear dates
              </button>
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
                <strong>No report records in this date range.</strong>
                Clear the filter or select a range that includes daily data, purchases, or sales.
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
                  <Table responsive className="report-table">
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
                  <Table responsive className="report-table">
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
                  <Table responsive className="report-table">
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
                          <td colSpan="7">No sales recorded in this date range.</td>
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
