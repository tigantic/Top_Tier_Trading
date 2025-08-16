import { Router } from 'express';

// Router for health check endpoints
export const healthRouter = Router();

/**
 * GET /healthz
 *
 * Simple liveness probe.  Returns HTTP 200 with body 'ok'.
 */
healthRouter.get('/', (_req, res) => {
  res.status(200).send('ok');
});
