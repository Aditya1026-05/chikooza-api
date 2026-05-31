import { Row, Col, Table, Card, CardTitle, CardBody, Button, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
// U: OLD: import jsPDF from "jspdf";
// U: OLD: import 'jspdf-autotable'
// U: NEW: lazy-load the PDF runtime only when the user exports.
import { loadAutoTable, loadJsPDF } from "../../utils/pdf";
import { Link, useLocation, useNavigate } from "react-router-dom";


const ListPurchase = () => {
    let [farms, setFarms] = useState([]);
    let [flocks, setFlocks] = useState([]);
    const [showFlock, setShowFlock] = useState(false);
    const [showForm, setShowForm] = useState(false);
    let [purchaseList, setPurchaseList] = useState([]);
    const [selectedFarmId, setSelectedFarmId] = useState("0");
    const [selectedFlockId, setSelectedFlockId] = useState("0");
    const [selectedFlockName, setSelectedFlockName] = useState("");
    const [isExportingPdf, setIsExportingPdf] = useState(false);
    let navigate = useNavigate()
    const location = useLocation();
    const prefillFarmId = String(location.state?.farmPublicId || "0");
    const prefillFlockId = String(location.state?.flockPublicId || "0");
    const purchaseTotal = purchaseList.reduce((total, item) => total + Number(item.cost || 0), 0);

    useEffect(() => {
        let url = `${apiPath}farm/`;
        // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
        // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, getAuthConfig()).then((res) => {
            if (res.data.results.length === 0) {
                setFarms([{ public_id: 0, name: 'No farm available' }]);
            } else {
                setFarms(res.data.results);
            }

            if (prefillFarmId !== "0") {
                // U: NEW: when the farmer comes from add-purchase review,
                // U: keep the same farm/flock selected on the manage screen.
                setSelectedFarmId(prefillFarmId);
                axios.get(`${apiPath}flocks/${prefillFarmId}/`, getAuthConfig()).then((flockRes) => {
                    setShowFlock(true);
                    if (flockRes.data.results.total_records === 0) {
                        setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                        return;
                    }
                    const flockList = flockRes.data.results.flock_list || [];
                    setFlocks(flockList);
                    const selected = flockList.find((item) => String(item.flock_public_id) === prefillFlockId);
                    if (selected) {
                        setSelectedFlockId(prefillFlockId);
                        setSelectedFlockName(selected.flock_name || "Selected flock");
                        axios.get(`${apiPath}purchase/?flock_public_id=${prefillFlockId}`, getAuthConfig()).then((purchaseRes) => {
                            setPurchaseList(purchaseRes.data.results.purchase_list || []);
                            setShowForm(true);
                        }).catch((err) => {
                            setPurchaseList([]);
                            handleUnauthorized(err, navigate);
                        });
                    }
                }).catch((err) => {
                    handleUnauthorized(err, navigate);
                });
            }
        }).catch((err) => {
            setFarms([{ public_id: 0, name: 'No farm available' }]);
            handleUnauthorized(err, navigate);
        });
    }, [navigate, prefillFarmId, prefillFlockId])

    let changeFarm = (e) => {
        setSelectedFarmId(e.target.value);
        setSelectedFlockId("0");
        setSelectedFlockName("");
        setPurchaseList([]);
        setShowForm(false);
        if (e.target.value === "0") {
            //setFarm_public_iderr('Please select farm');
            setShowFlock(false);
            setFlocks([]);
        } else {
            let url = `${apiPath}flocks/${e.target.value}/`;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, getAuthConfig()).then((res) => {
                setShowFlock(true);
                if (res.data.results.total_records === 0) {
                    setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                } else {
                    setFlocks(res.data.results.flock_list);
                }
                setShowForm(false);
            }).catch((err) => {
                // U: Avoid reading err.data.results because Axios errors expose response data under err.response.
                setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                handleUnauthorized(err, navigate);
            });
        }
    }
    let changeFlocks = (e) => {
        setSelectedFlockId(e.target.value);
        if (e.target.value === "0") {
            setShowForm(false);
            setPurchaseList([]);
            setSelectedFlockName("");
        } else {
            const selected = flocks.find((item) => String(item.flock_public_id) === e.target.value);
            setSelectedFlockName(selected?.flock_name || "Selected flock");
            let url = `${apiPath}purchase/?flock_public_id=${e.target.value}`;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, getAuthConfig()).then((res) => {
                setPurchaseList(res.data.results.purchase_list);
                setShowForm(true);
            }).catch((err) => {
                setShowForm(false);
                setPurchaseList([]);
                handleUnauthorized(err, navigate);
            });
        }
    }
    let getformateddate = (tdate) => {
        let dt = new Date(tdate);
        let day = dt.getDate();
        if (day === 1 || day === 21 || day === 31) {
            day = `${day}st`;
        } else if (day === 2 || day === 22) {
            day = `${day}nd`;
        } else if (day === 3 || day === 23) {
            day = `${day}rd`;
        } else {
            day = `${day}th`;
        }
        return `${day} ${dt.toLocaleString('en-us', { month: 'short' })} ${dt.getFullYear().toString().substr(-2)}`;
    }
    const downloadPdf = async () => {
        setIsExportingPdf(true);
        const unit = "pt";
        const size = "A4"; // Use A1, A2, A3 or A4
        const orientation = "landscape"; // portrait or landscape
        try {
            const [jsPDF, autoTable] = await Promise.all([
                loadJsPDF(),
                loadAutoTable(),
            ]);
            const doc = new jsPDF(orientation, unit, size);
            doc.setFontSize(15);
            const headers = [["Date", "Type", "Company Name", 'Item Name', 'Amount(Rs)', 'Quantity', 'Remarks']];
            const data = purchaseList.map((elt) => [
                elt.date,
                elt.type,
                elt.company_name,
                elt.item_name,
                elt.cost,
                elt.quantity,
                elt.remarks,
            ]);
            let content = {
                startY: 50,
                head: headers,
                body: data
            };
            autoTable(doc, content);
            doc.save('Purchase List.pdf');
        } finally {
            setIsExportingPdf(false);
        }
    }
    return (
        <Row>
            <Col>
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-1*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card className="pb-4">
                    <CardTitle tag="h6" className="border-bottom p-3 mb-0">
                        View/purchase
                    </CardTitle>
                    <CardBody>
                        <Row className="mt-3">
                            <Col sm="12" md={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        <FormGroup>
                                            <div className="input-group">
                                                <Input onChange={changeFarm} value={selectedFarmId} id="farmSelect" name="farm" type="select">
                                                    <option value="0">Select Farm</option>
                                                    {
                                                        farms.map((item) => {
                                                            return (
                                                                <option key={item.public_id} value={item.public_id}>{item.name}</option>
                                                            )
                                                        })
                                                    }
                                                </Input>
                                            </div>
                                        </FormGroup>
                                        {
                                            showFlock &&
                                            <FormGroup>
                                                <Label for="farmselect">Select Flocks</Label>
                                                <div className="input-group">
                                                    <Input onChange={changeFlocks} id="farmSelect" name="flock" type="select" value={selectedFlockId}>
                                                        <option value="0">Select Flocks</option>
                                                        {
                                                            flocks.map((item) => {
                                                                return (
                                                                    <option key={item.flock_public_id} value={item.flock_public_id}>{item.flock_name}</option>
                                                                )
                                                            })
                                                        }
                                                    </Input>
                                                </div>
                                            </FormGroup>
                                        }
                                        {
                                            showForm &&
                                            <>
                                                <div className="record-review-toolbar">
                                                    <div>
                                                        <span>Manage purchases</span>
                                                        <strong>{selectedFlockName}</strong>
                                                        <p>{purchaseList.length} purchase{purchaseList.length === 1 ? "" : "s"} saved, Rs. {purchaseTotal.toFixed(2)} total cost.</p>
                                                    </div>
                                                    <div className="record-review-actions">
                                                        <Button color="danger" type="button" onClick={() => navigate("/addpurchase", { state: { farmPublicId: selectedFarmId, flockPublicId: selectedFlockId } })}>Add purchase</Button>
                                                        <Button type="button" color="danger" outline onClick={downloadPdf} disabled={isExportingPdf || purchaseList.length === 0}>
                                                            {isExportingPdf ? "Exporting..." : "Export"}
                                                        </Button>
                                                    </div>
                                                </div>
                                                {purchaseList.length > 0 ? (
                                                    <>
                                                        <div className="record-review-grid" aria-label="Purchase review cards">
                                                            {purchaseList.map((item) => (
                                                                <article key={item.public_id}>
                                                                    <div>
                                                                        <span>{item.type || "Purchase"}</span>
                                                                        <strong>Rs. {Number(item.cost || 0).toFixed(2)}</strong>
                                                                        <p>{item.date ? getformateddate(item.date) : "Date not added"}</p>
                                                                    </div>
                                                                    <dl>
                                                                        <div><dt>Item</dt><dd>{item.item_name || item.company_name || "Not added"}</dd></div>
                                                                        <div><dt>Quantity</dt><dd>{item.quantity || item.unit || "Not added"}</dd></div>
                                                                        <div><dt>Remarks</dt><dd>{item.remarks || "Not added"}</dd></div>
                                                                    </dl>
                                                                    <Button tag={Link} to={`/viewpurchase/${item.flock_public_id}/${item.public_id}`} color="danger" outline type="button">Review</Button>
                                                                </article>
                                                            ))}
                                                        </div>
                                                        <Table bordered striped responsive>
                                                            <thead>
                                                                <tr className="text-center">
                                                                    <th>Date</th>
                                                                    <th>Type</th>
                                                                    <th>Amount(Rs)</th>
                                                                    <th>Actions</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {purchaseList.map((item) => {
                                                                    return (
                                                                        <tr key={item.public_id} className="text-center">
                                                                            <td>{getformateddate(item.date)}</td>
                                                                            <td>{item.type}</td>
                                                                            <td>{item.cost}</td>
                                                                            <td className="text-blue-800 font-bold">
                                                                                <Link to={`/viewpurchase/${item.flock_public_id}/${item.public_id}`} style={{ textDecoration: "none" }}>View</Link></td>
                                                                        </tr>
                                                                    )
                                                                })}
                                                            </tbody>
                                                        </Table>
                                                    </>
                                                ) : (
                                                    <div className="record-review-empty">
                                                        <strong>No purchases saved for this flock yet.</strong>
                                                        <p>Add feed, medicine, vaccination, equipment, labour, or other costs so reports and Farmer AI can calculate expenses.</p>
                                                        <Button color="danger" type="button" onClick={() => navigate("/addpurchase", { state: { farmPublicId: selectedFarmId, flockPublicId: selectedFlockId } })}>Add first purchase</Button>
                                                    </div>
                                                )}
                                            </>
                                        }
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
export default ListPurchase;
