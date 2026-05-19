//MV-23-6-25- 17-10 new values & change in column names
import {
  Row,
  Col,
  Table,
  Card,
  CardTitle,
  CardBody,
  Form,
  FormGroup,
  Label,
  Input,
  CardHeader,
} from "reactstrap";
import "../../assets/css/header.css";
import { contentArea, apiPath, config } from "../../Constants";
import { useState, useEffect } from "react";
import axios from "axios";
// import '../ui/custom.css'
import jsPDF from "jspdf";
import "jspdf-autotable";
import { useNavigate } from "react-router-dom";

const DailyDataSheet = () => {
  const [showFlock, setShowFlock] = useState(false);
  const [showForm, setShowForm] = useState(false);
  let [flocks, setFlocks] = useState([]);
  let [flock, setFlock] = useState([]);
  let [farms, setFarms] = useState([]);
  let [dailydatalist, setDailyDataList] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    let url = `${apiPath}farm/`;
    config.headers["Authorization"] = `Bearer ${localStorage.getItem("token")}`;
    axios
      .get(url, config)
      .then((res) => {
        if (res.data.results.length === 0) {
          setFarms([{ public_id: 0, name: "No farm available" }]);
        } else {
          setFarms(res.data.results);
        }
      })
      .catch((err) => {
        setFarms([{ public_id: 0, name: "No farm available" }]);
        if (err.response.status === 401) {
          localStorage.clear();
          navigate("/login");
        }
      });
  }, []);
  let changeFarm = (e) => {
    if (e.target.value === 0) {
      setShowFlock(false);
      setFlocks([]);
    } else {
      let url = `${apiPath}flocks/${e.target.value}/`;
      config.headers["Authorization"] = `Bearer ${localStorage.getItem(
        "token"
      )}`;
      axios
        .get(url, config)
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
          if (err.response.status === 401) {
            localStorage.clear();
            navigate("/login");
          }
        });
    }
  };
  let changeFlock = (e) => {
    if (e.target.value === 0) {
      setShowForm(false);
    } else {
      const user = flocks.find((u) => u.flock_public_id === e.target.value);
      setShowForm(true);
      setFlock(user);
    }
  };
  const getDailyDataList = () => {
    let url = `${apiPath}dailyDataList/?flock_public_id=${flock.flock_public_id}`;
    const config = {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    };
    axios
      .get(url, config)
      .then((res) => {
        setDailyDataList(res.data.results.daily_data_list);
        console.log(res.data.results.daily_data_list);
      })
      .catch((err) => {
        console.log(err);
        if (err.response.status === 401) {
          localStorage.clear();
          navigate("/login");
        }
      });
  };

  const downloadPdf = () => {
    const unit = "pt";
    const size = "A4"; // Use A1, A2, A3 or A4
    const orientation = "landscape"; // portrait or landscape
    const doc = new jsPDF(orientation, unit, size);
    doc.setFontSize(15);
    const headers = [
      [
        "Date",
        "Age(In Days)",
        "Bird Count",
        "Mort",
        "Cum Mort(%)",
        "Daily Feed Kg(bags)",
        "Feed/Bird(gm)",
        "Cum Feed",
        "Cum Feed/Bird(gm)",
        "Avg Brd Wt",
        "FCR (Adj FCR)",
        "Fd Stk",
        "Remarks",
      ],
    ];
    const data = dailydatalist.map((elt, index) => {
      const currentBirds = parseFloat(elt.current_bird_count);
      const cumFeedPerBird = currentBirds > 0
        ? ((parseFloat(elt.total_feed) * 1000) / currentBirds).toFixed(2)
        : "-";

      return [
        elt.date,
        index + 1,
        elt.current_bird_count,
        elt.mortality,
        `${elt.cum_mort} (${elt.total_mortality_percentage.toFixed(2)}%)`,
        elt.feed_intake,
        elt.average_feed,
        elt.total_feed,
        cumFeedPerBird,
        elt.average_bird_weight <= 0 ? "-" : elt.average_bird_weight,
        elt.average_bird_weight <= 0
          ? "-"
          : `${elt.total_fcr.toFixed(2)} (${elt.fcr.toFixed(2)})`,
        elt.feed_stock,
        elt.remarks,
      ];
    });
    let content = {
      startY: 200,
      head: headers,
      body: data,
    };
    doc.autoTable(content);
    doc.html(document.querySelector("#flock_summary"), {
      callback: function (doc) {
        doc.save("Daily Data Sheet.pdf");
      },
      margin: [0, 0, 0, 0],
      x: 55,
      y: 15,
    });
  };

  return (
    <Row>
      <Col>
        <Card className="pb-4">
          <CardTitle
            tag="h6"
            className="border-bottom p-3 mb-0 font_family_sub fs-4"
          >
            Daily Data Sheet
          </CardTitle>
          <CardBody>
            {showForm === true ? (
              <div className="pdf-button">
                <button
                  type="button"
                  onClick={downloadPdf}
                  className="btn btn-outline-secondary font_family_content fs-5"
                >
                  Export as PDF
                </button>
              </div>
            ) : (
              <div></div>
            )}
            <Row className="mt-3">
              <Col sm="12" md={{ offset: 2, size: 8 }}>
                <div className={contentArea}>
                  <div className="gridmargin">
                    <Form>
                      <FormGroup>
                        <Label
                          for="farmselect"
                          className="font_family_sub fs-4"
                        >
                          Select Farm
                        </Label>
                        <div className="input-group">
                          <Input
                            onChange={changeFarm}
                            id="farmSelect"
                            name="farm"
                            type="select"
                            className="font_family_content fs-5"
                          >
                            <option
                              selected
                              value={0}
                              className="font_family_content fs-5"
                            >
                              Select Farm
                            </option>
                            {farms.map((item) => {
                              return (
                                <option
                                  key={item.public_id}
                                  value={item.public_id}
                                  className="font_family_content fs-5"
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
                              onClick={() => {
                                getDailyDataList();
                              }}
                              id="flockSelect"
                              name="flock"
                              type="select"
                              className="font_family_content fs-5"
                            >
                              <option
                                selected={true}
                                value={0}
                                className="font_family_content fs-5"
                              >
                                Select Flocks
                              </option>
                              {flocks.map((item) => {
                                return (
                                  <option
                                    key={item.flock_public_id}
                                    value={item.flock_public_id}
                                    className="font_family_content fs-5"
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
                          <div>
                            <Card>
                              <CardHeader
                                id="flock_summary"
                                style={{ backgroundColor: "rgb(242,242,242)" }}
                              >
                                <div className="row">
                                  <div className="col-md-5">
                                    <CardTitle
                                      tag="h6"
                                      className="border-bottom p-3 mb-0"
                                    >
                                      <span className="font_family_sub fs-5 ">
                                        {" "}
                                        Flock Name:{" "}
                                      </span>{" "}
                                      <span className="px-1 fs-6 font_family_content">
                                        {" "}
                                        {flock.flock_name}
                                      </span>
                                      <br />
                                      <span className="font_family_sub fs-5">
                                        Hatch Date:{" "}
                                      </span>{" "}
                                      <span className="px-1 fs-6 font_family_content">
                                        {" "}
                                        {flock.hatch_date}
                                      </span>
                                      <br />
                                      <span className="font_family_sub fs-5">
                                        {" "}
                                        Bird Count:{" "}
                                      </span>{" "}
                                      <span className="px-1 fs-6 font_family_content">
                                        {" "}
                                        {flock.actual_birds}
                                      </span>
                                      <br />
                                      <span className="font_family_sub fs-5">
                                        Integration?{" "}
                                      </span>{" "}
                                      <span className="px-1 fs-6 font_family_content">
                                        {" "}
                                        {flock.integration === true
                                          ? "Yes"
                                          : "No"}
                                      </span>
                                      <br />
                                      <span className=" font_family_sub fs-5">
                                        Day 1 Wt (gm){" "}
                                      </span>{" "}
                                      <span className="px-1 fs-6 font_family_content">
                                        {" "}
                                        {flock.chick_weight}
                                      </span>
                                    </CardTitle>
                                  </div>
                                  <div className="col-md-2"></div>
                                  <div className="col-md-5">
                                    <CardTitle
                                      tag="h6"
                                      className="border-bottom p-3 mb-0"
                                    >
                                      <span className=" font_family_sub fs-5">
                                        Farm Name:{" "}
                                      </span>{" "}
                                      <span className="px-1 fs-6 font_family_content">
                                        {" "}
                                        {flock.farm_name}
                                      </span>
                                      <br />
                                      <span className=" font_family_sub fs-5">
                                        Address:{" "}
                                      </span>
                                      <span className="px-1 fs-6 font_family_content">
                                        {" "}
                                        {flock.address}
                                      </span>
                                      <br />
                                      <span className=" font_family_sub fs-5">
                                        {" "}
                                        Phone:{" "}
                                      </span>{" "}
                                      <span className="px-1 fs-6 font_family_content">
                                        {" "}
                                        {flock.mobile_number}
                                      </span>
                                      <br />
                                      <span className=" font_family_sub fs-5">
                                        EC Shed?{" "}
                                      </span>{" "}
                                      <span className="px-1 fs-6 font_family_content">
                                        {" "}
                                        {flock.ec_shed === true ? "Yes" : "No"}
                                      </span>
                                    </CardTitle>
                                  </div>
                                </div>
                              </CardHeader>
                              <CardBody>
                                <Table
                                  className="no-wrap mt-3 align-middle table-responsive table-bordered table-striped"
                                  responsive
                                  borderless
                                >
                                  <thead>
                                    <tr>
                                      <th className=" font_family_sub fs-6">
                                        Date
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Age(In Days)
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Bird Count
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Mort
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Cum Mort (%)
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Daily Feed Kg(bags)
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Feed/Bird(gm)
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Cum Feed
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Cum Feed/Bird(gm)
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Avg Brd Wt
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        FCR
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Fd Stk
                                      </th>
                                      <th className=" font_family_sub fs-6">
                                        Remarks
                                      </th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {dailydatalist?.length > 0 &&
                                      dailydatalist.map((item, index) => {
                                        const currentBirds = parseFloat(
                                          item.current_bird_count
                                        );
                                        const initialBirds =
                                          parseFloat(flock?.actual_birds) || 1; // Fallback to 1 to avoid division by zero
                                        const cumFeedPerBird =
                                          currentBirds > 0
                                            ? (
                                                (parseFloat(item.total_feed) *
                                                  1000) /
                                                currentBirds
                                              ).toFixed(2)
                                            : "-";

                                        return (
                                          <tr key={item.flock_public_id}>
                                            <td className="fs-6 font_family_content">
                                              {item.date}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {index + 1}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.current_bird_count}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.mortality}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.cum_mort} (
                                              {item.total_mortality_percentage.toFixed(
                                                2
                                              )}
                                              %)
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.feed_intake}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.average_feed}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.total_feed}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {cumFeedPerBird}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.average_bird_weight <= 0
                                                ? "-"
                                                : item.average_bird_weight}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.average_bird_weight <= 0
                                                ? "-"
                                                : `${item.fcr.toFixed(2)}`}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.feed_stock}
                                            </td>
                                            <td className="fs-6 font_family_content">
                                              {item.remarks}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                  </tbody>
                                </Table>
                              </CardBody>
                            </Card>
                          </div>
                        </>
                      )}
                    </Form>
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

export default DailyDataSheet;
//MV-23-6-25- 17-10 change end