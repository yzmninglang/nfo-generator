import os
import subprocess
import requests
import re
import shutil

def download_asset(url, output_dir, filename):
    asset_path = os.path.join(output_dir, filename)
    if os.path.exists(asset_path): return True
    try:
        print(f"正在从网络下载 {filename}...")
        with requests.get(url, timeout=15, stream=True) as r:
            r.raise_for_status()
            with open(asset_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        print(f"{filename} 下载成功。")
        return True
    except requests.exceptions.RequestException as e:
        print(f"错误：下载 {filename} 失败: {e}"); return False

def batch_convert_to_typora_html(input_dir, output_dir, local_asset_dir="css_js"):
    if not os.path.isdir(input_dir):
        print(f"错误：输入目录 '{input_dir}' 不存在。"); return
    if not os.path.exists(output_dir):
        os.makedirs(output_dir); print(f"已创建输出目录：'{output_dir}'")

    assets = {
        'github-markdown.css': 'https://raw.githubusercontent.com/sindresorhus/github-markdown-css/main/github-markdown.css',
        'hljs_style.css': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css',
        'highlight.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js',
        'clipboard.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/clipboard.js/2.0.11/clipboard.min.js',
    }
    
    # This part is identical to your working script
    before_body_content = '<main class="markdown-body">'
    after_body_content = """
</main>
<script src="highlight.min.js"></script>
<script src="clipboard.min.js"></script>
<script>
    setTimeout(function() {
        if (typeof hljs !== 'undefined') {
            document.querySelectorAll('pre code').forEach((block) => { hljs.highlightElement(block); });
        }
        document.querySelectorAll('pre').forEach(function(preElement) {
            if (preElement.querySelector('.copy-btn')) return;
            let button = document.createElement('button');
            button.className = 'copy-btn';
            button.type = 'button';
            button.innerText = '复制';
            preElement.appendChild(button);
        });
        if (typeof ClipboardJS !== 'undefined' && document.querySelector('.copy-btn')) {
            var clipboard = new ClipboardJS('.copy-btn', {
                target: function(trigger) { return trigger.previousElementSibling; }
            });
            clipboard.on('success', function(e) {
                e.clearSelection();
                e.trigger.innerText = '已复制!';
                setTimeout(function() { e.trigger.innerText = '复制'; }, 2000);
            });
        }
    }, 100);
</script>
"""
    before_body_file = os.path.join(output_dir, 'before_body.html')
    after_body_file = os.path.join(output_dir, 'after_body.html')
    with open(before_body_file, 'w', encoding='utf-8') as f: f.write(before_body_content)
    with open(after_body_file, 'w', encoding='utf-8') as f: f.write(after_body_content)
    
    print("--- 正在准备样式和脚本文件 ---")
    local_assets_exist = os.path.isdir(local_asset_dir)
    if local_assets_exist: print(f"发现本地资源目录 '{local_asset_dir}'，将优先使用。")

    all_assets = {**assets, 'custom.css': ''}
    for filename, url in all_assets.items():
        output_path = os.path.join(output_dir, filename)
        local_path = os.path.join(local_asset_dir, filename)
        if local_assets_exist and os.path.exists(local_path):
            print(f"从 '{local_asset_dir}' 复制 '{filename}'...")
            shutil.copy(local_path, output_path)
        elif url:
            if not download_asset(url, output_dir, filename):
                print("程序中止。"); return
        elif filename == 'custom.css':
             print(f"警告：未在 '{local_asset_dir}' 中找到 'custom.css'。")

    print("\n--- 开始转换 Markdown 文件 ---")
    for filename in os.listdir(input_dir):
        if filename.lower().endswith((".md", ".markdown")):
            input_file_path = os.path.join(input_dir, filename)
            base_name = os.path.splitext(filename)[0]
            output_file_path = os.path.join(output_dir, base_name + ".html")
            print(f"正在转换: {filename} ...")
            try:
                # --- Final, robust Pandoc command ---
                command_str = (
                    # 1. Add --self-contained to embed images and other resources
                    # 2. Add --resource-path to tell Pandoc where to find local images
                    f'pandoc --self-contained '
                    f'--resource-path="{os.path.abspath(input_dir)}" '
                    # --- The rest is your working command structure ---
                    f'-f commonmark+pipe_tables+tex_math_dollars -t html5 --standalone --mathjax '
                    f'--metadata title="{base_name}" '
                    # These CSS and JS files are now relative to the *output* directory
                    f'--css "github-markdown.css" '
                    f'--css "hljs_style.css" '
                    f'--css "custom.css" '
                    f'--include-before-body "{os.path.abspath(before_body_file)}" '
                    f'--include-after-body "{os.path.abspath(after_body_file)}" '
                    f'-o "{os.path.abspath(output_file_path)}" "{os.path.abspath(input_file_path)}"'
                )
                
                # Execute from the output directory to make relative paths for CSS/JS work
                subprocess.run(command_str, shell=True, check=True, capture_output=True, text=True, encoding='utf-8', cwd=output_dir)
                print(f"  -> 成功生成自包含的 HTML: {os.path.basename(output_file_path)}")

            except FileNotFoundError: print("错误：'pandoc' 命令未找到。"); return
            except subprocess.CalledProcessError as e: print(f"  -> Pandoc 转换失败: {e.stderr}")

    # 清理临时文件
    if os.path.exists(before_body_file): os.remove(before_body_file)
    if os.path.exists(after_body_file): os.remove(after_body_file)

if __name__ == "__main__":
    markdown_input_directory = r"D:\Seafile\Seafile\文章记录\图像部分\bpg"
    html_output_directory = "./html_output"
    local_resource_directory = "./css_js"
    
    batch_convert_to_typora_html(markdown_input_directory, html_output_directory, local_resource_directory)
    print("\n--- 所有任务完成！---")