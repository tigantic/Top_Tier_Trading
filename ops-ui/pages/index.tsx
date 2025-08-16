import { useEffect, useState } from 'react';
import axios from 'axios';

interface Metrics {
  open_orders: number;
  kill_switch: boolean;
  exposures: Record<string, number>;
}

export default function Home() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    async function load() {
      try {
        const res = await axios.get<Metrics>('/api/metrics');
        setMetrics(res.data);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to load metrics');
      }
    }
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main style={{ padding: '2rem', fontFamily: 'Arial, sans-serif' }}>
      <h1>Atlas Trader Ops Dashboard</h1>
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {metrics ? (
        <div>
          <p><strong>Open Orders:</strong> {metrics.open_orders}</p>
          <p><strong>Kill Switch:</strong> {metrics.kill_switch ? 'ACTIVE' : 'off'}</p>
          <h2>Exposure</h2>
          <ul>
            {Object.entries(metrics.exposures).map(([product, exposure]) => (
              <li key={product}>
                {product}: {exposure.toFixed(2)}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p>Loading metrics...</p>
      )}
    </main>
  );
}