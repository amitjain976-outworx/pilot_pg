import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/Login";
import Register from "./pages/Register";
import OwnerDashboard from "./pages/owner/OwnerDashboard";
import PGDetail from "./pages/owner/PGDetail";
import ManagerDashboard from "./pages/manager/ManagerDashboard";
import ResidentDashboard from "./pages/resident/ResidentDashboard";

const ROLE_HOME = { OWNER: "/owner", MANAGER: "/manager", RESIDENT: "/resident" };

function Home() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={ROLE_HOME[user.role] || "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route path="/" element={<Home />} />

      <Route
        path="/owner"
        element={
          <ProtectedRoute allowedRoles={["OWNER"]}>
            <Layout><OwnerDashboard /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/owner/pgs/:pgId"
        element={
          <ProtectedRoute allowedRoles={["OWNER"]}>
            <Layout><PGDetail /></Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/manager"
        element={
          <ProtectedRoute allowedRoles={["MANAGER"]}>
            <Layout><ManagerDashboard /></Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/resident"
        element={
          <ProtectedRoute allowedRoles={["RESIDENT"]}>
            <Layout><ResidentDashboard /></Layout>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
