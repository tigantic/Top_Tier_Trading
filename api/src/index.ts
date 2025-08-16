import express from 'express';
import { healthRouter } from './routes/health';
import coinbaseRouter from './routes/coinbase';
import sseRouter from './routes/sse';

// Create the Express application
const app = express();

// Basic JSON parsing middleware
app.use(express.json());

// Health check endpoint
app.use('/healthz', healthRouter);

// API routes for Coinbase integration
app.use('/api', coinbaseRouter);

// Streaming routes (SSE)
app.use('/api/streams', sseRouter);

// Root endpoint
app.get('/', (_req, res) => {
  res.status(200).json({ message: 'Welcome to the Trading Platform API' });
});

// Start the server
const port = Number(process.env.PORT || 8000);
app.listen(port, () => {
  console.log(`API service listening on port ${port}`);
});
