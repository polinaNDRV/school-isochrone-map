#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import webbrowser
import threading
import time
import requests

def check_dependencies():
    required_packages = ['flask', 'geopandas', 'networkx', 'shapely', 'pyproj']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("\n❌ Отсутствуют необходимые пакеты:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nУстановите их командой:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    print("✅ Все зависимости установлены")
    return True

def wait_for_server(url, timeout=30):
    """Ожидание готовности сервера"""
    print(f"⏳ Ожидание готовности сервера...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/api/ready", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get('ready'):
                    print("✅ Сервер готов к работе!")
                    return True
                else:
                    print(f"  Сервер инициализируется: {data.get('message', '')}")
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            print(f"  Ожидание... ({str(e)[:50]})")
        
        time.sleep(1)
    
    print("⚠️ Таймаут ожидания сервера, но попробуем открыть браузер...")
    return False

def main():
    """Запуск приложения"""
    
    print("="*60)
    print("🚀 ЗАПУСК ИНТЕРАКТИВНОЙ КАРТЫ ИЗОХРОН")
    print("="*60)
    print()

    if not check_dependencies():
        return
    
    required_files = [
        'data/Школы_в_Ижевске.geojson',
        'data/entry-exit.geojson',
        'data/pedestrian_network_Izhevsk.geojson'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("\n❌ ОШИБКА: Отсутствуют следующие файлы:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nПожалуйста, поместите GeoJSON файлы в папку 'data/'")
        return
    
    print("✅ Все GeoJSON файлы найдены")
    print()
    
    backend_path = os.path.join(os.path.dirname(__file__), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    # Запускаем сервер в отдельном потоке
    def run_server():
        try:
            from backend.app import app
            app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
        except Exception as e:
            print(f"❌ Ошибка запуска сервера: {e}")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Ждем готовности сервера
    time.sleep(2)  # Даем серверу время на запуск
    
    url = 'http://localhost:5000'
    if wait_for_server(url):
        print(f"\n🌐 Открытие браузера: {url}")
        webbrowser.open(url)
    else:
        print(f"\n🌐 Попытка открыть браузер: {url}")
        webbrowser.open(url)
    
    print("\n📌 Сервер запущен. Нажмите Ctrl+C для остановки.")
    print("="*60)
    
    try:
        # Держим основной поток живым
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Сервер остановлен")
        sys.exit(0)

if __name__ == '__main__':
    main()