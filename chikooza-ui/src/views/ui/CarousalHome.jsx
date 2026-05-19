import React from 'react';
import '../../assets/css/header.css';
import Carousel from 'react-bootstrap/Carousel';
import Chicken from '../../assets/images/frontimages/Chicken.jpeg'
import Chick from '../../assets/images/frontimages/Chick.jpeg'
import Profit from '../../assets/images/frontimages/Profit.jpeg'
import DeepLearning from '../../assets/images/frontimages/DeepLearning.jpeg'

const CarousalHome = () => {
    return (
        <div>
            <div className="galleria-demo">

                <div className="card shadow-none">
                    <Carousel>
                        <Carousel.Item>
                            <img
                                className="d-block w-100"
                                src={Chicken}
                                style={{ width: "100%" }}
                                alt="First slide"
                            />
                        </Carousel.Item>

                        <Carousel.Item>
                            <img
                                className="d-block w-100"
                                src={Chick}
                                style={{ width: "100%" }}
                                alt="Second slide"
                            />
                        </Carousel.Item>
                        <Carousel.Item>
                            <img
                                className="d-block w-100"
                                src={Profit}
                                style={{ width: "100%" }}
                                alt="Third slide"
                            />
                        </Carousel.Item>

                        <Carousel.Item>
                            <img
                                className="d-block w-100"
                                src={DeepLearning}
                                style={{ width: "100%", height: "57vh" }}
                                alt="Third slide"
                            />
                        </Carousel.Item>
                    </Carousel>
                </div>
            </div>
        </div>
    );
}
export default CarousalHome;