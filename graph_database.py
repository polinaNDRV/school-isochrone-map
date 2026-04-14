# backend/graph_database.py
import sqlite3
import json
import pickle
from shapely.geometry import LineString, Point
from typing import Tuple, Optional, Dict, Any
import networkx as nx
import os

class GraphDatabase:
    """Класс для хранения графа дорожной сети в SQLite"""
    
    def __init__(self, db_path='cache/graph.db'):
        self.db_path = db_path
        # Создаем папку для кэша, если её нет
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Инициализация структуры базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица для узлов графа
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                x REAL NOT NULL,
                y REAL NOT NULL,
                latitude REAL,
                longitude REAL
            )
        ''')
        
        # Таблица для ребер графа
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                length REAL NOT NULL,
                geometry TEXT,
                is_bidirectional INTEGER DEFAULT 1,
                FOREIGN KEY(from_node) REFERENCES nodes(node_id),
                FOREIGN KEY(to_node) REFERENCES nodes(node_id),
                UNIQUE(from_node, to_node)
            )
        ''')
        
        # Создаем индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_node)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_node)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_coords ON nodes(x, y)')
        
        # Таблица для метаданных (версия графа, статистика)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        
        # Проверяем, есть ли данные в БД
        cursor.execute('SELECT COUNT(*) FROM nodes')
        node_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM edges')
        edge_count = cursor.fetchone()[0]
        
        conn.close()
        
        if node_count > 0:
            print(f"📀 База данных найдена: {node_count} узлов, {edge_count} ребер")
        else:
            print("🆕 Создана новая база данных для графа")
    
    def save_graph(self, graph: nx.Graph, metadata: Optional[Dict] = None):
        """
        Сохраняет граф в базу данных
        
        Parameters:
        - graph: networkx.Graph - граф для сохранения
        - metadata: dict - дополнительная информация (CRS, дата создания и т.д.)
        """
        print(f"\n💾 Сохранение графа в SQLite...")
        print(f"   Узлов: {graph.number_of_nodes()}")
        print(f"   Ребер: {graph.number_of_edges()}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Начинаем транзакцию для ускорения
        cursor.execute('BEGIN TRANSACTION')
        
        try:
            # Очищаем старые данные
            print("   Очистка старых данных...")
            cursor.execute('DELETE FROM edges')
            cursor.execute('DELETE FROM nodes')
            cursor.execute('DELETE FROM metadata')
            
            # Сохраняем узлы
            print("   Сохранение узлов...")
            nodes_data = []
            for node, data in graph.nodes(data=True):
                x = data.get('x', 0)
                y = data.get('y', 0)
                # Координаты в WGS84 могут быть добавлены позже
                nodes_data.append((str(node), float(x), float(y), None, None))
            
            cursor.executemany(
                'INSERT INTO nodes (node_id, x, y, latitude, longitude) VALUES (?, ?, ?, ?, ?)',
                nodes_data
            )
            print(f"   ✓ Сохранено {len(nodes_data)} узлов")
            
            # Сохраняем ребра
            print("   Сохранение ребер...")
            edges_data = []
            for u, v, data in graph.edges(data=True):
                length = data.get('length', 0)
                
                # Сохраняем геометрию как GeoJSON
                geometry_json = None
                if 'geometry' in data and data['geometry']:
                    try:
                        geometry_json = json.dumps(data['geometry'].__geo_interface__)
                    except:
                        # Если не получается сохранить как GeoJSON, сохраняем координаты
                        coords = list(data['geometry'].coords)
                        geometry_json = json.dumps({'type': 'LineString', 'coordinates': coords})
                
                edges_data.append((str(u), str(v), float(length), geometry_json, 1))
            
            cursor.executemany(
                'INSERT INTO edges (from_node, to_node, length, geometry, is_bidirectional) VALUES (?, ?, ?, ?, ?)',
                edges_data
            )
            print(f"   ✓ Сохранено {len(edges_data)} ребер")
            
            # Сохраняем метаданные
            if metadata is None:
                metadata = {}
            
            default_metadata = {
                'graph_version': '1.0',
                'total_nodes': str(graph.number_of_nodes()),
                'total_edges': str(graph.number_of_edges()),
                'is_directed': str(graph.is_directed())
            }
            default_metadata.update(metadata)
            
            for key, value in default_metadata.items():
                cursor.execute(
                    'INSERT INTO metadata (key, value) VALUES (?, ?)',
                    (key, str(value))
                )
            
            conn.commit()
            print(f"✅ Граф успешно сохранен в {self.db_path}")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка при сохранении графа: {e}")
            raise
        finally:
            conn.close()
    
    def load_graph(self) -> Optional[nx.Graph]:
        """
        Загружает граф из базы данных
        
        Returns:
        - networkx.Graph или None, если база данных пуста
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем, есть ли данные
        cursor.execute('SELECT COUNT(*) FROM nodes')
        node_count = cursor.fetchone()[0]
        
        if node_count == 0:
            print("📭 База данных пуста. Сначала нужно сохранить граф.")
            conn.close()
            return None
        
        print(f"\n📖 Загрузка графа из SQLite...")
        print(f"   Узлов в БД: {node_count}")
        
        G = nx.Graph()
        
        try:
            # Загружаем узлы
            print("   Загрузка узлов...")
            cursor.execute('SELECT node_id, x, y FROM nodes')
            nodes = cursor.fetchall()
            
            for node_id, x, y in nodes:
                G.add_node(node_id, x=float(x), y=float(y))
            
            print(f"   ✓ Загружено {len(nodes)} узлов")
            
            # Загружаем ребра
            print("   Загрузка ребер...")
            cursor.execute('SELECT from_node, to_node, length, geometry FROM edges')
            edges = cursor.fetchall()
            
            edges_loaded = 0
            for from_node, to_node, length, geometry_json in edges:
                edge_data = {'length': float(length)}
                
                # Восстанавливаем геометрию из JSON
                if geometry_json:
                    try:
                        geo_dict = json.loads(geometry_json)
                        if geo_dict['type'] == 'LineString':
                            from shapely.geometry import shape
                            edge_data['geometry'] = shape(geo_dict)
                    except:
                        pass
                
                G.add_edge(from_node, to_node, **edge_data)
                edges_loaded += 1
            
            print(f"   ✓ Загружено {edges_loaded} ребер")
            
            # Загружаем метаданные
            cursor.execute('SELECT key, value FROM metadata')
            metadata = {key: value for key, value in cursor.fetchall()}
            
            print(f"✅ Граф загружен из БД")
            if metadata:
                print(f"   Метаданные: версия={metadata.get('graph_version', 'unknown')}")
            
            conn.close()
            return G
            
        except Exception as e:
            print(f"❌ Ошибка при загрузке графа: {e}")
            conn.close()
            return None
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Получает статистику графа из БД без загрузки всего графа"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM nodes')
        node_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM edges')
        edge_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(length) FROM edges')
        avg_length = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(length) FROM edges')
        total_length = cursor.fetchone()[0]
        
        cursor.execute('SELECT key, value FROM metadata')
        metadata = {key: value for key, value in cursor.fetchall()}
        
        conn.close()
        
        return {
            'nodes': node_count,
            'edges': edge_count,
            'avg_edge_length': float(avg_length) if avg_length else 0,
            'total_length_km': float(total_length) / 1000 if total_length else 0,
            'metadata': metadata
        }
    
    def find_nearest_node(self, x: float, y: float, max_distance: float = 100) -> Optional[str]:
        """
        Находит ближайший узел к заданным координатам (без загрузки всего графа)
        
        Parameters:
        - x, y: координаты в UTM
        - max_distance: максимальное расстояние в метрах
        
        Returns:
        - node_id или None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Используем формулу расстояния для приблизительного поиска
        query = '''
            SELECT node_id, x, y, 
                   ((x - ?) * (x - ?) + (y - ?) * (y - ?)) as dist_sq
            FROM nodes
            WHERE ((x - ?) * (x - ?) + (y - ?) * (y - ?)) < ?
            ORDER BY dist_sq
            LIMIT 1
        '''
        
        max_dist_sq = max_distance * max_distance
        
        cursor.execute(query, (x, x, y, y, x, x, y, y, max_dist_sq))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            node_id, node_x, node_y, dist_sq = result
            distance = (dist_sq ** 0.5)
            return node_id
        return None
    
    def get_edge_between(self, node1: str, node2: str) -> Optional[Dict]:
        """Получает информацию о ребре между двумя узлами"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT from_node, to_node, length, geometry 
            FROM edges 
            WHERE (from_node = ? AND to_node = ?) OR (from_node = ? AND to_node = ?)
        ''', (node1, node2, node2, node1))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'from': result[0],
                'to': result[1],
                'length': result[2],
                'geometry': result[3]
            }
        return None
    
    def graph_exists(self) -> bool:
        """Проверяет, есть ли данные в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM nodes')
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0