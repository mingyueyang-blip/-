# 今天吃什么 · 外卖扭蛋机

扭蛋机趣味推荐外卖，减脂/放纵双模式，记录消费与周复盘（工作日/周末）。

## 运行方式

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 启动网页：
   ```bash
   streamlit run app.py
   ```
   或双击 `run.sh`（Mac/Linux 需先 `chmod +x run.sh`）。

浏览器会自动打开；若无，请访问终端中显示的地址（一般为 http://localhost:8501）。

**想让别人也能访问？** 见 [DEPLOY.md](DEPLOY.md)（Streamlit 云部署 / 局域网 / 自建服务器）。

## 数据与素材

- 消费记录保存在项目目录下 `data/records.db`（SQLite）。
- 可选素材放在 `assets/`：扭蛋机背景图 `bg_gacha.png`、小橘贴纸 `xiaoju.png`，详见 `assets/README.md`。

## 环境

- Python 3.8+
- 支持 Mac / Windows；浏览器建议 Chrome、Safari、Edge。
