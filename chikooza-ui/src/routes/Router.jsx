import { lazy } from "react";


/****Layouts*****/
const FullLayout = lazy(() => import("../layouts/FullLayout.jsx"));
const FullLayoutMember = lazy(() => import("../layouts/FullLayoutMember.jsx"));
const HeaderLayout = lazy(() => import("../layouts/HeaderLayout.jsx"));
const AuthLayout = lazy(() => import("../layouts/AuthLayout.jsx"));


/***** Pages ****/

//Original Pages
const Login = lazy(() => import("../views/ui/Login.jsx"));
// U: OLD unused route-level import caused a build warning; chatbot is mounted inside Home/Chatbot pages.
// const ChikoozaChatbot = lazy(() => import('../components/ChikoozaChatbot/ChikoozaChatbot'));
const Register = lazy(() => import("../views/ui/Register.jsx"));
const Member = lazy(() => import("../views/ui/Member.jsx"));
const AddFlock = lazy(() => import("../views/ui/Addflock.jsx"));
const AddFarm = lazy(() => import("../views/ui/AddFarm.jsx"));
const ManageFarm = lazy(() => import("../views/ui/ManageFarm.jsx"));
const AddPurchase = lazy(() => import("../views/ui/AddPurchase.jsx"));
const ManageFlock = lazy(() => import("../views/ui/ManageFlock.jsx"));
const DailyDataSheet = lazy(() => import("../views/ui/DailyDataSheet.jsx"));
const FlockSummary = lazy(() => import("../views/ui/FlockSummary.jsx"));
const FlockDailyData = lazy(() => import("../views/ui/FlockDailyData.jsx"));
const DayData = lazy(() => import("../views/ui/DayData.jsx"));
const Home = lazy(() => import("../views/ui/Home.jsx"));
const About = lazy(() => import("../views/ui/About.jsx"));
const Contact = lazy(() => import("../views/ui/Contact.jsx"));
const MemberAbout = lazy(() => import("../views/ui/MemberAbout.jsx"));
const MemberContact = lazy(() => import("../views/ui/MemberContact.jsx"));
const Profile = lazy(() => import("../views/ui/Profile.jsx"));
const ChangePassword = lazy(() => import("../views/ui/ChangePassword.jsx"));
const ForgetPassword = lazy(() => import("../views/ui/ForgetPassword.jsx"));
const FlockSale = lazy(() => import("../views/ui/FlockSale.jsx"));
const ViewSale = lazy(() => import("../views/ui/ViewSale.jsx"));
const EditSale = lazy(() => import("../views/ui/EditSale.jsx"));
const ListPurchase = lazy(() => import("../views/ui/ListPurchase.jsx"));
const ViewPurchase = lazy(() => import("../views/ui/ViewPurchase.jsx"));
const UpdateMobile = lazy(() => import("../views/ui/UpdateMobile.jsx"));

// MV-2025-07-05-<1>  STARTS
const Chatbot = lazy(() => import("../views/ui/Chatbot.jsx"));
// MV-2025-07-05-<1>  ENDS

// const ResetPassword = lazy(() => import("../views/ui/ResetPassword.jsx"));
//Original Pages

/*****Routes AddPurchase******/

const ThemeRoutes = [
  {
    path: "/",
    element: <HeaderLayout />,
    children: [
      { path: "/", exact: true, element: <Home /> },
    ],
  }, {
    path: "/",
    element: <AuthLayout />,
    children: [
      // U: NEW: auth screens are standalone pages without public header/footer.
      { path: "/login", exact: true, element: <Login /> },
      { path: "/register", exact: true, element: <Register /> },
    ],
  }, {
    path: "/",
    element: <FullLayout />,
    children: [
      { path: "/about", exact: true, element: <About /> },
      { path: "/contact", exact: true, element: <Contact /> },
      { path: "/forgetpassword", exact: true, element: <ForgetPassword /> },
// MV-2025-07-05-<8>  STARTS
      // U: OLD: /chatbot was also registered under the public layout, so Farmer AI
      // U: could render with the public header. It now lives only in FullLayoutMember.
      // { path: "/chatbot", exact: true, element: <Chatbot /> }
// MV-2025-07-05-<8>  ENDS
    ],
  },
  {
    path: "/",
    element: <FullLayoutMember />,
    children: [
      { path: "/member", exact: true, element: <Member /> },
      { path: "/member/about", exact: true, element: <MemberAbout /> },
      { path: "/member/contact", exact: true, element: <MemberContact /> },
      { path: "/addflock", exact: true, element: <AddFlock /> },
      { path: "/addfarm", exact: true, element: <AddFarm /> },
      { path: "/managefarm", exact: true, element: <ManageFarm /> },
      { path: "/addpurchase", exact: true, element: <AddPurchase /> },
      { path: "/manageflock", exact: true, element: <ManageFlock /> },
      { path: "/flockdailydata", exact: true, element: <FlockDailyData /> },
      { path: "/daydata/:farmid/:flockid/:date", exact: true, element: <DayData></DayData> },
      { path: "/dailydatasheet", exact: true, element: <DailyDataSheet /> },
      { path: "/flocksummary", exact: true, element: <FlockSummary /> },
      { path: "/profile", exact: true, element: <Profile /> },
      { path: "/changepassword", exact: true, element: <ChangePassword /> },
      { path: "/flocksale", exact: true, element: <FlockSale></FlockSale> },
      { path: "/viewsale", exact: true, element: <ViewSale></ViewSale> },
      { path: "/editsale", exact: true, element: <EditSale></EditSale> },
      { path: "/viewpurchase/:flockPublicId/:purchasePublicID", exact: true, element: <ViewPurchase></ViewPurchase> },
      { path: "/listpurchase", exact: true, element: <ListPurchase></ListPurchase> },
      { path: "/updatemobile", exact: true, element: <UpdateMobile /> },

// MV-2025-07-05-<8>  STARTS
      { path: "/chatbot", exact: true, element: <Chatbot /> }
// MV-2025-07-05-<8>  ENDS

    ],
  },
];

export default ThemeRoutes;
