import networkx as nx
from shapely.geometry import Point, Polygon, LineString, MultiLineString
from shapely.ops import unary_union
from pyproj import Transformer
import math
from heapq import heappush, heappop

class IsochroneCalculator:
    """Класс для расчета изохрон (зон пешеходной доступности) и маршрутов"""
    
    def __init__(self, graph, utm_crs='EPSG:32640', graph_builder=None):
        self.graph = graph
        self.utm_crs = utm_crs
        self.walking_speed_kmh = 5
        self.graph_builder = graph_builder  
        
    def calculate_isochrone(self, start_point, time_minutes, walking_speed_kmh=5):
        """Рассчет изохрон"""
        self.walking_speed_kmh = walking_speed_kmh
        
        # Скорость в метрах в минуту
        speed_m_per_min = (self.walking_speed_kmh * 1000) / 60
        max_distance_meters = time_minutes * speed_m_per_min
        
        print(f"\n--- РАСЧЕТ ИЗОХРОНЫ ---")
        print(f"Время: {time_minutes} мин")
        print(f"Скорость: {self.walking_speed_kmh} км/ч = {speed_m_per_min:.1f} м/мин")
        print(f"Макс. расстояние: {max_distance_meters:.1f} м")
        
        # Находим ближайший узел
        nearest_node = self._find_nearest_node(start_point)
        if nearest_node is None:
            print("ОШИБКА: Не удалось найти ближайший узел")
            return None, [], {'error': 'Не удалось найти ближайший узел графа'}
        
        print(f"Ближайший узел: {nearest_node}")
        
        # Получаем подграф (зону доступности) 
        subgraph = self._get_ego_graph(nearest_node, max_distance_meters)
        
        # Создаем изохрону 
        isochrone_polygon = self._create_isochrone_from_subgraph(subgraph)
        
        # Собираем достижимые ребра для отображения
        reachable_edges = self._collect_edges_from_subgraph(subgraph)
        
        # Площадь
        area_sq_meters = isochrone_polygon.area if isochrone_polygon else 0
        
        stats = {
            'time_minutes': time_minutes,
            'walking_speed_kmh': walking_speed_kmh,
            'max_distance_meters': max_distance_meters,
            'nodes_reachable': subgraph.number_of_nodes(),
            'edges_reachable': subgraph.number_of_edges(),
            'area_sq_meters': round(area_sq_meters, 0),  
            'area_hectares': round(area_sq_meters / 10000, 2)  
        }
        
        print(f"Площадь изохроны: {stats['area_sq_meters']:.0f} кв.м ({stats['area_hectares']:.2f} га)")
        print(f"--- РАСЧЕТ ЗАВЕРШЕН ---\n")
        
        return isochrone_polygon, reachable_edges, stats
    
    def _get_ego_graph(self, start_node, max_distance):

        distances = {start_node: 0}
        heap = [(0, start_node)]
        reachable_nodes = set([start_node])
        
        while heap:
            current_dist, current_node = heappop(heap)
            
            if current_dist > max_distance:
                continue
                
            for neighbor in self.graph.neighbors(current_node):
                edge_data = self.graph.get_edge_data(current_node, neighbor)
                edge_length = edge_data.get('length', 0)
                new_dist = current_dist + edge_length
                
                if new_dist <= max_distance:
                    if neighbor not in distances or new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        reachable_nodes.add(neighbor)
                        heappush(heap, (new_dist, neighbor))
        
        subgraph = self.graph.subgraph(reachable_nodes).copy()
        return subgraph
    
    def _create_isochrone_from_subgraph(self, subgraph):
        if subgraph.number_of_nodes() == 0:
            return None
        
        try:
            # Собираем все геометрии ребер из подграфа
            edges_geometry = []
            for u, v, data in subgraph.edges(data=True):
                if 'geometry' in data and data['geometry']:
                    edges_geometry.append(data['geometry'])
            
            if not edges_geometry:
                nodes_coords = [Point(node) for node in subgraph.nodes()]
                if nodes_coords:
                    all_points = unary_union(nodes_coords)
                    return all_points.convex_hull
            
            # Объединяем все линии в одну геометрию
            all_lines = unary_union(edges_geometry)
            
            convex_hull = all_lines.convex_hull

            buffered = convex_hull.buffer(5)
            
            return buffered
            
        except Exception as e:
            print(f"Ошибка при создании изохроны: {e}")
            nodes_coords = [Point(node) for node in subgraph.nodes()]
            if nodes_coords:
                all_points = unary_union(nodes_coords)
                return all_points.convex_hull
            return None
    
    def _collect_edges_from_subgraph(self, subgraph):
        edges = []
        for u, v, data in subgraph.edges(data=True):
            if 'geometry' in data and data['geometry']:
                edges.append(data['geometry'])
        return edges
    
    def find_shortest_path(self, start_point, end_point):
        """Находит кратчайший путь между двумя точками"""
        print(f"\n--- ПОИСК КРАТЧАЙШЕГО ПУТИ ---")
        
        start_node = self._find_nearest_node(start_point)
        end_node = self._find_nearest_node(end_point)
        
        if start_node is None:
            print(f"ОШИБКА: Не найден узел для начальной точки {start_point}")
            return None, None
        if end_node is None:
            print(f"ОШИБКА: Не найден узел для конечной точки {end_point}")
            return None, None
        
        print(f"Начальный узел: {start_node}")
        print(f"Конечный узел: {end_node}")
        
        try:
            if not nx.has_path(self.graph, start_node, end_node):
                print("ОШИБКА: Нет пути между узлами")
                return None, None
            
            path_nodes = nx.shortest_path(self.graph, source=start_node, target=end_node, weight='length')
            distance = nx.shortest_path_length(self.graph, source=start_node, target=end_node, weight='length')
            
            print(f"Путь найден! Длина пути: {distance:.1f} метров")
            print(f"Количество узлов в пути: {len(path_nodes)}")
            
            path_geometry = self._build_path_geometry(path_nodes)
            
            if path_geometry is None:
                print("ОШИБКА: Не удалось построить геометрию пути")
                return None, None
            
            print(f"--- ПУТЬ ПОСТРОЕН ---\n")
            return path_geometry, distance
            
        except nx.NetworkXNoPath:
            print("ОШИБКА: Путь не найден в графе")
            return None, None
        except Exception as e:
            print(f"ОШИБКА при поиске пути: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def _find_nearest_node(self, point):
        """Находит ближайший узел (использует БД если доступна)"""
        if self.graph_builder:
            node = self.graph_builder.find_nearest_node_fast(point.x, point.y)
            if node:
                return node
        
        # Обычный поиск
        if self.graph is None or self.graph.number_of_nodes() == 0:
            return None
        
        min_dist = float('inf')
        nearest_node = None
        
        for node in self.graph.nodes():
            node_point = Point(node)
            dist = node_point.distance(point)
            if dist < min_dist:
                min_dist = dist
                nearest_node = node
        
        return nearest_node
    
    def _build_path_geometry(self, path_nodes):
        if not path_nodes or len(path_nodes) < 2:
            return None
        
        coords = []
        for i in range(len(path_nodes) - 1):
            node1 = path_nodes[i]
            node2 = path_nodes[i + 1]
            edge_data = self.graph.get_edge_data(node1, node2)
            
            if edge_data and 'geometry' in edge_data and edge_data['geometry']:
                geom = edge_data['geometry']
                if i == 0:
                    coords.extend(list(geom.coords))
                else:
                    coords.extend(list(geom.coords)[1:])
            else:
                if i == 0:
                    coords.append(node1)
                coords.append(node2)
        
        if len(coords) < 2:
            return None
        
        return LineString(coords)
    
    def convert_to_wgs84(self, geometry):
        transformer = Transformer.from_crs(self.utm_crs, 'EPSG:4326', always_xy=True)
        
        if geometry is None:
            return None
            
        if geometry.geom_type == 'Polygon':
            coords = []
            for point in geometry.exterior.coords:
                lon, lat = transformer.transform(point[0], point[1])
                coords.append([lon, lat])
            return Polygon(coords)
        
        elif geometry.geom_type == 'LineString':
            coords = []
            for point in geometry.coords:
                lon, lat = transformer.transform(point[0], point[1])
                coords.append([lon, lat])
            return LineString(coords)
        
        elif geometry.geom_type == 'MultiLineString':
            new_lines = []
            for line in geometry.geoms:
                coords = []
                for point in line.coords:
                    lon, lat = transformer.transform(point[0], point[1])
                    coords.append([lon, lat])
                new_lines.append(LineString(coords))
            return MultiLineString(new_lines)
        
        return geometry