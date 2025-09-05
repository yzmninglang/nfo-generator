import os
import subprocess
import sys

def batch_convert_md_to_pdf(input_dir, output_dir, miktex_bin_path):
    """
    使用 Pandoc 和指定路径的 LaTeX 引擎 (MiKTeX) 将 Markdown 文件批量转换为高质量的 PDF。
    """
    xelatex_path = os.path.join(miktex_bin_path, 'xelatex.exe')
    if not os.path.exists(xelatex_path):
        print(f"错误：无法在指定路径找到 xelatex.exe: '{xelatex_path}'")
        print("请检查脚本底部的 'miktex_bin_path' 变量是否正确。")
        return

    if not os.path.isdir(input_dir):
        print(f"错误：输入目录 '{input_dir}' 不存在。"); return
    if not os.path.exists(output_dir):
        os.makedirs(output_dir); print(f"已创建输出目录：'{output_dir}'")
        
    env = os.environ.copy()
    env["PATH"] = f"{miktex_bin_path};{env['PATH']}"

    print("\n--- 开始将 Markdown 转换为 PDF ---")
    for filename in os.listdir(input_dir):
        if filename.lower().endswith((".md", ".markdown")):
            input_file_path = os.path.abspath(os.path.join(input_dir, filename))
            base_name = os.path.splitext(filename)[0]
            output_file_path = os.path.abspath(os.path.join(output_dir, base_name + ".pdf"))
            
            print(f"正在转换: {filename} ...")
            try:
                # --- 这是专为生成高质量、支持中文和特殊符号的 PDF 设计的 Pandoc 命令 ---
                command_str = (
                    f'pandoc "{input_file_path}" '
                    f'--pdf-engine=xelatex '
                    f'--resource-path="{os.path.abspath(input_dir)}" '
                    f'-f commonmark+pipe_tables+tex_math_dollars '
                    f'--highlight-style=tango '
                    
                    # --- 字体和页面布局设置 (最终优化版) ---
                    # 关键改动：使用 Microsoft YaHei UI 作为主中文字体，它包含了大量的符号。
                    f'-V CJKmainfont="Microsoft YaHei UI" '
                    # 您也可以尝试 "SimHei" (黑体) 或其他现代中文字体
                    
                    # mainfont 指定英文字体
                    f'-V mainfont="Times New Roman" '
                    # monofont 指定代码块的等宽字体
                    f'-V monofont="Consolas" '
                    # geometry 用于设置页面边距
                    f'-V geometry:margin=1in '
                    # fontsize 设置基础字体大小
                    f'-V fontsize=12pt '
                    
                    f'-o "{output_file_path}"'
                )
                
                print("  (正在调用 LaTeX 引擎，请耐心等待...)")
                subprocess.run(command_str, shell=True, check=True, capture_output=True, text=True, encoding='utf-8', env=env)
                
                print(f"  -> 成功转换为 PDF: {os.path.basename(output_file_path)}")

            except FileNotFoundError: 
                print("错误：'pandoc' 命令未找到。请确保 Pandoc 已安装并位于系统 PATH 中。")
                return
            except subprocess.CalledProcessError as e:
                print(f"  -> Pandoc 转换失败。")
                print("--- Pandoc/LaTeX 错误信息 ---")
                # 使用系统编码解码错误信息，更稳健
                print(e.stderr.encode(sys.stdout.encoding, errors='ignore').decode(sys.stdout.encoding, errors='ignore'))
                print("---------------------------")
                print("常见错误原因：")
                print("1. MiKTeX 正在尝试下载宏包但失败了，请检查网络或代理设置。")
                print("2. 指定的中文字体 (如 'Microsoft YaHei UI') 在您的系统中不存在或名称不正确。")
                return

if __name__ == "__main__":
    # --- 用户配置 ---
    miktex_bin_path = r"C:\Users\ninglang\AppData\Local\Programs\MiKTeX\miktex\bin\x64"

    markdown_input_directory = r"D:\Seafile\Seafile\文章记录\图像部分\bpg"
    pdf_output_directory = "./pdf_output"
    
    batch_convert_md_to_pdf(markdown_input_directory, pdf_output_directory, miktex_bin_path)
    print("\n--- 所有任务完成！---")