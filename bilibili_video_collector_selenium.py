import os
import json
import time
import random
import socket
import re
import requests
from selenium import webdriver
from bilibili_downloader import BilibiliDownloader
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

class BilibiliVideoCollectorSelenium:
    """B站视频列表收集类（Selenium版本），用于通过浏览器模拟获取UP主视频列表"""
    
    def __init__(self, cookie_path=None, proxy=None):
        """初始化视频收集器
        
        Args:
            cookie_path: Cookie文件路径
            proxy: 代理设置，如 http://127.0.0.1:7890
        """
        # 保存cookie路径和proxy，供下载器使用
        self.cookie_path = cookie_path
        self.proxy = proxy
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
    
    def get_videos_by_selenium(self, uid, max_videos=None, headless=True):
        """使用Selenium模拟用户浏览获取UP主视频列表
        
        Args:
            uid: UP主UID
            max_videos: 最大获取视频数量，None表示获取全部
            headless: 是否使用无头模式
            
        Returns:
            tuple: (BV号列表, 从页面获取的UP主信息)
        """
        # 初始化bvid_list为空列表，确保在异常情况下也不会引用未定义变量
        bvid_list = []
        page_up_info = {}  # 用于存储从页面获取的UP主信息
        
        print(f"开始使用Selenium获取UP主 {uid} 的视频BV号...")
        
        # 先做简单的UID验证
        if not isinstance(uid, (int, str)) or (isinstance(uid, str) and not uid.isdigit()):
            print(f"错误: 无效的UID格式 - {uid}")
            return []
        
        uid = str(uid)
        driver = None
        
        try:
            # 配置Chrome选项
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless')
            
            # 解决SessionNotCreatedException错误的关键参数
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--remote-debugging-port=9222')  # 解决DevToolsActivePort问题
            chrome_options.add_argument('--user-data-dir=' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chrome_profile'))  # 指定用户数据目录
            chrome_options.add_argument('--disable-features=site-per-process')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # 添加网络相关配置
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--allow-insecure-localhost')
            
            # 确保用户数据目录存在
            user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chrome_profile')
            if not os.path.exists(user_data_dir):
                os.makedirs(user_data_dir)
            
            # 尝试使用项目中的cookies目录作为用户数据目录（如果存在）
            uid_cookies_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies', uid)
            if os.path.exists(uid_cookies_dir):
                print(f"找到UP主 {uid} 的已有用户数据目录，使用它来避免登录")
                chrome_options.add_argument('--user-data-dir=' + uid_cookies_dir)
            else:
                # 使用通用的用户数据目录
                print("使用通用的用户数据目录")
                chrome_options.add_argument('--user-data-dir=' + user_data_dir)
            
            # 尝试多种方式初始化Chrome驱动
            print("初始化浏览器...")
            
            # 方法1：尝试直接使用系统已有的Chrome驱动（如果存在）
            system_driver_paths = [
                'C:\\Program Files\\Google\\Chrome\\Application\\chromedriver.exe',
                'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chromedriver.exe',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chromedriver.exe'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'chromedriver.exe')  # 添加tools目录下的驱动路径
            ]
            
            driver_path = None
            for path in system_driver_paths:
                if os.path.exists(path):
                    driver_path = path
                    print(f"找到系统已安装的Chrome驱动: {driver_path}")
                    break
            
            if driver_path:
                # 使用找到的驱动路径
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # 方法2：尝试使用webdriver-manager，但添加代理支持
                print("未找到系统驱动，尝试使用webdriver-manager自动下载...")
                try:
                    # 配置代理（如果需要）
                    # 注意：这里可以根据需要修改代理设置
                    os.environ['WDM_PROXY'] = 'http://127.0.0.1:7890'  # 示例代理，根据实际情况修改
                    os.environ['WDM_LOCAL'] = '1'  # 优先使用本地缓存
                    
                    # 尝试获取Chrome驱动
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                except Exception as wdm_error:
                    print(f"webdriver-manager下载失败: {str(wdm_error)}")
                    print("\n请手动下载Chrome驱动并放在项目根目录或Chrome安装目录下")
                    print("Chrome驱动下载地址: https://chromedriver.chromium.org/downloads")
                    print("请确保下载的驱动版本与已安装的Chrome浏览器版本匹配")
                    return bvid_list, page_up_info, page_up_info
            
            # 增加等待时间以确保页面完全加载
            wait = WebDriverWait(driver, 20)  # 增加到20秒
            
            # 访问UP主空间页面
            space_url = f"https://space.bilibili.com/{uid}/video"
            print(f"正在访问: {space_url}")
            driver.get(space_url)
            
            # 增加初始等待时间
            time.sleep(3)
            
            # 尝试处理可能的验证码或登录提示
            print("检查页面状态...")
            page_source = driver.page_source
            # 使用更精确的条件检测是否需要登录
            if ('登录' in page_source and '登录按钮' in page_source) or ('验证码' in page_source and '请输入验证码' in page_source):
                    print("检测到可能需要登录或验证码")
                    if self.cookies:
                        print("尝试添加Cookie...")
                        # 清除现有的Cookie
                        driver.delete_all_cookies()
                        # 添加Cookie
                        try:
                            print(f"尝试添加Cookie，数据类型: {type(self.cookies).__name__}")
                            if isinstance(self.cookies, dict):
                                for name, value in self.cookies.items():
                                    cookie_dict = {
                                        'name': name,
                                        'value': value,
                                        'domain': '.bilibili.com',
                                        'path': '/',
                                        'secure': True,
                                        'httpOnly': True
                                    }
                                    try:
                                        driver.add_cookie(cookie_dict)
                                    except Exception as cookie_error:
                                        print(f"添加Cookie {name} 时出错: {str(cookie_error)}")
                            elif isinstance(self.cookies, list):
                                for cookie in self.cookies:
                                    try:
                                        driver.add_cookie(cookie)
                                    except Exception as cookie_error:
                                        print(f"添加Cookie时出错: {str(cookie_error)}")
                            print("Cookie添加完成，刷新页面...")
                            # 刷新页面
                            driver.refresh()
                            time.sleep(3)
                            # 重新检查页面状态
                            new_page_source = driver.page_source
                            if ('登录' in new_page_source and '登录按钮' in new_page_source) and not headless:
                                print("30秒后继续，您可以在此期间手动登录...")
                                time.sleep(30)
                                print(f"重新访问UP主空间页面: {space_url}")
                                driver.get(space_url)
                                time.sleep(2)
                            else:
                                print("似乎已登录或无需登录，继续处理...")
                        except Exception as e:
                            print(f"处理Cookie时出错: {str(e)}")
                    elif not headless:
                        print("请手动登录B站...")
                        print("30秒后继续处理...")
                        time.sleep(30)
                        print(f"重新访问UP主空间页面: {space_url}")
                        driver.get(space_url)
                        time.sleep(2)
                    else:
                        print("在无头模式下无法手动登录，请提供有效的Cookie文件")
            
            try:
                # 使用更通用的选择器等待视频列表
                print("等待视频列表加载...")
                # 等待页面主体内容加载
                wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                print("页面主体内容加载成功")
                
                # 等待更长时间确保动态内容加载完成
                print("等待动态内容加载...")
                time.sleep(5)
                
                # 打印页面信息进行调试
                print(f"当前页面URL: {driver.current_url}")
                print(f"页面标题: {driver.title}")
                print("页面内容中是否包含'视频'字样: {'视频' in driver.page_source}")
                
                # 尝试从页面获取UP主名字和信息
                try:
                    print("尝试从页面获取UP主信息...")
                    
                    # 1. 首先检查页面标题是否包含UP主名字
                    if ' - 哔哩哔哩' in driver.title:
                        title_name = driver.title.split(' - 哔哩哔哩')[0].strip()
                        if title_name and len(title_name) > 1 and not title_name.startswith('加载中') and not title_name.startswith('B站'):
                            page_up_info['name'] = title_name
                            print(f"从页面标题获取到UP主名字: {title_name}")
                    
                    # 2. 如果标题中没找到，尝试使用更多选择器
                    if not page_up_info.get('name'):
                        # 扩展的选择器列表，覆盖B站UP主空间的各种可能结构
                        name_selectors = [
                            # 主要选择器
                            (By.CSS_SELECTOR, '.user-info h1'),
                            (By.CSS_SELECTOR, '.up-info__name'),
                            (By.CSS_SELECTOR, '.up-name'),
                            (By.CSS_SELECTOR, '.name'),
                            
                            # 备用选择器
                            (By.CSS_SELECTOR, '.user-name'),
                            (By.CSS_SELECTOR, '.username'),
                            (By.CSS_SELECTOR, '.header-info h1'),
                            (By.CSS_SELECTOR, '.header-info .name'),
                            (By.CSS_SELECTOR, '.user-header .name'),
                            
                            # 更通用的选择器
                            (By.XPATH, '//h1[contains(@class, "name")]'),
                            (By.XPATH, '//*[contains(@class, "user") and contains(@class, "name")]'),
                            (By.XPATH, '//*[contains(@class, "up") and contains(@class, "name")]'),
                            (By.XPATH, '//*[contains(text(), "的空间")]/preceding-sibling::*'),
                            (By.XPATH, '//div[contains(@class, "user-info")]//*[contains(@class, "name")]'),
                            (By.XPATH, '//div[contains(@class, "up-info")]//*[contains(@class, "name")]'),
                            
                            # 从meta标签获取
                            (By.XPATH, '//meta[@name="description"]')
                        ]
                        
                        # 尝试所有选择器
                        for selector_type, selector in name_selectors:
                            try:
                                elements = driver.find_elements(selector_type, selector)
                                for element in elements:
                                    # 对于meta标签特殊处理
                                    if selector.endswith("meta[@name='description']"):
                                        content = element.get_attribute('content')
                                        if content and len(content) > 10:
                                            # 尝试从描述中提取UP主名字
                                            import re
                                            name_match = re.search(r'UP主：([^，,]+)', content)
                                            if name_match:
                                                up_name = name_match.group(1).strip()
                                                if up_name and len(up_name) > 1:
                                                    page_up_info['name'] = up_name
                                                    print(f"从meta标签获取到UP主名字: {up_name}")
                                                    break
                                    else:
                                        # 常规元素处理
                                        up_name = element.text.strip()
                                        if not up_name:
                                            up_name = element.get_attribute('title').strip()
                                        if not up_name:
                                            up_name = element.get_attribute('alt').strip()
                                        
                                        if up_name and not up_name.startswith('加载中') and not up_name.startswith('B站') and len(up_name) > 1:
                                            # 过滤掉不是UP主名字的内容
                                            if '的空间' not in up_name and '视频' not in up_name and '动态' not in up_name and '关注' not in up_name:
                                                page_up_info['name'] = up_name
                                                print(f"从页面元素获取到UP主名字: {up_name}")
                                                break
                                if page_up_info.get('name'):
                                    break
                            except Exception as selector_error:
                                print(f"尝试选择器 {selector} 时出错: {str(selector_error)}")
                    
                    # 3. 尝试从页面HTML中直接搜索
                    if not page_up_info.get('name'):
                        print("尝试从HTML中直接搜索UP主名字...")
                        page_html = driver.page_source
                        
                        # 尝试匹配页面中可能的UP主名字格式
                        import re
                        # 匹配"UP主：名字"或类似格式
                        name_patterns = [
                            r'UP主[:：]([^<\s,，]+)',
                            r'<title>[^-\s]+([^-\s]+)[-\s]+哔哩哔哩',
                            r'class=["\'].*?name.*?["\'].*?>([^<]+)<',
                            r'<h1[^>]*>([^<]+)<\/h1>'
                        ]
                        
                        for pattern in name_patterns:
                            matches = re.findall(pattern, page_html)
                            for match in matches:
                                if match and len(match) > 1 and not match.startswith('加载中') and not match.startswith('B站'):
                                    # 过滤掉明显不是名字的内容
                                    if '的空间' not in match and '视频' not in match and '动态' not in match and '关注' not in match and len(match) < 50:
                                        page_up_info['name'] = match.strip()
                                        print(f"从HTML中直接匹配到UP主名字: {page_up_info['name']}")
                                        break
                            if page_up_info.get('name'):
                                break
                    
                    # 4. 尝试从关注按钮获取
                    if not page_up_info.get('name'):
                        try:
                            # 查找关注按钮，通常旁边会有UP主名字
                            follow_buttons = driver.find_elements(By.XPATH, '//*[contains(text(), "关注") or contains(text(), "已关注")]')
                            for button in follow_buttons:
                                try:
                                    # 查找按钮附近的文本
                                    parent = button.find_element(By.XPATH, './..')
                                    siblings = parent.find_elements(By.XPATH, './*')
                                    for sibling in siblings:
                                        text = sibling.text.strip()
                                        if text and len(text) > 1 and not text.startswith('加载中') and not text.startswith('B站') and '关注' not in text:
                                            page_up_info['name'] = text
                                            print(f"从关注按钮附近获取到UP主名字: {text}")
                                            break
                                    if page_up_info.get('name'):
                                        break
                                except:
                                    pass
                        except:
                            pass
                    
                    # 尝试获取个性签名
                    try:
                        sign_element = driver.find_element(By.CSS_SELECTOR, '.sign')
                        sign_text = sign_element.text.strip()
                        if sign_text:
                            page_up_info['sign'] = sign_text
                            print(f"获取到个性签名: {sign_text}")
                    except:
                        try:
                            # 尝试其他可能的签名选择器
                            sign_selectors = ['.user-desc', '.up-desc', '.description', '.intro']
                            for sel in sign_selectors:
                                try:
                                    sign_element = driver.find_element(By.CSS_SELECTOR, sel)
                                    sign_text = sign_element.text.strip()
                                    if sign_text:
                                        page_up_info['sign'] = sign_text
                                        print(f"获取到个性签名: {sign_text}")
                                        break
                                except:
                                    pass
                        except:
                            pass
                    
                    # 打印最终从页面获取的UP主信息
                    if page_up_info:
                        print(f"从页面成功获取UP主信息: {page_up_info}")
                    else:
                        print("未能从页面获取到UP主信息")
                        
                except Exception as e:
                    print(f"从页面获取UP主信息时发生错误: {str(e)}")
                    import traceback
                    traceback.print_exc()
                
                # 打印页面部分HTML用于调试
                try:
                    # 获取body的outerHTML的前5000个字符
                    body_html = driver.find_element(By.TAG_NAME, 'body').get_attribute('outerHTML')[:5000]
                    print("\n页面HTML结构预览（前5000字符）:")
                    print(body_html)
                    
                    # 查找包含BV号的部分
                    bv_matches = re.findall(r'BV[0-9A-Za-z]{10}', body_html)
                    if bv_matches:
                        print(f"\n在页面HTML中找到的BV号预览: {bv_matches[:5]}")
                    else:
                        print("\n在页面HTML预览中未找到BV号")
                except Exception as e:
                    print(f"打印HTML时出错: {str(e)}")
            except TimeoutException:
                print("页面加载超时，但继续尝试获取视频")
            
            # 增强滚动加载逻辑
            print("开始滚动加载视频列表...")
            # 初始滚动高度
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            max_scrolls = 10  # 减少滚动次数，因为我们主要依赖选择器
            no_change_count = 0
            
            # 尝试多种滚动方式
            scroll_methods = [
                "window.scrollTo(0, document.body.scrollHeight);",
                "window.scrollTo(0, document.documentElement.scrollHeight);",
                "window.scrollBy(0, window.innerHeight * 0.8);"
            ]
            method_index = 0
            
            while scroll_count < max_scrolls and no_change_count < 3:
                # 循环使用不同的滚动方法
                scroll_script = scroll_methods[method_index % len(scroll_methods)]
                driver.execute_script(scroll_script)
                
                # 增加等待时间
                time.sleep(4)  # 增加等待时间确保内容加载
                
                # 计算新的滚动高度
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                # 如果滚动高度没有变化，增加计数
                if new_height == last_height:
                    no_change_count += 1
                    print(f"滚动高度未变化，计数: {no_change_count}")
                else:
                    no_change_count = 0
                    last_height = new_height
                
                scroll_count += 1
                print(f"已滚动 {scroll_count} 次")
                
                # 提取视频BV号 - 使用多种选择器确保找到视频
                # 方法1: 使用多种CSS选择器组合定位UP主视频
                # 尝试B站常见的视频列表容器选择器
                # 尝试从页面中提取视频链接
                # 使用多种CSS选择器组合，提高匹配成功率
                selectors = [
                    # B站视频列表常见选择器
                    '.col-full a[href^="//www.bilibili.com/video/"]',  # 主页视频链接
                    '.col-full a[href^="/video/"]',                   # 相对路径视频链接
                    '#submit-video-list .video-item',                  # 常见的视频列表布局
                    '.video-list .video-item',                         # 通用视频列表
                    '.video-item',                                     # 直接匹配视频项
                    '.contents-item',                                  # 另一种可能的视频项类名
                    '.video-card',                                     # 卡片式布局
                    '.video-a',                                        # 视频链接类
                    '.small-item',                                     # 小视频项
                    '.list-item',                                      # 列表项
                    'a[href*="/video/"]',                             # 包含/video/的链接
                    '.video-container .video-cover',                   # 视频封面
                    '.i-1-4 .video-item',                              # 4列布局
                    '.i-1-5 .video-item',                              # 5列布局
                    '.article-item',                                   # 文章项（可能包含视频）
                    '.card-box .video-item',                           # 卡片盒内的视频项
                    '.columns .video-item',                            # 列布局中的视频项
                    '.video-list-item'                                 # 视频列表项
                ]
                
                # 尝试所有选择器，收集所有匹配的BV号
                collected_bvids = set()
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        print(f"通过选择器 {selector} 找到 {len(elements)} 个元素")
                        
                        # 处理找到的元素
                        for element in elements:
                            # 尝试从href属性获取BV号
                            href = element.get_attribute('href')
                            if href:
                                # 使用正则表达式提取BV号
                                bv_match = re.search(r'(BV[0-9A-Za-z]{10})', href)
                                if bv_match:
                                    bv = bv_match.group(1)
                                    collected_bvids.add(bv)
                                    print(f"从href找到BV号: {bv}")
                            
                            # 尝试从innerHTML获取BV号
                            try:
                                inner_html = element.get_attribute('innerHTML')
                                if inner_html:
                                    bv_matches = re.findall(r'(BV[0-9A-Za-z]{10})', inner_html)
                                    for bv in bv_matches:
                                        collected_bvids.add(bv)
                                        print(f"从innerHTML找到BV号: {bv}")
                            except Exception:
                                pass
                    except Exception as e:
                        print(f"应用选择器 {selector} 时出错: {str(e)}")
                
                # 更新主BV号列表
                bvid_list = list(collected_bvids)
                print(f"当前已收集到 {len(bvid_list)} 个唯一BV号")
                
                # 如果已达到最大视频数量，提前结束
                if max_videos and len(bvid_list) >= max_videos:
                    print(f"已达到最大视频数量 {max_videos}，提前结束滚动")
                    break
            
            # 翻页处理 - 循环翻页获取更多视频
            current_page_url = driver.current_url
            page_count = 0
            max_pages = 10  # 设置最大翻页次数，避免无限循环
            page_history = set([current_page_url])  # 用于检测重复页面
            
            # 扩展的下一页按钮选择器列表
            next_page_selectors = [
                # B站特有分页器
                '.be-pager-next',                     # UP主空间专用分页器
                '.pagination .next-page',             # 通用分页类名
                
                # 图标/样式检测
                '.next-btn',                           # 下一页按钮
                '.next-page-btn',                      # 下一页按钮
                
                # URL参数检测
                'a[href*="pn="]',                    # 包含pn参数的链接
                
                # B站自定义选择器
                '.nav-item.nav-item-next',            # 导航项-下一页
                '.page-item.page-item-next',          # 页面项-下一页
                '.bilibili-pagelist-next',            # B站专用分页下一页
                '.pagelist-item.next',                # 分页列表项-下一页
                '.paginator .next',                   # 分页器-下一页
                '.pagination-item.pagination-next'    # 分页项-下一页
            ]
            
            print("\n开始翻页处理...")
            
            while page_count < max_pages:
                page_count += 1
                print(f"\n[翻页 {page_count}/{max_pages}]")
                next_button_found = False
                
                # 第一阶段：尝试使用CSS选择器直接找到下一页按钮
                for selector in next_page_selectors:
                    try:
                        # 查找所有匹配的元素
                        next_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        # 筛选可见且有效（可点击）的按钮
                        for next_button in next_buttons:
                            if next_button.is_displayed():
                                # 检查按钮是否包含"下一页"相关文本
                                button_text = next_button.text.strip().lower()
                                button_aria_label = next_button.get_attribute('aria-label') or ''
                                button_title = next_button.get_attribute('title') or ''
                                
                                if any(keyword in button_text or keyword in button_aria_label.lower() or keyword in button_title.lower() 
                                       for keyword in ['下一页', 'next', '>' '→', '›']):
                                    print(f"找到下一页按钮: {selector}")
                                    next_button_found = True
                                    
                                    # 尝试点击下一页按钮
                                    try:
                                        # 尝试直接点击
                                        print("尝试直接点击下一页按钮...")
                                        next_button.click()
                                        # 等待页面加载
                                        print("等待页面加载...")
                                        time.sleep(5)
                                    except Exception as click_error:
                                        print(f"直接点击失败: {str(click_error)}")
                                        # 如果直接点击失败，尝试使用JavaScript点击
                                        print("尝试使用JavaScript点击...")
                                        driver.execute_script("arguments[0].click();", next_button)
                                        # 等待页面加载
                                        print("等待页面加载...")
                                        time.sleep(5)
                                    
                                    # 检查URL是否变化
                                    if driver.current_url != current_page_url and driver.current_url not in page_history:
                                        current_page_url = driver.current_url
                                        page_history.add(current_page_url)
                                        print(f"翻页成功，新页面URL: {current_page_url}")
                                        
                                        # 重新滚动加载新页面的视频
                                        print("在新页面上滚动加载...")
                                        driver.execute_script("window.scrollTo(0, 0);")
                                        time.sleep(1)
                                        last_height = driver.execute_script("return document.body.scrollHeight")
                                        no_change_count = 0
                                        
                                        for scroll_step in range(5):  # 新页面滚动5次
                                            # 随机选择滚动方式
                                            scroll_script = scroll_methods[random.randint(0, len(scroll_methods) - 1)]
                                            driver.execute_script(scroll_script)
                                            time.sleep(3)
                                            
                                            new_height = driver.execute_script("return document.body.scrollHeight")
                                            if new_height == last_height:
                                                no_change_count += 1
                                            else:
                                                no_change_count = 0
                                                last_height = new_height
                                            
                                            if no_change_count >= 2:
                                                break
                                        
                                        # 重新提取视频BV号
                                        print("在新页面上提取视频BV号...")
                                        for selector in selectors:
                                            try:
                                                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                                for element in elements:
                                                    href = element.get_attribute('href')
                                                    if href:
                                                        bv_match = re.search(r'(BV[0-9A-Za-z]{10})', href)
                                                        if bv_match:
                                                            bv = bv_match.group(1)
                                                            collected_bvids.add(bv)
                                            except Exception:
                                                pass
                                        
                                        # 更新主BV号列表
                                        bvid_list = list(collected_bvids)
                                        print(f"翻页后共收集到 {len(bvid_list)} 个唯一BV号")
                                        
                                        # 如果已达到最大视频数量，提前结束
                                        if max_videos and len(bvid_list) >= max_videos:
                                            print(f"已达到最大视频数量 {max_videos}，提前结束翻页")
                                            break
                                    else:
                                        print("翻页失败，URL没有变化或已访问过该页面")
                                
                                break  # 找到有效按钮后退出循环
                        
                        if next_button_found:
                            break  # 找到按钮后退出选择器循环
                    except Exception as e:
                        print(f"使用选择器 {selector} 时出错: {str(e)}")
                
                # 如果第一阶段没有找到下一页按钮，尝试第二阶段：查找所有可见的链接和按钮
                if not next_button_found:
                    print("未通过CSS选择器找到下一页按钮，尝试查找所有可见链接和按钮...")
                    try:
                        # 获取所有可见的a标签和button标签
                        all_links = driver.find_elements(By.CSS_SELECTOR, 'a, button')
                        visible_elements = [el for el in all_links if el.is_displayed()]
                        
                        # 筛选包含"下一页"相关文本的元素 - 更严格的匹配
                        next_page_keywords = ['下一页', 'next page', '>', '→', '›', '后页', 'page']
                        # 排除非下一页按钮的关键词 - 增加更多排除项
                        exclude_keywords = [
                            '首页', 'home', 'index', '返回首页', '首页推荐',
                            '直播', 'live', '直播间', 'live room',
                            '番剧', 'anime', '动画', '番组',
                            '电影', 'movie', '影院', 'cinema',
                            '游戏', 'game', 'game center',
                            '会员购', 'vip', 'mall', 'shop',
                            '漫画', 'comic', 'manga',
                            '音乐', 'music', 'audio',
                            '相簿', 'album', 'photo',
                            '专栏', 'article', 'column',
                            '动态', 'activity', 'feed',
                            '排行榜', 'rank', 'ranking',
                            '搜索', 'search', '查找',
                            '消息', 'message', '通知', 'notification',
                            '设置', 'setting', '配置',
                            '关于', 'about', 'help', '帮助',
                            '历史', 'history', 'record',
                            '收藏', 'collect', 'favorite',
                            '点赞', 'like', 'upvote',
                            '分享', 'share', '转发'
                        ]
                        
                        for element in visible_elements:
                            try:
                                text = element.text.strip().lower()
                                aria_label = element.get_attribute('aria-label') or ''
                                title = element.get_attribute('title') or ''
                                inner_html = element.get_attribute('innerHTML') or ''
                                href = element.get_attribute('href') or ''
                                
                                # 检查是否包含排除关键词，跳过首页等按钮
                                if any(exclude_keyword.lower() in text or exclude_keyword.lower() in aria_label.lower() or 
                                       exclude_keyword.lower() in title.lower() or exclude_keyword.lower() in inner_html.lower()
                                       for exclude_keyword in exclude_keywords):
                                    print(f"跳过可能的首页按钮，文本: '{text}'，href: {href}")
                                    continue
                                
                                # 更严格的下一页关键词检查，避免误识别
                                has_next_keyword = False
                                for keyword in next_page_keywords:
                                    # 对于数字符号，要求是独立的或在页码前后
                                    if keyword in ['>', '→', '›']:
                                        if (keyword in text and (len(text) <= 3 or text.strip().isdigit())) or (keyword in aria_label and (len(aria_label) <= 3 or aria_label.strip().isdigit())) or (keyword in title and (len(title) <= 3 or title.strip().isdigit())):
                                            has_next_keyword = True
                                            break
                                    # 对于文字关键词，要求是完整或主要部分
                                    elif keyword == 'page' and (text.strip() == keyword or aria_label.lower().strip() == keyword or title.lower().strip() == keyword):
                                        has_next_keyword = True
                                        break
                                    # 对于"下一页"等中文关键词
                                    elif keyword in text or keyword in aria_label or keyword in title or keyword in inner_html:
                                        has_next_keyword = True
                                        break
                                
                                if has_next_keyword:
                                    # 确保href包含有效的URL（不是javascript:void(0)等）
                                    if href and 'javascript:void(0)' not in href and href != '':
                                        # 额外检查href是否为UP主空间页面的翻页链接
                                        if 'space.bilibili.com' not in href:
                                            # 进一步检查是否包含页码参数
                                            has_page_param = any(p in href.lower() for p in ['?pn=', '&pn=', '?page=', '&page='])
                                            if not has_page_param:
                                                print(f"跳过非UP主空间链接且不含页码参数: {href}")
                                                continue
                                        
                                        # 跳过已知的非翻页域名
                                        skip_domains = ['live.bilibili.com', 'anime.bilibili.com', 'mall.bilibili.com', 'game.bilibili.com']
                                        if any(domain in href for domain in skip_domains):
                                            print(f"跳过已知的非翻页域名: {href}")
                                            continue
                                        
                                        print(f"找到可能的下一页按钮，文本: '{text}'，href: {href}")
                                        next_button_found = True
                                        
                                        # 保存当前URL以便验证
                                        pre_click_url = driver.current_url
                                        
                                        # 尝试点击
                                        try:
                                            element.click()
                                            time.sleep(5)
                                        except Exception:
                                            driver.execute_script("arguments[0].click();", element)
                                            time.sleep(5)
                                        
                                        # 立即检查是否仍然在UP主空间页面
                                        if 'space.bilibili.com' not in driver.current_url:
                                            print(f"警告：点击后跳转到非UP主空间页面: {driver.current_url}，跳过此按钮")
                                            # 如果有跳转，尝试返回上一页
                                            if driver.current_url != pre_click_url:
                                                try:
                                                    driver.back()
                                                    time.sleep(3)
                                                except:
                                                    pass
                                            next_button_found = False
                                            continue
                                        
                                        # 记录翻页前的视频数量
                                        pre_pagination_count = len(collected_bvids)
                                        
                                        # 检查URL变化
                                        url_changed = driver.current_url != current_page_url and driver.current_url not in page_history
                                        
                                        # 重新滚动和提取（与前面相同的逻辑）
                                        print(f"翻页后重新滚动页面，URL变化: {url_changed}")
                                        driver.execute_script("window.scrollTo(0, 0);")
                                        time.sleep(2)  # 增加等待时间
                                        
                                        # 尝试强制刷新页面内容
                                        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
                                        time.sleep(3)
                                        
                                        for scroll_step in range(5):
                                            scroll_script = scroll_methods[random.randint(0, len(scroll_methods) - 1)]
                                            driver.execute_script(scroll_script)
                                            time.sleep(3)
                                        
                                        # 使用更多的选择器尝试提取视频
                                        print("使用增强选择器提取视频...")
                                        enhanced_selectors = selectors + [
                                            '.video-item a', '.list-item a', '.content a',
                                            '.video-card a', '.article-item a', 'a.cover'
                                        ]
                                        
                                        for selector in enhanced_selectors:
                                            try:
                                                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                                print(f"选择器 {selector} 找到 {len(elements)} 个元素")
                                                for element in elements:
                                                    href = element.get_attribute('href')
                                                    if href:
                                                        bv_match = re.search(r'(BV[0-9A-Za-z]{10})', href)
                                                        if bv_match:
                                                            bv = bv_match.group(1)
                                                            collected_bvids.add(bv)
                                            except Exception as e:
                                                print(f"选择器 {selector} 出错: {str(e)}")
                                        
                                        bvid_list = list(collected_bvids)
                                        new_video_count = len(bvid_list) - pre_pagination_count
                                        print(f"翻页后共收集到 {len(bvid_list)} 个唯一BV号，新增 {new_video_count} 个视频")
                                        
                                        # 更新URL历史，无论URL是否变化
                                        if url_changed:
                                            current_page_url = driver.current_url
                                            page_history.add(current_page_url)
                                            print(f"翻页成功，新页面URL: {current_page_url}")
                                        elif new_video_count > 0:
                                            print("翻页成功（通过AJAX加载，URL未变化）")
                                            
                                            if max_videos and len(bvid_list) >= max_videos:
                                                print(f"已达到最大视频数量 {max_videos}，提前结束翻页")
                                                break
                                
                                if next_button_found:
                                    break
                            except Exception:
                                pass
                    except Exception as e:
                        print(f"查找所有链接和按钮时出错: {str(e)}")
                
                # 专注于查找和点击下一页按钮，不再使用URL参数翻页
                # 如果没有找到下一页按钮，尝试更精确的选择器和AJAX加载检测
                if not next_button_found:
                    print("未找到下一页按钮，尝试更精确的选择器查找...")
                    
                    # 尝试使用更精确的下一页按钮选择器
                    next_page_selectors = [
                        'button.page-btn.next',  # 常见按钮类名
                        '.page-item.next a',     # 分页项中的下一页链接
                        '.pager-next',           # 分页器下一页
                        '.paginator-next',       # 分页器下一页变体
                        'a.page-next',           # 页面下一页链接
                        'a.next-page',           # 下一页链接变体
                        'a[class*="next"]',     # 类名包含next的链接
                        'button[class*="next"]', # 类名包含next的按钮
                        'a[aria-label="下一页"]', # 下一页aria标签
                        'a[title="下一页"]',     # 下一页标题
                        '.be-pager-next',         # B站特定分页器
                        '.vui_pagenation_next',   # B站特定分页器
                        '.pg_next',               # B站特定分页器
                    ]
                    
                    # 初始化found_button变量
                    found_button = None
                    
                    # 先尝试直接通过文本查找下一页按钮
                    try:
                        # 使用XPath查找包含"下一页"文本的按钮或链接
                        text_elements = driver.find_elements(By.XPATH, '//*[contains(text(), "下一页")]')
                        for element in text_elements:
                            if element.is_displayed() and element.is_enabled():
                                # 检查是否为有效按钮（链接或可点击元素）
                                tag_name = element.tag_name.lower()
                                if tag_name in ['a', 'button', 'div', 'span']:
                                    found_button = element
                                    print(f"直接通过文本找到下一页按钮，标签: {tag_name}，文本: '{element.text.strip()}'")
                                    break
                        if found_button:
                            print("通过文本查找成功找到下一页按钮")
                    except Exception as e:
                        print(f"通过文本查找下一页按钮出错: {str(e)}")
                    for selector in next_page_selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            # 筛选可见且可点击的元素
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    # 避免首页按钮
                                    href = element.get_attribute('href') or ''
                                    text = element.text.strip()
                                    aria_label = element.get_attribute('aria-label') or ''
                                    title = element.get_attribute('title') or ''
                                    
                                    # 检查是否为下一页按钮特征
                                    if ('下一页' in text or 'next' in text.lower() or 
                                        '下一页' in aria_label or 'next' in aria_label.lower() or
                                        '下一页' in title or 'next' in title.lower() or
                                        '>>' in text or '›' in text or '>' in text):
                                        found_button = element
                                        print(f"找到潜在下一页按钮，选择器: {selector}，文本: '{text}'")
                                        break
                        except Exception as e:
                            print(f"尝试选择器 {selector} 出错: {str(e)}")
                        if found_button:
                            break
                    
                    if found_button:
                        try:
                            print(f"尝试点击找到的下一页按钮...")
                            # 先滚动到按钮位置
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", found_button)
                            time.sleep(2)
                            
                            # 尝试点击
                            found_button.click()
                            next_button_found = True
                            print("点击成功，等待页面加载...")
                            time.sleep(5)
                            
                            # 滚动加载更多内容并提取BV号
                            print("翻页后滚动加载更多内容并提取BV号...")
                            # 等待页面内容加载完成
                            time.sleep(3)
                            # 使用增强选择器提取当前页面的BV号
                            print(f"正在提取第 {page_count} 页的BV号...")
                            page_collected = 0
                            # 第一次滚动到底部
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(3)
                            
                            # 使用增强选择器提取
                            for selector in ['a[href*="/video/"]', 'a[href*="BV"]', '.video-card a', '.video-item a']:
                                try:
                                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                    for element in elements:
                                        try:
                                            href = element.get_attribute('href')
                                            if href:
                                                bv_match = re.search(r'(BV[0-9A-Za-z]{10})', href)
                                                if bv_match:
                                                    bv = bv_match.group(1)
                                                    if bv not in collected_bvids:
                                                        collected_bvids.add(bv)
                                                        page_collected += 1
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                            
                            # 额外的滚动加载
                            for i in range(4):  # 总共5次滚动，第一次已经完成
                                driver.execute_script("window.scrollBy(0, document.body.scrollHeight * 0.8);")
                                time.sleep(3)
                                # 每次滚动后再次提取
                                for selector in ['a[href*="/video/"]', 'a[href*="BV"]']:
                                    try:
                                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                        for element in elements:
                                            try:
                                                href = element.get_attribute('href')
                                                if href:
                                                    bv_match = re.search(r'(BV[0-9A-Za-z]{10})', href)
                                                    if bv_match:
                                                        bv = bv_match.group(1)
                                                        if bv not in collected_bvids:
                                                            collected_bvids.add(bv)
                                                            page_collected += 1
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                            
                            print(f"第 {page_count} 页提取完成，新增 {page_collected} 个BV号")
                        except Exception as e:
                            print(f"点击下一页按钮失败: {str(e)}")
                            # 尝试JavaScript点击
                            try:
                                print("尝试使用JavaScript点击...")
                                driver.execute_script("arguments[0].click();", found_button)
                                next_button_found = True
                                print("JavaScript点击成功，等待页面加载...")
                                time.sleep(5)
                            except Exception as js_error:
                                print(f"JavaScript点击也失败: {str(js_error)}")
                    else:
                        print("未找到下一页按钮，尝试检测是否有AJAX无限滚动加载...")
                        # 记录翻页前的视频数量
                        pre_pagination_count = len(collected_bvids)
                        # 尝试检测AJAX加载
                        last_height = driver.execute_script("return document.body.scrollHeight")
                        no_new_content_count = 0
                        max_scrolls = 10
                        
                        for i in range(max_scrolls):
                            # 记录当前视频数量
                            current_count = len(collected_bvids)
                            
                            # 滚动到底部
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(3)
                            
                            # 检查是否有新内容加载
                            new_height = driver.execute_script("return document.body.scrollHeight")
                            
                            # 重新提取视频
                            for selector in selectors + [
                                'a[href*="/video/"]', 'a[href*="BV"]',
                                '.video-item a', '.list-item a'
                            ]:
                                try:
                                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                    for element in elements:
                                        href = element.get_attribute('href')
                                        if href:
                                            bv_match = re.search(r'(BV[0-9A-Za-z]{10})', href)
                                            if bv_match:
                                                bv = bv_match.group(1)
                                                collected_bvids.add(bv)
                                except Exception:
                                    pass
                            
                            # 检查是否有新视频加载
                            new_count = len(collected_bvids)
                            if new_count > current_count:
                                print(f"AJAX滚动加载发现新视频，新增 {new_count - current_count} 个视频")
                                no_new_content_count = 0
                            else:
                                no_new_content_count += 1
                                print(f"滚动 {i+1}/{max_scrolls}，未发现新内容")
                            
                            # 如果高度不再变化且没有新内容，认为已加载完
                            if new_height == last_height and no_new_content_count >= 3:
                                print("已到达内容末尾，无更多视频加载")
                                break
                            
                            last_height = new_height
                        
                        # 检查是否通过AJAX加载了新内容
                        if len(collected_bvids) > pre_pagination_count:
                            print(f"AJAX滚动加载成功，共新增 {len(collected_bvids) - pre_pagination_count} 个视频")
                            next_button_found = True  # 视为翻页成功
                        else:
                            print("AJAX滚动加载也未发现新内容")
                
                # 如果仍然没有找到下一页按钮或AJAX加载失败，结束翻页循环
                if not next_button_found:
                    print("无法找到下一页按钮且AJAX加载失败，结束翻页")
                    break
                
                # 如果已达到最大视频数量，结束翻页循环
                if max_videos and len(bvid_list) >= max_videos:
                    break
            
            print(f"\n翻页结束，共翻页 {page_count} 次")
            print(f"从所有页面共收集到 {len(bvid_list)} 个视频的BV号")
            
            # 第二次尝试：使用更多的选择器重新提取
            print("开始第二次尝试 18 种选择器提取视频元素")
            enhanced_selectors = [
                'a[href*="/video/"]',
                '.video-card a',
                '.video-item a',
                '.video-container a',
                '.list-item a',
                '.contents-item a',
                '.article-item a',
                '.card-box a',
                '.columns a',
                '.video-list-item a',
                '.i-1-4 a',
                '.i-1-5 a',
                '.small-item a',
                '.col-full a',
                'li.video-item a',
                'div.video-card a',
                'div.video-container a',
                'div.video-list-item a'
            ]
            
            # 尝试所有增强选择器
            for selector in enhanced_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"第二次尝试: 通过选择器 {selector} 找到 {len(elements)} 个元素")
                    
                    for element in elements:
                        try:
                            href = element.get_attribute('href')
                            if href:
                                bv_match = re.search(r'(BV[0-9A-Za-z]{10})', href)
                                if bv_match:
                                    bv = bv_match.group(1)
                                    collected_bvids.add(bv)
                        except Exception:
                            pass
                except Exception:
                    pass
                
                # 更新BV号列表并检查是否已找到足够的元素
                bvid_list = list(collected_bvids)
                print(f"当前累计找到 {len(bvid_list)} 个唯一元素")
                
                # 如果已找到足够数量的元素，可以提前退出
                if len(bvid_list) >= 50:  # 设置一个阈值，避免过多尝试
                    print("已找到足够数量的元素，提前退出第二次选择器尝试")
                    break
            
            # 最终处理BV号列表
            bvid_list = list(collected_bvids)
            
            # 如果有最大数量限制，进行裁剪
            if max_videos and len(bvid_list) > max_videos:
                bvid_list = bvid_list[:max_videos]
                print(f"已限制最大视频数量为 {max_videos}")
            
            print(f"\n总共找到 {len(bvid_list)} 个视频的BV号")
            
        except Exception as e:
            print(f"使用Selenium获取视频列表时发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 无论如何都要关闭浏览器
            if driver:
                print("关闭浏览器...")
                try:
                    driver.quit()
                except Exception as quit_error:
                    print(f"关闭浏览器时出错: {str(quit_error)}")
        
        return bvid_list, page_up_info
    
    def get_up_info(self, uid):
        """获取UP主信息
        
        Args:
            uid: UP主UID
            
        Returns:
            UP主信息字典
        """
        # 尝试通过API获取UP主信息
        api_url = 'https://api.bilibili.com/x/space/acc/info'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': f'https://space.bilibili.com/{uid}/'
        }
        
        try:
            print(f"正在获取UP主 {uid} 的信息...")
            response = requests.get(
                api_url,
                params={'mid': uid},
                headers=headers,
                cookies=self.cookies,
                proxies=self.proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and 'data' in data:
                    return {
                        'uid': uid,
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
        except Exception as e:
            print(f"通过API获取UP主信息失败: {str(e)}")
        
        # 如果API获取失败，返回基本信息
        print("获取UP主信息失败，返回基本信息")
        return {
            'uid': uid,
            'name': f'未知用户{uid}',
            'sign': '无法获取简介',
            'archive_count': 0
        }
    
    def save_to_json(self, up_info, videos, output_dir='./downloads'):
        """保存UP主信息和视频列表到JSON文件
        
        Args:
            up_info: UP主信息字典
            videos: 视频BV号列表
            output_dir: 输出目录
        """
        # 确保下载目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用UP主名字作为子文件夹名称，处理可能的特殊字符
        up_name = up_info.get('name', f'未知用户{up_info.get("uid")}')
        # 移除或替换可能导致文件系统问题的字符
        safe_up_name = re.sub(r'[<>"/\\|?*]', '_', up_name)
        
        # 创建UP主子文件夹
        up_dir = os.path.join(output_dir, safe_up_name)
        os.makedirs(up_dir, exist_ok=True)
        
        # 构建JSON数据
        json_data = {
            'up_info': up_info,
            'videos': videos,
            'collect_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_videos': len(videos)
        }
        
        # 保存到JSON文件
        json_file_path = os.path.join(up_dir, f'videos_{up_info.get("uid")}.json')
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            print(f"\n已成功保存数据到: {json_file_path}")
            print(f"共收集到 {len(videos)} 个视频的BV号")
            return json_file_path
        except Exception as e:
            print(f"保存JSON文件失败: {str(e)}")
            return None
    
    def collect_videos_by_selenium(self, uid, max_videos=None, headless=True, auto_download=False):
        """使用Selenium收集UP主视频的主方法
        
        Args:
            uid: UP主UID
            max_videos: 最大获取视频数量
            headless: 是否使用无头模式
            auto_download: 是否在收集后自动下载每个视频
            
        Returns:
            BV号列表
        """
        # 在使用Selenium前先进行网络测试
        print("正在测试网络连接...")
        try:
            import socket
            socket.create_connection(('space.bilibili.com', 80), timeout=10)
            print("网络连接测试成功")
        except Exception as e:
            print(f"网络连接测试失败: {str(e)}")
            print("无法连接到B站服务器，请检查网络连接或防火墙设置")
        
        # 先通过API获取UP主信息
        up_info = self.get_up_info(uid)
        
        # 获取视频列表，同时可能从页面获取UP主名字
        bvid_list, page_up_info = self.get_videos_by_selenium(uid, max_videos, headless)
        
        # 如果API获取失败但从页面获取到了名字，更新UP主信息
        if up_info.get('name', '').startswith('未知用户') and page_up_info:
            print(f"从页面更新UP主信息: {page_up_info.get('name')}")
            up_info.update(page_up_info)
        
        print(f"UP主: {up_info.get('name', '未知')}")
        print(f"简介: {up_info.get('sign', '无简介')}")
        
        # 保存到JSON文件而不是打印
        json_file_path = None
        if bvid_list:
            json_file_path = self.save_to_json(up_info, bvid_list)
        else:
            print("未获取到任何视频的BV号")
        
        # 如果启用了自动下载
        if auto_download and bvid_list and json_file_path:
            print(f"\n开始自动下载视频，共 {len(bvid_list)} 个视频...")
            # 初始化下载器，使用相同的cookie和代理
            downloader = BilibiliDownloader(cookie_path=self.cookie_path, proxy=self.proxy)
            
            # 获取保存的文件夹路径（从json文件路径中提取）
            output_dir = os.path.dirname(json_file_path)
            
            # 遍历所有视频进行下载
            for index, bvid in enumerate(bvid_list, 1):
                print(f"\n=== 下载视频 {index}/{len(bvid_list)}: BV{bvid} ===")
                try:
                    downloader.download_video(bvid, output_dir=output_dir)
                except Exception as e:
                    print(f"下载失败: {str(e)}")
                    print(f"继续下载下一个视频...")
                
                # 添加下载间隔，避免请求过于频繁
                if index < len(bvid_list):
                    print("休息5秒后继续下载...")
                    time.sleep(5)
            
            print("\n所有视频下载完成！")
        
        return bvid_list