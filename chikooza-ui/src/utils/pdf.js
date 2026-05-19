// U: OLD: report pages imported jspdf and jspdf-autotable at route load time.
// U: NEW: keep the PDF libraries out of normal page chunks until the user exports a report.
export const loadJsPDF = async () => {
  const { default: jsPDF } = await import("jspdf");
  return jsPDF;
};

export const loadAutoTable = async () => {
  const autoTableModule = await import("jspdf-autotable");
  return autoTableModule.default || autoTableModule.autoTable;
};
