#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
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
        self.ensure_output_dir()

    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logging.info(f'创建输出目录: {self.output_dir}')

    def check_adb_device(self):
        """检查ADB设备连接状态"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
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
                text=True
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

    def extract_quickapp(self, app_name):
        """提取单个快应用的资源"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            app_output_dir = os.path.join(self.output_dir, f'{app_name}_{timestamp}')
            os.makedirs(app_output_dir, exist_ok=True)

            source_path = f'{self.source_dir}/{app_name}'
            temp_path = f'/sdcard/quickapp_temp/{app_name}'
            
            # 创建临时目录
            subprocess.run(
                ['adb', 'shell', 'su -c', f'mkdir -p /sdcard/quickapp_temp'],
                capture_output=True,
                text=True
            )
            
            # 修改目录权限并复制到临时目录
            copy_result = subprocess.run(
                ['adb', 'shell', 'su -c', f'cp -r {source_path} {temp_path}'],
                capture_output=True,
                text=True
            )
            if copy_result.returncode != 0:
                logging.error(f'复制到临时目录失败 {app_name}: {copy_result.stderr}')
                return False

            # 修改临时目录权限
            chmod_result = subprocess.run(
                ['adb', 'shell', 'su -c', f'chmod -R 777 {temp_path}'],
                capture_output=True,
                text=True
            )
            if chmod_result.returncode != 0:
                logging.error(f'修改临时目录权限失败 {app_name}: {chmod_result.stderr}')
                return False

            # 从临时目录提取快应用资源
            result = subprocess.run(
                ['adb', 'pull', temp_path, app_output_dir],
                capture_output=True,
                text=True
            )

            # 清理临时目录
            subprocess.run(
                ['adb', 'shell', 'su -c', f'rm -rf {temp_path}'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logging.info(f'成功提取快应用: {app_name} -> {app_output_dir}')
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

        success_count = 0
        for app in apps:
            if self.extract_quickapp(app):
                success_count += 1

        logging.info(f'提取完成: 成功 {success_count}/{len(apps)}')

def main():
    extractor = QuickAppExtractor()
    extractor.extract_all()

if __name__ == '__main__':
    main()