import os
import subprocess
import requests
import re
import os
# proxy_url = 'http://hinas-v4.ninglang.top:7891'
# os.environ['HTTP_PROXY'] = proxy_url
# os.environ['HTTPS_PROXY'] = proxy_url

def download_asset(url, output_dir, filename):
    """通用资源下载函数"""
    asset_path = os.path.join(output_dir, filename)
    if not os.path.exists(asset_path):
        try:
            print(f"正在下载 {filename}...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(asset_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"{filename} 下载成功。")
            return True
        except requests.exceptions.RequestException as e:
            print(f"错误：下载 {filename} 失败: {e}")
            return False
    else:
        print(f"{filename} 已存在，跳过下载。")
        return True

def generate_html_structure(title, body_content, css_path, js_paths):
    """生成最终的 HTML 文件结构"""
    css_links = ''.join([f'<link rel="stylesheet" href="{path}">\n' for path in css_path])
    js_scripts = ''.join([f'<script src="{path}"></script>\n' for path in js_paths])

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {css_links}
</head>
<body>
    <main class="markdown-body">
        {body_content}
    </main>
    {js_scripts}
    <script>
        document.addEventListener('DOMContentLoaded', (event) => {{
            // 初始化 highlight.js
            hljs.highlightAll();

            // 为每个代码块添加复制按钮
            document.querySelectorAll('pre code').forEach(function(codeBlock) {{
                let preElement = codeBlock.parentNode;
                
                // 创建按钮
                let button = document.createElement('button');
                button.className = 'copy-btn';
                button.type = 'button';
                button.innerText = '复制';
                
                preElement.style.position = 'relative';
                preElement.appendChild(button);
            }});

            // 初始化 clipboard.js
            var clipboard = new ClipboardJS('.copy-btn', {{
                target: function(trigger) {{
                    return trigger.previousElementSibling;
                }}
            }});

            clipboard.on('success', function(e) {{
                e.clearSelection();
                e.trigger.innerText = '已复制!';
                setTimeout(function() {{
                    e.trigger.innerText = '复制';
                }}, 2000);
            }});

            clipboard.on('error', function(e) {{
                e.trigger.innerText = '失败!';
                setTimeout(function() {{
                    e.trigger.innerText = '复制';
                }}, 2000);
            }});
        }});
    </script>
</body>
</html>
"""

def batch_convert_to_typora_html(input_dir, output_dir):
    """主函数：使用 Pandoc 将 Markdown 批量转换为 Typora 风格的 HTML"""
    # --- 检查和创建目录 ---
    if not os.path.isdir(input_dir):
        print(f"错误：输入目录 '{input_dir}' 不存在。")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"已创建输出目录：'{output_dir}'")

    # --- 资源 URL 和文件名 ---
    assets = {
        'main_style.css': 'https://raw.githubusercontent.com/sindresorhus/github-markdown-css/main/github-markdown.css',
        'hljs_style.css': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css',
        'custom.css': '', # 本地创建
        'highlight.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js',
        'clipboard.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/clipboard.js/2.0.11/clipboard.min.js'
    }

    # --- 下载所有外部资源 ---
    print("--- 正在准备样式和脚本文件 ---")
    for filename, url in assets.items():
        if url: # 只下载有 URL 的
            if not download_asset(url, output_dir, filename):
                print(f"由于资源下载失败，程序中止。")
                return
    
    # --- 创建自定义 CSS 文件 ---
    custom_css_content = """
body {
    background-color: #f6f8fa;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
}
.markdown-body {
    box-sizing: border-box;
    min-width: 200px;
    max-width: 980px;
    margin: 0 auto;
    padding: 45px;
    background-color: #ffffff;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
}
pre {
    position: relative;
}
.copy-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    background-color: #e1e4e8;
    border: 1px solid #d1d5da;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 12px;
    cursor: pointer;
    opacity: 0; /* 默认隐藏 */
    transition: opacity 0.2s ease-in-out;
}
pre:hover .copy-btn {
    opacity: 1; /* 鼠标悬浮时显示 */
}
.copy-btn:hover {
    background-color: #d1d5da;
}
@media (max-width: 767px) {
    .markdown-body {
        padding: 15px;
    }
}
"""
    with open(os.path.join(output_dir, 'custom.css'), 'w', encoding='utf-8') as f:
        f.write(custom_css_content)
    print("custom.css 文件已创建。")

    print("\n--- 开始转换 Markdown 文件 ---")
    # --- 遍历并转换文件 ---
    for filename in os.listdir(input_dir):
        if filename.lower().endswith((".md", ".markdown")):
            input_file_path = os.path.join(input_dir, filename)
            base_name = os.path.splitext(filename)[0]
            output_file_path = os.path.join(output_dir, base_name + ".html")

            print(f"正在转换: {filename} ...")
            try:
                # 使用 Pandoc 将 Markdown 转换为 HTML 片段 (fragment)
                command = [
                    'pandoc',
                    '-f', 'gfm',  # 输入格式：GitHub Flavored Markdown
                    '-t', 'html', # 输出格式：HTML 片段
                    input_file_path
                ]
                result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
                html_fragment = result.stdout

                # 构建完整的 HTML 页面
                full_html = generate_html_structure(
                    title=base_name,
                    body_content=html_fragment,
                    css_path=['main_style.css', 'hljs_style.css', 'custom.css'],
                    js_paths=['highlight.min.js', 'clipboard.min.js']
                )

                # 写入最终的 HTML 文件
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(full_html)

                print(f"  -> 成功转换为 {os.path.basename(output_file_path)}")

            except FileNotFoundError:
                print("错误：'pandoc' 命令未找到。请确保 Pandoc 已安装并配置在系统 PATH 中。")
                return
            except subprocess.CalledProcessError as e:
                print(f"  -> Pandoc 转换失败: {e.stderr}")

if __name__ == "__main__":
    # --- 用户配置 ---
    markdown_input_directory = r"D:\Seafile\Seafile\文章记录\LeetCode-master\题解"
    html_output_directory = "./html_output"

    # --- 执行 ---
    batch_convert_to_typora_html(markdown_input_directory, html_output_directory)
    print("\n--- 所有任务完成！---")