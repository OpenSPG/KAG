from pptx import Presentation

# 加载 PowerPoint 文件
presentation = Presentation('中国风背景.pptx')

# 访问幻灯片母版
slide_master = presentation.slide_master

# 打印母版中的布局数量
print(f"Number of layouts in slide master: {len(slide_master.slide_layouts)}")

# 遍历每个布局
for i, layout in enumerate(slide_master.slide_layouts):
    print(f"Layout {i}: {layout.name}")
