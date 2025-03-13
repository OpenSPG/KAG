from .ppt_manager import PPTManager


class BatchPPTCreator:
    @staticmethod
    def batch_create(data_list, template_path=None):
        manager = PPTManager(template_path)
        """批量创建PPT"""
        for item in data_list:
            # 遍历数据列表并创建PPT
            try:
                # 创建标题页
                manager.creators['title'].add_title_slide(
                    item['title'],
                    item.get('subtitle')
                )

                # 创建内容页
                if 'content' in item:
                    manager.creators['content'].add_content_slide(
                        "目录",
                        item['content']
                    )

                # 创建图表页
                if 'chart_data' in item:
                    manager.creators['chart'].add_multi_series_chart(
                        "销售季度数量",
                        "图中展示了销售量信息，可以发现Q4最高，Q1最低",
                        item['chart_data']
                    )

                # 创建图片页
                if 'images' in item:
                    for img in item['images']:
                        manager.creators['image'].add_image_slide_offline(
                            img['title'],
                            img['path']
                        )

            except Exception as e:
                print(f"处理 {item['title']} 时出错：{str(e)}")
                continue

        manager.save("最终合并的PPT.pptx")
