import React, { useEffect, useState } from "react";
import { getMyPayments, getMyRent, getMyRoom, logMyPayment } from "../../api/client";
import { Badge, Button, Card, ErrorText, Input, Select, SuccessText, Table, extractErrorMessage } from "../../components/ui";

export default function ResidentDashboard() {
  const [room, setRoom] = useState(null);
  const [rent, setRent] = useState(null);
  const [payments, setPayments] = useState([]);
  const [loadError, setLoadError] = useState("");

  const [payForm, setPayForm] = useState({
    amount: "", payment_date: new Date().toISOString().slice(0, 10), payment_mode: "UPI", transaction_reference: "",
  });
  const [paySubmitting, setPaySubmitting] = useState(false);
  const [payError, setPayError] = useState("");
  const [paySuccess, setPaySuccess] = useState("");

  const loadAll = () => {
    getMyRoom().then((res) => setRoom(res.data)).catch((err) => setLoadError(extractErrorMessage(err)));
    getMyRent().then((res) => setRent(res.data)).catch((err) => setLoadError(extractErrorMessage(err)));
    getMyPayments().then((res) => setPayments(res.data)).catch((err) => setLoadError(extractErrorMessage(err)));
  };
  useEffect(loadAll, []);

  const handlePay = async (e) => {
    e.preventDefault();
    setPayError("");
    setPaySuccess("");
    setPaySubmitting(true);
    try {
      await logMyPayment({
        amount: payForm.amount,
        payment_date: payForm.payment_date,
        payment_mode: payForm.payment_mode,
        transaction_reference: payForm.transaction_reference || null,
      });
      setPaySuccess("Payment recorded and applied to your oldest unpaid rent.");
      setPayForm({ ...payForm, amount: "", transaction_reference: "" });
      loadAll();
    } catch (err) {
      setPayError(extractErrorMessage(err));
    } finally {
      setPaySubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">My Stay</h1>
        <p className="text-slate-500 text-sm">Your room, rent status, and payment history.</p>
      </div>

      <ErrorText>{loadError}</ErrorText>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <Card title="My Room">
          {room ? (
            <div className="space-y-1 text-sm">
              <p><span className="text-slate-500">PG:</span> {room.pg_name}</p>
              <p><span className="text-slate-500">Room:</span> {room.room_number}</p>
              <p><span className="text-slate-500">Bed:</span> {room.bed_number}</p>
            </div>
          ) : (
            <p className="text-slate-400 text-sm">Not assigned to a room yet.</p>
          )}
        </Card>

        <Card title="My Rent">
          {rent ? (
            <div className="space-y-1 text-sm">
              <p><span className="text-slate-500">Monthly rent:</span> {rent.monthly_rent}</p>
              {rent.status ? (
                <>
                  <p><span className="text-slate-500">Period:</span> {rent.billing_month}/{rent.billing_year}</p>
                  <p><span className="text-slate-500">Amount due:</span> {rent.amount_due}</p>
                  <p><span className="text-slate-500">Amount paid:</span> {rent.amount_paid}</p>
                  <p><span className="text-slate-500">Outstanding:</span> {rent.outstanding}</p>
                  <p><span className="text-slate-500">Status:</span> <Badge status={rent.status} /></p>
                </>
              ) : (
                <p className="text-slate-400">No rent record for this period yet.</p>
              )}
            </div>
          ) : (
            <p className="text-slate-400 text-sm">Loading...</p>
          )}
        </Card>
      </div>

      <Card title="Log a payment">
        <p className="text-xs text-slate-500 mb-3">
          Applies to your oldest unpaid rent record automatically.
        </p>
        <form onSubmit={handlePay} className="grid grid-cols-2 sm:grid-cols-4 gap-3 items-end">
          <Input label="Amount" type="number" step="0.01" value={payForm.amount} onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })} required />
          <Input label="Payment date" type="date" value={payForm.payment_date} onChange={(e) => setPayForm({ ...payForm, payment_date: e.target.value })} required />
          <Select label="Mode" value={payForm.payment_mode} onChange={(e) => setPayForm({ ...payForm, payment_mode: e.target.value })}>
            <option value="UPI">UPI</option>
            <option value="CASH">Cash</option>
            <option value="BANK_TRANSFER">Bank Transfer</option>
            <option value="CARD">Card</option>
            <option value="OTHER">Other</option>
          </Select>
          <Input label="Reference (optional)" value={payForm.transaction_reference} onChange={(e) => setPayForm({ ...payForm, transaction_reference: e.target.value })} />
          <div className="col-span-2 sm:col-span-4">
            <ErrorText>{payError}</ErrorText>
            <SuccessText>{paySuccess}</SuccessText>
            <Button type="submit" disabled={paySubmitting}>{paySubmitting ? "Recording..." : "Log Payment"}</Button>
          </div>
        </form>
      </Card>

      <Card title="Payment history">
        <Table
          columns={["Amount", "Date", "Mode", "Status"]}
          rows={payments.map((p) => [p.amount, p.payment_date, p.payment_mode, <Badge status={p.status} />])}
          emptyText="No payments logged yet."
        />
      </Card>
    </div>
  );
}
