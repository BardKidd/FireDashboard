# 部署到 Google Cloud 免費主機（e2-micro）

讓 FireDashboard 24 小時開在 Google Cloud 的永久免費主機上，自己的電腦關機或睡眠都不影響。

對外連線一樣用 Cloudflare Tunnel + Cloudflare Access（email 驗證碼登入），**不需要開任何對外的埠**。Cloudflare 那段的設定和 [deploy-oracle.md](deploy-oracle.md) 第 8～10 節完全一樣，這份只寫 Google Cloud 這邊不同的地方。

2026-11-12 實際照這份從 OrbStack 上的 Linux VM 搬到 Google Cloud。介面以那時的 Google Cloud Console 為準。

---

## 免費額度（Always Free，2026 年 11 月）

每個帳單帳戶每個月都有，沒有期限（不是新帳號那 90 天、300 美元的試用額度）：

| 項目 | 免費額度 |
| --- | --- |
| 主機 | **1 台 e2-micro** 跑整個月，只限 `us-west1`、`us-central1`、`us-east1` |
| 硬碟 | **30 GB Standard persistent disk** |
| 快照 | 5 GB |
| 對外流量 | 每月 1 GB（傳到中國、澳洲不算） |

e2-micro 是 2 個共用 vCPU、1 GB 記憶體。FireDashboard 平常只用 0.3 GB 左右，夠用，但 **build image 時需要 swap**（見第 4 節）。

要守的規則：

- 只開**一台** e2-micro，第二台就會收錢。
- 開機磁碟一定要選 **Standard**，預設的 Balanced 會收錢。
- 不要開自動快照、不要裝 Ops Agent（見第 3 節）。
- 建立主機時，右邊的月費估算會顯示約 6 美元，那是原價，帳單結算時會用免費額度抵掉。

額度會變動，以[官方說明](https://cloud.google.com/free/docs/free-cloud-features#compute)為準。

> 主機的對外 IPv4（ephemeral）是否會被收一點費用，官方文件寫得不清楚。tunnel 需要主機能連外，所以保留預設的對外 IP，靠下一節的預算警示把關，開好後一兩天去 Billing 看一下實際費用。

---

## 1. 註冊並綁定帳單

1. 到 <https://cloud.google.com/free> 按「免費開始使用」，用 Google 帳號登入，國家選台灣，綁信用卡。
2. 進到 Console 後，畫面上方如果有「Enable billing」橫幅，按它建立帳單帳戶。
3. **確認帳單帳戶有連到專案**：搜尋列輸入 `Billing`，如果顯示「This project has no billing account」，按 **Link a billing account** → 選剛建立的帳戶 → **Set account**。
   沒連的話，下一步啟用 Compute Engine 會出現 `Billing account for project ... is not found` 錯誤。

## 2. 設預算警示

左邊選單 **Billing → Budgets & caps → Create budget**：

1. 選 **Alerts only**，名稱例如 `free-dashboard-guard`。
   不要選 Spend cap enforcement：它只支援部分服務，而且一觸發就會暫停服務，儀表板會斷線。
2. Scope 用預設（Monthly、全部專案、全部服務）。
3. Amount 選 **Specified amount**，填 `1`（美元）。
4. Actions 用預設的 50% / 90% / 100%，寄 email 給帳單管理員 → **Finish**。

這個月被收超過 0.5 美元就會收到信。

## 3. 建立主機

1. 直接打開 <https://console.cloud.google.com/compute/instances>，第一次會要你啟用 **Compute Engine API**，按 Enable，等一兩分鐘。
   （用搜尋列找時小心，容易點到 Gemini / AI Applications 的頁面，那個不用啟用。）
2. 按 **Create instance**，照左邊分頁一頁一頁填：

| 分頁 | 設定 |
| --- | --- |
| Machine configuration | Name `fire-dashboard`；Region **us-west1 (Oregon)**（三個免費區域裡離台灣最近）；Zone 預設；系列 **E2**；Machine type **e2-micro** |
| OS and storage | 按 Change：**Ubuntu 24.04 LTS Minimal**（x86/64）、**Standard persistent disk**、**30 GB** |
| Data protection | **No backups**（預設的每日快照很快會超過 5 GB 免費量） |
| Networking | 預設；**不要**勾 Allow HTTP / HTTPS traffic |
| Observability | **取消勾選** Install Ops Agent（常駐吃 100～200 MB 記憶體，監控資料也可能收費） |
| Security / Advanced | 預設 |

3. 確認右邊估算只剩「2 vCPU + 1 GB memory」和「30 GB standard persistent disk $0.00」兩行，按 **Create**，等名稱前出現綠色勾勾。

## 4. 連進主機、加 swap、裝 Docker

在 VM 列表按那台主機的 **SSH** 按鈕，會開一個瀏覽器終端機（第一次要按 Authorize）。不用自己管 SSH 金鑰。

加 2 GB swap（重開機也會自動啟用）：

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab && free -h
```

裝 Docker 和 git（約 3～5 分鐘，中間很久沒輸出是正常的）：

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git && curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER
```

**關掉 SSH 視窗再重開一個**（讓 docker 群組生效），確認：

```bash
docker compose version
```

登入時看到「New release 26.04 available」不用理，24.04 支援到 2029 年。

## 5. 拉程式碼、先 build

```bash
git clone https://github.com/BardKidd/FireDashboard.git && cd FireDashboard && docker compose build
```

e2-micro 很慢，大約要 **13 分鐘**，前端那段停很久是正常的。這步不會啟動服務，可以在舊主機還開著時先做。

## 6. 搬資料

要搬的只有兩個檔案（都不在 git 裡）：

- `data/fire.db`：所有持股、紀錄、設定
- `.env`：埠號和 Cloudflare Tunnel token

**先在舊主機停掉服務**。新舊兩台用同一個 tunnel token，同時開著的話 Cloudflare 會把連線分給兩台，資料就會分岔：

```bash
cd ~/Projects/FireDashboard && docker compose down
```

（`down` 只停容器，不會刪資料。）

把兩個檔案放到開 Google Cloud 網頁的那台電腦上。舊主機如果是 Mac 上的 OrbStack Linux 機器，Mac 的資料夾已經掛在 `/mnt/mac` 底下，在舊主機上直接複製到 Mac 的 Downloads：

```bash
for d in /mnt/mac/Users/*/Downloads; do cp data/fire.db "$d/fire.db" && cp .env "$d/fire.env" && echo "已複製到 $d"; done
```

`.env` 存成 `fire.env`，因為 Mac 的選檔視窗會隱藏點開頭的檔案。舊主機在別台機器的話，改用 `scp 主機:路徑 ~/Downloads/` 抓回來。

回到 Google Cloud 的 SSH 視窗，右上角 **UPLOAD FILE** 分別上傳 `fire.db` 和 `fire.env`（會放在家目錄），再放到正確位置。`data/` 被 .gitignore 排除，clone 下來時不存在，要先建：

```bash
mkdir -p ~/FireDashboard/data && mv ~/fire.env ~/FireDashboard/.env && mv ~/fire.db ~/FireDashboard/data/fire.db && ls -la ~/FireDashboard/.env ~/FireDashboard/data/
```

確認 `fire.db` 的大小和舊主機上一樣。

## 7. 啟動

```bash
cd ~/FireDashboard && docker compose up -d && sleep 45 && docker compose ps
```

四個容器（backend、frontend、cloudflared、tunnel-watchdog）都要是 Up，cloudflared 要是 **healthy**。`.env` 裡的 `COMPOSE_FILE` 已經包含 tunnel 設定，Cloudflare 那邊的路由（`http://frontend:80`）和 Access 登入規則都不用改，同一條 tunnel 換到新主機上接手而已。

打開 `https://fire.你的網域`，登入後確認資料是最新的。

確認沒問題後，舊主機**不要再** `docker compose up`。舊的 `fire.db` 可以留著當備份。

## 8. 自動更新（合併到 main 後自動部署）

GitHub 上每次有新的 commit 進到 main，GitHub Actions（`.github/workflows/images.yml`）會先跑後端測試，通過後把 backend、frontend 兩個 image 建好，放到 GitHub Container Registry（`ghcr.io/bardkidd/firedashboard-backend`、`-frontend`）。主機每 5 分鐘檢查一次，有新版而且那個 commit 的 image 已經建好，就自動 `git pull`、下載 image、重開容器。

- 主機不用自己 build（原本要 10～20 分鐘、吃滿記憶體），更新只要下載，一兩分鐘。
- 主機不需要開任何埠給 GitHub，GitHub 也不用存主機的金鑰，是主機自己去拉。
- 測試沒過時 image 不會產生，主機就停在舊版。

### 8.1 把 image 設成 Public（只要做一次）

GitHub 第一次建好 image 時，預設是 Private，主機沒登入就拉不到。到 GitHub 個人頁面的 **Packages** 分頁，分別點 `firedashboard-backend` 和 `firedashboard-frontend` → 右邊 **Package settings** → 最下面 **Change visibility** → **Public**。

程式碼本來就是公開的，image 裡只有程式，不含 `data/` 和 `.env`。

### 8.2 在主機上安裝自動更新

```bash
cd ~/FireDashboard && git pull && bash deploy/install-auto-deploy.sh
```

會建立 `fire-auto-deploy.timer`（開機 2 分鐘後開始，之後每 5 分鐘一次），並立刻跑一次。

看紀錄：`sudo journalctl -u fire-auto-deploy -n 30 --no-pager`
暫停自動更新：`sudo systemctl disable --now fire-auto-deploy.timer`

主機上不要直接改 repo 裡的檔案，不然 `git merge --ff-only` 會失敗，自動更新會卡住（紀錄裡會看到錯誤）。

---

## 日常維護

| 想做的事 | 在 SSH 視窗執行 |
| --- | --- |
| 更新到最新版 | 裝了第 8 節的自動更新就不用管；手動更新用 `bash ~/FireDashboard/deploy/auto-deploy.sh` |
| 看自動更新紀錄 | `sudo journalctl -u fire-auto-deploy -n 30 --no-pager` |
| 看 tunnel 狀態 | `docker compose ps`、`docker compose logs tunnel-watchdog \| tail` |
| 備份資料到自己電腦 | SSH 視窗右上角 **DOWNLOAD FILE**，路徑填 `/home/你的帳號/FireDashboard/data/fire.db` |

每天自動在主機上留一份備份（保留 30 天），執行 `crontab -e` 加上：

```cron
15 4 * * * mkdir -p ~/backups && cp ~/FireDashboard/data/fire.db ~/backups/fire-$(date +\%F).db && find ~/backups -name 'fire-*.db' -mtime +30 -delete
```

主機上的時區是 UTC，這行是台灣時間中午 12:15 執行。
