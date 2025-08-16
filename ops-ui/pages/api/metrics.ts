import type { NextApiRequest, NextApiResponse } from 'next';
import fetch from 'node-fetch';

interface Metrics {
  open_orders: number;
  kill_switch: boolean;
  exposures: Record<string, number>;
}

const METRICS_URL = process.env.METRICS_URL || 'http://workers:9108/metrics';

function parsePrometheusMetrics(text: string): Metrics {
  const exposures: Record<string, number> = {};
  let openOrders = 0;
  let killSwitch = false;
  const lines = text.split('\n');
  for (const line of lines) {
    if (line.startsWith('atlas_open_orders')) {
      const parts = line.split(' ');
      if (parts.length >= 2) {
        openOrders = parseFloat(parts[1]);
      }
    } else if (line.startsWith('atlas_kill_switch')) {
      const parts = line.split(' ');
      if (parts.length >= 2) {
        killSwitch = parseFloat(parts[1]) === 1;
      }
    } else if (line.startsWith('atlas_exposure')) {
      // Example line: atlas_exposure{product="BTC-USD"} 1234.56
      const match = line.match(/atlas_exposure\{product="([^"]+)"\} ([0-9eE+\-\.]+)/);
      if (match) {
        exposures[match[1]] = parseFloat(match[2]);
      }
    }
  }
  return { open_orders: openOrders, kill_switch: killSwitch, exposures };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<Metrics | { error: string }>) {
  try {
    const response = await fetch(METRICS_URL as string);
    const text = await response.text();
    const metrics = parsePrometheusMetrics(text);
    res.status(200).json(metrics);
  } catch (err: any) {
    console.error('Failed to fetch metrics:', err);
    res.status(500).json({ error: 'Failed to fetch metrics' });
  }
}