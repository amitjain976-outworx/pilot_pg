import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ROLE_HOME = {
  OWNER: "/owner",
  MANAGER: "/manager",
  RESIDENT: "/resident",
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
      <Link to={ROLE_HOME[user.role]} className="font-semibold text-brand-700 text-lg">
        PG Hostel Management
      </Link>
      <div className="flex items-center gap-4 text-sm">
        <span className="text-slate-500">
          {user.name} <span className="text-slate-400">({user.role})</span>
        </span>
        <span className="bg-slate-100 text-slate-600 px-2 py-1 rounded font-mono text-xs">
          My ID: {user.id}
        </span>
        <button
          onClick={handleLogout}
          className="text-red-600 hover:text-red-700 font-medium"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
