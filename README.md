# Informed Trading in Prediction Markets

Empirical analysis of Polymarket on-chain data: replication of Gomez-Cram et al. (2026) and exploration of traditional-market stylized facts on prediction-market prices.

## Overview

This project collects and analyzes raw on-chain trading data from Polymarket, a decentralized prediction market operating on the Polygon blockchain. The goal is to test whether prediction markets exhibit the same statistical properties as traditional financial markets, and to replicate key results from recent academic work on informed trading in event-driven environments.

## Data

| File | Description |
|---|---|
| `onchain_trades.parquet` | 8.7M raw on-chain trades scraped from Polygon RPC (blocks 69M+) via Ankr |
| `onchain_trades.csv` | Same dataset in CSV format |
| `polymarket_markets_2023_2025.json` | Market metadata for 1,539 markets / 279 events fetched from the GAMMA API |

**Coverage:** March–June 2025 · ~$1.6B total volume · 395k unique wallets

Prices are constructed as `usdc_amount / share_amount` per trade, aggregated to the last hourly price per market, with gaps forward-filled.

## Analyses

### 1. Market microstructure
- Daily trading volume (aggregated USDC) across ~1,539 markets
- Daily unique active accounts (taker addresses)
- Account-level volume distribution by percentile (log scale) — p99/p50 gap of ~3 orders of magnitude, consistent with a Pareto distribution

### 2. Stylized facts
- **Fat tails:** hourly log-return distributions vs fitted normal, for the 10 most liquid markets
- **Volatility clustering:** 24h rolling volatility per market; visual clustering confirmed
- **Ljung-Box test on squared returns** (lag 5): 1,029/1,337 markets reject H₀ at 5% (77%), median p-value = 3e-8
- **GARCH(1,1)-t fit** on 479 converged markets: median persistence (α+β) = 0.87, 46% of markets > 0.9 — slow volatility decay consistent with high vol carry

### 3. Figure 1 replication
Replication of the aggregate daily volume figure from Gomez-Cram et al. (2026), showing volume spikes around major political and macroeconomic events.

## Stack

```
Python 3.9 · pandas · numpy · scipy · arch · statsmodels · web3.py · matplotlib
```

Data collection: Polygon RPC via Ankr (block-level scraping) + GAMMA API (market metadata)

## Notes

- GARCH fits on markets with fewer than 100 observations are excluded; the 479 converged markets are biased toward liquid ones
- Markets trading near 0 or 1 (resolved) are filtered out before GARCH fitting to avoid degenerate series
- The 23% of markets not showing volatility clustering are likely illiquid (too few trades for meaningful time series)
