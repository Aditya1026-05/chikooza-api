export const templatePath = process.env.REACT_APP_TEMPLATE_BASE_URL;
export const apiPath = process.env.REACT_APP_API_BASE_URL;


export const config = {
    headers: {
        "Access-Control-Allow-Origin": "*",
        "Content-type": "application/json"
    }
};

// U: OLD: screens mutated config.headers.Authorization directly before API calls.
// U: NEW: create a fresh config object per authenticated request to avoid shared mutable headers.
export const getAuthConfig = () => ({
    ...config,
    headers: {
        ...config.headers,
        Authorization: `Bearer ${localStorage.getItem("token")}`
    }
});

// U: OLD: every screen repeated localStorage.clear() + navigate("/login") with unsafe err.response access.
// U: NEW: one helper handles expired sessions consistently without crashing on network errors.
export const handleUnauthorized = (err, navigate) => {
    if (err?.response?.status === 401) {
        localStorage.clear();
        navigate("/login");
        return true;
    }
    return false;
};
export const contentArea = "bg-white p-2 border buttoncurve";
