import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button, Card, ErrorText, Input, Select, extractErrorMessage } from "../components/ui";

const ROLE_HOME = { OWNER: "/owner", MANAGER: "/manager", RESIDENT: "/resident" };

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "", role: "OWNER" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await register(form);
      navigate(ROLE_HOME[user.role] || "/");
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 py-8">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold text-center text-brand-700 mb-6">
          Create an account
        </h1>
        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Full name" value={form.name} onChange={update("name")} required />
            <Input label="Email" type="email" value={form.email} onChange={update("email")} required />
            <Input label="Phone" value={form.phone} onChange={update("phone")} />
            <Input
              label="Password"
              type="password"
              value={form.password}
              onChange={update("password")}
              minLength={8}
              required
            />
            <Select label="Role" value={form.role} onChange={update("role")}>
              <option value="OWNER">Owner</option>
              <option value="MANAGER">Manager</option>
              <option value="RESIDENT">Resident</option>
            </Select>
            <ErrorText>{error}</ErrorText>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Creating account..." : "Register"}
            </Button>
          </form>
        </Card>
        <p className="text-center text-sm text-slate-500 mt-4">
          Already have an account? <Link to="/login" className="text-brand-600 font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
