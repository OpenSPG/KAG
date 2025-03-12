import json

from template1.batch_ppt_creator import BatchPPTCreator
from template1.ppt_utils import PPTUtils


def demo_test():
    # 创建PPT生成器
    creator = BatchPPTCreator()
    # 准备数据
    data_list = [
        {
            'title': '2024年度报告',
            'subtitle': '语言与机器智能部-知识引擎',
            'content': [
                    '1、项目完成情况',
                    '2、技术创新',
                    '3、团队建设',
                    '4、未来规划'
            ],
            'chart_data': {
                'title': '项目情况',
                'categories': ['Q1', 'Q2', 'Q3', 'Q4'],
                'series': {
                    '项目数': [10, 15, 12, 18],
                    '完成率': [0.8, 0.85, 0.9, 0.95]
                }
            },
            'images': [
                {
                    'title': '团队照片分享',
                    'path': '/Users/wan/Documents/KAG/kag/examples/ppt/template1/picture/image_8.png'
                }
            ]
        }
    ]
    # 批量生成PPT
    creator.batch_create(data_list,template_path='template1/中国风背景.pptx')
    # creator.save('2024年度报告.pptx')


if __name__ == '__main__':
    # 验证ppt功能测试
    # demo_test()

    # 解析输入文本为 JSON 格式
    parsed_json_data = PPTUtils.parse_text_to_json(text_file='doc.txt', output_file='output.json')

    # 创建内容生成器
    from template1.ppt_manager import PPTManager
    ppt_manager = PPTManager('template1/中国风背景.pptx')


    with open("output.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    title = data.get("title", "无标题")
    ppt_manager.creators['title'].add_title_slide(title, '语言与机器智能部-知识引擎')
    attributes = data.get("attributes", [])
    ppt_manager.creators['content'].add_content_slide('目录', attributes)
    pages = data.get("pages", [])
    for page in pages:
        page_title = page.get("title", "无标题")
        content = page.get("content", [])
        ppt_manager.creators['content'].add_multi_column_slide(page_title, content)

    ppt_manager.save('服装制作.pptx')

