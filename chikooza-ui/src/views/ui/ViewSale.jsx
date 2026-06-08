
import { Row, Col, Table, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
// import '../ui/custom.css'
import { useLocation, useNavigate } from "react-router-dom";
import {
    readInitialWorkspace,
    resolveWorkspaceFarm,
    resolveWorkspaceFlock,
    writeCurrentWorkspace,
} from "../../utils/currentWorkspace";

const ViewSale = () => {
    const [activeWorkspace] = useState(() => readInitialWorkspace());
    const [showFlock, setShowFlock] = useState(false);
    const [showForm, setShowForm] = useState(false);
    let [flocks, setFlocks] = useState([]);
    let [farms, setFarms] = useState([]);
    let [salelist, setSaleList] = useState([]);
    const [selectedFarmId, setSelectedFarmId] = useState("0");
    const [selectedFlockId, setSelectedFlockId] = useState("0");
    const [selectedFlockName, setSelectedFlockName] = useState("");
    const saleTotal = salelist.reduce((total, item) => total + Number(item.cost || 0), 0);
    const saleTypeLabel = (value) => value === "final_lifting" ? "Final lifting" : value === "partial_lifting" ? "Partial lifting" : (value || "Sale");
    const save = (e) => {
        e.preventDefault();
    }
    let navigate = useNavigate()
    const location = useLocation();
    const prefillFarmId = String(location.state?.farmPublicId || "0");
    const prefillFlockId = String(location.state?.flockPublicId || "0");

    function getSalesList(flockPublicId) {
        let url = `${apiPath}sales/?flock_public_id=${flockPublicId}`
        axios.get(url, getAuthConfig())
            .then(res => {
                setSaleList(res.data.results.sales_list || [])
            }
            ).catch(err => {
                console.log(err)
                setSaleList([]);
                handleUnauthorized(err, navigate);
            })
    }

    function selectFlockForSales(selectedFlock, { persistCurrent = false, source = "view_sale_manual_flock" } = {}) {
        if (!selectedFlock || String(selectedFlock.flock_public_id) === "0") {
            setShowForm(false);
            setSaleList([]);
            setSelectedFlockId("0");
            setSelectedFlockName("");
            if (persistCurrent) {
                writeCurrentWorkspace({ farmPublicId: selectedFarmId, flockPublicId: "0", source });
            }
            return;
        }

        const farmId = String(selectedFlock.farm_public_id || selectedFarmId);
        const flockId = String(selectedFlock.flock_public_id);
        setSelectedFarmId(farmId);
        setSelectedFlockId(flockId);
        setSelectedFlockName(selectedFlock.flock_name || "Selected flock");
        if (persistCurrent) {
            writeCurrentWorkspace({ farmPublicId: farmId, flockPublicId: flockId, source });
        }
        setShowForm(true);
        getSalesList(selectedFlock.flock_public_id);
    }

    function loadFlocksForFarm(farmId, preferredFlockId = "0", { persistCurrent = false, source = "view_sale_manual_farm" } = {}) {
        if (!farmId || String(farmId) === "0") {
            setShowFlock(false);
            setShowForm(false);
            setFlocks([]);
            setSaleList([]);
            setSelectedFlockId("0");
            setSelectedFlockName("");
            if (persistCurrent) {
                writeCurrentWorkspace({ farmPublicId: "0", flockPublicId: "0", source });
            }
            return;
        }

        setSelectedFarmId(String(farmId));
        axios.get(`${apiPath}flocks/${farmId}/`, getAuthConfig()).then((flockRes) => {
            setShowFlock(true);
            if (flockRes.data.results.total_records === 0) {
                setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                setShowForm(false);
                setSaleList([]);
                setSelectedFlockId("0");
                setSelectedFlockName("");
                if (persistCurrent) {
                    writeCurrentWorkspace({ farmPublicId: farmId, flockPublicId: "0", source });
                }
                return;
            }

            const flockList = flockRes.data.results.flock_list || [];
            const selected = resolveWorkspaceFlock(flockList, preferredFlockId);
            setFlocks(flockList);
            selectFlockForSales(selected, { persistCurrent, source });
        }).catch((err) => {
            setFlocks([]);
            setShowFlock(false);
            setShowForm(false);
            setSaleList([]);
            handleUnauthorized(err, navigate);
        });
    }

    useEffect(() => {
        let url = `${apiPath}farm/`;
        // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
        // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        axios.get(url, getAuthConfig()).then((res) => {
            if (res.data.results.length === 0) {
                setFarms([{ public_id: 0, name: 'No farm available' }]);
            } else {
                const farmList = res.data.results;
                setFarms(farmList);
                const requestedFarmId = prefillFarmId !== "0" ? prefillFarmId : activeWorkspace.farmPublicId;
                const selectedFarm = resolveWorkspaceFarm(farmList, requestedFarmId);
                const targetFlockId = prefillFlockId !== "0" ? prefillFlockId : activeWorkspace.flockPublicId;
                if (selectedFarm) {
                    loadFlocksForFarm(selectedFarm.public_id, targetFlockId);
                }
            }
        }).catch((err) => {
            setFarms([{ public_id: 0, name: 'No farm available' }]);
            handleUnauthorized(err, navigate);
        });
    }, [activeWorkspace.farmPublicId, activeWorkspace.flockPublicId, navigate, prefillFarmId, prefillFlockId])
    let changeFarm = (e) => {
        setSelectedFarmId(e.target.value);
        setSelectedFlockId("0");
        setSelectedFlockName("");
        setSaleList([]);
        setShowForm(false);
        if (e.target.value === "0") {
            setShowFlock(false)
            setFlocks([]);
            writeCurrentWorkspace({ farmPublicId: "0", flockPublicId: "0", source: "view_sale_manual_farm" });
        } else {
            loadFlocksForFarm(e.target.value, "0", { persistCurrent: true, source: "view_sale_manual_farm" });
        }
    }
    let changeFlock = (e) => {
        const flockPublicId = e.target.value;
        if (flockPublicId === "0") {
            setShowForm(false)
            setSaleList([]);
            setSelectedFlockId("0");
            setSelectedFlockName("");
            writeCurrentWorkspace({ farmPublicId: selectedFarmId, flockPublicId: "0", source: "view_sale_manual_flock" });
        } else {
            const user = flocks.find(u => String(u.flock_public_id) === flockPublicId);
            if (!user) {
                setShowForm(false);
                setSaleList([]);
                setSelectedFlockId("0");
                setSelectedFlockName("");
                return;
            }
            selectFlockForSales(user, { persistCurrent: true, source: "view_sale_manual_flock" });
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
                        View/Sales

                    </CardTitle>
                    <CardBody>
                        <Row className="mt-3">
                            <Col sm="12" md={{ offset: 2, size: 8 }}>
                                <div className={contentArea}>
                                    <div className='gridmargin'>
                                        <Form onSubmit={save}>
                                            <FormGroup>
                                                <Label for="farmselect" className="font_family_sub fs-4">Select Farm</Label>
                                                <div className="input-group">
                                                    <Input onChange={changeFarm} id="farmSelect" name="farm" type="select" className='font_family_content fs-5' value={selectedFarmId} >
                                                        <option value="0" className='font_family_content fs-5'>Select Farm</option>
                                                        {
                                                            farms.map((item) => {
                                                                return (
                                                                    <option key={item.public_id} value={item.public_id} className='font_family_content fs-5' >{item.name}</option>
                                                                )
                                                            })
                                                        }
                                                    </Input>
                                                </div>
                                            </FormGroup>
                                            {
                                                showFlock &&
                                                <FormGroup>
                                                    <Label for="farmselect" className="font_family_sub fs-4">Select Flock</Label>
                                                    <div className="input-group">
                                                        <Input onChange={changeFlock} id="flockSelect" name="flock" type="select" className='font_family_content fs-5' value={selectedFlockId}>
                                                            <option value="0" className='font_family_content fs-5'>Select Flocks</option>
                                                            {
                                                                flocks.map((item) => {
                                                                    return (
                                                                        <option key={item.flock_public_id} value={item.flock_public_id} className='font_family_content fs-5'>{item.flock_name}</option>
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
                                                            <span>Manage sales</span>
                                                            <strong>{selectedFlockName}</strong>
                                                            <p>{salelist.length} sale{salelist.length === 1 ? "" : "s"} saved, Rs. {saleTotal.toFixed(2)} total revenue.</p>
                                                        </div>
                                                        <Button color="danger" type="button" onClick={() => navigate("/flocksale", { state: { farmPublicId: selectedFarmId, flockPublicId: selectedFlockId } })}>Add sale</Button>
                                                    </div>
                                                    {salelist.length > 0 ? (
                                                        <>
                                                            <Table bordered striped responsive className="sales-review-table">
                                                                <thead>
                                                                    <tr className="text-center">
                                                                        <th>Date</th>
                                                                        <th>Type</th>
                                                                        <th>Count</th>
                                                                        <th>Actions</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {salelist.map((item) => {
                                                                        return (
                                                                            <tr className="text-center" key={item.public_id}>
                                                                                <th scope="row">{item.date}</th>
                                                                                <td>{saleTypeLabel(item.sales_type)}</td>
                                                                                <td>{item.lifting_count}</td>
                                                                                <td className="sales-review-table__action">
                                                                                    <Button className="table-action-button table-action-button--compact" color="danger" outline size="sm" type="button" onClick={() => navigate('/editsale', { state: { item, farmPublicId: selectedFarmId, flockPublicId: selectedFlockId } })}>
                                                                                        View
                                                                                    </Button>
                                                                                </td>
                                                                            </tr>
                                                                        )
                                                                    })}
                                                                </tbody>
                                                            </Table>
                                                        </>
                                                    ) : (
                                                        <div className="record-review-empty">
                                                            <strong>No sales saved for this flock yet.</strong>
                                                            <p>Add partial or final lifting when birds are sold so reports and Farmer AI can calculate revenue and profit.</p>
                                                            <Button color="danger" type="button" onClick={() => navigate("/flocksale", { state: { farmPublicId: selectedFarmId, flockPublicId: selectedFlockId } })}>Add first sale</Button>
                                                        </div>
                                                    )}
                                                </>
                                            }
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

export default ViewSale;
