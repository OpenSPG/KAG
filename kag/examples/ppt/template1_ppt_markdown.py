from template1.ppt_utils import PPTUtils

if __name__ == "__main__":
    ppt_utils = PPTUtils()

    # 提取所有表格内容
    all_tables = ppt_utils.extract_markdown_tables('农林牧渔.md')

    for i, table in enumerate(all_tables):
        print(f"Table {i + 1}:")
        for row in table:
            print(row)
        print()  # 空行分割不同表格

    # 提取所有图片信息
    images = ppt_utils.extract_md_images("农林牧渔.md")

    for idx, img in enumerate(images, 1):
        print(f"图片 {idx}:")
        print(f"标题：{img.get('title', '无标题')}")
        print(f"URL：{img['url']}")
        if 'figure_text' in img:
            print(f"FigureText：{img['figure_text']}")
        print("-" * 30)
