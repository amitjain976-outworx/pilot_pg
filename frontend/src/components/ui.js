import React from "react";

export function Card({ title, children, className = "" }) {
  return (
    <div className={`bg-white rounded-lg border border-slate-200 shadow-sm p-5 ${className}`}>
      {title && <h2 className="text-base font-semibold text-slate-800 mb-3">{title}</h2>}
      {children}
    </div>
  );
}

export function Button({ children, variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-brand-600 hover:bg-brand-700 text-white",
    secondary: "bg-slate-100 hover:bg-slate-200 text-slate-700",
    danger: "bg-red-600 hover:bg-red-700 text-white",
  };
  return (
    <button
      className={`px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input({ label, className = "", ...props }) {
  return (
    <label className="block text-sm">
      {label && <span className="block text-slate-600 mb-1">{label}</span>}
      <input
        className={`w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent ${className}`}
        {...props}
      />
    </label>
  );
}

export function Select({ label, children, className = "", ...props }) {
  return (
    <label className="block text-sm">
      {label && <span className="block text-slate-600 mb-1">{label}</span>}
      <select
        className={`w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent bg-white ${className}`}
        {...props}
      >
        {children}
      </select>
    </label>
  );
}

export function Table({ columns, rows, emptyText = "No data yet." }) {
  if (!rows || rows.length === 0) {
    return <p className="text-slate-400 text-sm py-4">{emptyText}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500 border-b border-slate-200">
            {columns.map((col) => (
              <th key={col} className="pb-2 pr-4 font-medium">{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-slate-100 last:border-0">
              {row.map((cell, j) => (
                <td key={j} className="py-2 pr-4">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Badge({ status }) {
  const colors = {
    PAID: "bg-green-100 text-green-700",
    PENDING: "bg-amber-100 text-amber-700",
    PARTIAL: "bg-orange-100 text-orange-700",
    OVERDUE: "bg-red-100 text-red-700",
    ACTIVE: "bg-green-100 text-green-700",
    VACANT: "bg-slate-100 text-slate-600",
    OCCUPIED: "bg-blue-100 text-blue-700",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || "bg-slate-100 text-slate-600"}`}>
      {status}
    </span>
  );
}

export function ErrorText({ children }) {
  if (!children) return null;
  return <p className="text-red-600 text-sm mt-1">{children}</p>;
}

export function SuccessText({ children }) {
  if (!children) return null;
  return <p className="text-green-600 text-sm mt-1">{children}</p>;
}

export function extractErrorMessage(error) {
  return error?.response?.data?.detail || error?.message || "Something went wrong.";
}
