
import { Row, Col, Table, Card, CardTitle, CardBody, Form, FormGroup, Label, Input } from "reactstrap";
import '../../assets/css/header.css';
import { contentArea, apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import { useState, useEffect } from "react";
import axios from 'axios';
// import '../ui/custom.css'
import { useNavigate } from "react-router-dom";

const ViewSale = () => {
    const [showFlock, setShowFlock] = useState(false);
    const [showForm, setShowForm] = useState(false);
    let [flocks, setFlocks] = useState([]);
    let [farms, setFarms] = useState([]);
    let [salelist, setSaleList] = useState([]);
    const save = (e) => {
        e.preventDefault();
    }
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
        } else {
            const user = flocks.find(u => String(u.flock_public_id) === flockPublicId);
            if (!user) {
                setShowForm(false);
                setSaleList([]);
                return;
            }
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
                                                    <Input onChange={changeFarm} id="farmSelect" name="farm" type="select" className='font_family_content fs-5' defaultValue="0" >
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
                                                        <Input onChange={changeFlock} id="flockSelect" name="flock" type="select" className='font_family_content fs-5' defaultValue="0">
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
                                                    <Table bordered striped>
                                                        <thead>
                                                            <tr className="text-center">
                                                                <th>Date</th>
                                                                <th>Type</th>
                                                                <th>Count</th>
                                                                <th>Actions</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {
                                                                salelist?.length > 0 &&
                                                                salelist.map((item, index) => {
                                                                    return (
                                                                        <tr className="text-center" key={item.public_id}>
                                                                            <th scope="row">{item.date}</th>
                                                                            <td>{item.sales_type}</td>
                                                                            <td>{item.lifting_count}</td>
                                                                            <td className="text-blue-800 font-bold" onClick={() => navigate('/editsale', { state: { item } })} style={{ cursor: 'pointer' }}>View</td>
                                                                        </tr>
                                                                    )
                                                                })}
                                                        </tbody>
                                                    </Table>
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
