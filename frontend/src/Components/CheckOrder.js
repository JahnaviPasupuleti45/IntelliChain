import React, { useState } from "react";
import { apiFetch } from "../api";
import RiskBadge from "./RiskBadge";

function CheckOrder({ onAuthError }) {
  const [shipmentId, setShipmentId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleCheck = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);
    try {
      setResult(await apiFetch(`/api/shipments/${encodeURIComponent(shipmentId.trim())}`));
    } catch (err) {
      if (err.status === 401) onAuthError();
      else setError(err.message);
    }
  };

  const latest = result?.readings[0];

  return (
    <div>
      <form className="card form-card" onSubmit={handleCheck}>
        <h2>Check Order</h2>
        <input placeholder="Shipment ID (e.g. SHP2)" value={shipmentId} onChange={(e) => setShipmentId(e.target.value)} required />
        <button className="btn" type="submit">Check Status</button>
        {error && <p className="error">{error}</p>}
      </form>

      {latest && (
        <div className="card">
          <h3>
            {result.shipment_id} · {latest.product_type} · {latest.location}{" "}
            <RiskBadge risk={latest.risk} probability={latest.risk_probability} />
          </h3>
          <p>{latest.report}</p>

          <h4>Reading history ({result.readings.length})</h4>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Time</th><th>Temp (°C)</th><th>Humidity (%)</th><th>Delay (h)</th><th>Risk</th></tr>
              </thead>
              <tbody>
                {result.readings.map((r) => (
                  <tr key={r.id}>
                    <td>{new Date(r.created_at).toLocaleString()}</td>
                    <td>{r.temperature}</td>
                    <td>{r.humidity}</td>
                    <td>{r.delay_hours}</td>
                    <td><RiskBadge risk={r.risk} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default CheckOrder;
