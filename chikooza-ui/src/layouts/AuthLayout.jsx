import { Outlet } from "react-router-dom";

const AuthLayout = () => {
  return (
    <div className="auth-route-layout" id="main-content" tabIndex="-1">
      {/* U: NEW: Login/Register are standalone auth screens, so they do not use
          U: the public marketing header/footer layout. */}
      <Outlet />
    </div>
  );
};

export default AuthLayout;
