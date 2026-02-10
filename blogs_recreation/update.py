import os
import glob
import re
from datetime import datetime
from pathlib import Path

def extract_title_from_md(filepath):
    """
    从markdown文件中提取标题
    支持的格式：
    1. @[toc](标题) - 目录语法
    2. # 标题 - 一级标题
    3. ## 标题 - 二级标题
    4. YAML Front Matter 中的 title 字段
    5. 文件名（作为后备）
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(3000)  # 读取前3000字符
            
            # 方法1：查找 @[toc](标题) 格式
            # 匹配 @[toc](标题内容) 或者 [toc](标题内容)
            # 允许有空格：@[toc] (标题)
            toc_patterns = [
                r'@\[toc\]\s*\(([^)]+)\)',      # @[toc](标题)
                r'\[toc\]\s*\(([^)]+)\)',       # [toc](标题)
                r'<!--toc-->\s*([^<]+)',        # <!--toc--> 标题
                r'<!--\s*toc\s*-->\s*([^<]+)',  # <!-- toc --> 标题
            ]
            
            for pattern in toc_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    # 清理可能的额外括号
                    title = re.sub(r'^\(|\)$', '', title)
                    if title:
                        return title
            
            # 方法2：查找一级标题 (# 标题)
            # 排除代码块中的标题
            lines = content.split('\n')
            in_code_block = False
            
            for line in lines:
                # 检测代码块开始/结束
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                
                if not in_code_block:
                    # 匹配 # 标题
                    h1_match = re.match(r'^#\s+(.+)$', line)
                    if h1_match:
                        title = h1_match.group(1).strip()
                        # 清理标题中的格式
                        title = clean_markdown_format(title)
                        if title:
                            return title
            
            # 方法3：查找二级标题 (## 标题)
            in_code_block = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                
                if not in_code_block:
                    h2_match = re.match(r'^##\s+(.+)$', line)
                    if h2_match:
                        title = h2_match.group(1).strip()
                        title = clean_markdown_format(title)
                        if title:
                            return title
            
            # 方法4：尝试查找第一个非空的非代码行作为标题
            in_code_block = False
            for line in lines:
                line = line.strip()
                if line.startswith('```'):
                    in_code_block = not in_code_block
                    continue
                
                if not in_code_block and line and not line.startswith(('|', '>', '-', '*', '+', '`')):
                    # 跳过注释
                    if line.startswith('<!--') and line.endswith('-->'):
                        continue
                    
                    # 清理可能的格式
                    clean_line = clean_markdown_format(line)
                    if len(clean_line) < 150:  # 标题通常不会太长
                        return clean_line[:100]  # 截断过长的标题
            
    except (UnicodeDecodeError, OSError) as e:
        print(f"警告：无法读取文件 {filepath}: {e}")
    
    # 方法5：使用文件名（美化处理）
    filename = os.path.basename(filepath)
    name_without_ext = os.path.splitext(filename)[0]
    
    # 美化文件名：将连字符、下划线、点替换为空格
    pretty_name = re.sub(r'[-_.]', ' ', name_without_ext)
    # 首字母大写每个单词
    pretty_name = ' '.join(word.capitalize() for word in pretty_name.split())
    
    return pretty_name

def clean_markdown_format(text):
    """清理markdown格式标记"""
    if not text:
        return text
    
    # 移除链接 [文字](链接) -> 文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # 移除图片 ![](链接) -> 空
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    
    # 移除加粗和斜体 **文字** -> 文字
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    
    # 移除行内代码 `代码` -> 代码
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # 移除删除线 ~~文字~~ -> 文字
    text = re.sub(r'~~([^~]+)~~', r'\1', text)
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 移除特殊格式标记
    text = re.sub(r'<!--[^>]+-->', '', text)
    
    # 移除多余的空格
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_all_titles(filepath):
    """
    提取文件中的所有标题（用于生成子目录）
    返回标题结构列表
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        titles = []
        lines = content.split('\n')
        in_code_block = False
        
        for i, line in enumerate(lines):
            # 检测代码块
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if not in_code_block:
                # 匹配标题行
                for level in range(1, 7):  # 支持 h1-h6
                    pattern = f'^{"#" * level}\\s+(.+)$'
                    match = re.match(pattern, line)
                    if match:
                        title = match.group(1).strip()
                        title = clean_markdown_format(title)
                        titles.append({
                            'level': level,
                            'title': title,
                            'line_number': i + 1
                        })
                        break
        
        return titles
    except:
        return []

def generate_index_with_toc(md_file_path):
    """生成包含文章内部目录的索引"""
    folder_path = os.path.dirname(md_file_path)
    
    # 获取所有markdown文件
    articles = []
    for file in glob.glob(os.path.join(folder_path, "*.md")):
        filename = os.path.basename(file)
        if filename == "init.md":
            continue
        
        title = extract_title_from_md(file)
        all_titles = extract_all_titles(file)  # 提取所有标题
        
        # 获取文件信息
        stat = os.stat(file)
        modify_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
        size_kb = round(stat.st_size / 1024, 2)
        
        # 提取前几行作为描述
        description = ""
        try:
            with open(file, 'r', encoding='utf-8') as f:
                lines = []
                for i in range(10):  # 读取前10行
                    line = f.readline().strip()
                    if line and not line.startswith(('#', '@[toc]', '[toc]', '<!--')):
                        lines.append(line)
                if lines:
                    description = ' '.join(lines)[:150] + "..."
        except:
            description = ""
        
        # 计算字数（粗略估计）
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 去除代码块和链接
                clean_content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
                clean_content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean_content)
                word_count = len(clean_content.split())
        except:
            word_count = 0
        
        articles.append({
            'filename': filename,
            'title': title,
            'modify_time': modify_time,
            'size': size_kb,
            'description': description,
            'word_count': word_count,
            'titles': all_titles,  # 所有标题
            'full_path': file
        })
    
    # 按修改时间倒序排列
    articles.sort(key=lambda x: x['modify_time'], reverse=True)
    
    # 生成markdown内容
    md_content = f"""# 📚 文章索引

> 🕒 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 📁 目录：`{os.path.basename(folder_path)}`
> 📊 统计：共 **{len(articles)}** 篇文章

---

## 📋 文章总览

| 序号 | 标题 | 文件名 | 更新时间 | 字数 | 大小 | 链接 |
|------|------|--------|----------|------|------|------|
"""
    
    for idx, article in enumerate(articles, 1):
        md_content += f"| {idx} | **{article['title']}** | `{article['filename']}` | {article['modify_time']} | {article['word_count']}字 | {article['size']}KB | [阅读](./{article['filename']}) |\n"
    
    md_content += "\n---\n\n"
    
    # 生成每篇文章的详细目录
    md_content += "## 📄 文章详情\n\n"
    
    for article in articles:
        md_content += f"### [{article['title']}](./{article['filename']})\n\n"
        md_content += f"> 📝 **文件**: `{article['filename']}`\n"
        md_content += f"> 🕒 **更新**: {article['modify_time']}\n"
        md_content += f"> 📊 **统计**: {article['word_count']}字, {article['size']}KB\n\n"
        
        if article['description']:
            md_content += f"**摘要**: {article['description']}\n\n"
        
        if article['titles']:
            md_content += "**文章大纲**:\n\n"
            for title_info in article['titles'][:10]:  # 最多显示10个标题
                indent = "  " * (title_info['level'] - 1)
                md_content += f"{indent}- {title_info['title']}\n"
            
            if len(article['titles']) > 10:
                md_content += f"  ... 还有 {len(article['titles'])-10} 个小节\n"
        else:
            md_content += "> *（本文无章节标题）*\n"
        
        md_content += "\n---\n\n"
    
    # 添加统计信息
    total_words = sum(a['word_count'] for a in articles)
    total_size = sum(a['size'] for a in articles)
    
    md_content += f"""
## 📊 统计信息

- **文章总数**: {len(articles)} 篇
- **总字数**: {total_words:,} 字
- **总大小**: {total_size:.1f} KB
- **平均字数**: {total_words//len(articles) if articles else 0:,} 字/篇
- **最近更新**: {articles[0]['modify_time'] if articles else "无"}
"""

    # 写入文件
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✅ 索引生成完成！")
    print(f"   文章数: {len(articles)}")
    print(f"   总字数: {total_words:,}")
    
    # 显示标题提取统计
    toc_titles = sum(1 for a in articles if re.search(r'@\[toc\]', open(a['full_path'], 'r', encoding='utf-8').read(500)))
    print(f"   使用@[toc]格式的文章: {toc_titles}")
    
    return articles

def main():
    """主函数"""
    print("🤖 Markdown 索引生成器 (支持@[toc]格式)")
    print("=" * 60)
    
    # 自动检测当前文件夹
    current_dir = os.path.dirname(os.path.abspath(__file__))
    init_file = os.path.join(current_dir, "init.md")
    
    # 检查当前目录
    md_files = [f for f in os.listdir(current_dir) if f.endswith('.md') and f != 'init.md']
    
    if not md_files:
        print("⚠️  当前目录下没有找到markdown文件")
        create = input("是否创建空的索引文件？(y/n): ").lower() == 'y'
        if create:
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(f"""# 📚 文章索引

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 
> 当前目录下暂无文章。

请在此目录下添加Markdown文件，然后运行生成脚本。
""")
            print(f"✅ 已创建空索引: {init_file}")
        return
    
    print(f"📁 扫描目录: {current_dir}")
    print(f"📄 找到 {len(md_files)} 个markdown文件")
    print("-" * 60)
    
    # 生成索引
    try:
        articles = generate_index_with_toc(init_file)
        
        # 显示示例
        print("\n📋 标题提取示例:")
        print("-" * 60)
        for article in articles[:3]:  # 显示前3个
            print(f"📄 {article['filename']}")
            print(f"   → 标题: {article['title']}")
            if article['titles']:
                print(f"   → 包含 {len(article['titles'])} 个小节")
            print()
        
        if len(articles) > 3:
            print(f"... 还有 {len(articles)-3} 个文件")
        
        print(f"\n🎉 索引已保存至: {init_file}")
        
    except Exception as e:
        print(f"❌ 生成索引时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()