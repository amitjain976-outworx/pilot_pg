import React from "react";
import Navbar from "./Navbar";
import ChatWidget from "./ChatWidget";

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
      <ChatWidget />
    </div>
  );
}
