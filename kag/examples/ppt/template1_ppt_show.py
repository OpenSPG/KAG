from kag.examples.ppt.template1.ppt_manager import PPTManager


if __name__ == "__main__":
    # 创建一个新的 PowerPoint 演示文稿
    manager = PPTManager('template1/中国风背景.pptx')
    manager.generate_ppt('中国传统文化.md')
    manager.save('中国传统文化.pptx')
