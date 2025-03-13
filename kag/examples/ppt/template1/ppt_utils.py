import json
import os
import shutil
from copy import deepcopy

from PIL import Image
from pptx import Presentation
from typing import List, Tuple
from bs4 import BeautifulSoup
import re
import re
from pathlib import Path


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
                    current_page["content"].append(line)
        # 把最后一个页面添加进 JSON
        if current_page:
            json_data["pages"].append(current_page)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

        return json_data

    @staticmethod
    def extract_markdown_images(md_file):
        """
        提取Markdown文件中的图片信息
        :param md_file: Markdown文件路径
        :return: 包含图片信息的字典列表
        """
        content = Path(md_file).read_text(encoding='utf-8')
        lines = content.split('\n')

        images = []

        for i, line in enumerate(lines):
            img_info = {}

            # 匹配HTML格式图片
            if '<img' in line:
                # 提取src属性
                src_match = re.search(r'src=["\'](.*?)["\']', line)
                if src_match:
                    img_info['url'] = src_match.group(1)

                    # 向前搜索标题和figureText
                    j = i - 1
                    while j >= 0:
                        prev_line = lines[j].strip()

                        # 匹配标题（非空行）
                        if prev_line and not prev_line.startswith(('<', '![', '|')):
                            img_info['title'] = prev_line
                            break
                        j -= 1

                    images.append(img_info)

            # 匹配Markdown标准图片
            elif line.startswith('!['):
                md_match = re.match(r'!\[(.*?)\]\((.*?)\)', line)
                if md_match:
                    img_info = {
                        'title': md_match.group(1),
                        'url': md_match.group(2)
                    }
                    images.append(img_info)

        return images

    @staticmethod
    def extract_markdown_tables(md_file_path):
        """ 从Markdown内容中提取所有HTML表格并转换为结构化数据 """
        with open(md_file_path, "r", encoding="utf-8") as file:
            markdown_text = file.read()

        soup = BeautifulSoup(markdown_text, 'html.parser')
        parsed_tables = []

        # 修复1：使用find_all获取所有表格（原代码find只能获取第一个）
        for table in soup.find_all('table'):
            table_content = []
            merge_cells = []
            rowspans = {}  # 新增跨行单元格追踪

            # 修复2：重构行列计算逻辑
            max_cols = 0
            for row_idx, tr in enumerate(table.find_all('tr')):
                row = []
                col_idx = 0

                # 处理跨行单元格延续
                while col_idx in rowspans.get(row_idx, {}):
                    cell = rowspans[row_idx][col_idx]
                    row.append(cell['text'])
                    if cell['remaining'] > 1:
                        for r in range(row_idx+1, row_idx + cell['remaining']):
                            rowspans.setdefault(r, {})[col_idx] = {
                                'text': cell['text'],
                                'remaining': cell['remaining'] - (r - row_idx)
                            }
                    col_idx += 1

                # 处理当前行新单元格
                for cell in tr.find_all(['td', 'th']):
                    # 跳过已处理的合并单元格
                    while col_idx in rowspans.get(row_idx, {}):
                        col_idx += 1

                    # 获取单元格属性
                    text = cell.get_text(strip=True)
                    rowspan = int(cell.get('rowspan', 1))
                    colspan = int(cell.get('colspan', 1))

                    # 记录合并信息
                    if rowspan > 1 or colspan > 1:
                        merge_cells.append((
                            row_idx, col_idx,
                            row_idx + rowspan - 1,
                            col_idx + colspan - 1
                        ))

                    # 填充当前单元格
                    row.append(text)

                    # 处理行合并
                    if rowspan > 1:
                        for r in range(row_idx+1, row_idx + rowspan):
                            rowspans.setdefault(r, {})[col_idx] = {
                                'text': text,
                                'remaining': rowspan - (r - row_idx)
                            }

                    col_idx += colspan

                # 更新最大列数
                max_cols = max(max_cols, col_idx)
                table_content.append(row)

            # 修复3：统一填充空单元格
            for row in table_content:
                while len(row) < max_cols:
                    row.append('')

            parsed_tables.append((table_content, merge_cells))

        return parsed_tables