import React, { useState } from "react";
import Login from "./components/Login";

function App() {
  const [user, setUser] = useState(null);

  if (!user) return <Login onLogin={setUser} />;

  return (
    <div style={{ padding: "20px", textAlign: "center" }}>
      <h1>Welcome, {user.firstName}</h1>
      <p>Coin Balance: {user.coins}</p>
    </div>
  );
}

export default App;
