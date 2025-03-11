from pptx import Presentation

from .image_creator import ImagePPTCreator


class BatchPPTCreator(ImagePPTCreator):
    def batch_create(self, data_list, template_path=None):
        """批量创建PPT"""
        for item in data_list:
            # 使用模板或创建新PPT
            if template_path:
                self.prs = Presentation(template_path)
            else:
                self.prs = Presentation()

            try:
                # 创建标题页
                self.add_title_slide(
                    item['title'],
                    item.get('subtitle')
                )

                # 创建内容页
                if 'content' in item:
                    self.add_content_slide(
                        "目录",
                        item['content']
                    )

                # 创建图表页
                if 'chart_data' in item:
                    self.add_multi_series_chart(
                        "销售季度数量",
                        "图中展示了销售量信息，可以发现Q4最高，Q1最低",
                        item['chart_data']
                    )

                # 创建图片页
                if 'images' in item:
                    for img in item['images']:
                        self.add_image_slide(
                            img['title'],
                            img['path']
                        )

            except Exception as e:
                print(f"处理 {item['title']} 时出错：{str(e)}")
                continue
