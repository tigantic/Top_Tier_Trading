import { Router } from 'express';
import fetch from 'node-fetch';
// Dynamically import the Redis client only when needed.  The `redis` package
// is not a direct dependency of the API unless event‑bus SSE is enabled.
let Redis: any;

/**
 * Server‑Sent Events (SSE) router.
 *
 * This endpoint streams JSON‑encoded metrics to connected clients.  It flushes
 * data on a regular interval.  On connection close the interval is cleared.
 *
 * Clients should connect to `/api/streams/sse` and handle `message` events.
 */
const router = Router();

router.get('/sse', async (req, res) => {
  // Set headers to establish SSE
  res.set({
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  });
  res.flushHeaders();

  // Helper to send an event.  Events must end with two newlines.
  const sendEvent = (data: any) => {
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  };

  // Determine whether to use the event bus (Redis) for SSE.  When
  // ``USE_EVENT_BUS_SSE`` is truthy the API will subscribe to Redis
  // channels ``exposure_update`` and ``pnl_update`` and stream those
  // events directly.  Otherwise it falls back to polling Prometheus.
  const useEventBus = (process.env.USE_EVENT_BUS_SSE || '').toLowerCase() === 'true';

  if (useEventBus) {
    // Lazy load the redis client since it may not be installed if event bus SSE
    // is disabled.  If import fails, log and fall back to metrics polling.
    try {
      if (!Redis) {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        Redis = require('redis');
      }
      const redisUrl = process.env.REDIS_URL || undefined;
      const host = process.env.REDIS_HOST || 'localhost';
      const port = process.env.REDIS_PORT ? parseInt(process.env.REDIS_PORT, 10) : 6379;
      const client = redisUrl ? Redis.createClient({ url: redisUrl }) : Redis.createClient({ socket: { host, port } });
      client.on('error', (err: any) => {
        console.error('Redis SSE error:', err);
      });
      await client.connect();
      const subscriber = client.duplicate();
      await subscriber.connect();
      // Subscribe to both exposure and PnL update channels
      await subscriber.subscribe('exposure_update', (message: string) => {
        try {
          const data = JSON.parse(message);
          // Construct payload similar to Prometheus metrics
          const exposures = data.exposures || { [data.product_id]: data.exposure };
          const openOrders = data.open_orders ?? 0;
          sendEvent({ exposures, open_orders });
        } catch (err) {
          console.error('Failed to parse exposure_update:', err);
        }
      });
      await subscriber.subscribe('pnl_update', (message: string) => {
        try {
          const data = JSON.parse(message);
          const dailyPnl = data.daily_pnl || 0;
          const killSwitch = data.kill_switch || false;
          sendEvent({ daily_pnl: dailyPnl, kill_switch: killSwitch });
        } catch (err) {
          console.error('Failed to parse pnl_update:', err);
        }
      });
      // Clean up on client disconnect: unsubscribe and disconnect redis connections
      req.on('close', async () => {
        try {
          await subscriber.unsubscribe();
          await subscriber.disconnect();
          await client.disconnect();
        } catch (err) {
          // ignore
        }
      });
      return;
    } catch (err) {
      console.error('Falling back to metrics polling for SSE:', err);
      // Continue to metrics polling below
    }
  }

  /**
   * Parse a Prometheus metrics string into a metrics object.  Similar to the
   * parsing logic used in the Ops UI, but included here to avoid shared code.
   */
  function parsePrometheusMetrics(text: string) {
    const exposures: Record<string, number> = {};
    let openOrders = 0;
    let killSwitch = false;
    let dailyPnl = 0;
    let accountBalance = 0;
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
        const match = line.match(/atlas_exposure\{product="([^\"]+)"\} ([0-9eE+\-.]+)/);
        if (match) {
          exposures[match[1]] = parseFloat(match[2]);
        }
      } else if (line.startsWith('atlas_daily_pnl')) {
        const parts = line.split(' ');
        if (parts.length >= 2) {
          dailyPnl = parseFloat(parts[1]);
        }
      } else if (line.startsWith('atlas_account_balance')) {
        const parts = line.split(' ');
        if (parts.length >= 2) {
          accountBalance = parseFloat(parts[1]);
        }
      }
    }
    return { open_orders: openOrders, kill_switch: killSwitch, exposures, daily_pnl: dailyPnl, account_balance: accountBalance };
  }

  async function pushMetrics() {
    try {
      const metricsUrl = process.env.METRICS_URL || 'http://workers:9108/metrics';
      const response = await fetch(metricsUrl);
      const text = await response.text();
      const metrics = parsePrometheusMetrics(text);
      sendEvent(metrics);
    } catch (err) {
      // On error, just send a heartbeat and log the error to console
      console.error('Failed to fetch metrics for SSE:', err);
      sendEvent({ timestamp: new Date().toISOString() });
    }
  }

  // Emit immediately and then on a timer
  await pushMetrics();
  const intervalMs = Number(process.env.SSE_INTERVAL_MS || 5000);
  const interval = setInterval(() => {
    pushMetrics();
  }, intervalMs);

  // Clean up when the client disconnects
  req.on('close', () => {
    clearInterval(interval);
  });
});

export default router;