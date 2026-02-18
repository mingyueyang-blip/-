# 素材说明

## 扭蛋机动画（新交互）
- **machine.png** — 扭蛋机外壳，绿色区域居中展示；无则用 gashapon.png 或占位
- **ball.png** — 整颗扭蛋，从出口弹出并飞向中心
- **ball-left.png** / **ball-right.png** — 扭蛋裂开后的左/右两半，向两侧滑开
- **gashapon_template.html** — 扭蛋机区块的 HTML/CSS/JS 模板（勿删）

## 食物图标 food-icons/
- **sprite.png** — 8 格雪碧图（饭团、鸡腿、汉堡×2、咖啡、甜品×2、甜甜圈），当没有「品类名.png」时作为通用结果图标
- **品类名.png** — 可选，如 `日料.png`、`麦当劳.png`，抽中该品类时优先显示对应图标

## 旧版/其他
- **bg_diet.png** — 减脂模式首页扭蛋机区域背景
- **bg_indulge.png** — 放纵模式首页扭蛋机区域背景
- **bg_gacha_slim.png** / **bg_gacha_indulge.png** — 结果弹窗顶部装饰（80×80px）
- **gashapon.png** — 扭蛋机图（无 machine.png 时作 fallback）
- **xiaoju.png** — 小橘贴纸（80px 宽）

图片缺失时：扭蛋机用 SVG 占位，食物图标用 sprite 或仅显示文字。
