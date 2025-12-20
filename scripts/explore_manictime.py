"""
ManicTime 数据库探索脚本

用于探索 ManicTime 数据库结构，了解表和字段信息
"""
import sqlite3
from pathlib import Path
import os

# 配置路径
DB_PATH = r"D:\code_field\manicData\db\ManicTimeReports.db"
SCREENSHOTS_PATH = r"Y:\临时文件\ManicTimeScreenShots"

def explore_database():
    """探索数据库结构"""
    print(f"=" * 60)
    print(f"ManicTime 数据库探索")
    print(f"=" * 60)
    print(f"\n数据库路径: {DB_PATH}")
    print(f"截图路径: {SCREENSHOTS_PATH}")
    
    # 检查文件是否存在
    if not Path(DB_PATH).exists():
        print(f"\n错误: 数据库文件不存在!")
        return
    
    print(f"\n数据库文件大小: {Path(DB_PATH).stat().st_size / (1024*1024):.2f} MB")
    
    # 连接数据库(只读模式)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n发现 {len(tables)} 个表:")
    print("-" * 40)
    for table in tables:
        print(f"  - {table}")
    
    # 获取每个表的结构
    print(f"\n" + "=" * 60)
    print("表结构详情:")
    print("=" * 60)
    
    for table in tables:
        print(f"\n### {table} ###")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        print(f"字段 ({len(columns)}):")
        for col in columns:
            cid, name, dtype, notnull, default, pk = col
            pk_mark = " [PK]" if pk else ""
            print(f"  - {name}: {dtype}{pk_mark}")
        
        # 获取行数
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"记录数: {count}")
        
        # 获取样本数据
        if count > 0:
            cursor.execute(f"SELECT * FROM {table} LIMIT 2")
            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            print(f"样本数据:")
            for i, row in enumerate(rows):
                print(f"  Row {i+1}:")
                for name, val in zip(col_names, row):
                    val_str = str(val)[:80] if val else "NULL"
                    print(f"    {name}: {val_str}")
    
    conn.close()

def explore_screenshots():
    """探索截图目录结构"""
    print(f"\n" + "=" * 60)
    print("截图目录探索")
    print("=" * 60)
    
    if not Path(SCREENSHOTS_PATH).exists():
        print(f"\n警告: 截图目录不存在或无法访问: {SCREENSHOTS_PATH}")
        return
    
    # 统计文件
    files = list(Path(SCREENSHOTS_PATH).glob("**/*"))
    image_files = [f for f in files if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')]
    
    print(f"\n总文件数: {len(files)}")
    print(f"图片文件数: {len(image_files)}")
    
    if image_files:
        print(f"\n样本文件名:")
        for f in image_files[:5]:
            print(f"  - {f.name}")
        
        # 分析命名规则
        print(f"\n文件扩展名统计:")
        ext_count = {}
        for f in image_files:
            ext = f.suffix.lower()
            ext_count[ext] = ext_count.get(ext, 0) + 1
        for ext, count in sorted(ext_count.items(), key=lambda x: -x[1]):
            print(f"  {ext}: {count}")

if __name__ == "__main__":
    explore_database()
    explore_screenshots()
