import os

def generate_leetcode_index(html_directory):
    """
    扫描指定目录中的 HTML 文件，并创建一个 Markdown 格式的导航页。

    参数:
    html_directory (str): 包含 LeetCode HTML 文件的目录路径。
    """
    # --- 检查目录是否存在 ---
    if not os.path.isdir(html_directory):
        print(f"错误：目录 '{html_directory}' 不存在。")
        return

    print(f"正在扫描目录: '{html_directory}'...")

    # --- 查找所有符合条件的 HTML 文件 ---
    html_files = []
    for filename in os.listdir(html_directory):
        # 筛选出以 'L' 开头并以 '.html' 结尾的文件
        # 同时排除模板文件
        if filename.lower().startswith('l') and filename.lower().endswith('.html'):
            if filename != 'L0000_模板.html':
                html_files.append(filename)

    # 如果没有找到文件，则提前退出
    if not html_files:
        print("未在该目录中找到符合条件的 LeetCode HTML 文件。")
        return

    # --- 对文件进行排序 ---
    # Python 的默认字符串排序能很好地处理 'L0001', 'L0002', 'L0010' 这样的格式
    html_files.sort()

    # --- 生成 Markdown 链接列表 ---
    markdown_links = []
    for filename in html_files:
        # 提取文件名（不含扩展名）作为链接文本
        link_text = os.path.splitext(filename)[0]
        # 创建 Markdown 格式的超链接，格式为 "- [文本](链接)"
        markdown_links.append(f"- [{link_text}]({filename})")

    # --- 组合成最终的 Markdown 内容 ---
    # 添加一个大标题
    markdown_content = "# LeetCode 题解目录\n\n" + "\n".join(markdown_links)
    
    # --- 写入文件 ---
    output_filepath = os.path.join(html_directory, 'leetcode.md')
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"\n导航文件 '{output_filepath}' 已成功生成！")
        print(f"共包含 {len(markdown_links)} 个链接。")
    except Exception as e:
        print(f"错误：写入文件 '{output_filepath}' 时失败: {e}")


if __name__ == "__main__":
    # --- 用户配置 ---
    # 请确保这个路径指向您存放所有 HTML 文件的文件夹
    html_output_directory = "./html_output"

    # --- 执行生成 ---
    generate_leetcode_index(html_output_directory)