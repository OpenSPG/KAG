from pptx import Presentation
from kag.examples.ppt.template1.content_creator import ContentPPTCreator
from kag.examples.ppt.template1.title_creator import TitlePPTCreator
from kag.examples.ppt.template1.chart_creator import ChartPPTCreator
from kag.examples.ppt.template1.image_creator import ImagePPTCreator
from kag.examples.ppt.template1.table_creator import TablePPTCreator
from kag.examples.ppt.template1.ppt_utils import PPTUtils


class PPTManager:
    def __init__(self, template_path=None):
        """初始化内容页"""
        if template_path:
            self.prs = Presentation(template_path)
        else:
            self.prs = Presentation()
        self.creators = {
            'title': TitlePPTCreator(self.prs),
            'content': ContentPPTCreator(self.prs),
            'chart': ChartPPTCreator(self.prs),
            'image': ImagePPTCreator(self.prs),
            'table': TablePPTCreator(self.prs)
        }

    def save(self, output_path):
        """统一保存最终文件"""
        self.prs.save(output_path)

    def generate_ppt(self, markdown_file):
        """
        根据 Markdown 内容生成 PPT
        :param markdown_file: Markdown 文件路径
        """
        sections = PPTUtils.parse_markdown(markdown_file)
        for section in sections:
            md_type = section['type']
            title = section['title']
            content = section['content']

            if md_type == 'title':
                self.creators['title'].add_title_slide(title)
                continue

            table_data = PPTUtils.extract_markdown_tables(content)
            image_data = PPTUtils.extract_markdown_images(content)

            if table_data:  # 表格内容
                self.creators['table'].add_markdown_table_slide(
                    title=title,
                    content=None,  # 表格说明可以为空
                    table_data=table_data[0]
                )
            elif image_data:  # 图片内容
                self.creators['image'].add_image_slide_offline(
                    title=title,
                    image_path=image_data[0].get('url'),
                    figure_text=image_data[0].get('title')
                )
            elif content:  # 普通文本内容
                self.creators['content'].add_content_slide(
                    title=title,
                    content=content
                )
