# 让所有人访问你的扭蛋机（部署指南）

## 方式一：Streamlit 官方云（推荐，免费）

**适合**：希望任何人通过链接就能打开，无需你自己开电脑。

1. **把项目推到 GitHub**
   - 在 [GitHub](https://github.com) 新建一个仓库（如 `waimai-gashapon`）。
   - 在项目目录执行：
     ```bash
     git init
     git add .
     git commit -m "init"
     git remote add origin https://github.com/你的用户名/waimai-gashapon.git
     git push -u origin main
     ```
   - 若已有仓库，直接 `git push` 即可。

2. **在 Streamlit Cloud 部署**
   - 打开 [share.streamlit.io](https://share.streamlit.io)，用 GitHub 登录。
   - 点 “New app”，选你的仓库、分支（如 `main`）。
   - **Main file path** 填：`app.py`。
   - 点 “Deploy”，等几分钟。
   - 完成后会得到一个公网链接，例如：`https://xxx.streamlit.app`，**把链接发给别人即可访问**。

3. **注意**
   - 数据（`data/records.db`）在云端是独立的，每人/每次部署一份，不会和你本机混用。
   - 免费版应用一段时间不用会休眠，首次打开可能稍慢。

---

## 方式二：同一 WiFi 下的人访问（本机开放）

**适合**：同事/家人连的是你家或公司同一个 WiFi，只想临时一起用。

1. 在项目目录启动时加上 `--server.address 0.0.0.0`：
   ```bash
   streamlit run app.py --server.address 0.0.0.0
   ```
2. 终端里会显示本机 IP，例如：`Network URL: http://192.168.1.100:8501`。
3. 别人在**同一 WiFi** 下，用手机或电脑浏览器打开这个地址即可。
4. **前提**：你的电脑要一直开着并运行该命令；别人只能在你开机且同网络时访问。

---

## 方式三：自己的云服务器（VPS）

**适合**：有阿里云/腾讯云/海外 VPS，希望 24 小时在线、自己掌控。

1. 在服务器上安装 Python 3、克隆你的项目，安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 用 `0.0.0.0` 启动（允许外网访问）：
   ```bash
   streamlit run app.py --server.address 0.0.0.0 --server.port 8501
   ```
3. 在服务器安全组/防火墙里放行 **8501** 端口。
4. 用 **http://你的服务器公网IP:8501** 访问；可再配域名 + Nginx 反代做成 `https://扭蛋机.你的域名.com`。

若希望关掉终端也继续运行，可用：
```bash
nohup streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true &
```
或使用 systemd / supervisor 做常驻进程。

---

## 总结

| 方式           | 谁可以访问     | 需要           |
|----------------|----------------|----------------|
| Streamlit 云   | 任何人（有链接）| GitHub 账号    |
| 本机 0.0.0.0  | 同一 WiFi 的人 | 你电脑开机     |
| 自己的服务器  | 任何人（有链接）| 一台有公网 IP 的服务器 |

**想“所有人都能访问”时，优先用方式一（Streamlit 官方云），把生成的链接发出去即可。**
