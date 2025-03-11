from pptx import Presentation
from kag.examples.ppt.template1.content_creator import ContentPPTCreator
from kag.examples.ppt.template1.title_creator import TitlePPTCreator
from kag.examples.ppt.template1.chart_creator import ChartPPTCreator
from kag.examples.ppt.template1.image_creator import ImagePPTCreator

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
            'image': ImagePPTCreator(self.prs)
        }

    def save(self, output_path):
        """统一保存最终文件"""
        self.prs.save(output_path)