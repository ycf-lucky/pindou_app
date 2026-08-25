import json
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from collections import Counter
import io

# ========== 页面设置 ==========
st.set_page_config(page_title="拼豆图纸生成器", layout="wide")
st.title("🧩 MARD 221 拼豆图纸生成器")

# 侧边栏设置
st.sidebar.header("设置参数")
st.sidebar.caption("👉 点击左上角箭头，可以展开或收起设置面板。")

# 加载 221 色卡
try:
    with open('colors.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    MARD_COLORS = {}
    for item in data['colors']:
        code = item['code']
        r, g, b = item['rgb']
        MARD_COLORS[code] = (r, g, b)
    st.sidebar.success(f"成功加载 {len(MARD_COLORS)} 个色号")
except FileNotFoundError:
    st.sidebar.error("找不到 colors.json 文件，请确保它和 app.py 在同一文件夹！")
    st.stop()

# 用户输入参数
GRID_W = st.sidebar.number_input("宽度 (颗)", min_value=20, max_value=150, value=48, step=1)
GRID_H = st.sidebar.number_input("高度 (颗)", min_value=20, max_value=150, value=68, step=1)
max_colors = st.sidebar.slider("最多使用颜色数", min_value=6, max_value=64, value=24)

# 计算总数
total_beads = GRID_W * GRID_H
st.sidebar.info(f"总豆子数量：{total_beads} 颗")

if GRID_W > 52 or GRID_H > 52:
    st.sidebar.warning("提示：若超出了52x52底板，需要拼接底板或选择104×104底板")
else:
    st.sidebar.success("尺寸检查通过：正好适配52x52底板。")

# ========== 图片上传区 ==========
uploaded_file = st.file_uploader("上传你想DIY的照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 处理图片
    img = Image.open(uploaded_file).convert("RGB")

    # 裁剪逻辑
    target = GRID_W / GRID_H
    w, h = img.size
    if w / h > target:
        crop_w, crop_h = int(h * target), h
    else:
        crop_w, crop_h = w, int(w / target)
    cx, cy = int(w * 0.5), int(h * 0.5)
    left = max(0, min(cx - crop_w // 2, w - crop_w))
    top = max(0, min(cy - crop_h // 2, h - crop_h))
    img = img.crop((left, top, left + crop_w, top + crop_h))
    img = img.resize((GRID_W, GRID_H), Image.LANCZOS)


    # 匹配颜色
    def nearest_color(rgb):
        r, g, b = rgb
        best_code = None
        best_dist = float("inf")
        for code, (cr, cg, cb) in MARD_COLORS.items():
            dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if dist < best_dist:
                best_dist = dist
                best_code = code
        return best_code


    all_pixel_codes = []
    for y in range(GRID_H):
        for x in range(GRID_W):
            all_pixel_codes.append(nearest_color(img.getpixel((x, y))))

    # 提取高频颜色，清理噪点
    top_codes = [code for code, _ in Counter(all_pixel_codes).most_common(max_colors)]
    final_palette = {code: MARD_COLORS[code] for code in top_codes}

    cleaned_codes = []
    for c in all_pixel_codes:
        if c in final_palette:
            cleaned_codes.append(c)
        else:
            best_dist = float("inf")
            best_code = top_codes[0]
            for code in top_codes:
                cr, cg, cb = MARD_COLORS[code]
                dist = (MARD_COLORS[c][0] - cr) ** 2 + (MARD_COLORS[c][1] - cg) ** 2 + (MARD_COLORS[c][2] - cb) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_code = code
            cleaned_codes.append(best_code)

    all_pixel_codes = cleaned_codes
    final_grid = [all_pixel_codes[i * GRID_W:(i + 1) * GRID_W] for i in range(GRID_H)]

    # 生成图纸
    CELL_SIZE = 22
    PADDING_L = 40
    PADDING_T = 40
    FOOTER_H = 180

    TOTAL_W = GRID_W * CELL_SIZE + PADDING_L + 20
    TOTAL_H = GRID_H * CELL_SIZE + PADDING_T + FOOTER_H

    preview = Image.new("RGB", (TOTAL_W, TOTAL_H), (255, 255, 255))
    draw = ImageDraw.Draw(preview)

    try:
        font = ImageFont.truetype("arial.ttf", 11)
        small_font = ImageFont.truetype("arial.ttf", 9)
    except IOError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # 画主网格
    for y in range(GRID_H):
        for x in range(GRID_W):
            code = final_grid[y][x]
            color = MARD_COLORS[code]
            x0 = PADDING_L + x * CELL_SIZE
            y0 = PADDING_T + y * CELL_SIZE
            x1 = x0 + CELL_SIZE
            y1 = y0 + CELL_SIZE
            draw.rectangle([x0, y0, x1, y1], fill=color, outline=(220, 220, 220))
            text_color = (255, 255, 255) if sum(color) < 400 else (0, 0, 0)
            draw.text((x0 + 2, y0 + 5), code, fill=text_color, font=small_font)
            # 画外部粗边框（内框线）
            draw.rectangle([PADDING_L, PADDING_T, PADDING_L + GRID_W * CELL_SIZE, PADDING_T + GRID_H * CELL_SIZE],
                           outline=(0, 0, 0), width=4)

            # 画十字中轴线（横竖分割线）
            mid_x = PADDING_L + (GRID_W // 2) * CELL_SIZE
            mid_y = PADDING_T + (GRID_H // 2) * CELL_SIZE
            draw.line([(mid_x, PADDING_T), (mid_x, PADDING_T + GRID_H * CELL_SIZE)], fill=(0, 0, 0), width=3)
            draw.line([(PADDING_L, mid_y), (PADDING_L + GRID_W * CELL_SIZE, mid_y)], fill=(0, 0, 0), width=3)

    # 画坐标轴
    for x in range(GRID_W):
        draw.text((PADDING_L + x * CELL_SIZE + 6, 10), str(x + 1), fill=(0, 0, 0), font=font)
    for y in range(GRID_H):
        draw.text((5, PADDING_T + y * CELL_SIZE + 4), str(y + 1), fill=(0, 0, 0), font=font)

    # 画图例
    sorted_codes = sorted(final_palette.keys(), key=lambda c: -all_pixel_codes.count(c))
    COLOR_BOX = 16
    LEGEND_SLOT_WIDTH = 85
    LEGEND_ITEM_HEIGHT = 26
    legend_x = PADDING_L
    legend_y = PADDING_T + GRID_H * CELL_SIZE + 35
    max_legend_x = PADDING_L + GRID_W * CELL_SIZE

    for code in sorted_codes:
        color = MARD_COLORS[code]
        count = all_pixel_codes.count(code)
        if legend_x + LEGEND_SLOT_WIDTH > max_legend_x:
            legend_x = PADDING_L
            legend_y += LEGEND_ITEM_HEIGHT
        draw.rectangle([legend_x, legend_y, legend_x + COLOR_BOX, legend_y + COLOR_BOX], fill=color, outline=(0, 0, 0))
        draw.text((legend_x + COLOR_BOX + 4, legend_y + 1), f"{code} ({count})", fill=(0, 0, 0), font=font)
        legend_x += LEGEND_SLOT_WIDTH

    # 转成字节流以便网页显示和下载
    img_bytes = io.BytesIO()
    preview.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # 在网页上显示
    st.subheader("生成的拼豆图纸")
    st.caption("💡 提示：苹果用户可长按下方图片保存至相册；安卓用户可直接点击下方的下载按钮。")
    st.image(preview, use_container_width=True)

    # 下载按钮
    st.download_button(
        label="📥 下载拼豆图纸",
        data=img_bytes,
        file_name="bead_pattern_labeled.png",
        mime="image/png"
    )
