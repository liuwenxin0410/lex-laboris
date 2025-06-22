import os
import struct
import shutil
from pathlib import Path
from PIL import Image

# --- 配置 ---
# 请确保这个文件存在，并且最好是高清图 (例如 512x512 或 1024x1024)
SOURCE_IMAGE_PATH = r"C:\Users\34968\Desktop\lex-laboris-py\lex-laboris-final\source_icon.png" 
# 强制所有输出尺寸为 256x256
TARGET_SIZE = 256

# --- 输出目录 ---
BUILD_DIR = Path("desktop_ui") / "build"
ICNS_TEMP_DIR = BUILD_DIR / "temp_icns_images"


# --- ICNS 手动构建核心函数 (保持不变) ---
def create_icns_from_images(image_dir, output_path):
    """
    纯Python实现，手动将一个目录中的PNG图片打包成.icns文件。
    """
    toc_data = b''
    image_data = b''
    size_to_type = {
        16: b'icp4', 32: b'icp5', 64: b'icp6',
        128: b'ic07', 256: b'ic08', 512: b'ic09', 1024: b'ic10'
    }
    png_files = sorted(list(Path(image_dir).glob('*.png')), key=lambda p: int(p.stem.split('_')[1]))

    for png_path in png_files:
        size = int(png_path.stem.split('_')[1])
        if size not in size_to_type:
            continue
        with open(png_path, 'rb') as f:
            data = f.read()
        block_header = struct.pack('>4sI', size_to_type[size], len(data) + 8)
        image_data += block_header + data

    toc_header = struct.pack('>4sI', b'TOC ', len(image_data) + 8)
    toc_data = toc_header + image_data
    total_size = len(toc_data) + 8
    file_header = struct.pack('>4sI', b'icns', total_size)

    with open(output_path, 'wb') as f:
        f.write(file_header)
        f.write(toc_data)


# --- 主生成函数 (已修改) ---
def generate_all_icons():
    print(f"--- Starting Icon Generation (Forcing size to {TARGET_SIZE}x{TARGET_SIZE}) ---")
    source_path = Path(SOURCE_IMAGE_PATH)

    if not source_path.exists():
        print(f"!!! ERROR: Source image not found at '{source_path}'.")
        return

    # 准备目录
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if ICNS_TEMP_DIR.exists():
        shutil.rmtree(ICNS_TEMP_DIR)
    ICNS_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Build directory '{BUILD_DIR}' is ready.")

    try:
        with Image.open(source_path) as base_img:
            if base_img.mode != 'RGBA':
                base_img = base_img.convert('RGBA')
            print(f"Source image '{source_path}' loaded.")

            # --- 核心修改：先将图片精确缩放到目标尺寸 ---
            print(f"Resizing source image to {TARGET_SIZE}x{TARGET_SIZE}...")
            # 使用 LANCZOS 滤镜以获得最佳的缩放质量
            resized_img = base_img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
            print("  ✓ Resizing complete.")


            # 1. 生成 .ico 文件 (仅包含 256x256 尺寸)
            ico_path = BUILD_DIR / "icon.ico"
            print(f"Generating {ico_path} with a single {TARGET_SIZE}x{TARGET_SIZE} layer...")
            # Pillow 的 .save 方法允许指定尺寸列表
            resized_img.save(ico_path, format='ICO', sizes=[(TARGET_SIZE, TARGET_SIZE)])
            print(f"  ✓ Successfully created {ico_path}")


            # 2. 生成 Linux .png 图标 (尺寸为 256x256)
            linux_icon_path = BUILD_DIR / "icon.png"
            print(f"Generating {linux_icon_path} ({TARGET_SIZE}x{TARGET_SIZE})...")
            resized_img.save(linux_icon_path, "PNG")
            print(f"  ✓ Successfully created {linux_icon_path}")
            

            # 3. 手动构建 .icns 文件 (仅包含 256x256 尺寸)
            icns_path = BUILD_DIR / "icon.icns"
            print(f"Generating {icns_path} with a single {TARGET_SIZE}x{TARGET_SIZE} layer...")
            
            # 在临时目录中只创建一个 256x256 的 png
            temp_png_path = ICNS_TEMP_DIR / f"icon_{TARGET_SIZE}.png"
            resized_img.save(temp_png_path)
            
            # 调用我们自己写的ICNS构建函数，它会读取临时目录中的所有png
            create_icns_from_images(ICNS_TEMP_DIR, icns_path)
            print(f"  ✓ Successfully created {icns_path}")

    except Exception as e:
        print(f"!!! An error occurred: {e}")
    finally:
        # 清理临时目录
        if ICNS_TEMP_DIR.exists():
            shutil.rmtree(ICNS_TEMP_DIR)
            print(f"Temporary directory '{ICNS_TEMP_DIR}' cleaned up.")

    print(f"\n--- ✅ All icons (.ico, .icns, .png) generated with size {TARGET_SIZE}x{TARGET_SIZE}! ---")
    print(f"All icons are now located in the '{BUILD_DIR}' directory.")


if __name__ == "__main__":
    generate_all_icons()