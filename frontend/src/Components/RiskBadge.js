function RiskBadge({ risk, probability }) {
  return (
    <span className={`badge badge-${risk.toLowerCase()}`}>
      {risk}
      {probability !== undefined && ` · ${Math.round(probability * 100)}%`}
    </span>
  );
}

export default RiskBadge;
