# B站视频下载工具 (VScript Bilibili Catch)

一个高效的B站视频下载工具，支持单个视频和UP主视频批量下载，提供多种视频质量选项和格式选择。

## 功能特点

- 支持单个视频下载（通过BV号）
- 支持UP主视频批量下载
- 智能选择最佳视频流和音频流
- 支持Cookie登录以下载4K视频
- 断点续传功能（存疑）
- 多线程下载优化
- 自动合并视频和音频

## 环境要求

- Python 3.8 或更高版本
- 依赖库：requests, tqdm, selenium

## 安装步骤

1. 克隆或下载本项目到本地

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 对于Selenium方式的视频收集，需要安装Chrome浏览器并下载对应版本的chromedriver，放置在tools目录下。

## 使用方法

### 单个视频下载

使用以下命令下载单个视频：
例如：

```bash
python main.py --bvid BV1PCyqBREWT --cookie ./cookie.json --download    
```

### UP主视频批量下载

~~使用API方式批量下载UP主视频~~（这种方法效果很差，会被反爬虫机制限制）

或使用Selenium方式批量下载：
例如：

```bash
python main.py --selenium 35347825 --cookie ./cookie.json --download 
```

## 参数说明

### 通用参数

- `--bvid`: 视频的BV号，用于单个视频下载
- `--selenium`: 指定selenium方式批量下载UP主视频，需要提供UP主的用户ID
- `--cookie`: Cookie文件路径，用于下载大会员视频
- `--download`: 与--selenium一起使用时，收集视频后自动下载每个视频

## Cookie文件说明

为了下载更高质量的视频，需要提供Cookie文件。将Cookie保存为`cookie.json`文件放置在项目根目录即可。Cookie文件为以下格式：

```json
[
  {
    "name": "随意",
    "value": "你的cookie"
  }
]
```

## 目录结构

- `bilibili_downloader.py`: 核心下载器类，处理视频下载逻辑
- `bilibili_video_collector_api.py`: API方式的视频收集器
- `bilibili_video_collector_selenium.py`: Selenium方式的视频收集器
- `main.py`: 主程序入口
- `requirements.txt`: 项目依赖
- `downloads/`: 下载的视频存储目录
- `tools/`: 工具目录，存放chromedriver等

## 注意事项

1. 请遵守B站用户协议，仅下载用于个人学习和研究的视频
2. 部分高清视频和独家内容需要大会员权限
3. 频繁下载可能会被B站限制IP，建议适当控制下载频率
4. 本工具仅用于学习研究，请勿用于商业用途

## 常见问题

### 下载失败或只能获取低质量视频

1. 检查Cookie是否有效且包含必要信息
2. 确认视频是否为大会员独占内容

### JSON解析错误

1. 检查Cookie文件格式是否正确
2. 确认网络连接是否正常
3. 可能是B站API更新，尝试更新工具版本

## 免责声明

本工具仅用于学习和研究目的，使用者应遵守相关法律法规和B站用户协议。由于使用本工具产生的任何法律责任，由使用者自行承担。