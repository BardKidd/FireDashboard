# 部署到 Oracle Cloud 免費主機

讓 FireDashboard 24 小時開在雲端，手機隨時連得到，自己的電腦關機也沒關係。

整個流程分成兩段：

1. **把 FireDashboard 跑在 Oracle 主機上**（這份文件）。做完時只有你自己透過 SSH 看得到它，外面的人連不進來。
2. **加上 https 和登入**，讓手機能從外面連進來（另一份文件，看你選哪種登入方式）。

第 1 段做完、確認一切正常，再做第 2 段。登入還沒設好之前，**不要**把 `.env` 的 `FIRE_BIND` 改成 `0.0.0.0`，也不要在 Oracle 開放 80、443 以外的埠。

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

## 下一步：從手機連進來

到這裡 FireDashboard 已經在雲端 24 小時跑著了，但還沒有對外開放。接下來加上 https 網址和登入，手機就能從任何地方連進來，也能「加到主畫面」並離線看資料。
