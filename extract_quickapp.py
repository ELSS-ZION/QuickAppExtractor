#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import subprocess
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class QuickAppExtractor:
    def __init__(self):
        self.source_dir = '/data/data/com.miui.hybrid/app_resource'
        self.output_dir = 'extracted_quickapps'

    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logging.info(f'创建输出目录: {self.output_dir}')

    def check_adb_device(self):
        """检查ADB设备连接状态"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, encoding='utf-8')
            devices = [line.split()[0] for line in result.stdout.splitlines()[1:] if line.strip()]
            
            if not devices:
                logging.error('未检测到已连接的设备')
                return False
            
            if len(devices) > 1:
                logging.warning('检测到多个设备，将使用第一个设备')
            
            logging.info(f'已连接设备: {devices[0]}')
            return True
        except Exception as e:
            logging.error(f'检查设备时出错: {str(e)}')
            return False

    def list_quickapps(self):
        """列出快应用资源目录"""
        try:
            result = subprocess.run(
                ['adb', 'shell', 'su -c', f'ls {self.source_dir}'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            if result.returncode != 0:
                logging.error(f'列出快应用目录失败: {result.stderr}')
                return []
            
            apps = [app.strip() for app in result.stdout.splitlines() if app.strip()]
            logging.info(f'找到 {len(apps)} 个快应用资源目录')
            return apps
        except Exception as e:
            logging.error(f'列出快应用时出错: {str(e)}')
            return []

    def get_app_name_from_manifest(self, app_name):
        """从manifest.json获取应用名称"""
        try:
            # 从设备读取
            result = subprocess.run(
                ['adb', 'shell', 'su -c', f'cat {self.source_dir}/{app_name}/manifest.json'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            if result.returncode != 0:
                return app_name
            manifest_data = json.loads(result.stdout)
            
            return manifest_data.get('name', app_name)
        except Exception as e:
            logging.warning(f'读取manifest.json失败: {str(e)}, 使用原始包名')
            return app_name

    def extract_quickapp(self, app_name):
        """提取单个快应用的资源"""
        try:
            self.ensure_output_dir()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_output_dir = os.path.join(self.output_dir, f'{app_name}_{timestamp}')
            os.makedirs(temp_output_dir, exist_ok=True)

            source_path = f'{self.source_dir}/{app_name}'
            temp_path = f'/sdcard/quickapp_temp/{app_name}'
            
            # 创建临时目录
            subprocess.run(
                ['adb', 'shell', 'su -c', f'mkdir -p /sdcard/quickapp_temp'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            # 修改目录权限并复制到临时目录
            copy_result = subprocess.run(
                ['adb', 'shell', 'su -c', f'cp -r {source_path} {temp_path}'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            if copy_result.returncode != 0:
                logging.error(f'复制到临时目录失败 {app_name}: {copy_result.stderr}')
                return False

            # 修改临时目录权限
            chmod_result = subprocess.run(
                ['adb', 'shell', 'su -c', f'chmod -R 777 {temp_path}'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            if chmod_result.returncode != 0:
                logging.error(f'修改临时目录权限失败 {app_name}: {chmod_result.stderr}')
                return False

            # 从临时目录提取快应用资源
            result = subprocess.run(
                ['adb', 'pull', temp_path, temp_output_dir],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            # 清理临时目录
            subprocess.run(
                ['adb', 'shell', 'su -c', f'rm -rf {temp_path}'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            if result.returncode == 0:
                # 读取manifest.json获取应用名称
                app_display_name = self.get_app_name_from_manifest(app_name)
                # 使用应用名称重命名输出目录
                app_output_dir = os.path.join(self.output_dir, f'{app_display_name}_{timestamp}')
                os.rename(temp_output_dir, app_output_dir)
                logging.info(f'成功提取快应用: {app_display_name} ({app_name}) -> {app_output_dir}')
                return True
            else:
                logging.error(f'提取快应用失败 {app_name}: {result.stderr}')
                return False
        except Exception as e:
            logging.error(f'提取快应用 {app_name} 时出错: {str(e)}')
            return False

    def extract_all(self):
        """提取所有快应用资源"""
        if not self.check_adb_device():
            return

        apps = self.list_quickapps()
        if not apps:
            return
            
        self.ensure_output_dir()

        success_count = 0
        for app in apps:
            if self.extract_quickapp(app):
                success_count += 1

        logging.info(f'提取完成: 成功 {success_count}/{len(apps)}')

    def list_packages(self):
        """列出所有已缓存的快应用包名"""
        apps = self.list_quickapps()
        if apps:
            print('\n已缓存的快应用:')
            for app in apps:
                app_display_name = self.get_app_name_from_manifest(app)
                print(f'- {app_display_name} ({app})')
        else:
            print('未找到已缓存的快应用')

    def clear_cache(self):
        """清除所有快应用缓存"""
        if not self.check_adb_device():
            return

        apps = self.list_quickapps()
        if not apps:
            print('没有找到需要清理的快应用缓存')
            return

        print(f'\n即将清除以下快应用的缓存:')
        for app in apps:
            print(f'- {app}')

        confirm = input('\n确认要清除这些快应用的缓存吗？[y/N] ')
        if confirm.lower() != 'y':
            print('已取消清除操作')
            return

        success_count = 0
        for app in apps:
            try:
                result = subprocess.run(
                    ['adb', 'shell', 'su -c', f'rm -rf {self.source_dir}/{app}'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                if result.returncode == 0:
                    success_count += 1
                    logging.info(f'成功清除快应用缓存: {app}')
                else:
                    logging.error(f'清除快应用缓存失败 {app}: {result.stderr}')
            except Exception as e:
                logging.error(f'清除快应用缓存 {app} 时出错: {str(e)}')

        logging.info(f'清除完成: 成功 {success_count}/{len(apps)}')

def show_help():
    """显示帮助信息"""
    print('快应用资源提取工具')
    print('\n可用命令：')
    print('  extract [包名]  提取快应用资源，不指定包名则提取所有')
    print('  list     查看已缓存的快应用列表')
    print('  clear    清理快应用缓存')
    print('  help     显示此帮助信息')

def main():
    extractor = QuickAppExtractor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'extract':
            if len(sys.argv) > 2:
                extractor.extract_quickapp(sys.argv[2])
            else:
                extractor.extract_all()
        elif sys.argv[1] == 'list':
            extractor.list_packages()
        elif sys.argv[1] == 'clear':
            extractor.clear_cache()
        elif sys.argv[1] == 'help':
            show_help()
        else:
            print('无效的命令')
            show_help()
    else:
        show_help()

if __name__ == '__main__':
    main()