# FireDashboard

個人台美股資產與 Coast FIRE 追蹤儀表板。單機 Docker Compose：Vue 3 + FastAPI + SQLite。
完整規格見 [SPEC.md](SPEC.md)。

## 啟動

```bash
docker compose up -d --build
```

打開 <http://localhost:8080>。資料庫在 `./data/fire.db`，備份只要複製這個檔案。

第一次啟動後端會抓近 2 年的報價、股息與匯率；之後每天 06:30（美股收盤後）與 14:30（台股收盤後）自動更新，重開機或 Docker 停機幾天後，啟動時也會自動補齊。

> 只綁定 `127.0.0.1`，沒有登入機制。要放到 NAS 或外網前，請先加上有帳密的 reverse proxy。

## 使用方式

1. 右上「參數設定」填入出生年月、退休年齡、年開銷、SWR、報酬率、通膨與每月投入。
2. 「新增標的」輸入代號：台股只要打數字（`0050`、`00687B`），會自動判斷上市 `.TW` 或上櫃 `.TWO`；美股直接打 `VOO`、`SSO`。
3. 每次買賣按該列的「記錄」，可以指定過去的日期補登，歷史淨值會自動重算。
4. 股息依除息日持股自動計入現金：美股先扣 30% 預扣稅，台股單筆 ≥ 2 萬再扣 2.11% 二代健保（都可在設定調整）。

## 開發

```bash
# 後端
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest                      # 單元測試
uvicorn app.main:app --reload

# 前端（另一個終端機）
cd frontend
npm install
npm run dev                 # http://localhost:5173，/api 代理到 localhost:8000
```

環境變數：`FIRE_DB_PATH`（預設 `./data/fire.db`）、`FIRE_DISABLE_SCHEDULER=1`（關閉排程與啟動回補）。

## 關於 Yahoo 的資料

- Yahoo 的 `Close` 已經做過分割調整。系統保存 Yahoo 原值，計算淨值時再依分割紀錄換回當天的實際成交價，所以「實際股數 × 價格」在分割前後都正確。
- 少數台股分割 Yahoo 沒有列出事件（例如 0050 在 2025-06-18 的 1 拆 4，已內建）。遇到其他的，到該標的的「編輯」裡補上分割日期與比例。
- yfinance 是非官方 API，偶爾會被限流。失敗時頁面上方會顯示「部分標的更新失敗」，下一次排程會再試。
