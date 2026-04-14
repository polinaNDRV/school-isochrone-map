# utils/cache_manager.py
import os
import sqlite3
import argparse
from pathlib import Path

class CacheManager:
    """Утилита для управления SQLite кэшем графа"""
    
    def __init__(self, db_path='cache/graph.db'):
        self.db_path = db_path
    
    def get_info(self):
        """Показывает информацию о кэше"""
        if not os.path.exists(self.db_path):
            print("❌ Кэш не найден")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("="*60)
        print("ИНФОРМАЦИЯ О КЭШЕ ГРАФА")
        print("="*60)
        print(f"Файл: {self.db_path}")
        print(f"Размер: {os.path.getsize(self.db_path) / (1024*1024):.2f} MB")
        
        cursor.execute("SELECT COUNT(*) FROM nodes")
        nodes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM edges")
        edges = cursor.fetchone()[0]
        
        cursor.execute("SELECT key, value FROM metadata")
        metadata = cursor.fetchall()
        
        print(f"\n📊 Статистика:")
        print(f"  Узлов: {nodes:,}")
        print(f"  Ребер: {edges:,}")
        
        print(f"\n📝 Метаданные:")
        for key, value in metadata:
            print(f"  {key}: {value}")
        
        conn.close()
    
    def clear_cache(self):
        """Очищает кэш"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            print(f"✅ Кэш очищен: {self.db_path}")
        else:
            print("❌ Кэш не найден")
    
    def rebuild_cache(self, force=False):
        """Перестраивает кэш"""
        if not force and os.path.exists(self.db_path):
            response = input("Кэш уже существует. Перестроить? (y/N): ")
            if response.lower() != 'y':
                print("Отменено")
                return
        
        self.clear_cache()
        print("🔄 Перезапустите сервер для перестроения кэша")

def main():
    parser = argparse.ArgumentParser(description='Управление кэшем графа')
    parser.add_argument('command', choices=['info', 'clear', 'rebuild'], 
                       help='Команда для выполнения')
    parser.add_argument('--force', action='store_true', 
                       help='Принудительное выполнение')
    
    args = parser.parse_args()
    
    manager = CacheManager()
    
    if args.command == 'info':
        manager.get_info()
    elif args.command == 'clear':
        manager.clear_cache()
    elif args.command == 'rebuild':
        manager.rebuild_cache(force=args.force)

if __name__ == '__main__':
    main()