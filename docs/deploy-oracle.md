# 部署到 Oracle Cloud 免費主機

讓 FireDashboard 24 小時開在雲端，手機隨時連得到，自己的電腦關機也沒關係。

整個流程分成兩段：

1. **把 FireDashboard 跑在 Oracle 主機上**（第 1～7 節）。做完時只有你自己透過 SSH 看得到它，外面的人連不進來。
2. **用 Cloudflare 開一個 https 子網址，並加上 email 驗證碼登入**（第 8～10 節），手機就能從任何地方連進來。這一段也可以單獨用在自己家裡一直開著的機器上。

第 1 段做完、確認一切正常，再做第 2 段。整個過程**不需要**在 Oracle 開放任何對外的埠，`.env` 的 `FIRE_BIND` 也一直維持 `127.0.0.1`。

---

## 免費額度（2026 年 11 月）

| 項目 | 免費額度 |
| --- | --- |
| ARM 主機（Ampere A1） | 合計 2 核心、12 GB 記憶體 |
| 硬碟 | 合計 200 GB |
| 對外流量 | 每月 10 TB |

FireDashboard 只需要大約 0.3 GB 記憶體，開一台 1 核心、6 GB 的主機就綽綽有餘，剩下的額度留著以後用。

Oracle 的額度會變動，以[官方說明](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm)為準。

---

## 1. 註冊 Oracle Cloud

1. 到 <https://www.oracle.com/cloud/free/> 按「Start for free」。
2. 填 email、國家選 Taiwan，照畫面驗證 email。
3. **Home Region（主區域）選 `Japan Central (Osaka)`**。
   - 這個之後**不能改**，免費主機只能開在主區域。
   - 台灣沒有 Oracle 機房，大阪從台灣連過去很快。東京常常搶不到免費主機，所以選大阪。
4. 綁信用卡。Oracle 會先刷一筆小額授權確認卡片有效，之後會退回。
5. 等它說帳號建立完成（有時候要十幾分鐘），登入 Oracle Cloud Console。

### 建議：升級成「隨用隨付」

免費帳號的主機如果連續 7 天 CPU、網路、記憶體使用率都很低，Oracle 可能會把它回收。FireDashboard 平常很閒，很容易被判定成閒置。

升級成 Pay As You Go 後，只要用量在免費額度內一樣不收錢，主機也不會因為閒置被收回：

1. Console 右上角頭像 → **Billing & Cost Management** → **Upgrade and Manage Payment** → 選 **Pay As You Go**。
2. 升級後**一定要設預算警示**，萬一不小心開了收費資源會馬上收到通知：
   **Billing & Cost Management → Budgets → Create Budget**，金額填 `1`（美元），警示門檻 `1%`，填你的 email。

---

## 2. 開一台主機

1. Console 左上選單 → **Compute** → **Instances** → **Create instance**。
2. **Name**：`firedashboard`。
3. **Image and shape** 按 **Edit**：
   - Image：**Canonical Ubuntu 24.04**（選有 `aarch64` 字樣的版本）。
   - Shape：**Ampere** → **VM.Standard.A1.Flex**，OCPU 填 `1`、記憶體填 `6` GB。
   - 確認旁邊有「Always Free-eligible」標籤。
4. **Networking**：選「Create new virtual cloud network」，subnet 選 public，並勾選 **Assign a public IPv4 address**。
5. **Add SSH keys**：選「Generate a key pair for me」，按 **Save private key** 把私鑰存下來（例如存成 `~/.ssh/oracle-fire.key`）。這把鑰匙不見就連不進主機了，請好好保存。
6. **Boot volume**：預設就好。
7. 按 **Create**。

如果出現 **Out of capacity**，代表那個機房的免費主機暫時被搶光了。可以換一個 Availability Domain 再試，或隔幾個小時再按一次，通常一兩天內就搶得到。

建立好後，在主機頁面記下 **Public IP address**。

---

## 3. 用 SSH 連進主機

在你的 Linux VM 或任何有終端機的電腦上：

```bash
chmod 600 ~/.ssh/oracle-fire.key
ssh -i ~/.ssh/oracle-fire.key ubuntu@<主機的 Public IP>
```

第一次會問要不要信任這台主機，輸入 `yes`。

---

## 4. 安裝 Docker

在主機上執行：

```bash
sudo timedatectl set-timezone Asia/Taipei
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit
```

重新 SSH 連進去（讓 docker 群組生效），確認：

```bash
docker run --rm hello-world
```

看到「Hello from Docker!」就成功了。

---

## 5. 把 FireDashboard 跑起來

```bash
git clone https://github.com/BardKidd/FireDashboard.git
cd FireDashboard
cp .env.example .env
docker compose up -d --build
```

`.env` 維持預設的 `FIRE_BIND=127.0.0.1`，代表只有主機自己能連，外面連不進來。第一次建置 ARM 版本大約要 5 到 10 分鐘。

### 搬現有的資料過去

如果你的 Linux VM 上已經有在用的資料，把 `fire.db` 複製過去：

```bash
# 在 Oracle 主機上：先停下來
cd ~/FireDashboard && docker compose down

# 在你的 Linux VM 上：把資料複製到 Oracle 主機
scp -i ~/.ssh/oracle-fire.key ./data/fire.db ubuntu@<主機的 Public IP>:~/FireDashboard/data/

# 回到 Oracle 主機上：再啟動
cd ~/FireDashboard && docker compose up -d
```

### 先從自己電腦看一眼

登入還沒設好前，用 SSH 通道從自己電腦看：

```bash
ssh -i ~/.ssh/oracle-fire.key -L 8080:localhost:8080 ubuntu@<主機的 Public IP>
```

這個視窗開著的時候，在自己電腦的瀏覽器打開 <http://localhost:8080>，看到的就是 Oracle 上的 FireDashboard。

---

## 6. 每天自動備份

在主機上執行 `crontab -e`，最後加一行：

```cron
15 4 * * * mkdir -p ~/backups && cp ~/FireDashboard/data/fire.db ~/backups/fire-$(date +\%F).db && find ~/backups -name 'fire-*.db' -mtime +30 -delete
```

每天凌晨 4:15 複製一份資料，保留最近 30 天。

偶爾也把備份抓回自己電腦一份，萬一主機出事還有得救：

```bash
scp -i ~/.ssh/oracle-fire.key "ubuntu@<主機的 Public IP>:~/backups/*" ./fire-backups/
```

---

## 7. 之後要更新程式

```bash
cd ~/FireDashboard && git pull && docker compose up -d --build
```

---

## 8. 建立 Cloudflare Tunnel 並啟動

Tunnel 是主機上的一個小程式，它主動連到 Cloudflare，手機連 `https://fire.你的網域` 時，Cloudflare 再沿著這條線把連線送回主機。主機不用開任何埠，也不用固定 IP。

> 第 8～10 節不限定 Oracle。在家裡的 Linux VM、NAS 或任何一直開著、裝了 Docker 的機器上，步驟都一樣（2026-11-11 就是先在自己的 VM 上照這三節上線的）。

以下假設你的網域已經在 Cloudflare 上管理。新增子網址不會影響網域底下原本的網站或專案。介面以 2026 年 11 月的 Cloudflare 為準。

1. 登入 Cloudflare，左邊選單點 **Zero Trust**。
   - 第一次進來會要你取一個 team name，方案選 **Free**（50 人以內不收費）。
2. **Networks → Tunnels** → **Create Tunnel** → 選 **Cloudflared** → 名稱填 `firedashboard`。
3. 作業系統選 **Docker**，畫面上會出現一行 `docker run ... --token eyJ...`。**只複製 `--token` 後面那一長串**，這就是 token。它等同於這條通道的鑰匙，不要貼到任何地方（包括聊天）。
4. 這個頁面先開著，**Continue 要等通道連上才能按**。

回到主機，編輯 `.env`（`nano ~/FireDashboard/.env`），在最下面加上這兩行（`.env.example` 裡也有範本）：

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.tunnel.yml
CF_TUNNEL_TOKEN=eyJ...（剛剛複製的 token）
```

`COMPOSE_FILE` 的意思是「啟動時除了原本的設定，也把 Cloudflare Tunnel 一起開起來」。存檔（`Ctrl+O` → Enter → `Ctrl+X`）後啟動：

```bash
cd ~/FireDashboard && git pull && docker compose up -d --build
docker compose logs cloudflared | tail
```

幾秒後回到 Cloudflare 的頁面，會顯示已連線，Tunnels 列表也會顯示 **Healthy**。這時還沒設定網址，外面連不進來，所以先啟動是安全的。

---

## 9. 先設登入，再開放網址

順序很重要：**先建立登入規則，再加網址路由**，這樣網址一開通，前面就已經有登入擋著。

### 9-1. 建立 Access 應用程式（登入規則）

1. Zero Trust → **Access controls → Applications** → **Create new application**。
2. 上方選 **Self-hosted and private**，下面那排選 **Public DNS** → **Continue with Self-hosted and private**。
3. **Public hostnames**：Subdomain 填 `fire`，Domain 選你的網域，Path 空白。
4. **Access policies** → **Create new policy**：
   - Policy Name：`Only Me`
   - Action：**Allow**
   - Policy session duration：維持 `Same as application session duration`
   - 左邊 **Include** 的 Selector 選 **Emails**，填你收得到信的 email，按 Enter → **Save policy**。
5. 往下到 **Details**：Name 填 `fire`，**Session Duration 選 1 month**（預設 24 小時，等於每天要收一次驗證碼）。
6. 存檔。回到 Applications 列表，應該看到 `fire`，Destinations 是 `fire.你的網域`，Policies 是 `Only Me`。

之後想讓家人也能看，到 **Access controls → Policies → Only Me** 多加一個 email 就好。

### 9-2. 加網址路由

1. Zero Trust → **Networks → Tunnels** → 點 `firedashboard` → **Add route** → 選 **Published application**。
2. 填：
   - **Subdomain**：`fire`（**一定要填**。留空會把整個網域都轉到 FireDashboard，蓋掉網域上原本的東西）
   - **Domain**：你的網域
   - **Path**：空白
   - **Service URL**：`http://frontend:80`
3. 確認 **Full hostname** 是 `fire.你的網域` → **Add route**。Cloudflare 會自動建好 DNS。

`frontend:80` 是什麼：cloudflared 和 FireDashboard 都跑在同一個 docker compose 網路裡，容器之間用服務名稱互找。`frontend` 是前端 nginx 的服務名稱，`80` 是它在容器裡聽的埠。不能填 `localhost:8080`，因為對 cloudflared 容器來說 localhost 是它自己。

### 9-3. 測試

用無痕視窗打開 `https://fire.你的網域`（DNS 剛建好，打不開就等一兩分鐘）。應該先看到 **Cloudflare Access** 的登入頁：填 Only Me 規則裡的那個 email → **Send login code** → 輸入信裡的 6 位數驗證碼，之後才會看到 FireDashboard。

填其他 email 時，Cloudflare 一樣會顯示已寄出，但不會真的寄信，這是為了不讓別人猜出哪些 email 有權限。

### 換 token

token 如果不小心外流（例如貼到聊天裡），到 Tunnel 頁面按 **Rotate token**，把新的貼進 `.env` 的 `CF_TUNNEL_TOKEN`，再執行 `docker compose up -d`。

### 主機睡眠後自動重連

主機睡眠或 VM 被暫停再醒來時，容器都還顯示 Up，但 tunnel 的連線其實已經斷了，外面會連不進來。開了 tunnel 之後會多一個 `tunnel-watchdog` 小容器自動處理這件事，不用另外設定：

- 它發現時間一下跳了一大段（代表整台機器剛睡過），等 5 秒讓網路恢復，就重新啟動 cloudflared。
- cloudflared 自己的健康檢查連續失敗（約 1.5 分鐘連不上 Cloudflare）時，也會重新啟動它。

想看它做過什麼：

```bash
docker compose logs tunnel-watchdog | tail
```

醒來後看到 `clock jumped ...` 和 `cloudflared restarted` 就是它自動重連了。想不睡覺先測試，可以把它暫停一分半再恢復，效果和主機睡眠一樣：

```bash
docker compose pause tunnel-watchdog && sleep 90 && docker compose unpause tunnel-watchdog
sleep 20 && docker compose logs tunnel-watchdog | tail -3
```

它需要讀寫 `/var/run/docker.sock` 才能重啟 cloudflared，只會動同一個 compose 專案裡的 cloudflared。

---

## 10. 手機加到主畫面

1. 手機瀏覽器打開 `https://fire.你的網域`，用 email 驗證碼登入。
2. 加到主畫面：
   - **iPhone**：Safari 下方的「分享」→「加入主畫面」。
   - **Android**：Chrome 右上「⋮」→「安裝應用程式」或「加到主畫面」。
3. 從主畫面打開營火圖示。iPhone 的主畫面 App 和 Safari 是分開記住登入的，所以**第一次從主畫面打開時要再登入一次**，之後一個月內都不用。

現在是 https，離線功能也會啟用：沒有網路時打開，會顯示最後一次的資料，並標註是幾點的資料。

登入過期時，App 會自動重新整理並帶你回 Cloudflare 的登入頁，重新收一次驗證碼就好。
