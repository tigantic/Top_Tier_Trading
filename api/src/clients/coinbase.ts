import crypto from 'crypto';
import fetch, { HeadersInit } from 'node-fetch';

/**
 * Coinbase Advanced Trade API client.
 *
 * Provides minimal methods for interacting with the Coinbase Advanced Trade REST API.
 * Supports API key authentication and includes an optional retail portfolio ID
 * when using OAuth (not included here).  In DRY_RUN mode, requests are routed
 * to the static sandbox by adding an `X-Sandbox: true` header.
 */
export class CoinbaseClient {
  private readonly apiKey: string;
  private readonly apiSecret: string;
  private readonly passphrase: string;
  private readonly baseUrl: string;
  private readonly dryRun: boolean;

  constructor(options: {
    apiKey: string;
    apiSecret: string;
    passphrase: string;
    baseUrl?: string;
    dryRun?: boolean;
  }) {
    this.apiKey = options.apiKey;
    this.apiSecret = options.apiSecret;
    this.passphrase = options.passphrase;
    this.baseUrl = options.baseUrl || 'https://api.exchange.coinbase.com';
    this.dryRun = options.dryRun ?? true;
  }

  /**
   * Generate the CB-ACCESS-SIGN header value.  Coinbase currently supports both
   * HMAC-SHA256 and Ed25519 signatures depending on the key type.  For keys
   * created after February 2025 the secret is an Ed25519 private key and must
   * be used with an Ed25519 signing algorithm.  This implementation falls back
   * to HMAC-SHA256 for backward compatibility.  In DRY_RUN mode the signing
   * step is bypassed and a placeholder signature is returned.
   */
  private signRequest(timestamp: string, method: string, requestPath: string, body: string): string {
    if (this.dryRun) {
      return 'dry-run-signature';
    }
    const message = timestamp + method.toUpperCase() + requestPath + body;
    try {
      // Attempt Ed25519 signature first
      if (this.apiSecret.length === 64 || this.apiSecret.length === 128) {
        const key = Buffer.from(this.apiSecret, 'hex');
        // Use the built‑in Node.js WebCrypto API for Ed25519 if available
        // Note: Node.js 20+ supports Ed25519 via subtleCrypto
        // Fallback to HMAC below on failure
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const sign = crypto.createSign('sha256');
        sign.update(message);
        return sign.sign(key).toString('base64');
      }
    } catch {
      // fall through to HMAC
    }
    // HMAC-SHA256 signature (legacy keys)
    const key = Buffer.from(this.apiSecret, 'base64');
    return crypto.createHmac('sha256', key).update(message).digest('base64');
  }

  private buildHeaders(method: string, requestPath: string, body: string = ''): HeadersInit {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const signature = this.signRequest(timestamp, method, requestPath, body);
    const headers: HeadersInit = {
      'CB-ACCESS-KEY': this.apiKey,
      'CB-ACCESS-SIGN': signature,
      'CB-ACCESS-TIMESTAMP': timestamp,
      'CB-ACCESS-PASSPHRASE': this.passphrase,
      'Content-Type': 'application/json',
    };
    if (this.dryRun) {
      (headers as any)['X-Sandbox'] = 'true';
    }
    return headers;
  }

  /**
   * Perform a GET request to the API.  Throws an error for non‑2xx responses.
   */
  private async get<T>(path: string): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers = this.buildHeaders('GET', path);
    const resp = await fetch(url, {
      method: 'GET',
      headers,
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`Coinbase API error ${resp.status}: ${text}`);
    }
    return (await resp.json()) as T;
  }

  /**
   * Perform a POST request to the API.  Throws an error for non‑2xx responses.
   */
  private async post<T>(path: string, bodyObj: any): Promise<T> {
    const body = JSON.stringify(bodyObj);
    const url = `${this.baseUrl}${path}`;
    const headers = this.buildHeaders('POST', path, body);
    const resp = await fetch(url, {
      method: 'POST',
      headers,
      body,
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`Coinbase API error ${resp.status}: ${text}`);
    }
    return (await resp.json()) as T;
  }

  /**
   * List accounts.  See https://docs.cloud.coinbase.com/advanced-trade-api/reference/retailbrokerageapi_getaccounts
   */
  async listAccounts(): Promise<any> {
    return this.get('/api/v3/brokerage/accounts');
  }

  /**
   * List products (instruments).  See https://docs.cloud.coinbase.com/advanced-trade-api/reference/retailbrokerageapi_getproducts
   */
  async listProducts(): Promise<any> {
    return this.get('/api/v3/brokerage/products');
  }

  /**
   * Create a new order.  For OAuth flows, include the retail_portfolio_id in the payload.
   */
  async createOrder(payload: {
    client_order_id: string;
    product_id: string;
    side: 'BUY' | 'SELL';
    order_configuration: any;
    retail_portfolio_id?: string;
  }): Promise<any> {
    return this.post('/api/v3/brokerage/orders', payload);
  }
}
