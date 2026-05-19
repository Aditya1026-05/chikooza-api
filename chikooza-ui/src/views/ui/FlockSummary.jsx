//MV-23-6-25- 17-10 improved with cost tracking and dynamic sales data
import {
  Row,
  Col,
  Table,
  Card,
  CardTitle,
  CardBody,
  FormGroup,
  Label,
  Input,
  Alert,
} from "reactstrap";
import "../../assets/css/header.css";
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from "axios";
// import '../ui/custom.css'
// U: OLD: import jsPDF from "jspdf";
// U: OLD: import "jspdf-autotable";
// U: NEW: lazy-load the PDF runtime only when the user exports.
import { loadJsPDF } from "../../utils/pdf";
import { useNavigate } from "react-router-dom";

const FlockSummary = () => {
  const [showFlock, setShowFlock] = useState(false);
  const [showForm, setShowForm] = useState(false);
  let [flocks, setFlocks] = useState([]);
  let [farms, setFarms] = useState([]);
  let [currentFlock, setcurrentFlock] = useState({});
  let [flockdata, setFlockData] = useState({});
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  let navigate = useNavigate();

  useEffect(() => {
    let url = `${apiPath}farm/`;
    // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
    // config.headers["Authorization"] = `Bearer ${localStorage.getItem("token")}`;
    axios
      .get(url, getAuthConfig())
      .then((res) => {
        if (res.data.results.length === 0) {
          setFarms([{ public_id: 0, name: "No farm available" }]);
        } else {
          setFarms(res.data.results);
        }
      })
      .catch((err) => {
        setFarms([{ public_id: 0, name: "No farm available" }]);
        handleUnauthorized(err, navigate);
      });
  }, [navigate]);
  let changeFarm = (e) => {
    setShowForm(false);
    setFlockData({});
    if (e.target.value === "0") {
      setShowFlock(false);
      setFlocks([]);
    } else {
      let url = `${apiPath}flocks/${e.target.value}/`;
      // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
      // config.headers["Authorization"] = `Bearer ${localStorage.getItem("token")}`;
      axios
        .get(url, getAuthConfig())
        .then((res) => {
          if (res.data.results.total_records === 0) {
            setFlocks([
              { flock_public_id: 0, flock_name: "No flock available" },
            ]);
          } else {
            //setData({...data,farm:e.target.value,flock:null,seltype:null});
            setFlocks(res.data.results.flock_list);
          }
          setShowFlock(true);
        })
        .catch((err) => {
          //setFormError('No Flock available.');
          handleUnauthorized(err, navigate);
        });
    }
  };
  const getsetFlockData = (flockPublicId) => {
    let url = `${apiPath}flockSummary/${flockPublicId}/`;
    axios
      .get(url, getAuthConfig())
      .then((res) => {
        setFlockData(res.data.results);
      })
      .catch((err) => {
        console.log(err);
        handleUnauthorized(err, navigate);
      });
  };
  let changeFlock = (e) => {
    const flockPublicId = e.target.value;
    if (flockPublicId === "0") {
      setShowForm(false);
      setFlockData({});
    } else {
      const user = flocks.find((u) => String(u.flock_public_id) === flockPublicId);
      if (!user) {
        setShowForm(false);
        setFlockData({});
        return;
      }
      setcurrentFlock(user);
      setShowForm(true);
      // U: Replaced click-time summary fetch with an explicit load after flock selection.
      getsetFlockData(flockPublicId);
    }
  };
  async function downloadPDFWithjsPDF() {
    setIsExportingPdf(true);
    const orientation = "portrait"; // portrait or landscape
    try {
      const jsPDF = await loadJsPDF();
      var doc = new jsPDF(orientation, "pt", "a4");
      await new Promise((resolve) => {
        doc.html(document.querySelector("#flock_summary"), {
          callback: function (doc) {
            doc.save("Flock summary.pdf");
            resolve();
          },
          margin: [0, 0, 0, 0],
          x: 60,
          y: 15,
        });
      });
    } finally {
      setIsExportingPdf(false);
    }
  }
  return (
    <Row>
      <Col>
        <Card className="pb-4">
          <CardTitle
            tag="h6"
            className="border-bottom p-3 mb-0 font_family_sub fs-4"
          >
            Flock Summary
          </CardTitle>
          <CardBody>
            {showForm === true ? (
              <div className="pdf-button">
                <button
                  type="button"
                  onClick={downloadPDFWithjsPDF}
                  disabled={isExportingPdf}
                  className="btn btn-outline-secondary font_family_content "
                >
                  {isExportingPdf ? "Exporting..." : "Export as PDF"}
                </button>
              </div>
            ) : (
              <div></div>
            )}
            <Row className="mt-3">
              <Col sm="12" md={{ offset: 2, size: 8 }}>
                <div className={contentArea}>
                  <div className="gridmargin">
                    <FormGroup>
                      <Label for="farmselect" className="font_family_sub fs-4">
                        Select Farm
                      </Label>
                      <div className="input-group">
                        <Input
                          onChange={changeFarm}
                          id="farmSelect"
                          name="farm"
                          type="select"
                          className="font_family_content "
                          defaultValue="0"
                        >
                          <option
                            value="0"
                            className="font_family_content "
                          >
                            Select Farm
                          </option>
                          {farms.map((item) => {
                            return (
                              <option
                                key={item.public_id}
                                value={item.public_id}
                                className="font_family_content "
                              >
                                {item.name}
                              </option>
                            );
                          })}
                        </Input>
                      </div>
                    </FormGroup>
                    {showFlock && (
                      <FormGroup>
                        <Label
                          for="farmselect"
                          className="font_family_sub fs-4"
                        >
                          Select Flock
                        </Label>
                        <div className="input-group">
                          <Input
                            onChange={changeFlock}
                            id="flockSelect"
                            name="flock"
                            type="select"
                            className="font_family_content "
                            defaultValue="0"
                          >
                            <option
                              value="0"
                              className="font_family_content "
                            >
                              Select Flocks
                            </option>
                            {flocks.map((item) => {
                              return (
                                <option
                                  key={item.flock_public_id}
                                  value={item.flock_public_id}
                                  className="font_family_content "
                                >
                                  {item.flock_name}
                                </option>
                              );
                            })}
                          </Input>
                        </div>
                      </FormGroup>
                    )}
                    {showForm && (
                      <>
                        <div id="flock_summary">
                          <Card>
                            <CardBody>
                              <Alert color="secondary text-center  font_family_heading">
                                Flock Details
                              </Alert>
                              <Table
                                className="no-wrap mt-3 align-middle table-responsive table-bordered "
                                responsive
                                borderless
                              >
                                <tbody>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Flock Name
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.flock_name}
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Status
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.status}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td
                                      className="font_family_sub"
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Flock Size
                                    </td>
                                    <td className=" font_family_content">
                                      {flockdata.flock_size}
                                    </td>
                                    <td
                                      className="font_family_sub"
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Current Count
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.current_bird_count}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Mortality(%)
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.cum_mort}(
                                      {flockdata.total_mortality_percentage})
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Hatch Date
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.hatch_date}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Age(days)
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.age}
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Breed
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.chick_breed}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Feed Intake(Kg)
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.feed_intake}
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Avg. Feed/Bird(gm)
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.average_feed}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Avg. Wt./Bird(gm)
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.average_bird_weight}
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      FCR
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.fcr}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Bal. Feed Stock (Kg)
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.feed_stock}
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    ></td>
                                    <td className="font_family_content"></td>
                                  </tr>
                                </tbody>
                              </Table>
                            </CardBody>
                          </Card>
                          <Card>
                            <CardBody>
                              <Alert color="secondary text-center fs-3  font_family_heading">
                                Cost
                              </Alert>
                              <Table
                                className="no-wrap mt-3 align-middle table-responsive table-bordered "
                                responsive
                                borderless
                              >
                                <tbody>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Total Feed (Kgs)
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.total_feed > 0
                                        ? flockdata.total_feed
                                        : "-"}
                                    </td>
                                    {/* <td className="font_family_sub " style={{ backgroundColor: "rgb(229,229,229)" }}>Status</td>
                                                                        <td className="font_family_content">{flockdata.status}</td> */}
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Feed Cost
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.total_feed_cost > 0
                                        ? flockdata.total_feed_cost
                                        : "-"}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Flock Cost
                                    </td>
                                    <td className="font_family_content">
                                      {currentFlock.chick_cost > 0
                                        ? currentFlock.chick_cost
                                        : "-"}
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Vaccine
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.vaccine > 0
                                        ? flockdata.vaccine
                                        : "-"}
                                    </td>
                                  </tr>
                                  <tr></tr>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Labor
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.labour > 0
                                        ? flockdata.labour
                                        : "-"}
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Medicine
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.medicine > 0
                                        ? flockdata.medicine
                                        : "-"}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Equipment
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.equipment > 0
                                        ? flockdata.equipment
                                        : "-"}
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Other
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.other > 0
                                        ? flockdata.other
                                        : "-"}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Total Cost
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.total_cost > 0 ? (
                                        <strong>{flockdata.total_cost}</strong>
                                      ) : (
                                        "-"
                                      )}
                                    </td>
                                  </tr>
                                </tbody>
                              </Table>
                            </CardBody>
                          </Card>
                          <Card>
                            <CardBody>
                              <Alert color="secondary text-center fs-3  font_family_heading">
                                Sale
                              </Alert>
                              {flockdata.sales_data?.map((sale, index) => (
                                <Table
                                  key={sale.public_id || `${sale.date}-${index}`}
                                  className="no-wrap mt-3 align-middle table-responsive table-bordered sales-table"
                                  responsive
                                  borderless
                                >
                                  <tbody>
                                    <tr>
                                      <td
                                        className="font_family_sub "
                                        style={{
                                          backgroundColor: "rgb(229,229,229)",
                                        }}
                                      >
                                        Birds Lifted
                                      </td>
                                      <td className="font_family_content">
                                        {sale.lifting_count > 0
                                          ? sale.lifting_count
                                          : "-"}
                                      </td>
                                      {/* <td className="font_family_sub " style={{ backgroundColor: "rgb(229,229,229)" }}>Status</td>
                                                                        <td className="font_family_content">{flockdata.status}</td> */}
                                      <td
                                        className="font_family_sub "
                                        style={{
                                          backgroundColor: "rgb(229,229,229)",
                                        }}
                                      >
                                        Avg. Wt.
                                      </td>
                                      <td className="font_family_content">
                                        {sale.average_weight > 0
                                          ? sale.average_weight
                                          : "-"}
                                      </td>
                                    </tr>
                                    <tr>
                                      <td
                                        className="font_family_sub "
                                        style={{
                                          backgroundColor: "rgb(229,229,229)",
                                        }}
                                      >
                                        Sale Date
                                      </td>
                                      <td className="font_family_content">
                                        {sale.date}
                                      </td>
                                      <td
                                        className="font_family_sub "
                                        style={{
                                          backgroundColor: "rgb(229,229,229)",
                                        }}
                                      >
                                        Sale Amt.
                                      </td>
                                      <td className="font_family_content">
                                        {sale.cost > 0
                                          ? sale.cost
                                          : "-"}
                                      </td>
                                    </tr>
                                  </tbody>
                                </Table>
                              ))}
                              <Table
                                className="no-wrap mt-3 align-middle table-responsive table-bordered sales-table"
                                responsive
                                borderless
                              >
                                <tbody>
                                  <tr>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Total Sale
                                    </td>
                                    <td className="font_family_content">
                                      <strong>{flockdata.sales_amount}</strong>
                                    </td>
                                    <td
                                      className="font_family_sub "
                                      style={{
                                        backgroundColor: "rgb(229,229,229)",
                                      }}
                                    >
                                      Profit/Loss
                                    </td>
                                    <td className="font_family_content">
                                      {flockdata.sales_amount <= 0 ? (
                                        <strong>-</strong>
                                      ) : (
                                        <strong
                                          className={
                                            flockdata.profit_loss > 0
                                              ? "text-green-600"
                                              : "text-red-600"
                                          }
                                        >
                                          {flockdata.profit_loss}
                                        </strong>
                                      )}
                                    </td>
                                  </tr>
                                </tbody>
                              </Table>
                            </CardBody>
                          </Card>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </Col>
            </Row>
          </CardBody>
        </Card>
      </Col>
    </Row>
  );
};

export default FlockSummary;
//MV-23-6-25- 17-10 change end
