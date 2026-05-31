
import { Row, Col, Table, Card, CardTitle, CardBody, Button, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
// import '../ui/custom.css'
import { useLocation, useNavigate } from "react-router-dom";

const ViewSale = () => {
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
                // U: NEW: preserve the selected farm/flock when opening sales
                // U: management from the sale-entry review block.
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
                        axios.get(`${apiPath}sales/?flock_public_id=${prefillFlockId}`, getAuthConfig()).then((saleRes) => {
                            setSaleList(saleRes.data.results.sales_list || []);
                            setShowForm(true);
                        }).catch((err) => {
                            setSaleList([]);
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
        setSaleList([]);
        setShowForm(false);
        if (e.target.value === "0") {
            setShowFlock(false)
            setFlocks([]);
        } else {
            let url = `${apiPath}flocks/${e.target.value}/`;
            // U: Replaced shared config mutation with per-request auth headers from getAuthConfig().
            // config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
            axios.get(url, getAuthConfig()).then((res) => {
                if (res.data.results.total_records === 0) {
                    setFlocks([{ flock_public_id: 0, flock_name: 'No flock available' }]);
                } else {
                    //setData({...data,farm:e.target.value,flock:null,seltype:null});
                    setFlocks(res.data.results.flock_list);
                }
                setShowFlock(true)
            }).catch((err) => {
                //setFormError('No Flock available.');
                handleUnauthorized(err, navigate);
            });
        }
    }
    const getSalesList = (flockPublicId) => {
        let url = `${apiPath}sales/?flock_public_id=${flockPublicId}`
        axios.get(url, getAuthConfig())
            .then(res => {
                setSaleList(res.data.results.sales_list)
                // console.log(res.data.results.sales_list)
            }
            ).catch(err => {
                console.log(err)
                handleUnauthorized(err, navigate);
            })
    }
    let changeFlock = (e) => {
        const flockPublicId = e.target.value;
        if (flockPublicId === "0") {
            setShowForm(false)
            setSaleList([]);
            setSelectedFlockId("0");
            setSelectedFlockName("");
        } else {
            const user = flocks.find(u => String(u.flock_public_id) === flockPublicId);
            if (!user) {
                setShowForm(false);
                setSaleList([]);
                setSelectedFlockId("0");
                setSelectedFlockName("");
                return;
            }
            setSelectedFlockId(flockPublicId);
            setSelectedFlockName(user.flock_name || "Selected flock");
            setShowForm(true)
            // U: Replaced render-time API call with an explicit load after flock selection.
            getSalesList(flockPublicId)
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
                                                            <div className="record-review-grid" aria-label="Sale review cards">
                                                                {salelist.map((item) => (
                                                                    <article key={item.public_id}>
                                                                        <div>
                                                                            <span>{saleTypeLabel(item.sales_type)}</span>
                                                                            <strong>Rs. {Number(item.cost || 0).toFixed(2)}</strong>
                                                                            <p>{item.date || "Date not added"}</p>
                                                                        </div>
                                                                        <dl>
                                                                            <div><dt>Birds sold</dt><dd>{item.lifting_count || 0}</dd></div>
                                                                            <div><dt>Total weight</dt><dd>{item.total_weight || 0} kg</dd></div>
                                                                            <div><dt>Rate</dt><dd>Rs. {item.rate_per_kg || 0}/kg</dd></div>
                                                                        </dl>
                                                                        <Button color="danger" outline type="button" onClick={() => navigate('/editsale', { state: { item } })}>Review / edit</Button>
                                                                    </article>
                                                                ))}
                                                            </div>
                                                            <Table bordered striped responsive>
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
                                                                                <td className="text-blue-800 font-bold" onClick={() => navigate('/editsale', { state: { item } })} style={{ cursor: 'pointer' }}>View</td>
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
