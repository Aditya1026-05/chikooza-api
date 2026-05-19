import { lazy, Suspense } from "react";

// U: OLD: Screens imported react-apexcharts directly, forcing the large chart runtime into route chunks.
// import Chart from "react-apexcharts";
// U: NEW: Lazy-load the chart runtime so dashboard routes stay smaller after the ApexCharts upgrade.
const Chart = lazy(() => import("react-apexcharts"));

const ApexChart = (props) => (
  <Suspense
    fallback={
      <div className="d-flex align-items-center justify-content-center text-muted py-5">
        Loading chart...
      </div>
    }
  >
    <Chart {...props} />
  </Suspense>
);

export default ApexChart;
