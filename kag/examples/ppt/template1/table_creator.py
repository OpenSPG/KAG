from typing import List
from pptx.util import Inches
from typing import List, Tuple
from bs4 import BeautifulSoup


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
        if content is not None:
            shape = slide.shapes[1]
            shape.text = content
        # 设置表格位置和大小
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

    def add_table_slide_with_merge(
            self, title: str, content, table_content: List[List[str]], merge_cells: List[Tuple[int, int, int, int]]
    ):
        """
        添加带有合并单元格的表格到 PowerPoint 幻灯片中
        :param title: 幻灯片标题
        :param table_content: 表格内容，二维列表
        :param merge_cells: 合并单元格信息 (start_row, start_col, end_row, end_col)
        """
        # 创建一个空白布局幻灯片
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[8])

        # 设置标题
        title_box = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(8), Inches(1))
        title_frame = title_box.text_frame
        title_frame.text = title

        if content is not None:
            shape = slide.shapes[1]
            shape.text = content

        rows = len(table_content)
        cols = max(len(row) for row in table_content)
        # 设置表格位置和大小
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

        # 填充内容并合并单元格
        for (start_row, start_col, end_row, end_col) in merge_cells:
            try:
                # 合并单元格
                table.cell(start_row, start_col).merge(
                    table.cell(end_row, end_col))
            except IndexError:
                # 添加错误处理
                print(f"警告：无效的合并范围 ({start_row},{start_col})-({end_row},{end_col})")

        # 填充文本内容
        for row_idx, row in enumerate(table_content):
            for col_idx, text in enumerate(row):
                cell = table.cell(row_idx, col_idx)
                cell.text_frame.paragraphs[0].text = text

        return slide

    def save(self, filename):
        """保存PPT文件"""
        self.prs.save(filename)
