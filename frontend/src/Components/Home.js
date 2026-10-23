function Home({ onGetStarted }) {
  return (
    <div className="hero">
      <h1>🚚 IntelliChain</h1>
      <p>
        Smart supply-chain monitoring: IoT sensor readings are scored by a machine-learning risk model,
        and an AI copilot answers questions using live shipment data and company SOPs.
      </p>
      <button className="btn" onClick={onGetStarted}>Get Started</button>
    </div>
  );
}

export default Home;
