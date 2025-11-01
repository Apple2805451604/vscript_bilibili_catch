import os
import sys
import argparse
from bilibili_downloader import BilibiliDownloader
from bilibili_video_collector_api import BilibiliVideoCollectorAPI
from bilibili_video_collector_selenium import BilibiliVideoCollectorSelenium

def main():
    """主函数，解析命令行参数并执行视频下载或列表收集"""
    parser = argparse.ArgumentParser(description='B站视频工具 - 支持单个视频下载和UP主视频列表收集')
    
    # 模式选择 - 新增互斥组
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--bvid', type=str, help='单个视频的BV号（下载模式）')
    mode_group.add_argument('--uid', type=int, help='UP主UID（列表收集模式）')
    mode_group.add_argument('--selenium', type=int, help='UP主UID（Selenium模式，模拟浏览器获取视频BV号）')
    parser.add_argument('--download', action='store_true', help='当与--selenium一起使用时，收集视频后自动下载每个视频')
    
    # 共同参数
    parser.add_argument('--cookie', type=str, default=None, help='Cookie文件路径')
    parser.add_argument('--proxy', type=str, default=None, help='代理设置，如 http://127.0.0.1:7890')
    
    # 下载模式参数
    parser.add_argument('--output', type=str, default='./downloads', help='输出目录（下载模式）')
    parser.add_argument('--quality', type=int, choices=[16, 32, 64, 74, 80, 112, 116], default=None, 
                        help='视频质量代码 (16=流畅 32=高清 64=超清 74=1080P 80=1080P+ 112=4K 116=HDR)')
    parser.add_argument('--audio_quality', type=int, choices=[30200, 30216, 30232], default=None,
                        help='音频质量代码 (30200=普通 30216=高清 30232=无损)')
    parser.add_argument('--format', type=str, default='mp4', choices=['mp4', 'mkv', 'flv'], help='输出视频格式')
    
    # 列表收集模式参数
    parser.add_argument('--max', type=int, default=None, help='最大获取视频数量（列表收集模式和Selenium模式）')
    parser.add_argument('--all', action='store_true', help='显示所有信息（列表收集模式）')
    parser.add_argument('--headless', action='store_true', default=False, help='是否使用无头模式（Selenium模式）')
    
    args = parser.parse_args()
    
    # 检查Cookie文件是否存在
    if args.cookie and not os.path.exists(args.cookie):
        print(f"警告: Cookie文件 '{args.cookie}' 不存在")
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    try:
        if args.bvid:
            # 下载模式
            # 初始化下载器
            downloader = BilibiliDownloader(cookie_path=args.cookie, proxy=args.proxy)
            
            # 下载单个视频
            print(f"\n开始下载视频: {args.bvid}")
            output_path = downloader.download_video(
                args.bvid,
                output_dir=args.output,
                quality=args.quality,
                audio_quality=args.audio_quality,
                format=args.format
            )
            
            if output_path:
                print(f"\n视频下载完成: {output_path}")
            else:
                print("\n视频下载失败")
        elif args.uid:
            # 列表收集模式
            # 初始化API版本视频收集器
            collector = BilibiliVideoCollectorAPI(cookie_path=args.cookie, proxy=args.proxy)
            
            # 收集并打印视频列表
            collector.collect_videos_by_uid(args.uid, args.max, args.all)
        elif args.selenium:
            # Selenium模式
            # 初始化Selenium版本视频收集器
            collector = BilibiliVideoCollectorSelenium(cookie_path=args.cookie, proxy=args.proxy)
            
            # 使用Selenium收集视频BV号
            collector.collect_videos_by_selenium(args.selenium, args.max, args.headless, auto_download=args.download)
    
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"\n程序异常: {str(e)}")
        import traceback
        traceback.print_exc()
    
if __name__ == "__main__":
    main()