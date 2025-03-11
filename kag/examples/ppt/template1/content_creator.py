from pptx.util import Inches, Pt

from .title_creator import PPTCreator
from .ppt_utils import PPTUtils


class ContentPPTCreator(PPTCreator):
    def add_content_slide(self, title, content_list, layout_idx=1):
        """添加内容页"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[1])
        # 设置标题
        title_shape = slide.shapes.title
        title_shape.text = title
        PPTUtils.get_placeholder_information(slide)
        # 设置内容
        body_shape = slide.shapes.placeholders[1]
        tf = body_shape.text_frame

        # 添加项目符号
        for idx, item in enumerate(content_list):
            p = tf.add_paragraph()
            p.text = item

        return slide

    def add_two_column_slide(self, title, left_content, right_content):
        """添加双栏内容页"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[3])

        # 设置标题
        title_shape = slide.shapes.title
        title_shape.text = title

        # 左侧内容
        left_shape = slide.shapes.add_textbox(
            Inches(1), Inches(1.5),
            Inches(3.5), Inches(5)
        )
        left_tf = left_shape.text_frame
        left_tf.text = left_content

        # 右侧内容
        right_shape = slide.shapes.add_textbox(
            Inches(5), Inches(1.5),
            Inches(3.5), Inches(5)
        )
        right_tf = right_shape.text_frame
        right_tf.text = right_content

        return slide
