import { useEffect, useState } from 'react';
import axios from 'axios';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Register necessary Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface Metrics {
  open_orders: number;
  kill_switch: boolean;
  exposures: Record<string, number>;
}

export default function ExposuresPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let interval: NodeJS.Timeout | null = null;

    async function loadMetrics() {
      try {
        const res = await axios.get<Metrics>('/api/metrics');
        setMetrics(res.data);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to load metrics');
      }
    }

    // Attempt to open an SSE connection for real‑time updates.  If it fails
    // (e.g. the browser or server does not support SSE), fall back to polling.
    try {
      eventSource = new EventSource('/api/streams/sse');
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // If the SSE message contains exposure metrics, update state directly.
          if (data && data.exposures) {
            const m: Metrics = {
              open_orders: data.open_orders ?? 0,
              kill_switch: !!data.kill_switch,
              exposures: data.exposures,
            };
            setMetrics(m);
            setError(null);
          } else {
            // Otherwise fall back to HTTP fetch to update metrics.
            loadMetrics();
          }
        } catch (err) {
          console.error('Failed to parse SSE data', err);
        }
      };
      eventSource.onerror = (err) => {
        console.warn('SSE connection error, falling back to polling', err);
        if (eventSource) {
          eventSource.close();
        }
        eventSource = null;
        interval = setInterval(loadMetrics, 5000);
      };
    } catch (_err) {
      // If EventSource construction throws (unlikely in modern browsers), fallback
      interval = setInterval(loadMetrics, 5000);
    }

    // Initial load
    loadMetrics();

    return () => {
      if (eventSource) {
        eventSource.close();
      }
      if (interval) {
        clearInterval(interval);
      }
    };
  }, []);

  if (error) {
    return <p style={{ padding: '2rem', color: 'red' }}>Error: {error}</p>;
  }

  if (!metrics) {
    return <p style={{ padding: '2rem' }}>Loading exposures...</p>;
  }

  const labels = Object.keys(metrics.exposures);
  const dataValues = labels.map((symbol) => metrics.exposures[symbol]);

  const data = {
    labels,
    datasets: [
      {
        label: 'Exposure (USD)',
        data: dataValues,
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Exposure by Product',
      },
    },
  };

  return (
    <main style={{ padding: '2rem', fontFamily: 'Arial, sans-serif' }}>
      <h1>Exposure Chart</h1>
      <Bar data={data} options={options} />
    </main>
  );
}