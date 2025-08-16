import { Router } from 'express';
import { CoinbaseClient } from '../clients/coinbase';

const router = Router();

// Instantiate the Coinbase client with environment variables
const client = new CoinbaseClient({
  apiKey: process.env.COINBASE_API_KEY || '',
  apiSecret: process.env.COINBASE_API_SECRET || '',
  passphrase: process.env.COINBASE_PASSPHRASE || '',
  dryRun: process.env.DRY_RUN !== 'false',
});

/**
 * GET /api/accounts
 *
 * Returns a list of trading accounts.  Requires API key or OAuth credentials.
 */
router.get('/accounts', async (_req, res) => {
  try {
    const accounts = await client.listAccounts();
    res.json(accounts);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * GET /api/products
 *
 * Returns a list of products (trading instruments).
 */
router.get('/products', async (_req, res) => {
  try {
    const products = await client.listProducts();
    res.json(products);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * POST /api/orders
 *
 * Creates a new order.  Expects a JSON payload with required fields.
 */
router.post('/orders', async (req, res) => {
  try {
    const payload = req.body;
    // If OAuth and a retail portfolio ID is configured, include it automatically
    if (process.env.COINBASE_RETAIL_PORTFOLIO_ID && !payload.retail_portfolio_id) {
      payload.retail_portfolio_id = process.env.COINBASE_RETAIL_PORTFOLIO_ID;
    }
    const result = await client.createOrder(payload);
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
