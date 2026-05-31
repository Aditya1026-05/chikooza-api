export const todayIso = () => new Date().toISOString().slice(0, 10);

export const toNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

export const formatNumber = (value, decimals = 2) => {
  const parsed = toNumber(value);
  if (Number.isInteger(parsed)) {
    return String(parsed);
  }
  return parsed.toFixed(decimals);
};

export const formatCurrency = (value) => `Rs. ${formatNumber(value, 2)}`;

export const formatDate = (value) => {
  if (!value) {
    return "-";
  }
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

export const filterRowsByDate = (rows, startDate, endDate) => {
  return rows.filter((row) => {
    if (!row?.date) {
      return false;
    }
    if (startDate && row.date < startDate) {
      return false;
    }
    if (endDate && row.date > endDate) {
      return false;
    }
    return true;
  });
};

export const sortByDate = (rows) => {
  return [...rows].sort((first, second) => String(first.date).localeCompare(String(second.date)));
};

export const getAgeInDays = (hatchDate, rowDate) => {
  if (!hatchDate || !rowDate) {
    return "-";
  }
  const hatch = new Date(`${hatchDate}T00:00:00`);
  const current = new Date(`${rowDate}T00:00:00`);
  if (Number.isNaN(hatch.getTime()) || Number.isNaN(current.getTime())) {
    return "-";
  }
  const diff = Math.floor((current - hatch) / (1000 * 60 * 60 * 24));
  return Math.max(diff + 1, 1);
};

export const sanitizeFilePart = (value) => {
  const clean = String(value || "Report")
    .trim()
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return clean || "Report";
};

export const buildReportFilename = (reportName, entityName, generatedDate = todayIso()) => {
  return `Chikooza_${sanitizeFilePart(reportName)}_${sanitizeFilePart(entityName)}_${generatedDate}.pdf`;
};

export const summarizeDailyRows = (rows) => {
  const lastRow = rows[rows.length - 1] || {};
  const totalMortality = rows.reduce((sum, row) => sum + toNumber(row.mortality), 0);
  const totalFeed = rows.reduce((sum, row) => sum + toNumber(row.feed_intake), 0);
  const rowsWithFcr = rows.filter((row) => toNumber(row.fcr) > 0);
  const averageFcr = rowsWithFcr.length
    ? rowsWithFcr.reduce((sum, row) => sum + toNumber(row.fcr), 0) / rowsWithFcr.length
    : 0;

  return {
    recordCount: rows.length,
    totalMortality,
    totalFeed,
    latestBirdCount: toNumber(lastRow.current_bird_count),
    latestFeedStock: toNumber(lastRow.feed_stock),
    averageFcr,
  };
};

export const purchaseTypeTotals = (purchases, flock, startDate, endDate) => {
  const totals = {
    Feed: 0,
    Medicine: 0,
    Vaccination: 0,
    Equipment: 0,
    Labour: 0,
    Other: 0,
    Chick: 0,
  };

  purchases.forEach((purchase) => {
    const type = totals[purchase.type] !== undefined ? purchase.type : "Other";
    totals[type] += toNumber(purchase.cost);
  });

  const includeChickCost =
    !flock?.chick_cost
    || (!startDate && !endDate)
    || (!startDate || flock.hatch_date >= startDate) && (!endDate || flock.hatch_date <= endDate);

  if (includeChickCost) {
    totals.Chick = toNumber(flock?.chick_cost);
  }

  return totals;
};

export const summarizeCosts = (purchaseTotals) => {
  return Object.values(purchaseTotals).reduce((sum, value) => sum + toNumber(value), 0);
};

export const summarizeSales = (sales) => {
  const totalAmount = sales.reduce((sum, sale) => sum + toNumber(sale.cost), 0);
  const totalBirds = sales.reduce((sum, sale) => sum + toNumber(sale.lifting_count), 0);
  const totalWeight = sales.reduce((sum, sale) => sum + toNumber(sale.total_weight), 0);

  return {
    totalAmount,
    totalBirds,
    totalWeight,
    averageWeight: totalBirds > 0 ? totalWeight / totalBirds : 0,
    averageRate: totalWeight > 0 ? totalAmount / totalWeight : 0,
  };
};
