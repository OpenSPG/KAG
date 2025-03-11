import os

from pptx import Presentation
from PIL import Image
from pptx.util import Inches

from .chart_creator import ChartPPTCreator
from .ppt_creator_base import PPTCreatorBase
from .ppt_utils import PPTUtils


class ImagePPTCreator:
    def __init__(self, prs):
        """接收统一的 Presentation 对象"""
        self.prs = prs

    def add_image_slide(self, title, image_path, position=None):
        """添加图片页"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[9])

        if slide.shapes.title:
            # 如果存在标题占位符，设置标题文本
            title_shape = slide.shapes.title
            title_shape.text = title

        # 处理图片
        img_path = self._process_image(image_path)
        # 设置图片位置
        if position is None:
            placeholder = slide.shapes[1]
            # 添加图片
            slide.shapes.add_picture(
                img_path,
                placeholder.left,
                placeholder.top,
                placeholder.width,
                placeholder.height,
            )
            # 删除占位符
            slide.shapes._spTree.remove(placeholder._element)
        else:
            slide.shapes.add_picture(
                img_path,
                position.left,
                position.top,
                position.width,
                position.height,
            )

        return slide

    @staticmethod
    def _process_image(image_path, max_size_mb=2):
        """处理图片尺寸和大小"""
        img = Image.open(image_path)

        # 压缩图片直到小于指定大小
        while os.path.getsize(image_path) > max_size_mb * 1024 * 1024:
            width, height = img.size
            img = img.resize((int(width * 0.8), int(height * 0.8)))
            img.save(image_path)

        return image_path

    def save(self, filename):
        """保存PPT文件"""
        self.prs.save(filename)