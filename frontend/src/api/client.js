import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL });

// Attach the JWT to every request once the user is logged in.
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If the token is invalid/expired, bounce back to login rather than showing
// a confusing "silent failure" on whatever page the user was on.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// --- Auth ---
export const registerUser = (payload) => client.post("/api/auth/register", payload);

export const loginUser = (email, password) => {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  return client.post("/api/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
};

export const fetchMe = () => client.get("/api/auth/me");

// --- Owner ---
export const createPG = (payload) => client.post("/api/owner/pgs", payload);
export const listMyPGs = () => client.get("/api/owner/pgs");
export const assignManager = (pgId, managerUserId) =>
  client.post(`/api/owner/pgs/${pgId}/managers`, { manager_user_id: managerUserId });
export const getOwnerOccupancy = (pgId) => client.get(`/api/owner/pgs/${pgId}/occupancy`);
export const getOwnerPendingRents = (pgId, billingMonth, billingYear) =>
  client.get(`/api/owner/pgs/${pgId}/pending-rents`, {
    params: { billing_month: billingMonth, billing_year: billingYear },
  });
export const getOwnerPGSecurityDeposits = (pgId) => client.get(`/api/owner/pgs/${pgId}/security-deposits`);
export const getOwnerAllSecurityDeposits = () => client.get("/api/owner/security-deposits");

// --- Manager ---
export const createRoom = (payload) => client.post("/api/manager/rooms", payload);
export const listRooms = () => client.get("/api/manager/rooms");
export const createBed = (roomId, bedNumber) =>
  client.post(`/api/manager/rooms/${roomId}/beds`, { bed_number: bedNumber });
export const listBeds = (roomId) => client.get(`/api/manager/rooms/${roomId}/beds`);
export const createResident = (payload) => client.post("/api/manager/residents", payload);
export const listResidents = () => client.get("/api/manager/residents");
export const createRentRecord = (payload) => client.post("/api/manager/rent-records", payload);
export const getManagerPendingRents = (billingMonth, billingYear) =>
  client.get("/api/manager/rent-records/pending", {
    params: { billing_month: billingMonth, billing_year: billingYear },
  });
export const collectPayment = (rentRecordId, payload) =>
  client.post(`/api/manager/rent-records/${rentRecordId}/payments`, payload);
export const getManagerSecurityDeposits = () => client.get("/api/manager/security-deposits");

// --- User ---
export const getUserById = (userId) => client.get(`/api/users/${userId}`);

// --- Resident ---
export const getMyRoom = () => client.get("/api/resident/me/room");
export const getMyRent = () => client.get("/api/resident/me/rent");
export const getMyPayments = () => client.get("/api/resident/me/payments");
export const logMyPayment = (payload) => client.post("/api/resident/me/payments", payload);
export const getMySecurityDeposit = () => client.get("/api/resident/me/security-deposit");

// --- Chat ---
export const sendChatMessage = (message) => client.post("/api/chat", { message });

export default client;
