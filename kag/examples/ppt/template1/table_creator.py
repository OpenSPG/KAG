from pptx import Presentation
from pptx.util import Inches
from typing import List

class TablePPTCreator:
    def __init__(self, prs):
        """接收统一的 Presentation 对象"""
        self.prs = prs

    def add_table_slide(self, title, content, rows: int, cols: int, table_content: List[List[str]], position=None):
        """添加表格页"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[8])

        if slide.shapes.title:
            # 如果存在标题占位符，设置标题文本
            title_shape = slide.shapes.title
            title_shape.text = title

            # 设置表格位置和大小
        shape = slide.shapes[1]
        shape.text = content

        shape = slide.shapes[2]
        placeholder = shape
        table_left, table_top, table_width, table_height = (
            placeholder.left,
            placeholder.top,
            placeholder.width,
            placeholder.height,
        )

        # 添加表格
        table = slide.shapes.add_table(rows, cols, table_left, table_top, table_width, table_height).table

        for i in range(rows):
            for j in range(cols):
                # 设置单元格内容
                cell = table.cell(i, j)
                cell.text = table_content[i][j]

        return slide

    def save(self, filename):
        """保存PPT文件"""
        self.prs.save(filename)