import React, { useEffect, useState } from "react";
import {
  createBed, createResident, createRentRecord, createRoom, collectPayment,
  getManagerPendingRents, listBeds, listResidents, listRooms,
} from "../../api/client";
import { Badge, Button, Card, ErrorText, Input, Select, SuccessText, Table, extractErrorMessage } from "../../components/ui";

const TABS = ["Rooms & Beds", "Residents", "Rent & Payments"];
const now = new Date();

export default function ManagerDashboard() {
  const [tab, setTab] = useState(TABS[0]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Manager Dashboard</h1>
        <p className="text-slate-500 text-sm">Manage rooms, beds, residents, and rent for your assigned PG.</p>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
              tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Rooms & Beds" && <RoomsBedsSection />}
      {tab === "Residents" && <ResidentsSection />}
      {tab === "Rent & Payments" && <RentPaymentsSection />}
    </div>
  );
}

// ---------------------------------------------------------------------
function RoomsBedsSection() {
  const [rooms, setRooms] = useState([]);
  const [error, setError] = useState("");
  const [roomForm, setRoomForm] = useState({ room_number: "", floor: "", room_type: "OTHER", capacity: 1 });
  const [submitting, setSubmitting] = useState(false);

  const [expandedRoom, setExpandedRoom] = useState(null);
  const [beds, setBeds] = useState({});
  const [bedNumber, setBedNumber] = useState("");
  const [bedSubmitting, setBedSubmitting] = useState(false);

  const loadRooms = () => {
    listRooms().then((res) => setRooms(res.data)).catch((err) => setError(extractErrorMessage(err)));
  };
  useEffect(loadRooms, []);

  const handleCreateRoom = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await createRoom({ ...roomForm, capacity: Number(roomForm.capacity) });
      setRoomForm({ room_number: "", floor: "", room_type: "OTHER", capacity: 1 });
      loadRooms();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleRoom = async (roomId) => {
    if (expandedRoom === roomId) {
      setExpandedRoom(null);
      return;
    }
    setExpandedRoom(roomId);
    if (!beds[roomId]) {
      const res = await listBeds(roomId);
      setBeds((prev) => ({ ...prev, [roomId]: res.data }));
    }
  };

  const handleAddBed = async (roomId) => {
    if (!bedNumber.trim()) return;
    setBedSubmitting(true);
    try {
      await createBed(roomId, bedNumber.trim());
      const res = await listBeds(roomId);
      setBeds((prev) => ({ ...prev, [roomId]: res.data }));
      setBedNumber("");
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBedSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card title="Add a room">
        <form onSubmit={handleCreateRoom} className="grid grid-cols-2 sm:grid-cols-4 gap-3 items-end">
          <Input label="Room number" value={roomForm.room_number} onChange={(e) => setRoomForm({ ...roomForm, room_number: e.target.value })} required />
          <Input label="Floor" value={roomForm.floor} onChange={(e) => setRoomForm({ ...roomForm, floor: e.target.value })} />
          <Select label="Type" value={roomForm.room_type} onChange={(e) => setRoomForm({ ...roomForm, room_type: e.target.value })}>
            <option value="SINGLE">Single</option>
            <option value="DOUBLE">Double</option>
            <option value="TRIPLE">Triple</option>
            <option value="DORMITORY">Dormitory</option>
            <option value="OTHER">Other</option>
          </Select>
          <Input label="Capacity" type="number" min={1} value={roomForm.capacity} onChange={(e) => setRoomForm({ ...roomForm, capacity: e.target.value })} />
          <div className="col-span-2 sm:col-span-4">
            <ErrorText>{error}</ErrorText>
            <Button type="submit" disabled={submitting}>{submitting ? "Adding..." : "Add Room"}</Button>
          </div>
        </form>
      </Card>

      <Card title="Rooms">
        {rooms.length === 0 ? (
          <p className="text-slate-400 text-sm">No rooms yet — add one above.</p>
        ) : (
          <div className="space-y-2">
            {rooms.map((room) => (
              <div key={room.id} className="border border-slate-200 rounded-lg">
                <button
                  onClick={() => toggleRoom(room.id)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left"
                >
                  <span className="font-medium text-slate-800">
                    Room {room.room_number} <span className="text-slate-400 font-normal">({room.room_type}, Capacity: {room.capacity})</span>
                  </span>
                  <span className="text-slate-400 text-xs">Room ID: {room.id} · {expandedRoom === room.id ? "▲" : "▼"}</span>
                </button>
                {expandedRoom === room.id && (
                  <div className="px-4 pb-4 border-t border-slate-100 pt-3">
                    <div className="flex flex-wrap gap-2 mb-3">
                      {(beds[room.id] || []).map((bed) => (
                        <span key={bed.id} className="flex items-center gap-1 border border-slate-200 rounded px-2 py-1 text-xs">
                          Bed {bed.bed_number} (ID: {bed.id}) <Badge status={bed.status} />
                        </span>
                      ))}
                      {(beds[room.id] || []).length === 0 && <span className="text-slate-400 text-xs">No beds yet.</span>}
                    </div>
                    <div className="flex items-end gap-2">
                      <Input label="Bed number" value={bedNumber} onChange={(e) => setBedNumber(e.target.value)} className="w-32" />
                      <Button variant="secondary" onClick={() => handleAddBed(room.id)} disabled={bedSubmitting}>
                        Add Bed
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------
function ResidentsSection() {
  const [residents, setResidents] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [beds, setBeds] = useState([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    user_id: "", room_id: "", bed_id: "", joining_date: new Date().toISOString().slice(0, 10),
    rent_amount: "", security_deposit: "0",
  });

  const load = async () => {
    try {
      const residentsRes = await listResidents();
      const roomsRes = await listRooms();
      setRooms(roomsRes.data);
      setResidents(residentsRes.data);

      // Fetch all beds for the form (when selecting rooms)
      const allBeds = [];
      for (const room of roomsRes.data) {
        try {
          const bedsRes = await listBeds(room.id);
          allBeds.push(...bedsRes.data);
        } catch (err) {
          // Skip if bed loading fails for a room
        }
      }
      setBeds(allBeds);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!form.room_id) {
      setBeds([]);
      return;
    }
    const roomId = Number(form.room_id);
    listBeds(roomId).then((res) => {
      const vacantBeds = res.data.filter((b) => b.status === "VACANT");
      setBeds(vacantBeds);
    }).catch(() => setBeds([]));
  }, [form.room_id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await createResident({
        user_id: Number(form.user_id),
        room_id: Number(form.room_id),
        bed_id: Number(form.bed_id),
        joining_date: form.joining_date,
        rent_amount: form.rent_amount,
        security_deposit: form.security_deposit,
      });
      setForm({ ...form, user_id: "", room_id: "", bed_id: "", rent_amount: "" });
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card title="Attach a resident to a room/bed">
        <p className="text-xs text-slate-500 mb-3">
          The resident must have already registered with role RESIDENT — ask them for their "My ID" badge.
        </p>
        <form onSubmit={handleSubmit} className="grid grid-cols-2 sm:grid-cols-3 gap-3 items-end">
          <Input label="Resident User ID" type="number" value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} required />
          <Select label="Room" value={form.room_id} onChange={(e) => setForm({ ...form, room_id: e.target.value, bed_id: "" })} required>
            <option value="">Select a room</option>
            {rooms.map((r) => (
              <option key={r.id} value={r.id}>Room {r.room_number}</option>
            ))}
          </Select>
          <Select label="Bed (vacant only)" value={form.bed_id} onChange={(e) => setForm({ ...form, bed_id: e.target.value })} required disabled={!form.room_id}>
            <option value="">Select a bed</option>
            {beds.map((b) => {
              return (
                <option key={b.id} value={b.id}>Bed {b.bed_number} </option>
              );
            })}
          </Select>
          <Input label="Joining date" type="date" value={form.joining_date} onChange={(e) => setForm({ ...form, joining_date: e.target.value })} required />
          <Input label="Monthly rent" type="number" step="0.01" value={form.rent_amount} onChange={(e) => setForm({ ...form, rent_amount: e.target.value })} required />
          <Input label="Security deposit" type="number" step="0.01" value={form.security_deposit} onChange={(e) => setForm({ ...form, security_deposit: e.target.value })} />
          <div className="col-span-2 sm:col-span-3">
            <ErrorText>{error}</ErrorText>
            <Button type="submit" disabled={submitting}>{submitting ? "Saving..." : "Attach Resident"}</Button>
          </div>
        </form>
      </Card>

      <Card title="Residents in your PG">
        <Table
          columns={["Name", "Room Number", "Bed Number", "Rent", "Status"]}
          rows={residents.map((r) => [
            r.resident_name || `User ${r.user_id}`,
            r.room_number || `Room ${r.room_id}`,
            r.bed_number || `Bed ${r.bed_id}`,
            r.rent_amount,
            <Badge status={r.status} />
          ])}
          emptyText="No residents attached yet."
        />
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------
function RentPaymentsSection() {
  const [residents, setResidents] = useState([]);
  const [error, setError] = useState("");

  const [rentForm, setRentForm] = useState({
    resident_id: "", billing_month: now.getMonth() + 1, billing_year: now.getFullYear(),
    amount_due: "", due_date: new Date().toISOString().slice(0, 10),
  });
  const [rentSubmitting, setRentSubmitting] = useState(false);
  const [rentSuccess, setRentSuccess] = useState("");

  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [pending, setPending] = useState(null);
  const [pendingLoading, setPendingLoading] = useState(false);

  const [payForm, setPayForm] = useState({
    resident_id: "", billing_month: now.getMonth() + 1, billing_year: now.getFullYear(),
    rent_record_id: "", amount: "", payment_date: new Date().toISOString().slice(0, 10),
    payment_mode: "CASH", transaction_reference: "",
  });
  const [rentRecords, setRentRecords] = useState([]);
  const [paySubmitting, setPaySubmitting] = useState(false);
  const [paySuccess, setPaySuccess] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const residentsRes = await listResidents();
        setResidents(residentsRes.data);
      } catch (err) {
        // Silently fail
      }
    };
    load();
  }, []);

  // When payment section resident or month/year changes, fetch rent records for that period
  useEffect(() => {
    if (!payForm.resident_id || !payForm.billing_month || !payForm.billing_year) {
      setRentRecords([]);
      return;
    }
    const loadRecords = async () => {
      try {
        // This will depend on your API - you may need to add an endpoint to get rent records for a specific resident/month/year
        // For now, we'll load all pending rents and filter
        const res = await getManagerPendingRents(payForm.billing_month, payForm.billing_year);
        const filtered = res.data.filter((r) => r.resident_id === Number(payForm.resident_id));
        setRentRecords(filtered);
      } catch (err) {
        setRentRecords([]);
      }
    };
    loadRecords();
  }, [payForm.resident_id, payForm.billing_month, payForm.billing_year]);

  const handleCreateRent = async (e) => {
    e.preventDefault();
    setError("");
    setRentSuccess("");
    setRentSubmitting(true);
    try {
      await createRentRecord({
        resident_id: Number(rentForm.resident_id),
        billing_month: Number(rentForm.billing_month),
        billing_year: Number(rentForm.billing_year),
        amount_due: rentForm.amount_due,
        due_date: rentForm.due_date,
      });
      setRentSuccess("Rent record created.");
      setRentForm({ ...rentForm, resident_id: "", amount_due: "" });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setRentSubmitting(false);
    }
  };

  const loadPending = async () => {
    setPendingLoading(true);
    setError("");
    try {
      const res = await getManagerPendingRents(month, year);
      setPending(res.data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setPendingLoading(false);
    }
  };

  const handleCollectPayment = async (e) => {
    e.preventDefault();
    setError("");
    setPaySuccess("");
    setPaySubmitting(true);
    try {
      await collectPayment(Number(payForm.rent_record_id), {
        amount: payForm.amount,
        payment_date: payForm.payment_date,
        payment_mode: payForm.payment_mode,
        transaction_reference: payForm.transaction_reference || null,
      });
      setPaySuccess("Payment recorded — rent status updated.");
      setPayForm({ ...payForm, resident_id: "", rent_record_id: "", amount: "", transaction_reference: "", billing_month: now.getMonth() + 1, billing_year: now.getFullYear() });
      setRentRecords([]);
      loadPending();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setPaySubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card title="Schedule rent for a resident">
        <p className="text-xs text-slate-500 mb-3">This only records what's owed — it does not collect payment.</p>
        <form onSubmit={handleCreateRent} className="grid grid-cols-2 sm:grid-cols-4 gap-3 items-end">
          <Select label="Resident" value={rentForm.resident_id} onChange={(e) => setRentForm({ ...rentForm, resident_id: e.target.value })} required>
            <option value="">Select resident</option>
            {residents.map((r) => (
              <option key={r.id} value={r.id}>{r.resident_name || `User ${r.user_id}`}</option>
            ))}
          </Select>
          <Input label="Month" type="number" min={1} max={12} value={rentForm.billing_month} onChange={(e) => setRentForm({ ...rentForm, billing_month: e.target.value })} />
          <Input label="Year" type="number" value={rentForm.billing_year} onChange={(e) => setRentForm({ ...rentForm, billing_year: e.target.value })} />
          <Input label="Amount due" type="number" step="0.01" value={rentForm.amount_due} onChange={(e) => setRentForm({ ...rentForm, amount_due: e.target.value })} required />
          <Input label="Due date" type="date" value={rentForm.due_date} onChange={(e) => setRentForm({ ...rentForm, due_date: e.target.value })} required />
          <div className="col-span-2 sm:col-span-4">
            <ErrorText>{error}</ErrorText>
            <SuccessText>{rentSuccess}</SuccessText>
            <Button type="submit" disabled={rentSubmitting}>{rentSubmitting ? "Saving..." : "Create Rent Record"}</Button>
          </div>
        </form>
      </Card>

      <Card title="Pending rent this period">
        <div className="flex items-end gap-3 mb-4">
          <Input label="Month" type="number" min={1} max={12} value={month} onChange={(e) => setMonth(Number(e.target.value))} className="w-24" />
          <Input label="Year" type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} className="w-28" />
          <Button variant="secondary" onClick={loadPending} disabled={pendingLoading}>
            {pendingLoading ? "Checking..." : "Check"}
          </Button>
        </div>
        {pending && (
          <Table
            columns={["Resident", "Amount Due", "Amount Paid", "Outstanding", "Status"]}
            rows={pending.map((r) => [r.resident_name, r.amount_due, r.amount_paid, r.outstanding, <Badge status={r.status} />])}
            emptyText="No pending rent for this period."
          />
        )}
      </Card>

      <Card title="Collect a payment (marks rent as paid/partial)">
        <p className="text-xs text-slate-500 mb-3">
          Select a resident, month, and year to see their rent records, then select the specific record to collect payment.
        </p>
        <form onSubmit={handleCollectPayment} className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Select label="Resident" value={payForm.resident_id} onChange={(e) => setPayForm({ ...payForm, resident_id: e.target.value, rent_record_id: "" })} required>
              <option value="">Select resident</option>
              {residents.map((r) => (
                <option key={r.id} value={r.id}>{r.resident_name || `User ${r.user_id}`}</option>
              ))}
            </Select>
            <Input label="Month" type="number" min={1} max={12} value={payForm.billing_month} onChange={(e) => setPayForm({ ...payForm, billing_month: e.target.value })} />
            <Input label="Year" type="number" value={payForm.billing_year} onChange={(e) => setPayForm({ ...payForm, billing_year: e.target.value })} />
          </div>
          
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 items-end">
            <Select label="Rent Record" value={payForm.rent_record_id} onChange={(e) => setPayForm({ ...payForm, rent_record_id: e.target.value })} required>
              <option value="">Select rent record</option>
              {rentRecords.map((rec) => (
                <option key={rec.id} value={rec.id}>Amount Due: {rec.amount_due} | Outstanding: {rec.outstanding}</option>
              ))}
            </Select>
            <Input label="Amount" type="number" step="0.01" value={payForm.amount} onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })} required />
            <Input label="Payment date" type="date" value={payForm.payment_date} onChange={(e) => setPayForm({ ...payForm, payment_date: e.target.value })} required />
            <Select label="Mode" value={payForm.payment_mode} onChange={(e) => setPayForm({ ...payForm, payment_mode: e.target.value })}>
              <option value="CASH">Cash</option>
              <option value="UPI">UPI</option>
              <option value="BANK_TRANSFER">Bank Transfer</option>
              <option value="CARD">Card</option>
              <option value="OTHER">Other</option>
            </Select>
            <Input label="Reference (optional)" value={payForm.transaction_reference} onChange={(e) => setPayForm({ ...payForm, transaction_reference: e.target.value })} />
            <div className="col-span-2 sm:col-span-3">
              <SuccessText>{paySuccess}</SuccessText>
              <Button type="submit" disabled={paySubmitting}>{paySubmitting ? "Recording..." : "Collect Payment"}</Button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  );
}
