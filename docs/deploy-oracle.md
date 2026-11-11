# 部署到 Oracle Cloud 免費主機

讓 FireDashboard 24 小時開在雲端，手機隨時連得到，自己的電腦關機也沒關係。

整個流程分成兩段：

1. **把 FireDashboard 跑在 Oracle 主機上**（第 1～7 節）。做完時只有你自己透過 SSH 看得到它，外面的人連不進來。
2. **用 Cloudflare 開一個 https 子網址，並加上 email 驗證碼登入**（第 8～10 節），手機就能從任何地方連進來。

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

## 8. 建立 Cloudflare Tunnel

Tunnel 是主機上的一個小程式，它主動連到 Cloudflare，手機連 `https://fire.你的網域` 時，Cloudflare 再沿著這條線把連線送回主機。主機不用開任何埠，也不用固定 IP。

以下假設你的網域已經在 Cloudflare 上管理。新增子網址不會影響網域底下原本的網站或專案。

1. 登入 Cloudflare，左邊選單點 **Zero Trust**。
   - 第一次進來會要你取一個 team name（隨便取，例如 `valens`），方案選 **Free**。Free 方案可能也要求填付款方式，但 50 人以內不收費。
2. **Networks → Tunnels**（新版介面可能叫 **Connectors**）→ **Create a tunnel** → 選 **Cloudflared**。
3. 名稱填 `firedashboard` → **Save tunnel**。
4. 安裝方式選 **Docker**，畫面上會出現一行 `docker run ... --token eyJ...`。**只複製 `--token` 後面那一長串**，這就是 token。它等同於這條通道的鑰匙，不要貼到別的地方。
5. 按 **Next**，設定 **Public hostname**：
   - Subdomain：`fire`
   - Domain：選你的網域
   - Service Type：`HTTP`
   - URL：`frontend:80`
6. **Save tunnel**。

回到 Oracle 主機，編輯 `.env`（`nano ~/FireDashboard/.env`），把最下面兩行的 `#` 拿掉並貼上 token：

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.tunnel.yml
CF_TUNNEL_TOKEN=eyJ...（剛剛複製的 token）
```

存檔，**先不要啟動**，接著做第 9 節把登入設好。

---

## 9. 加上 email 驗證碼登入（Cloudflare Access）

1. Zero Trust → **Access → Applications** → **Add an application** → **Self-hosted**。
2. **Application name**：`FireDashboard`。
3. **Application domain**：Subdomain `fire`，Domain 選你的網域。
4. **Session Duration** 選 **1 month**，這樣手機一個月才需要重新登入一次。
5. 下一步建立 **Policy**：
   - Policy name：`只有我`
   - Action：**Allow**
   - Include → Selector 選 **Emails**，填你自己的 email。
6. 登入方式維持預設的 **One-time PIN**，存檔。

之後想讓家人也能看，回到這個 Policy 多加一個 email 就好。

### 啟動 Tunnel

登入設好了，回到 Oracle 主機啟動：

```bash
cd ~/FireDashboard && docker compose up -d
docker compose logs cloudflared | tail
```

看到 `Registered tunnel connection` 就代表接上了，Cloudflare 的 Tunnel 頁面也會顯示 **Healthy**。

測試：用無痕視窗打開 `https://fire.你的網域`，應該先看到 Cloudflare 的登入頁。填你的 email，信箱會收到 6 位數驗證碼，輸入後才會看到 FireDashboard。換一個沒加進名單的 email 試試，應該收不到碼也進不去。

---

## 10. 手機加到主畫面

1. 手機瀏覽器打開 `https://fire.你的網域`，用 email 驗證碼登入。
2. 加到主畫面：
   - **iPhone**：Safari 下方的「分享」→「加入主畫面」。
   - **Android**：Chrome 右上「⋮」→「安裝應用程式」或「加到主畫面」。
3. 從主畫面打開營火圖示。iPhone 的主畫面 App 和 Safari 是分開記住登入的，所以**第一次從主畫面打開時要再登入一次**，之後一個月內都不用。

現在是 https，離線功能也會啟用：沒有網路時打開，會顯示最後一次的資料，並標註是幾點的資料。

登入過期時，App 會自動重新整理並帶你回 Cloudflare 的登入頁，重新收一次驗證碼就好。
