import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { assignManager, getOwnerOccupancy, getOwnerPendingRents } from "../../api/client";
import { Button, Card, ErrorText, Input, SuccessText, Table, extractErrorMessage } from "../../components/ui";

const now = new Date();

export default function PGDetail() {
  const { pgId } = useParams();

  const [occupancy, setOccupancy] = useState(null);
  const [occError, setOccError] = useState("");

  const [managerId, setManagerId] = useState("");
  const [assignError, setAssignError] = useState("");
  const [assignSuccess, setAssignSuccess] = useState("");
  const [assigning, setAssigning] = useState(false);

  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [pendingRents, setPendingRents] = useState(null);
  const [pendingError, setPendingError] = useState("");
  const [pendingLoading, setPendingLoading] = useState(false);

  const loadOccupancy = () => {
    getOwnerOccupancy(pgId)
      .then((res) => setOccupancy(res.data))
      .catch((err) => setOccError(extractErrorMessage(err)));
  };

  useEffect(loadOccupancy, [pgId]);

  const handleAssign = async (e) => {
    e.preventDefault();
    setAssignError("");
    setAssignSuccess("");
    setAssigning(true);
    try {
      const res = await assignManager(pgId, Number(managerId));
      setAssignSuccess(res.data.message || "Manager assigned.");
      setManagerId("");
    } catch (err) {
      setAssignError(extractErrorMessage(err));
    } finally {
      setAssigning(false);
    }
  };

  const loadPendingRents = async () => {
    setPendingError("");
    setPendingLoading(true);
    try {
      const res = await getOwnerPendingRents(pgId, month, year);
      setPendingRents(res.data);
    } catch (err) {
      setPendingError(extractErrorMessage(err));
    } finally {
      setPendingLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <Link to="/owner" className="text-sm text-brand-600">&larr; Back to PGs</Link>
        <h1 className="text-xl font-semibold text-slate-800 mt-1">PG #{pgId}</h1>
      </div>

      <Card title="Occupancy">
        <ErrorText>{occError}</ErrorText>
        {occupancy ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <Stat label="Total Rooms" value={occupancy.total_rooms} />
            <Stat label="Total Beds" value={occupancy.total_beds} />
            <Stat label="Occupied Beds" value={occupancy.occupied_beds} />
            <Stat label="Vacant Beds" value={occupancy.vacant_beds} />
            <Stat label="Occupancy %" value={occupancy.occupancy_percentage ?? "—"} />
          </div>
        ) : (
          !occError && <p className="text-slate-400 text-sm">Loading...</p>
        )}
      </Card>

      <Card title="Assign a manager">
        <p className="text-xs text-slate-500 mb-3">
          Ask the manager to log in and share their "My ID" badge (top right of their dashboard).
        </p>
        <form onSubmit={handleAssign} className="flex items-end gap-3">
          <Input
            label="Manager User ID"
            type="number"
            value={managerId}
            onChange={(e) => setManagerId(e.target.value)}
            required
            className="w-40"
          />
          <Button type="submit" disabled={assigning}>{assigning ? "Assigning..." : "Assign"}</Button>
        </form>
        <ErrorText>{assignError}</ErrorText>
        <SuccessText>{assignSuccess}</SuccessText>
      </Card>

      <Card title="Pending rent by month">
        <div className="flex items-end gap-3 mb-4">
          <Input label="Month" type="number" min={1} max={12} value={month} onChange={(e) => setMonth(Number(e.target.value))} className="w-24" />
          <Input label="Year" type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} className="w-28" />
          <Button onClick={loadPendingRents} disabled={pendingLoading} variant="secondary">
            {pendingLoading ? "Checking..." : "Check"}
          </Button>
        </div>
        <ErrorText>{pendingError}</ErrorText>
        {pendingRents && (
          <Table
            columns={["Resident", "Amount Due", "Amount Paid", "Outstanding", "Status"]}
            rows={pendingRents.map((r) => [r.resident_name, r.amount_due, r.amount_paid, r.outstanding, r.status])}
            emptyText="No pending rent for this month — everyone's paid up."
          />
        )}
      </Card>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-2xl font-semibold text-brand-700">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  );
}
