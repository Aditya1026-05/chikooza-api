import { Row, Col, Table, Card, CardTitle, CardBody, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";
// U: OLD: import jsPDF from "jspdf";
// U: OLD: import 'jspdf-autotable'
// U: NEW: lazy-load the PDF runtime only when the user exports.
import { loadAutoTable, loadJsPDF } from "../../utils/pdf";
import { useNavigate } from "react-router-dom";


const ListPurchase = () => {
    let [farms, setFarms] = useState([]);
    let [flocks, setFlocks] = useState([]);
    const [showFlock, setShowFlock] = useState(false);
    const [showForm, setShowForm] = useState(false);
    let [purchaseList, setPurchaseList] = useState([]);
    const [isExportingPdf, setIsExportingPdf] = useState(false);
    let navigate = useNavigate()

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
        }).catch((err) => {
            setFarms([{ public_id: 0, name: 'No farm available' }]);
            handleUnauthorized(err, navigate);
        });
    }, [navigate])

    let changeFarm = (e) => {
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
        if (e.target.value === "0") {
            setShowForm(false);
            setPurchaseList([]);
        } else {
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
                                                <Input onChange={changeFarm} defaultValue="0" id="farmSelect" name="farm" type="select">
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
                                                    <Input onChange={changeFlocks} id="farmSelect" name="flock" type="select" defaultValue="0">
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
                                                <button type="button" onClick={downloadPdf} disabled={isExportingPdf} className="btn-danger font_family_content mb-2 fs-5">
                                                    {isExportingPdf ? "Exporting..." : "Export"}
                                                </button>
                                                <Table bordered striped>
                                                    <thead>
                                                        <tr className="text-center">
                                                            <th>Date</th>
                                                            <th>Type</th>
                                                            <th>Amount(Rs)</th>
                                                            <th>Actions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {
                                                            purchaseList.length > 0 ?
                                                                purchaseList.map((item) => {
                                                                    return (
                                                                        <tr key={item.public_id} className="text-center">
                                                                            <td>{getformateddate(item.date)}</td>
                                                                            <td>{item.type}</td>
                                                                            <td>{item.cost}</td>
                                                                            <td className="text-blue-800 font-bold">
                                                                                <Link to={`/viewpurchase/${item.flock_public_id}/${item.public_id}`} style={{ textDecoration: "none" }}>View</Link></td>
                                                                        </tr>
                                                                    )
                                                                }) :
                                                                <tr className="text-center">
                                                                    <td colSpan={4}>No purchase found</td>
                                                                </tr>
                                                        }
                                                    </tbody>
                                                </Table>
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
