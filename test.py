import os

# 定义PPT文件夹路径和BB文件夹路径
ppt_folder = './PPT'
bb_folder = './BB'

# 获取PPT文件夹中的所有文件名
ppt_files = os.listdir(ppt_folder)
bb_files = os.listdir(bb_folder)
for file in ppt_files:
    print(f"{file}")
    parts = file.split('-PPT-')
    print(parts)
    for file_bb in bb_files:
        if file_bb.startswith(parts[0]) and file_bb.endswith('.mp4'):
            print(f"Found matching BB file: {file_bb}")
            # 构建新的文件名
            new_name = f"{parts[0]}-BB-{parts[1]}"
            new_path = os.path.join(bb_folder, new_name)
            # 重命名BB文件
            os.rename(os.path.join(bb_folder, file_bb), new_path)
            print(f"Renamed {file_bb} to {new_name}")
    # if file.endswith('.mp4'):
    #     parts = file.split('-', 2)
    #     if len(parts) == 3:
    #         content_to_extract = parts[2]
    #         # 构建BB文件夹中对应的文件名
    #         bb_file_name = file.replace('PPT', 'BB')
    #         bb_file_path = os.path.join(bb_folder, bb_file_name)
    #         if os.path.exists(bb_file_path):
    #             new_name = f"{parts[0]}-{parts[1]}-BB-{content_to_extract}"
    #             new_path = os.path.join(bb_folder, new_name)
    #             os.rename(bb_file_path, new_path)