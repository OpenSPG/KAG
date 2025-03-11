import json
import os
import shutil
from copy import deepcopy

from PIL import Image
from pptx import Presentation


class PPTUtils:
    @staticmethod
    def check_font(font_name):
        """检查字体是否可用"""
        from matplotlib.font_manager import FontManager
        fm = FontManager()
        font_list = [f.name for f in fm.ttflist]
        return font_name in font_list

    @staticmethod
    def merge_ppts(ppt_list, output_path):
        """合并多个PPT"""
        merged_ppt = Presentation()

        for ppt_path in ppt_list:
            ppt = Presentation(ppt_path)

            for slide in ppt.slides:
                # 复制页面
                new_slide = merged_ppt.slides.add_slide(
                    merged_ppt.slide_layouts[
                        slide.slide_layout.index
                    ]
                )

                # 复制所有形状
                for shape in slide.shapes:
                    el = shape.element
                    new_el = deepcopy(el)
                    new_slide.shapes._spTree.insert_element_before(
                        new_el,
                        'p:extLst'
                    )

        merged_ppt.save(output_path)

    @staticmethod
    def copy_image_to_temp(image_path, target_dir=''):
        """复制图片到临时文件夹，并确保临时文件夹存在"""
        # 确定临时目录和目标路径
        os.makedirs(target_dir, exist_ok=True)  # 确保临时文件夹存在
        target_path = os.path.join(target_dir, os.path.basename(image_path))

        # 检查原始图片文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件未找到: {image_path}")

        # 使用 Pillow 打开图片，验证图片是否可用（可选）
        img = Image.open(image_path)
        img.verify()  # 验证图片完整性

        # 将图片复制到临时目录（直接复制文件）
        shutil.copy(image_path, target_path)

        print(f"图片已复制到: {target_path}")
        return target_path

    @staticmethod
    def get_placeholder_information(slide):
        """查看ppt母版的占位符信息，方便根据母版的对应占位符添加相关信息"""
        for placeholder in slide.placeholders:
            print(f"Placeholder {placeholder.placeholder_format.idx}: {placeholder.name}")

    @staticmethod
    def parse_text_to_json(text_file, output_file="output.json"):
        with open(text_file, "r", encoding="utf-8") as file:
            content = file.read()

        lines = content.strip().split("\n")  # 将文本按行分割
        json_data = {
            "title": None,
            "attributes": [],
            "pages": []
        }
        current_page = {}  # 当前处理的页面信息
        for line in lines:
            line = line.strip()  # 去除行首尾的空格
            if line.startswith("# "):  # 顶级标题（文件主标题）
                json_data["title"] = line[2:].strip()
            elif line.startswith("## "):  # 二级标题（目录属性）
                json_data["attributes"].append(line[3:].strip())
            elif line.startswith("### "):  # 三级标题（内容页标题）
                if current_page:  # 如果当前页面不为空，将当前页面信息存入 JSON
                    json_data["pages"].append(current_page)
                current_page = {"title": line[4:].strip(), "content": []}
            else:  # 内容部分（正文）
                if current_page:
                    if line.startswith("####"):
                        current_page["content"].append(line[5:])
                    else:
                        current_page["content"].append(line)
        # 把最后一个页面添加进 JSON
        if current_page:
            json_data["pages"].append(current_page)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

