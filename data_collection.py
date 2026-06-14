import requests
import json
import time
import os
from web3 import Web3
from datetime import datetime, timedelta

# ── Paramètres ────────────────────────────────────────────────────────────────
ANKR_KEY = "Ma clé Ankr"
POLYGON_RPC = f"https://rpc.ankr.com/polygon/{ANKR_KEY}"

CTF_EXCHANGE       = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982e"
NEG_RISK_EXCHANGE  = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
ORDER_FILLED_TOPIC = "0x" + Web3.keccak(text="OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)").hex()

BLOCK_START = 69_000_000 
BLOCK_END   = 72_500_000
BATCH_SIZE  = 100

# ── Token IDs cibles ──────────────────────────────────────────────────────────
with open("polymarket_markets_2023_2025.json") as f:
    markets = [m for m in json.load(f) if isinstance(m, dict)]

import pandas as pd
df = pd.DataFrame(markets)
df['volumeNum'] = pd.to_numeric(df['volumeNum'], errors='coerce').fillna(0)
df_sample = df.nlargest(3000, 'volumeNum')

target_tokens = set()
for _, row in df_sample.iterrows():
    tokens = row.get('clobTokenIds') or []
    if isinstance(tokens, str):
        try: tokens = json.loads(tokens)
        except: tokens = []
    for tid in tokens:
        target_tokens.add(int(tid))

print(f"Token IDs cibles : {len(target_tokens)}")

# ── Décodage ──────────────────────────────────────────────────────────────────
def decode_order_filled(log):
    data = bytes.fromhex(log['data'][2:])
    return {
        "block":          int(log['blockNumber'], 16),
        "timestamp":      int(log['blockTimestamp'], 16),
        "tx_hash":        log['transactionHash'],
        "maker":          "0x" + log['topics'][2][-40:],
        "taker":          "0x" + log['topics'][3][-40:],
        "maker_asset_id": int.from_bytes(data[0:32],   'big'),
        "taker_asset_id": int.from_bytes(data[32:64],  'big'),
        "maker_amount":   int.from_bytes(data[64:96],  'big') / 1e6,
        "taker_amount":   int.from_bytes(data[96:128], 'big') / 1e6,
        "fee":            int.from_bytes(data[128:160], 'big') / 1e6,
    }

# ── Fetch avec retry ──────────────────────────────────────────────────────────
def fetch_logs(contract, from_block, to_block, retries=3):
    for attempt in range(retries):
        try:
            r = requests.post(POLYGON_RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [{
                    "address": contract,
                    "topics": [ORDER_FILLED_TOPIC],
                    "fromBlock": hex(from_block),
                    "toBlock": hex(to_block)
                }],
                "id": 1
            }, timeout=60)
            data = r.json()
            if data.get('error'):
                return []
            return data.get('result', [])
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            print(f"Erreur bloc {from_block}: {e}")
            return []
    return []

# ── Pull ──────────────────────────────────────────────────────────────────────
CHECKPOINT = "checkpoint.json"
OUTPUT     = "onchain_trades.json"

all_trades = []
start_block = BLOCK_START

if os.path.exists(CHECKPOINT):
    with open(CHECKPOINT) as f:
        cp = json.load(f)
        start_block = cp['last_block']
        all_trades  = cp['trades']
    print(f"Reprise depuis bloc {start_block} | {len(all_trades)} trades")

total_blocks = BLOCK_END - BLOCK_START

for from_block in range(start_block, BLOCK_END, BATCH_SIZE):
    to_block = min(from_block + BATCH_SIZE, BLOCK_END)

    for contract in [CTF_EXCHANGE, NEG_RISK_EXCHANGE]:
        for log in fetch_logs(contract, from_block, to_block):
            try:
                t = decode_order_filled(log)
                if t['maker_asset_id'] in target_tokens or t['taker_asset_id'] in target_tokens:
                    all_trades.append(t)
            except:
                pass

    if (from_block - BLOCK_START) % (10000 * BATCH_SIZE) == 0:
        pct = (from_block - BLOCK_START) / total_blocks * 100
        print(f"bloc {from_block} | {pct:.1f}% | trades={len(all_trades)}")
        with open(CHECKPOINT, 'w') as f:
            json.dump({'last_block': from_block, 'trades': all_trades}, f)

with open(OUTPUT, 'w') as f:
    json.dump(all_trades, f)

print(f"Done : {len(all_trades)} trades sauvegardés")



all_markets = []

# Générer les tranches mensuelles 2023-01 → 2025-12
start = datetime(2023, 1, 1)
end = datetime(2026, 1, 1)

current = start
while current < end:
    next_month = current + relativedelta(months=1)
    date_min = current.strftime("%Y-%m-%d")
    date_max = next_month.strftime("%Y-%m-%d")
    
    offset = 0
    limit = 500
    month_total = 0
    
    while True:
        r = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={
                "limit": limit,
                "offset": offset,
                "closed": "true",
                "start_date_min": date_min,
                "start_date_max": date_max,
                "order": "createdAt",
                "ascending": "true"
            }
        )
        data = [m for m in r.json() if isinstance(m, dict)]
        if not data:
            break
        
        all_markets.extend(data)
        month_total += len(data)
        
        if len(data) < limit:
            break
        offset += limit
        time.sleep(0.05)
    
    print(f"{date_min} → {date_max} : {month_total} marchés | total={len(all_markets)}")
    current = next_month

print(f"\nTotal final : {len(all_markets)}")
