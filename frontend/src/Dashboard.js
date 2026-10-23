import React, { useCallback, useEffect, useState } from "react";
import { apiFetch } from "./api";
import RiskBadge from "./Components/RiskBadge";

const REFRESH_MS = 5000;

function Dashboard({ onAuthError }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(null);

  const load = useCallback(async () => {
    try {
      setData(await apiFetch("/api/dashboard"));
      setError("");
    } catch (err) {
      if (err.status === 401) onAuthError();
      else setError(err.message);
    }
  }, [onAuthError]);

  // Load now, then refresh every few seconds so new sensor readings appear live
  useEffect(() => {
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Loading shipments...</p>;

  const { summary, shipments } = data;

  return (
    <div>
      <h2>📦 Shipment Dashboard</h2>
      <p className="muted">Latest reading per shipment · refreshes every {REFRESH_MS / 1000}s · click a row for its report</p>

      <div className="stats">
        <div className="stat"><span>{summary.total_shipments}</span>Shipments</div>
        <div className="stat stat-high"><span>{summary.HIGH}</span>High risk</div>
        <div className="stat stat-medium"><span>{summary.MEDIUM}</span>Medium risk</div>
        <div className="stat stat-low"><span>{summary.LOW}</span>Low risk</div>
      </div>

      {shipments.length === 0 ? (
        <p className="card">No shipment data yet. Run <code>python simulate_iot.py</code> in the backend folder.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Shipment</th><th>Product</th><th>Location</th>
                <th>Temp (°C)</th><th>Humidity (%)</th><th>Delay (h)</th><th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {shipments.map((s) => (
                <React.Fragment key={s.id}>
                  <tr className="clickable" onClick={() => setExpanded(expanded === s.id ? null : s.id)}>
                    <td><b>{s.shipment_id}</b></td>
                    <td>{s.product_type}</td>
                    <td>{s.location}</td>
                    <td>{s.temperature}</td>
                    <td>{s.humidity}</td>
                    <td>{s.delay_hours}</td>
                    <td><RiskBadge risk={s.risk} probability={s.risk_probability} /></td>
                  </tr>
                  {expanded === s.id && (
                    <tr>
                      <td colSpan="7" className="report">
                        <small className="muted">
                          {s.report_source === "llm" ? "AI-generated report" : "Template report"}
                        </small>
                        <p>{s.report}</p>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
