#!/usr/bin/env python3
"""测试hook - 在docs文件夹下创建txt文件记录执行时间"""

import os
from datetime import datetime

def main():
    # 目标文件路径
    docs_dir = r"D:\code_field\MainVisualizer\docs"
    output_file = os.path.join(docs_dir, "hook_test_result.txt")

    # 获取当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 写入内容
    content = f"hook成功执行\n时间: {current_time}\n"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Hook executed successfully at {current_time}")

if __name__ == "__main__":
    main()
