import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createPG, listMyPGs } from "../../api/client";
import { Button, Card, ErrorText, Input, extractErrorMessage } from "../../components/ui";

export default function OwnerDashboard() {
  const [pgs, setPgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: "", city: "", address: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadPGs = () => {
    setLoading(true);
    listMyPGs()
      .then((res) => setPgs(res.data))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(loadPGs, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await createPG(form);
      setForm({ name: "", city: "", address: "" });
      loadPGs();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Your PGs</h1>
        <p className="text-slate-500 text-sm">Manage your properties, assign managers, and track rent.</p>
      </div>

      <Card title="Add a new PG">
        <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <Input label="City" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          <Input label="Address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <div className="sm:col-span-3">
            <ErrorText>{error}</ErrorText>
            <Button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Create PG"}</Button>
          </div>
        </form>
      </Card>

      <Card title="Your properties">
        {loading ? (
          <p className="text-slate-400 text-sm">Loading...</p>
        ) : pgs.length === 0 ? (
          <p className="text-slate-400 text-sm">No PGs yet — create one above.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {pgs.map((pg) => (
              <Link
                key={pg.id}
                to={`/owner/pgs/${pg.id}`}
                className="block border border-slate-200 rounded-lg p-4 hover:border-brand-400 hover:shadow-sm transition"
              >
                <p className="font-medium text-slate-800">{pg.name}</p>
                <p className="text-sm text-slate-500">{pg.city || "No city set"}</p>
                <p className="text-xs text-slate-400 mt-2">PG ID: {pg.id} · {pg.status}</p>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
