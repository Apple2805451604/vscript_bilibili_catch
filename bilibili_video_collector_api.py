import os
import json
import time
import random
import requests
from tqdm import tqdm

class BilibiliVideoCollectorAPI:
    """B站视频列表收集类（API版本），用于通过API根据UP主UID获取所有视频列表"""
    
    def __init__(self, cookie_path=None, proxy=None):
        """初始化视频收集器
        
        Args:
            cookie_path: Cookie文件路径
            proxy: 代理设置，如 http://127.0.0.1:7890
        """
        # 初始化cookies属性
        self.cookies = {}
        self.proxies = None
        
        # 设置代理
        if proxy:
            self.proxies = {'http': proxy, 'https': proxy}
        
        # 加载Cookie
        if cookie_path and os.path.exists(cookie_path):
            try:
                with open(cookie_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    if isinstance(cookies, list):
                        self.cookies = {cookie['name']: cookie['value'] for cookie in cookies}
                    elif isinstance(cookies, dict):
                        self.cookies = cookies
                    print(f"已加载Cookie，共{len(self.cookies)}项")
            except Exception as e:
                print(f"警告: 加载Cookie失败 - {str(e)}")
        
        # API地址 - 使用更简单的接口
        self.api_urls = {
            'up_info': 'https://api.bilibili.com/x/space/acc/info',
            'video_list': 'https://api.bilibili.com/x/space/wbi/arc/search'
        }
        
        # 重试次数和延迟设置
        self.max_retries = 3
        self.page_size = 10  # 减少每页数量，降低请求负载
    
    def _get_simple_headers(self):
        """获取简单的请求头，避免被识别为爬虫"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
    
    def _get_common_params(self, params):
        """添加通用请求参数
        
        Args:
            params: 请求参数
            
        Returns:
            添加通用参数后的参数字典
        """
        # 只添加时间戳，避免过多参数触发反爬
        params['_'] = str(int(time.time() * 1000))  # 使用毫秒级时间戳
        return params
    
    def get_up_info(self, uid):
        """获取UP主信息
        
        Args:
            uid: UP主UID
            
        Returns:
            UP主信息字典
        """
        params = self._get_common_params({'mid': uid})
        headers = self._get_simple_headers()
        
        # 添加Referer
        headers['Referer'] = f'https://space.bilibili.com/{uid}/'
        
        for retry in range(self.max_retries):
            try:
                print(f"正在获取UP主信息 (尝试 {retry + 1}/{self.max_retries})...")
                
                # 使用简单的get请求，不使用session
                response = requests.get(
                    self.api_urls['up_info'],
                    params=params,
                    headers=headers,
                    cookies=self.cookies,
                    proxies=self.proxies,
                    timeout=10
                )
                
                # 检查响应状态码
                if response.status_code == 200:
                    data = response.json()
                    
                    # 检查API返回的状态
                    if data.get('code') == 0 and 'data' in data:
                        # 提取需要的信息
                        return {
                            'name': data['data'].get('name', '未知'),
                            'face': data['data'].get('face', ''),
                            'sign': data['data'].get('sign', '无简介'),
                            'level': data['data'].get('level', 0),
                            'archive_count': data['data'].get('archive_count', 0),
                            'article_count': data['data'].get('article_count', 0),
                            'following': data['data'].get('following', 0),
                            'fans': data['data'].get('fans', 0),
                            'likes': data['data'].get('likes', 0)
                        }
                    else:
                        error_msg = data.get('message', '未知错误')
                        print(f"获取UP主信息失败: {error_msg} (code: {data.get('code')})")
                else:
                    print(f"获取UP主信息失败: HTTP状态码 {response.status_code}")
                    print(f"响应内容: {response.text[:200]}...")
            except Exception as e:
                print(f"获取UP主信息时发生异常: {str(e)}")
            
            # 重试前等待
            if retry < self.max_retries - 1:
                wait_time = random.uniform(5, 10)
                print(f"{wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
        
        # 如果多次尝试后仍失败，返回基本信息
        print("获取UP主信息失败，返回基本信息")
        return {
            'name': f'未知用户{uid}',
            'sign': '无法获取简介',
            'archive_count': 0
        }
    
    def get_up_videos(self, uid, max_videos=None):
        """获取UP主所有视频列表
        
        Args:
            uid: UP主UID
            max_videos: 最大获取视频数量，None表示获取全部
            
        Returns:
            视频列表
        """
        videos = []
        page = 1
        has_more = True
        
        # 计算需要获取的页数
        total_pages = float('inf')  # 初始化为无穷大
        if max_videos:
            total_pages = (max_videos + self.page_size - 1) // self.page_size
        
        print(f"开始获取视频列表，每页 {self.page_size} 个视频")
        
        while has_more and page <= total_pages:
            print(f"正在获取第 {page} 页视频...")
            
            # 构建请求参数
            params = self._get_common_params({
                'mid': uid,
                'pn': page,
                'ps': self.page_size,
                'order': 'pubdate',  # 按发布日期排序
                'tid': 0  # 全部分区
            })
            
            headers = self._get_simple_headers()
            headers['Referer'] = f'https://space.bilibili.com/{uid}/'
            
            try:
                # 发送请求
                response = requests.get(
                    self.api_urls['video_list'],
                    params=params,
                    headers=headers,
                    cookies=self.cookies,
                    proxies=self.proxies,
                    timeout=15
                )
                
                # 检查响应状态码
                if response.status_code == 200:
                    data = response.json()
                    
                    # 检查API返回的状态
                    if data.get('code') == 0 and 'data' in data and 'list' in data['data'] and 'vlist' in data['data']['list']:
                        page_videos = data['data']['list']['vlist']
                        
                        # 处理每一个视频
                        for video in page_videos:
                            video_info = {
                                'bvid': video.get('bvid', ''),
                                'aid': video.get('aid', 0),
                                'title': video.get('title', '未知标题'),
                                'description': video.get('description', ''),
                                'pic': video.get('pic', ''),
                                'created': video.get('created', 0),
                                'length': video.get('length', ''),
                                'play': video.get('play', 0),
                                'comment': video.get('comment', 0),
                                'video_review': video.get('video_review', 0),
                                'favorites': video.get('favorites', 0),
                                'author': video.get('author', ''),
                                'typeid': video.get('typeid', 0),
                                'typename': video.get('typename', ''),
                                'is_union_video': video.get('is_union_video', 0)
                            }
                            videos.append(video_info)
                            
                            # 如果已达到最大视频数量，停止获取
                            if max_videos and len(videos) >= max_videos:
                                has_more = False
                                break
                        
                        # 检查是否还有更多页
                        if len(page_videos) < self.page_size or (max_videos and len(videos) >= max_videos):
                            has_more = False
                        else:
                            # 增加页码，准备获取下一页
                            page += 1
                            # 添加随机延迟，避免请求过于频繁
                            wait_time = random.uniform(3, 7)
                            print(f"已获取第 {page-1} 页，等待 {wait_time:.1f} 秒后继续获取第 {page} 页...")
                            time.sleep(wait_time)
                    else:
                        error_msg = data.get('message', '未知错误')
                        print(f"获取视频列表失败: {error_msg} (code: {data.get('code')})")
                        # 尝试重试
                        if page > 1:
                            wait_time = random.uniform(5, 10)
                            print(f"{wait_time:.1f} 秒后重试第 {page} 页...")
                            time.sleep(wait_time)
                        else:
                            # 第一页失败，直接结束
                            has_more = False
                else:
                    print(f"获取视频列表失败: HTTP状态码 {response.status_code}")
                    # 尝试重试
                    if page > 1:
                        wait_time = random.uniform(5, 10)
                        print(f"{wait_time:.1f} 秒后重试第 {page} 页...")
                        time.sleep(wait_time)
                    else:
                        # 第一页失败，直接结束
                        has_more = False
            except Exception as e:
                print(f"获取视频列表时发生异常: {str(e)}")
                # 尝试重试
                if page > 1:
                    wait_time = random.uniform(5, 10)
                    print(f"{wait_time:.1f} 秒后重试第 {page} 页...")
                    time.sleep(wait_time)
                else:
                    # 第一页失败，直接结束
                    has_more = False
        
        print(f"共获取到 {len(videos)} 个视频")
        return videos
    
    def print_video_list(self, videos, show_all=False):
        """打印视频列表
        
        Args:
            videos: 视频列表
            show_all: 是否显示所有信息
        """
        if not videos:
            print("没有找到视频")
            return
        
        # 按发布时间排序（从新到旧）
        sorted_videos = sorted(videos, key=lambda x: x.get('created', 0), reverse=True)
        
        # 打印视频信息
        for i, video in enumerate(sorted_videos, 1):
            # 格式化发布时间
            pub_date = time.strftime('%Y-%m-%d', time.localtime(video.get('created', 0)))
            
            print(f"\n视频 {i}: {video.get('title', '未知标题')}")
            print(f"发布时间: {pub_date}")
            print(f"时长: {video.get('length', '未知')}")
            print(f"播放量: {video.get('play', 0):,}")
            print(f"收藏数: {video.get('favorites', 0):,}")
            print(f"BV号: {video.get('bvid', '未知')}")
            print(f"视频链接: https://www.bilibili.com/video/{video.get('bvid', '')}")
            
            if show_all:
                print(f"评论数: {video.get('comment', 0):,}")
                print(f"弹幕数: {video.get('video_review', 0):,}")
                if video.get('description', ''):
                    # 限制描述长度
                    desc = video.get('description', '')[:200]
                    print(f"简介: {desc}..." if len(video.get('description', '')) > 200 else f"简介: {desc}")
            
            print("=" * 80)
        
        print(f"\n总计获取到 {len(sorted_videos)} 个视频")
    
    def _get_mock_videos(self, uid, max_videos=None):
        """获取模拟视频数据，用于测试或API请求失败时提供替代数据
        
        Args:
            uid: UP主UID
            max_videos: 最大获取视频数量
            
        Returns:
            模拟视频列表
        """
        # 生成模拟视频数据
        mock_videos = []
        count = min(max_videos or 10, 10)  # 最多生成10个模拟视频
        
        for i in range(count):
            mock_videos.append({
                'bvid': f"BV{random.randint(100000000000, 999999999999)}",
                'title': f"模拟视频标题 {i+1}",
                'description': f"这是一个模拟的视频描述，用于测试显示功能。\nUP主ID: {uid}",
                'created': int(time.time()) - i * 86400,  # 每天一个视频
                'length': f"{random.randint(1, 30)}:{random.randint(0, 59):02d}",
                'play': random.randint(1000, 100000),
                'comment': random.randint(10, 1000),
                'favorites': random.randint(100, 10000)
            })
        
        return mock_videos
    
    def collect_videos_by_uid(self, uid, max_videos=None, show_all=False):
        """根据UID收集并打印UP主视频列表
        
        Args:
            uid: UP主UID
            max_videos: 最大获取视频数量
            show_all: 是否显示所有信息
            
        Returns:
            视频列表
        """
        print(f"开始获取UP主 {uid} 的视频列表...")
        
        # 先做简单的UID验证
        if not isinstance(uid, (int, str)) or (isinstance(uid, str) and not uid.isdigit()):
            print(f"错误: 无效的UID格式 - {uid}")
            return []
        
        uid = str(uid)
        videos = []
        
        try:
            # 1. 获取UP主信息（单独的请求，使用更长的延迟）
            print("\n[步骤1] 获取UP主信息...")
            up_info = self.get_up_info(uid)
            print(f"UP主: {up_info.get('name', '未知')}")
            print(f"简介: {up_info.get('sign', '无简介')}")
            if 'fans' in up_info:
                print(f"粉丝数: {up_info.get('fans', 0):,}")
            if 'archive_count' in up_info:
                print(f"总视频数: {up_info.get('archive_count', 0)}")
            print("=" * 50)
            
            # 2. 间隔较长时间后获取视频列表
            print("\n[步骤2] 等待一段时间后获取视频列表...")
            wait_time = random.uniform(5, 8)
            print(f"等待 {wait_time:.1f} 秒，避免触发频率限制...")
            time.sleep(wait_time)
            
            # 3. 获取视频列表
            videos = self.get_up_videos(uid, max_videos)
            
            # 4. 打印视频列表
            if videos:
                print("\n[步骤3] 打印视频列表...")
                self.print_video_list(videos, show_all)
            else:
                print("\n未获取到任何视频")
                
        except KeyboardInterrupt:
            print("\n用户中断操作")
        except Exception as e:
            print(f"发生错误: {str(e)}")
            # 即使出错，也尝试提供模拟数据
            if not videos:
                print("提供模拟视频数据...")
                videos = self._get_mock_videos(uid, max_videos)
                if videos:
                    self.print_video_list(videos, show_all)
        
        return videos