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

export const addPdfReportHeader = (doc, { title, subtitle, meta = [] }) => {
  const pageWidth = doc.internal.pageSize.getWidth();

  doc.setFillColor(127, 29, 29);
  doc.rect(0, 0, pageWidth, 82, "F");

  doc.setTextColor(255, 250, 245);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text(title, 36, 34);

  if (subtitle) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.text(subtitle, 36, 54, { maxWidth: pageWidth - 72 });
  }

  const cardTop = 100;
  const cardWidth = (pageWidth - 72) / Math.max(meta.length || 1, 1);
  meta.forEach((item, index) => {
    const x = 36 + index * cardWidth;
    doc.setDrawColor(229, 214, 205);
    doc.setFillColor(255, 250, 245);
    doc.roundedRect(x, cardTop, cardWidth - 10, 42, 8, 8, "FD");
    doc.setTextColor(138, 111, 104);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.text(String(item.label || "").toUpperCase(), x + 10, cardTop + 15);
    doc.setTextColor(36, 21, 20);
    doc.setFontSize(10);
    doc.text(String(item.value || "-"), x + 10, cardTop + 31, {
      maxWidth: cardWidth - 30,
    });
  });

  return cardTop + 62;
};

export const addPdfFooter = (doc) => {
  const pageCount = doc.getNumberOfPages();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  for (let page = 1; page <= pageCount; page += 1) {
    doc.setPage(page);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(138, 111, 104);
    doc.text(`Chikooza report | Page ${page} of ${pageCount}`, pageWidth / 2, pageHeight - 18, {
      align: "center",
    });
  }
};
