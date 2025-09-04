import React, { useEffect, useState } from "react";
import axios from "axios";

const API_BASE = "https://gamevault-backend-2adm.onrender.com";

export default function Login({ onLogin }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const tg = window.Telegram.WebApp;
    const initData = tg?.initData;

    if (!initData) {
      setError("Telegram initData not found");
      setLoading(false);
      return;
    }

    // Send initData to backend
    axios
      .post(`${API_BASE}/api/auth/login`, { initData })
      .then((res) => {
        onLogin(res.data.user); // Pass user data to App
        setLoading(false);
      })
      .catch((err) => {
        console.error("Login error:", err);
        setError("Service error. Please try again.");
        setLoading(false);
      });
  }, [onLogin]);

  if (loading) return <div>Initializing…</div>;
  if (error) return <div>{error}</div>;

  return null;
}
