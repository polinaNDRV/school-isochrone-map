# backend/graph_builder.py
import networkx as nx
from shapely.geometry import Point, LineString, MultiLineString
import os
from graph_database import GraphDatabase

class GraphBuilder:
    """Класс для построения графа дорожной сети с поддержкой SQLite"""
    
    def __init__(self, use_database=True, db_path='cache/graph.db'):
        self.graph = None
        self.use_database = use_database
        self.db_path = db_path
        self.db = GraphDatabase(db_path) if use_database else None
        
    def build_graph_from_roads(self, roads_gdf, force_rebuild=False):
        """
        Строит граф из линий дорог GeoDataFrame
        Использует SQLite для кэширования
        """
        print("="*60)
        print("ПОСТРОЕНИЕ ГРАФА ДОРОЖНОЙ СЕТИ")
        print("="*60)
        
        # Пытаемся загрузить из БД
        if self.use_database and not force_rebuild and self.db.graph_exists():
            print("📀 Загрузка графа из SQLite...")
            self.graph = self.db.load_graph()
            
            if self.graph and self.graph.number_of_nodes() > 0:
                stats = self.db.get_graph_stats()
                print(f"✅ Граф загружен из БД:")
                print(f"  - Узлов: {stats['nodes']:,}")
                print(f"  - Ребер: {stats['edges']:,}")
                print(f"  - Общая длина: {stats['total_length_km']:.1f} км")
                print("="*60)
                return self.graph
        
        # Строим граф с нуля
        print("🔨 Построение графа с нуля...")
        G = nx.Graph()
        
        total_segments = 0
        total_length = 0
        
        # Проходим по всем дорогам
        for idx, row in roads_gdf.iterrows():
            geom = row.geometry
            
            if geom.geom_type == 'LineString':
                lines = [geom]
            elif geom.geom_type == 'MultiLineString':
                lines = list(geom.geoms)
            else:
                continue
            
            for line in lines:
                coords = list(line.coords)
                
                for i in range(len(coords) - 1):
                    node1 = coords[i]
                    node2 = coords[i + 1]
                    
                    point1 = Point(node1)
                    point2 = Point(node2)
                    length = point1.distance(point2)
                    
                    # Добавляем узлы с координатами
                    G.add_node(node1, x=node1[0], y=node1[1])
                    G.add_node(node2, x=node2[0], y=node2[1])
                    
                    # Добавляем ребро
                    G.add_edge(
                        node1, node2,
                        length=length,
                        geometry=LineString([node1, node2])
                    )
                    
                    total_segments += 1
                    total_length += length
        
        self.graph = G
        
        print(f"✅ Граф построен:")
        print(f"  - Узлов: {G.number_of_nodes():,}")
        print(f"  - Ребер: {G.number_of_edges():,}")
        print(f"  - Общая длина: {total_length/1000:.1f} км")
        print(f"  - Сегментов: {total_segments:,}")
        
        # Сохраняем в SQLite
        if self.use_database:
            print("\n💾 Сохранение графа в SQLite...")
            metadata = {
                'total_length_m': str(total_length),
                'total_segments': str(total_segments),
                'crs': str(roads_gdf.crs) if roads_gdf.crs else 'Unknown'
            }
            self.db.save_graph(G, metadata)
        
        print("="*60)
        return G
    
    def get_graph_stats(self):
        """Получает статистику графа (из БД если возможно)"""
        if self.use_database and self.db and self.db.graph_exists():
            return self.db.get_graph_stats()
        
        if self.graph is None:
            return None
            
        return {
            'nodes': self.graph.number_of_nodes(),
            'edges': self.graph.number_of_edges(),
            'is_connected': nx.is_connected(self.graph)
        }
    
    def find_nearest_node_fast(self, x, y):
        """Быстрый поиск ближайшего узла через БД"""
        if self.use_database and self.db:
            return self.db.find_nearest_node(x, y)
        
        # Fallback на обычный поиск
        if self.graph is None:
            return None
            
        min_dist = float('inf')
        nearest_node = None
        for node in self.graph.nodes():
            node_point = Point(node)
            dist = node_point.distance(Point(x, y))
            if dist < min_dist:
                min_dist = dist
                nearest_node = node
        return nearest_node