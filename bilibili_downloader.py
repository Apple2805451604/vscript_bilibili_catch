import os
import sys
import json
import time
import random
import requests
from tqdm import tqdm
import subprocess

class BilibiliDownloader:
    """B站视频下载类，用于下载单个视频"""
    
    def __init__(self, cookie_path=None, proxy=None):
        """初始化下载器
        
        Args:
            cookie_path: Cookie文件路径
            proxy: 代理设置，如 http://127.0.0.1:7890
        """
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Connection': 'keep-alive',
            'Referer': 'https://www.bilibili.com/',
            'Origin': 'https://www.bilibili.com',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1'
        }
        
        # 设置请求头
        self.session.headers.update(self.headers)
        
        # 加载Cookie
        self.cookies_loaded = False
        if cookie_path and os.path.exists(cookie_path):
            try:
                with open(cookie_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    
                    try:
                        cookies = json.loads(file_content)
                        
                        print(f"调试: Cookie格式类型: {type(cookies)}")
                        
                        # 处理常规格式
                        if isinstance(cookies, list):
                            print(f"调试: 处理列表格式cookie，共{len(cookies)}条")
                            for cookie in cookies:
                                if isinstance(cookie, dict):
                                    # 标准浏览器cookie导出格式
                                    if 'name' in cookie and 'value' in cookie:
                                        self.session.cookies.set(cookie['name'], cookie['value'])
                                        print(f"已加载cookie: {cookie['name']}")
                                    # 兼容其他可能的格式
                                    elif 'value' in cookie:
                                        # 尝试从value中提取键值对
                                        cookie_str = str(cookie['value'])
                                        if '=' in cookie_str:
                                            try:
                                                k, v = cookie_str.split('=', 1)
                                                self.session.cookies.set(k.strip(), v.strip())
                                                print(f"已加载cookie: {k.strip()}")
                                            except:
                                                continue
                                elif isinstance(cookie, str):
                                    # 字符串格式，尝试按分号分割
                                    for pair in cookie.split(';'):
                                        pair = pair.strip()
                                        if '=' in pair:
                                            try:
                                                k, v = pair.split('=', 1)
                                                self.session.cookies.set(k.strip(), v.strip())
                                                print(f"已加载cookie: {k.strip()}")
                                            except:
                                                continue
                        elif isinstance(cookies, dict):
                            print(f"调试: 处理字典格式cookie，共{len(cookies)}条")
                            # 直接设置每个cookie
                            for key, value in cookies.items():
                                # 如果值本身是一个包含多个cookie的字符串，尝试分割
                                if isinstance(value, str) and '=' in value and ';' in value:
                                    for pair in value.split(';'):
                                        pair = pair.strip()
                                        if '=' in pair:
                                            try:
                                                k, v = pair.split('=', 1)
                                                self.session.cookies.set(k.strip(), v.strip())
                                                print(f"已加载cookie: {k.strip()}")
                                            except:
                                                continue
                                else:
                                    # 直接设置单个cookie
                                    self.session.cookies.set(key, str(value))
                                    print(f"已加载cookie: {key}")
                    except json.JSONDecodeError:
                        print("JSON解析失败，尝试作为文本直接解析cookie")
                        import re
                        cookie_pairs = re.findall(r'([^=;]+)=([^;]+)', file_content)
                        for name, value in cookie_pairs:
                            name = name.strip()
                            value = value.strip()
                            self.session.cookies.set(name, value)
                            print(f"已从文本提取cookie: {name}")
                    
                    # 额外检查：直接从文件内容中提取所有可能的cookie
                    import re
                    cookie_matches = re.findall(r'(\w+)=(\S+)', file_content)
                    for name, value in cookie_matches:
                        if name not in self.session.cookies:
                            self.session.cookies.set(name, value.split(';')[0])
                            print(f"已从文件内容提取cookie: {name}")
                    
                    self.cookies_loaded = True
                    print(f"Cookie加载完成，总共加载了{len(self.session.cookies)}个cookie")
                    
                    # 检查关键cookie是否已加载
                    critical_cookies = ['SESSDATA', 'bili_jct', 'DedeUserID', 'DedeUserID__ckMd5', 'sid']
                    for critical in critical_cookies:
                        if critical in self.session.cookies:
                            print(f"✓ 关键cookie已加载: {critical}")
                        else:
                            print(f"✗ 关键cookie缺失: {critical}")
                            
            except Exception as e:
                print(f"警告: 加载Cookie失败 - {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print("警告: Cookie文件不存在或路径无效")
        
        # 设置代理
        if proxy:
            self.proxies = {'http': proxy, 'https': proxy}
            self.session.proxies.update(self.proxies)
        
        # API地址
        self.api_urls = {
            'video_info': 'https://api.bilibili.com/x/web-interface/view',
            'play_url': 'https://api.bilibili.com/x/player/playurl'
        }
        
        # 重试次数
        self.max_retries = 3
    
    def get_video_info(self, bvid):
        """获取视频信息
        
        Args:
            bvid: 视频BV号
            
        Returns:
            视频信息字典
        """
        params = {'bvid': bvid}
        for retry in range(self.max_retries):
            try:
                response = self.session.get(self.api_urls['video_info'], params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get('code') == 0:
                    return data['data']
                else:
                    print(f"获取视频信息失败: {data.get('message', '未知错误')}")
                    if retry < self.max_retries - 1:
                        print(f"{retry + 1} 秒后重试...")
                        time.sleep(retry + 1)
            except Exception as e:
                print(f"获取视频信息异常: {str(e)}")
                if retry < self.max_retries - 1:
                    print(f"{retry + 1} 秒后重试...")
                    time.sleep(retry + 1)
        
        raise Exception(f"获取视频信息失败，已重试{self.max_retries}次")
    
    def get_video_streams(self, bvid, cid, quality=127):
        """获取视频流信息
        
        Args:
            bvid: 视频BV号
            cid: 视频cid
            quality: 请求的视频质量等级
            
        Returns:
            视频流信息字典
        """
        print(f"\n===== 获取视频流信息 =====")
        print(f"请求参数 - bvid: {bvid}, cid: {cid}, quality: {quality}")
        
        # 确保cookie正确设置到session中
        critical_cookies = ['SESSDATA', 'bili_jct', 'DedeUserID', 'DedeUserID__ckMd5', 'sid']
        found_cookies = [cookie.name for cookie in self.session.cookies if cookie.name in critical_cookies]
        print(f"当前session中的关键cookie: {', '.join(found_cookies)} ({len(found_cookies)}/{len(critical_cookies)})")
        
        # 更新API地址列表，增加wbi API支持
        api_endpoints = [
            'https://api.bilibili.com/x/player/wbi/playurl',  # 主要API（WBI加密）
            'https://api.bilibili.com/x/player/playurl',      # 传统API
            'https://api.bilibili.com/x/player/playurl/v2'    # V2 API
        ]
        
        # 定义不同的请求参数组合，尝试多种方式获取高质量视频
        request_configs = [
            # 4K专属配置 - 最高优先级
            {
                'params': {
                    'bvid': bvid,
                    'cid': cid,
                    'qn': 127,
                    'fnval': 4048,
                    'fnver': 0,
                    'fourk': 1,
                    'platform': 'pc',
                    'from_client': 'BROWSER',
                    'high_quality': 1,
                    'dash': 1,
                    'otype': 'json',
                    'ts': int(time.time() * 1000)
                },
                'label': '4K专属配置'
            },
            # 高级会员配置
            {
                'params': {
                    'bvid': bvid,
                    'cid': cid,
                    'qn': 125,  # 大会员专享清晰度
                    'fnval': 4048,
                    'fnver': 0,
                    'fourk': 1,
                    'platform': 'pc',
                    'from_client': 'BROWSER',
                    'high_quality': 1,
                    'dash': 1,
                    'otype': 'json',
                    'ts': int(time.time() * 1000)
                },
                'label': '高级会员配置'
            },
            # 标准高质量配置
            {
                'params': {
                    'bvid': bvid,
                    'cid': cid,
                    'qn': quality,
                    'fnval': 4048,
                    'fnver': 0,
                    'fourk': 1,
                    'platform': 'pc',
                    'from_client': 'BROWSER',
                    'ts': int(time.time() * 1000)
                },
                'label': '标准高质量'
            },
            # 增强配置，添加更多可能需要的参数
            {
                'params': {
                    'bvid': bvid,
                    'cid': cid,
                    'qn': quality,
                    'fnval': 4048,
                    'fnver': 0,
                    'fourk': 1,
                    'platform': 'pc',
                    'from_client': 'BROWSER',
                    'ts': int(time.time() * 1000),
                    'high_quality': 1,
                    'dash': 1,
                    'browser_resolution': '1920-1080',
                    'support_format': '0,2,5,7,8,10,12,14,16,18,20,22,24,26,28,30',
                },
                'label': '增强配置'
            },
            # 简化配置，防止参数过多被拒绝
            {
                'params': {
                    'bvid': bvid,
                    'cid': cid,
                    'qn': quality,
                    'fnval': 16,
                    'fnver': 0,
                    'fourk': 1,
                    'platform': 'html5',
                    'ts': int(time.time() * 1000)
                },
                'label': '简化配置'
            }
        ]
        
        # 不同的quality值，从高到低尝试
        quality_values = [quality, 125, 120, 116, 112, 80, 64, 32, 16]
        
        # 创建增强的请求头函数
        def create_enhanced_headers(bvid):
            headers = self.headers.copy()
            headers.update({
                'Accept': 'application/json, text/plain, */*',
                'Referer': f'https://www.bilibili.com/video/{bvid}',
                'X-Requested-With': 'XMLHttpRequest',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                # 增加重要的客户端标识
                'Client-Platform': 'web',
                'Client-App': 'browser',
                # 模拟真实浏览器特征
                'DNT': '1',
                'X-Real-IP': '114.114.114.114'
            })
            
            # 确保cookie被添加到请求头
            cookie_header = '; '.join([f"{c.name}={c.value}" for c in self.session.cookies])
            if cookie_header:
                headers['Cookie'] = cookie_header
            
            return headers
        
        # 定义AVC编码优先级，用于识别高规格编码
        AVC_PRIORITY = {
            'avc1.640033': 100,  # 4K AVC编码，最高优先级
            'avc1.640032': 90,   # 高规格AVC编码
            'avc1.640031': 85,   # 高规格AVC编码
            'avc1.640028': 80,   # 1080P高规格AVC编码
            'avc1.640027': 75,   # 1080P AVC编码
            'avc1.64001F': 70,   # 720P/852P AVC编码
        }
        
        # 分析视频流质量
        def analyze_streams(streams):
            if not streams:
                return None, None, None
            
            heights = [s.get('height', 0) for s in streams]
            codecs = [s.get('codecs', '') for s in streams]
            max_height = max(heights) if heights else 0
            
            # 检查是否有高规格AVC编码
            has_high_avc = any(avc_codec in codec for avc_codec in AVC_PRIORITY for codec in codecs)
            
            # 找出最高规格的AVC编码
            best_avc_codec = None
            best_priority = 0
            for codec in codecs:
                for avc_codec, priority in AVC_PRIORITY.items():
                    if avc_codec in codec and priority > best_priority:
                        best_priority = priority
                        best_avc_codec = avc_codec
            
            return max_height, has_high_avc, best_avc_codec
        
        # 尝试不同的API端点
        for endpoint in api_endpoints:
            print(f"\n尝试API端点: {endpoint}")
            
            # 尝试不同的请求配置
            for config in request_configs:
                params_template = config['params']
                label = config['label']
                print(f"尝试配置: {label}")
                
                # 对每个配置尝试不同的quality值
                for q in quality_values:
                    try:
                        # 复制参数模板并更新quality
                        params = params_template.copy()
                        params['qn'] = q
                        print(f"  尝试quality值: {q}, fnval={params.get('fnval')}, fourk={params.get('fourk')}")
                        
                        # 设置增强的请求头
                        enhanced_headers = create_enhanced_headers(bvid)
                        
                        # 打印当前请求的关键信息
                        has_sessdata = 'SESSDATA' in enhanced_headers.get('Cookie', '')
                        has_bili_jct = 'bili_jct' in enhanced_headers.get('Cookie', '')
                        print(f"  Cookie状态: SESSDATA={'✓' if has_sessdata else '✗'}, bili_jct={'✓' if has_bili_jct else '✗'}")
                        
                        # 发送请求
                        response = self.session.get(
                            endpoint, 
                            params=params, 
                            headers=enhanced_headers,
                            timeout=30
                        )
                        
                        print(f"  响应状态码: {response.status_code}")
                        
                        # 检查是否需要认证
                        if response.status_code == 401:
                            print("  警告: 需要登录认证，检查cookie是否有效")
                            continue
                        
                        # 尝试解析响应
                        try:
                            data = response.json()
                        except json.JSONDecodeError as e:
                            print(f"  JSON解析错误: {str(e)}")
                            print(f"  响应内容开头: {response.text[:100]}...")
                            # 尝试从文本中提取JSON
                            import re
                            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                            if json_match:
                                try:
                                    data = json.loads(json_match.group())
                                    print("  成功从文本中提取JSON")
                                except:
                                    print("  无法提取有效JSON")
                                    continue
                            else:
                                continue
                        
                        # 检查API响应状态
                        print(f"  API响应状态码: {data.get('code', '未知')}")
                        
                        if data.get('code') == 0 and 'data' in data:
                            # 检查是否获取到视频流，并分析其质量
                            dash = data.get('data', {}).get('dash', {})
                            video_streams = dash.get('video', [])
                            
                            if video_streams:
                                # 分析视频流质量
                                max_height, has_high_avc, best_avc_codec = analyze_streams(video_streams)
                                
                                # 输出详细信息
                                print(f"  ✓ 成功获取视频流信息")
                                print(f"  最高分辨率: {max_height}P")
                                print(f"  视频流数量: {len(video_streams)}")
                                
                                # 输出所有可用的视频流质量
                                available_qualities = set([v.get('height', 0) for v in video_streams])
                                print(f"  可用分辨率: {sorted(available_qualities, reverse=True)}P")
                                
                                # 输出编码信息
                                codecs = [v.get('codecs', '') for v in video_streams]
                                print(f"  可用编码: {codecs}")
                                
                                # 特殊标记高规格编码
                                if best_avc_codec:
                                    print(f"  ✓ 发现高规格AVC编码: {best_avc_codec} (优先级: {AVC_PRIORITY[best_avc_codec]})")
                                
                                # 保存当前找到的最佳流，继续尝试获取更高质量的流
                                if 'best_streams' not in locals():
                                    best_streams = {'data': data['data'], 'max_height': max_height, 'best_codec': best_avc_codec}
                                else:
                                    # 比较并更新最佳流
                                    if max_height > best_streams['max_height'] or \
                                       (max_height == best_streams['max_height'] and best_avc_codec and \
                                        (not best_streams['best_codec'] or \
                                         (best_streams['best_codec'] and AVC_PRIORITY.get(best_avc_codec, 0) > AVC_PRIORITY.get(best_streams['best_codec'], 0)))):
                                        best_streams = {'data': data['data'], 'max_height': max_height, 'best_codec': best_avc_codec}
                                        print(f"✓ 更新最佳视频流: {max_height}P, 编码: {best_avc_codec or '未知'}")
                                    
                                # 如果已经找到4K或高规格AVC编码，可以提前返回
                                if max_height >= 2160 or best_avc_codec == 'avc1.640033':
                                    print(f"🎉 找到最高质量视频流！4K或高规格AVC编码")
                                    return data['data']
                            else:
                                print("  警告: API返回成功但未包含视频流信息")
                                # 检查是否有权限信息
                                message = data.get('data', {}).get('message', '')
                                if message:
                                    print(f"  提示信息: {message}")
                                    if '大会员' in message or '会员' in message:
                                        print("  检测到会员专属内容，请确保cookie包含有效的会员权限")
                                continue
                        else:
                            error_msg = data.get('message', '未知错误')
                            print(f"  获取失败: {error_msg}")
                            # 特殊处理常见错误
                            if '权限不足' in error_msg or '权限' in error_msg:
                                print("  提示: 权限错误可能是因为cookie无效或内容需要特殊权限")
                            elif '403' in str(response.status_code):
                                print("  提示: 403错误通常表示被API拒绝，可能需要更新cookie或参数")
                            continue
                            
                    except Exception as e:
                        print(f"  获取异常: {str(e)}")
                        continue
                
                # 短暂延迟后重试
                time.sleep(0.5)
        
        # 如果在前面的尝试中找到了最佳流，返回它
        if 'best_streams' in locals():
            print(f"\n🏆 返回最佳视频流: {best_streams['max_height']}P, 最佳编码: {best_streams['best_codec'] or '未知'}")
            return best_streams['data']
            
        # 最后的尝试：使用最简化的参数
        try:
            url = 'https://api.bilibili.com/x/player/playurl'
            params = {
                'bvid': bvid,
                'cid': cid,
                'qn': 127,  # 最高质量要求
                'fnval': 128,  # 支持H.265等高级编码
                'fnver': 0,
                'fourk': 1,  # 开启4K请求
                'platform': 'html5'
            }
            
            print("\n尝试最后一次获取 (极简参数)")
            headers = create_enhanced_headers(bvid)
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            result = response.json()
            
            if result.get('code') == 0 and 'data' in result:
                print("✓ 成功获取基础视频流")
                return result['data']
            else:
                print(f"最终尝试失败: {result.get('message', '未知错误')}")
        except Exception as e:
            print(f"最终尝试异常: {str(e)}")
            
        raise Exception(f"获取视频流信息失败，已尝试所有可用API和配置")
    
    def select_best_stream(self, streams, prefer_quality=None, prefer_audio_quality=None):
        """选择最佳视频流和音频流，优先高规格AVC编码、4K画质和高质量音频
        
        Args:
            streams: 视频流信息
            prefer_quality: 指定视频质量
            prefer_audio_quality: 指定音频质量
            
        Returns:
            (best_video, best_audio) 元组
        """
        print(f"\n===== 媒体流选择与优化 =====")
        
        dash = streams.get('dash', {})
        video_streams = dash.get('video', [])
        audio_streams = dash.get('audio', [])
        
        if not video_streams:
            raise Exception("未找到可用的视频流")
        if not audio_streams:
            raise Exception("未找到可用的音频流")
        
        # 打印所有视频流的详细信息，帮助诊断问题
        print("\n📺 所有可用视频流信息:")
        for i, stream in enumerate(video_streams):
            height = stream.get('height', '未知')
            width = stream.get('width', '未知')
            codecs = stream.get('codecs', '未知')
            stream_id = stream.get('id', '未知')
            mimeType = stream.get('mimeType', '未知')
            bitrate = stream.get('bitrate', 0)
            fps = stream.get('frameRate', '未知')
            print(f"[{i+1}] {width}x{height}P, {codecs}, ID={stream_id}, FPS={fps}, 比特率={bitrate//1000}kbps, MIME={mimeType}")
        
        # 定义扩展的编码优先级字典
        AVC_PRIORITY = {
            'avc1.640033': 100,  # 4K AVC编码，最高优先级
            'avc1.640032': 90,   # 高规格AVC编码
            'avc1.640031': 85,   # 高规格AVC编码
            'avc1.640028': 80,   # 1080P高规格AVC编码
            'avc1.640027': 75,   # 1080P AVC编码
            'avc1.64001F': 70,   # 720P/852P AVC编码
            'avc1.64001E': 60,   # 480P AVC编码
            'avc1.64001B': 50,   # 360P AVC编码
            'avc1.64000D': 40,   # 低规格AVC编码
        }
        
        # 定义其他编码的优先级
        OTHER_CODEC_PRIORITY = {
            'av01': 65,    # AV1编码（新一代高效编码）
            'hevc': 60,    # HEVC/H.265
            'vp9': 55,     # VP9编码
            'h264': 45,    # 通用H.264
        }
        
        # 高级视频流评分函数 - 优化版
        def video_stream_score(stream):
            score = 0
            
            # 获取编码信息
            codecs = stream.get('codecs', '').lower()
            
            # 1. 检查是否是特定AVC编码并分配优先级分数
            is_specific_avc = False
            for avc_codec, priority in AVC_PRIORITY.items():
                if avc_codec.lower() in codecs:
                    score += priority * 2000  # 大幅提高编码优先级权重
                    print(f"  🔍 发现高级AVC编码: {codecs}, 优先级: {priority}")
                    is_specific_avc = True
                    break
            
            # 2. 如果不是特定的AVC编码，但包含avc或h264关键字
            if not is_specific_avc and any(keyword in codecs for keyword in ['avc', 'h264', 'x264', 'h.264']):
                score += 50000  # 给普通AVC编码更高权重
                print(f"  🔍 发现普通AVC编码流: {codecs}")
            
            # 3. 检查其他编码类型
            for codec_type, priority in OTHER_CODEC_PRIORITY.items():
                if codec_type in codecs:
                    score += priority * 1000
                    print(f"  🔍 发现{codec_type.upper()}编码流: {codecs}, 优先级: {priority}")
                    break
            
            # 4. 分辨率权重 - 大幅提高分辨率权重
            height = stream.get('height', 0) or 0
            if height >= 2160:  # 4K
                score += 100000
                print(f"  🎯 发现4K分辨率: {height}P")
            elif height >= 1440:  # 2K
                score += 70000
            elif height >= 1080:  # 1080P
                score += 50000
            elif height >= 852:   # 852P
                score += 30000
            elif height >= 720:   # 720P
                score += 20000
            elif height >= 480:   # 480P
                score += 10000
            
            # 5. 比特率权重 - 提高比特率权重
            bitrate = stream.get('bitrate', 0) or 0
            score += bitrate / 50  # 增加权重
            
            # 6. 帧率权重 - 高帧率优先
            fps = stream.get('frameRate', 0)
            # 确保fps是数字类型
            try:
                fps_num = float(fps)
                if fps_num >= 60:
                    score += 10000  # 高帧率加分
                    print(f"  ⚡ 发现高帧率: {fps} FPS")
                elif fps_num >= 30:
                    score += 5000  # 标准高帧率加分
            except (ValueError, TypeError):
                fps_num = 0
            
            # 7. 特殊处理：4K AVC编码(avc1.640033)给予超高优先级
            if 'avc1.640033' in codecs and height >= 2160:
                score += 200000  # 为4K AVC编码提供绝对优先级
                print(f"  🚀 发现4K AVC编码(avc1.640033)，获得超高优先级")
            
            return score
        
        # 第一步：检查所有4K流，并按优先级排序
        # 1. 首先找出所有4K流（高度>=2160）
        all_4k_streams = [stream for stream in video_streams 
                         if stream.get('height', 0) >= 2160]
        
        if all_4k_streams:
            print(f"\n🔍 发现{len(all_4k_streams)}个4K流！")
            
            # 为4K流定义优先级评分函数
            def fourk_stream_score(stream):
                score = 0
                codecs = stream.get('codecs', '').lower()
                
                # 1. AVC编码优先级（最高）
                if 'avc' in codecs or 'h264' in codecs:
                    score += 100000
                    # 特定AVC编码加分
                    for avc_codec, priority in AVC_PRIORITY.items():
                        if avc_codec.lower() in codecs:
                            score += priority * 5000
                            break
                # 2. 其他编码
                elif 'av01' in codecs:  # AV1
                    score += 80000
                elif 'hevc' in codecs or 'h265' in codecs:  # HEVC
                    score += 70000
                elif 'vp9' in codecs:  # VP9
                    score += 60000
                
                # 3. 比特率因素
                bitrate = stream.get('bitrate', 0) or 0
                score += bitrate / 10
                
                # 4. 帧率因素
                fps = stream.get('frameRate', 0)
                try:
                    fps_num = float(fps)
                    score += fps_num * 200
                except (ValueError, TypeError):
                    pass
                
                return score
            
            # 对4K流进行排序
            all_4k_streams.sort(key=fourk_stream_score, reverse=True)
            
            # 输出所有4K流的详细信息
            print("📊 4K流详细分析:")
            for i, stream in enumerate(all_4k_streams):
                codecs = stream.get('codecs', '未知')
                width = stream.get('width', '未知')
                height = stream.get('height', '未知')
                bitrate = stream.get('bitrate', 0) or 0
                fps = stream.get('frameRate', '未知')
                score = fourk_stream_score(stream)
                
                # 编码类型分析
                codec_type = "未知"
                if 'avc' in codecs.lower() or 'h264' in codecs.lower():
                    codec_type = "AVC/H.264"
                elif 'av01' in codecs.lower():
                    codec_type = "AV1"
                elif 'hevc' in codecs.lower() or 'h265' in codecs.lower():
                    codec_type = "HEVC/H.265"
                elif 'vp9' in codecs.lower():
                    codec_type = "VP9"
                
                print(f"  [{i+1}] {codec_type} | {codecs} | {width}x{height}P | {bitrate//1000}kbps | {fps}FPS | 评分={score:.0f}")
            
            # 直接选择评分最高的4K流
            best_video = all_4k_streams[0]
            print(f"\n🏆 优先选择4K流！")
            print(f"   分辨率: {best_video.get('width', '未知')}x{best_video.get('height')}P")
            print(f"   编码: {best_video.get('codecs', '未知')}")
            print(f"   比特率: {best_video.get('bitrate', 0)//1000}kbps")
            print(f"   帧率: {best_video.get('frameRate', '未知')} FPS")
        else:
            # 对所有视频流进行评分和排序
            video_streams_sorted = sorted(video_streams, key=video_stream_score, reverse=True)
            
            # 获取评分最高的视频流
            best_video = video_streams_sorted[0]
            best_height = best_video.get('height', 0)
            
            # 第二步：找出所有相同高度的视频流，进行更精细的编码比较
            same_height_streams = [stream for stream in video_streams_sorted 
                                 if stream.get('height') == best_height]
            
            if len(same_height_streams) > 1:
                print(f"\n🔍 在{best_height}P高度下发现{len(same_height_streams)}个流，进行精细编码分析...")
                
                # 为相同高度的流定义更精确的评分函数，重点关注编码规格和质量
                def same_height_score(stream):
                    codecs = stream.get('codecs', '').lower()
                    score = 0
                    
                    # 1. 优先检查特定的AVC编码规格
                    for avc_codec, priority in AVC_PRIORITY.items():
                        if avc_codec.lower() in codecs:
                            score += priority * 3000  # 增加权重系数
                            break
                    
                    # 2. 如果是普通AVC编码
                    if score == 0 and any(keyword in codecs for keyword in ['avc', 'h264']):
                        score += 60000
                    
                    # 3. 检查其他编码类型
                    for codec_type, priority in OTHER_CODEC_PRIORITY.items():
                        if codec_type in codecs:
                            score += priority * 1500
                            break
                    
                    # 4. 检查编码特征
                    codec_features = 0
                    if 'high' in codecs:
                        codec_features += 10000
                    if 'main' in codecs:
                        codec_features += 5000
                    if 'high10' in codecs:
                        codec_features += 15000
                    if 'high444' in codecs:
                        codec_features += 20000
                    score += codec_features
                    
                    # 5. 比特率因素（在相同高度下更重要）
                    bitrate = stream.get('bitrate', 0) or 0
                    score += bitrate / 25
                    
                    # 6. 帧率因素
                    fps = stream.get('frameRate', 0)
                    # 确保fps是数字类型
                    try:
                        fps_num = float(fps)
                        score += fps_num * 100
                    except (ValueError, TypeError):
                        fps_num = 0
                       
                    return score
                
                # 对相同高度的流重新排序
                same_height_streams.sort(key=same_height_score, reverse=True)
                
                # 输出详细分析结果
                print("📊 相同高度流精细分析结果:")
                for i, stream in enumerate(same_height_streams):
                    codecs = stream.get('codecs', '未知')
                    bitrate = stream.get('bitrate', 0) or 0
                    fps = stream.get('frameRate', '未知')
                    score = same_height_score(stream)
                    
                    # 分析编码类型
                    codec_analysis = "未知"
                    if any(avc_codec.lower() in codecs.lower() for avc_codec in AVC_PRIORITY):
                        codec_analysis = "高级AVC编码"
                        for avc_codec in AVC_PRIORITY:
                            if avc_codec.lower() in codecs.lower():
                                codec_analysis = f"AVC {avc_codec}"
                                break
                    elif 'avc' in codecs.lower() or 'h264' in codecs.lower():
                        codec_analysis = "普通H.264编码"
                    elif 'av01' in codecs.lower():
                        codec_analysis = "AV1编码"
                    elif 'hevc' in codecs.lower() or 'h265' in codecs.lower():
                        codec_analysis = "HEVC/H.265编码"
                    elif 'vp9' in codecs.lower():
                        codec_analysis = "VP9编码"
                    
                    print(f"  [{i+1}] {codecs} | {codec_analysis} | {bitrate//1000}kbps | {fps}FPS | 精细评分={score:.0f}")
                
                # 选择评分最高的流
                best_video = same_height_streams[0]
                selected_codecs = best_video.get('codecs', '')
                
                # 详细判断选择的编码类型
                codec_type = "未知编码"
                if 'avc1.640033' in selected_codecs.lower():
                    codec_type = "4K AVC编码 (avc1.640033)"
                elif 'avc1.6400' in selected_codecs.lower():
                    codec_type = f"高规格AVC编码 ({selected_codecs})"
                elif 'avc' in selected_codecs.lower() or 'h264' in selected_codecs.lower():
                    codec_type = f"AVC/H.264编码 ({selected_codecs})"
                elif 'av01' in selected_codecs.lower():
                    codec_type = f"AV1编码 ({selected_codecs})"
                elif 'hevc' in selected_codecs.lower() or 'h265' in selected_codecs.lower():
                    codec_type = f"HEVC/H.265编码 ({selected_codecs})"
                elif 'vp9' in selected_codecs.lower():
                    codec_type = f"VP9编码 ({selected_codecs})"
                
                print(f"\n✅ 选择最佳流 - 高度: {best_height}P, 编码: {codec_type}")
        
        # 增强版音频流评分函数
        def audio_stream_score(stream):
            score = 0
            
            # 1. 比特率权重（增加重要性）
            bitrate = stream.get('bitrate', 0) or 0
            score += bitrate / 50
            
            # 2. 音频采样率
            sample_rate = stream.get('sampling_rate', 0) or 0
            if sample_rate >= 96000:
                score += 5000  # 超高采样率
                print(f"  🔊 发现超高采样率音频: {sample_rate}Hz")
            elif sample_rate >= 48000:
                score += 3000  # 高采样率
                print(f"  🔊 发现高采样率音频: {sample_rate}Hz")
            elif sample_rate >= 44100:
                score += 1000  # 标准采样率
            
            # 3. 检查音频编码质量（更详细的分级）
            codec = stream.get('codecs', '').lower()
            if 'flac' in codec:
                score += 10000  # FLAC无损音频最高优先级
                print(f"  🎵 发现FLAC无损音频")
            elif 'aac-lc' in codec or 'mp4a.40.2' in codec:
                score += 5000  # AAC-LC高品质
            elif 'aac' in codec:
                score += 3000  # 普通AAC
            elif 'opus' in codec:
                score += 4000  # Opus高质量编码
            elif 'vorbis' in codec:
                score += 2000  # Vorbis编码
            elif 'mp3' in codec:
                score += 1000  # MP3编码
            
            # 4. 声道数检查（如果有）
            channels = stream.get('channels', 0)
            if channels >= 6:
                score += 8000  # 5.1声道
                print(f"  🔊 发现多声道音频: {channels}声道")
            elif channels >= 2:
                score += 2000  # 立体声
            
            # 5. 如果指定了音频质量，优先该质量
            if prefer_audio_quality and str(stream.get('id')) == str(prefer_audio_quality):
                score += 50000  # 极高优先级
            
            return score
        
        # 打印所有音频流信息
        print("\n🔊 所有可用音频流信息:")
        for i, stream in enumerate(audio_streams):
            codecs = stream.get('codecs', '未知')
            bitrate = stream.get('bitrate', 0) or 0
            sample_rate = stream.get('sampling_rate', '未知')
            channels = stream.get('channels', '未知')
            audio_id = stream.get('id', '未知')
            print(f"[{i+1}] {codecs} | {bitrate//1000}kbps | {sample_rate}Hz | 声道数:{channels} | ID:{audio_id}")
        
        # 排序音频流
        audio_streams_sorted = sorted(audio_streams, key=audio_stream_score, reverse=True)
        best_audio = audio_streams_sorted[0]
        
        # 输出最终选择的媒体流详细信息
        print(f"\n🎉 最终选择的媒体流:")
        
        # 视频信息
        video_width = best_video.get('width', '未知')
        video_height = best_video.get('height', '未知')
        video_codecs = best_video.get('codecs', '未知')
        video_bitrate = best_video.get('bitrate', 0) or 0
        video_fps = best_video.get('frameRate', '未知')
        
        # 判断视频编码类型
        video_codec_type = "未知编码"
        if 'avc1.640033' in video_codecs.lower():
            video_codec_type = "4K AVC编码"
        elif 'avc1.6400' in video_codecs.lower():
            video_codec_type = "高规格AVC编码"
        elif 'avc' in video_codecs.lower() or 'h264' in video_codecs.lower():
            video_codec_type = "AVC/H.264编码"
        elif 'av01' in video_codecs.lower():
            video_codec_type = "AV1编码"
        elif 'hevc' in video_codecs.lower() or 'h265' in video_codecs.lower():
            video_codec_type = "HEVC/H.265编码"
        elif 'vp9' in video_codecs.lower():
            video_codec_type = "VP9编码"
        
        print(f"📹 视频:")
        print(f"  分辨率: {video_width}x{video_height}P")
        print(f"  编码: {video_codecs} ({video_codec_type})")
        print(f"  比特率: {video_bitrate//1000}kbps")
        print(f"  帧率: {video_fps} FPS")
        
        # 音频信息
        audio_codecs = best_audio.get('codecs', '未知')
        audio_bitrate = best_audio.get('bitrate', 0) or 0
        audio_sample_rate = best_audio.get('sampling_rate', '未知')
        audio_channels = best_audio.get('channels', '未知')
        
        # 判断音频质量
        audio_quality = "未知"
        if 'flac' in audio_codecs.lower():
            audio_quality = "无损品质"
        elif 'aac-lc' in audio_codecs.lower() or 'mp4a.40.2' in audio_codecs.lower():
            audio_quality = "高品质AAC"
        elif 'opus' in audio_codecs.lower():
            audio_quality = "高音质Opus"
        elif 'aac' in audio_codecs.lower():
            audio_quality = "标准AAC"
        elif 'mp3' in audio_codecs.lower():
            audio_quality = "MP3"
        
        print(f"🔊 音频:")
        print(f"  编码: {audio_codecs} ({audio_quality})")
        print(f"  比特率: {audio_bitrate//1000}kbps")
        print(f"  采样率: {audio_sample_rate}Hz")
        print(f"  声道数: {audio_channels}")
        
        print(f"\n📋 媒体流摘要:")
        print(f"  视频: {video_height}P {video_codec_type}, {video_bitrate//1000}kbps")
        print(f"  音频: {audio_quality}, {audio_bitrate//1000}kbps, {audio_sample_rate}Hz")
        
        return best_video, best_audio
    
    def download_file(self, url, save_path):
        """下载文件，支持断点续传
        
        Args:
            url: 文件下载链接
            save_path: 保存路径
            
        Returns:
            保存路径
        """
        # 检查文件是否已存在
        resume_size = 0
        if os.path.exists(save_path):
            resume_size = os.path.getsize(save_path)
            print(f"文件已存在，尝试断点续传 (已下载 {resume_size} 字节)")
        
        # 增强的请求头，添加B站下载必需的头信息
        headers = self.headers.copy()
        headers.update({
            'Referer': 'https://www.bilibili.com/',
            'Origin': 'https://www.bilibili.com',
            'Accept-Encoding': 'identity',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        })
        
        if resume_size > 0:
            headers['Range'] = f'bytes={resume_size}-'
        
        # 添加更多的错误处理和重试逻辑
        max_download_retries = 3
        for retry in range(max_download_retries):
            try:
                # 使用session保持会话一致性
                response = self.session.get(url, headers=headers, stream=True, timeout=60)
                response.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                if response.status_code == 403 and retry < max_download_retries - 1:
                    print(f"403错误，{retry + 1} 秒后重试...")
                    time.sleep(retry + 1)
                    # 尝试更新Cookie或刷新会话
                    self._refresh_session()
                else:
                    raise e
            except Exception as e:
                if retry < max_download_retries - 1:
                    print(f"下载异常: {str(e)}, {retry + 1} 秒后重试...")
                    time.sleep(retry + 1)
                else:
                    raise e
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0)) + resume_size
        
        # 写入文件
        mode = 'ab' if resume_size > 0 else 'wb'
        with open(save_path, mode) as f:
            with tqdm(total=total_size, initial=resume_size, unit='B', unit_scale=True, desc=os.path.basename(save_path)) as pbar:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        pbar.update(len(chunk))
        
        return save_path
    
    def _refresh_session(self):
        """刷新会话，尝试更新Cookie和请求头"""
        # 重新设置请求头
        self.session.headers.update(self.headers)
        # 可以在这里添加更多的会话刷新逻辑
        pass
    
    def _check_ffmpeg(self):
        """检查ffmpeg是否可用
        
        Returns:
            bool: ffmpeg是否可用
        """
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def merge_video_audio(self, video_path, audio_path, output_path, force_avc=False):
        """合并视频和音频
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            force_avc: 是否强制将视频编码为AVC格式
            
        Returns:
            输出文件路径
        """
        if not self._check_ffmpeg():
            raise Exception("ffmpeg未安装或未添加到系统PATH中")
        
        print(f"\n正在合并视频和音频{'并强制转换为AVC格式' if force_avc else '...'}")
        
        # 根据是否需要强制AVC编码设置视频编码参数
        if force_avc:
            # 强制使用H.264/AVC编码
            video_codec = 'libx264'
            print("使用H.264编码器将视频转换为AVC格式")
            # 为H.264编码添加优化参数
            # crf参数控制质量(0-51，0为无损，23为默认，数值越小质量越好)
            # preset参数控制编码速度(slow, medium, fast等，越慢质量越好体积越小)
            avc_params = ['-crf', '23', '-preset', 'medium']
        else:
            # 复制视频流，不重新编码
            video_codec = 'copy'
            avc_params = []
        
        command = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', video_codec  # 使用指定的视频编码器
        ]
        
        # 添加AVC编码参数(如果需要)
        if avc_params:
            command.extend(avc_params)
        
        command.extend([
            '-c:a', 'aac',   # 音频编码为AAC以保证兼容性
            '-y',            # 覆盖已存在的文件
            output_path
        ])
        
        try:
            # 以二进制模式运行ffmpeg，避免编码问题
            process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            if process.returncode != 0:
                # 尝试以UTF-8解码错误输出，如果失败则以原始字节显示
                try:
                    error_msg = process.stderr.decode('utf-8', errors='replace')
                except:
                    error_msg = str(process.stderr)
                raise Exception(f"ffmpeg合并失败: {error_msg}")
            
            print("合并完成！")
            return output_path
        except subprocess.TimeoutExpired:
            raise Exception("ffmpeg合并超时")
        finally:
            # 清理临时文件
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except:
                pass
    
    def clean_filename(self, filename):
        """清理文件名中的非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # Windows非法字符
        illegal_chars = '<>"/\|?*:'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        # 移除控制字符
        filename = ''.join(char for char in filename if ord(char) >= 32)
        # 限制长度
        if len(filename) > 200:
            filename = filename[:197] + '...'
        return filename
    
    def download_video(self, bvid, output_dir='./downloads', quality=None, audio_quality=None, format='mp4'):
        """下载单个视频
        
        Args:
            bvid: 视频BV号
            output_dir: 输出目录
            quality: 指定视频质量代码
            audio_quality: 指定音频质量代码
            format: 输出格式 (mp4/mkv/flv)
            
        Returns:
            下载后的文件路径
        """
        start_time = time.time()
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 检查ffmpeg
        if not self._check_ffmpeg():
            print("警告: ffmpeg未安装或未添加到系统PATH中，将无法合并视频和音频")
        
        try:
            # 1. 获取视频信息
            print(f"\n获取视频信息: {bvid}")
            video_info = self.get_video_info(bvid)
            
            # 获取视频标题、cid和发布日期
            title = self.clean_filename(video_info.get('title', f'视频_{bvid}'))
            cid = video_info.get('cid', 0)
            
            # 获取发布日期，API返回的是发布时间戳
            publish_date = video_info.get('pubdate', 0)
            # 将时间戳转换为日期格式 YYYY-MM-DD
            import datetime
            if publish_date > 0:
                publish_date_str = datetime.datetime.fromtimestamp(publish_date).strftime('%Y-%m-%d')
            else:
                publish_date_str = '日期未知'
                
            print(f"视频标题: {title}")
            print(f"视频CID: {cid}")
            print(f"发布日期: {publish_date_str}")
            
            # 2. 获取视频流
            print("获取视频流信息...")
            streams = self.get_video_streams(bvid, cid)
            
            # 3. 选择最佳媒体流
            best_video, best_audio = self.select_best_stream(streams, quality, audio_quality)
            
            # 移除强制转换格式的检测逻辑
            
            # 4. 下载视频和音频
            video_url = best_video.get('base_url')
            audio_url = best_audio.get('base_url')
            
            # 生成临时文件名
            temp_video = os.path.join(output_dir, f"{bvid}_video_temp.m4s")
            temp_audio = os.path.join(output_dir, f"{bvid}_audio_temp.m4s")
            
            # 下载视频
            print(f"\n下载视频...")
            self.download_file(video_url, temp_video)
            
            # 下载音频
            print(f"\n下载音频...")
            self.download_file(audio_url, temp_audio)
            
            # 5. 合并视频和音频 - 格式化为 "上传日期 - 原来的视频名"
            output_filename = f"{publish_date_str} - {title}.{format}"
            output_path = os.path.join(output_dir, output_filename)
            
            if self._check_ffmpeg():
                # 不再强制转换视频格式，始终保留原始编码
                output_path = self.merge_video_audio(temp_video, temp_audio, output_path, force_avc=False)
            else:
                # 如果没有ffmpeg，只保留视频文件
                print("无法合并音视频，仅保留视频文件")
                output_path = os.path.join(output_dir, f"{publish_date_str} - {title}_video_only.mp4")
                os.rename(temp_video, output_path)
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
            
            # 6. 计算下载时间
            end_time = time.time()
            duration = end_time - start_time
            print(f"\n视频下载完成！")
            print(f"总耗时: {duration:.2f} 秒")
            print(f"保存路径: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"\n下载失败: {str(e)}")
            # 清理临时文件
            for temp_file in [
                os.path.join(output_dir, f"{bvid}_video_temp.m4s"),
                os.path.join(output_dir, f"{bvid}_audio_temp.m4s")
            ]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            return None

if __name__ == "__main__":
    # 简单的命令行接口
    import argparse
    
    parser = argparse.ArgumentParser(description='B站视频下载器')
    parser.add_argument('--bvid', type=str, required=True, help='视频BV号')
    parser.add_argument('--cookie', type=str, default=None, help='Cookie文件路径')
    parser.add_argument('--output', type=str, default='./downloads', help='输出目录')
    parser.add_argument('--proxy', type=str, default=None, help='代理设置')
    
    args = parser.parse_args()
    
    downloader = BilibiliDownloader(cookie_path=args.cookie, proxy=args.proxy)
    downloader.download_video(args.bvid, output_dir=args.output)