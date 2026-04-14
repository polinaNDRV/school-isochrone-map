# backend/app.py
from flask import Flask, jsonify, request, send_from_directory
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_loader import DataLoader
from graph_builder import GraphBuilder
from isochrone import IsochroneCalculator
from shapely.geometry import Point
from pyproj import Transformer

app = Flask(__name__, static_folder='../frontend', static_url_path='')

# Настройки
USE_DATABASE_CACHE = True  # Включить SQLite кэширование
CACHE_DIR = 'cache'

# Создаем папку для кэша
os.makedirs(CACHE_DIR, exist_ok=True)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

data_loader = None
graph_builder = None
isochrone_calculator = None

def initialize_backend():
    global data_loader, graph_builder, isochrone_calculator
    
    print("="*60)
    print("ИНИЦИАЛИЗАЦИЯ СЕРВЕРА")
    print("="*60)
    print(f"Кэширование: {'Включено (SQLite)' if USE_DATABASE_CACHE else 'Выключено'}")
    
    try:
        # Загружаем данные (они все равно нужны для школ и точек входа)
        data_loader = DataLoader(data_path='data/')
        data = data_loader.load_all_data()
        
        # Строим граф с использованием SQLite кэша
        graph_builder = GraphBuilder(
            use_database=USE_DATABASE_CACHE,
            db_path=os.path.join(CACHE_DIR, 'road_graph.db')
        )
        graph = graph_builder.build_graph_from_roads(data_loader.roads_utm)
        
        # Передаем graph_builder в isochrone_calculator для быстрого поиска
        isochrone_calculator = IsochroneCalculator(
            graph, 
            utm_crs=data_loader.utm_crs,
            graph_builder=graph_builder
        )
        
        print("="*60)
        print("ВСЕ ГОТОВО К РАБОТЕ")
        print("="*60)
        
        return data
    except Exception as e:
        print(f"ОШИБКА ИНИЦИАЛИЗАЦИИ: {e}")
        import traceback
        traceback.print_exc()
        return None

# Запускаем инициализацию
backend_data = initialize_backend()

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend', path)

@app.route('/api/schools', methods=['GET', 'OPTIONS'])
def get_schools():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if data_loader is None:
            return jsonify({'success': False, 'error': 'Data loader not initialized'}), 500
        
        schools_list = data_loader.get_schools_list()
        return jsonify({'success': True, 'schools': schools_list})
    except Exception as e:
        print(f"Ошибка в /api/schools: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/entries-exits', methods=['GET', 'OPTIONS'])
def get_entries_exits():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if data_loader is None:
            return jsonify({'success': False, 'error': 'Data loader not initialized'}), 500
        
        entries = data_loader.get_entries_exits_list()
        return jsonify({'success': True, 'entries': entries})
    except Exception as e:
        print(f"Ошибка в /api/entries-exits: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/roads', methods=['GET', 'OPTIONS'])
def get_roads():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if data_loader is None or data_loader.roads_wgs84 is None:
            return jsonify({'success': False, 'error': 'Roads data not available'}), 500
       
        features = []
        for idx, row in data_loader.roads_wgs84.iterrows():
            geom = row.geometry
            if geom is not None:
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': geom.geom_type,
                        'coordinates': list(geom.coords) if geom.geom_type == 'LineString' else [list(line.coords) for line in geom.geoms]
                    },
                    'properties': {}
                })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return jsonify(geojson)
    except Exception as e:
        print(f"Ошибка в /api/roads: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/schools-geojson', methods=['GET', 'OPTIONS'])
def get_schools_geojson():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if data_loader is None or data_loader.schools_wgs84 is None:
            return jsonify({'success': False, 'error': 'Schools data not available'}), 500

        features = []
        for idx, row in data_loader.schools_wgs84.iterrows():
            geom = row.geometry
            if geom is not None:

                if geom.geom_type == 'Polygon':
                    coords = [geom.centroid.x, geom.centroid.y]
                else:
                    coords = [geom.x, geom.y] if hasattr(geom, 'x') else list(geom.coords)[0]
                
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': coords
                    },
                    'properties': {
                        'name': row.get('name', f'Школа {idx}')
                    }
                })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return jsonify(geojson)
    except Exception as e:
        print(f"Ошибка в /api/schools-geojson: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/schools-polygons', methods=['GET', 'OPTIONS'])
def get_schools_polygons():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if data_loader is None or data_loader.schools_wgs84 is None:
            return jsonify({'success': False, 'error': 'Schools data not available'}), 500
        

        features = []
        for idx, row in data_loader.schools_wgs84.iterrows():
            geom = row.geometry
            if geom is not None:

                if geom.geom_type == 'Point':
                    buffer_size = 0.0002  
                    polygon = geom.buffer(buffer_size)
                    geom = polygon
                
                features.append({
                    'type': 'Feature',
                    'geometry': geom.__geo_interface__,
                    'properties': {
                        'name': row.get('name', f'Школа {idx}'),
                        'type': 'school'
                    }
                })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return jsonify(geojson)
    except Exception as e:
        print(f"Ошибка в /api/schools-polygons: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/schools-polygons-geojson', methods=['GET', 'OPTIONS'])
def get_schools_polygons_geojson():
    """Возвращает полигоны школ в формате GeoJSON (улучшенная версия)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if data_loader is None:
            return jsonify({'success': False, 'error': 'Data loader not initialized'}), 500
        
        # Используем новый метод из data_loader, если он есть
        if hasattr(data_loader, 'get_schools_polygons_geojson'):
            geojson = data_loader.get_schools_polygons_geojson()
            if geojson is None:
                return jsonify({'success': False, 'error': 'No school polygons available'}), 404
            return jsonify(geojson)
        
        if data_loader.schools_wgs84 is None:
            return jsonify({'success': False, 'error': 'Schools data not available'}), 500
        
        features = []
        for idx, row in data_loader.schools_wgs84.iterrows():
            geom = row.geometry
            if geom is not None:

                if geom.geom_type == 'Polygon':
                    polygon = geom
                else:

                    buffer_size = 0.0005  
                    polygon = geom.buffer(buffer_size)
                
                features.append({
                    'type': 'Feature',
                    'geometry': polygon.__geo_interface__,
                    'properties': {
                        'name': row.get('name', f'Школа {idx}'),
                        'type': 'school',
                        'area': polygon.area * 111319.9 * 111319.9  
                    }
                })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return jsonify(geojson)
        
    except Exception as e:
        print(f"Ошибка в /api/schools-polygons-geojson: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/calculate-isochrone', methods=['POST', 'OPTIONS'])
def calculate_isochrone():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        req_data = request.json
        lat = req_data.get('lat')
        lon = req_data.get('lon')
        time_minutes = req_data.get('time', 15)
        walking_speed = req_data.get('speed', 5)
        
        print(f"\n=== ЗАПРОС ИЗОХРОНЫ ===")
        print(f"Координаты: lat={lat}, lon={lon}")
        print(f"Время: {time_minutes} мин")
        print(f"Скорость: {walking_speed} км/ч")
        
        if not lat or not lon:
            return jsonify({'success': False, 'error': 'Не указаны координаты'}), 400
        
        transformer = Transformer.from_crs('EPSG:4326', data_loader.utm_crs, always_xy=True)
        x, y = transformer.transform(lon, lat)
        start_point_utm = Point(x, y)
        
        # Рассчитываем изохрону
        isochrone_polygon, reachable_edges, stats = isochrone_calculator.calculate_isochrone(
            start_point_utm, time_minutes, walking_speed
        )
        
        result = {'success': True, 'stats': stats}
        
        if isochrone_polygon:
            isochrone_wgs84 = isochrone_calculator.convert_to_wgs84(isochrone_polygon)
            result['isochrone'] = {
                'type': 'Feature',
                'geometry': isochrone_wgs84.__geo_interface__,
                'properties': {
                    'time': time_minutes,
                    'speed': walking_speed,
                    'area_sq_meters': stats['area_sq_meters']
                }
            }
        
        if reachable_edges:
            features = []
            for edge in reachable_edges[:100000]:
                edge_wgs84 = isochrone_calculator.convert_to_wgs84(edge)
                features.append({
                    'type': 'Feature',
                    'geometry': edge_wgs84.__geo_interface__,
                    'properties': {}
                })
            
            result['reachable_roads'] = {
                'type': 'FeatureCollection',
                'features': features
            }
        
        return jsonify(result)
    
    except Exception as e:
        print(f"ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/shortest-path', methods=['POST', 'OPTIONS'])
def shortest_path():
    """API: поиск кратчайшего пути между двумя точками"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        req_data = request.json
        start_lat = req_data.get('start_lat')
        start_lon = req_data.get('start_lon')
        end_lat = req_data.get('end_lat')
        end_lon = req_data.get('end_lon')
        
        print(f"\n=== ЗАПРОС КРАТЧАЙШЕГО ПУТИ ===")
        print(f"Старт: lat={start_lat}, lon={start_lon}")
        print(f"Финиш: lat={end_lat}, lon={end_lon}")
        
        if not all([start_lat, start_lon, end_lat, end_lon]):
            return jsonify({'success': False, 'error': 'Не указаны координаты точек'}), 400
        
        transformer = Transformer.from_crs('EPSG:4326', data_loader.utm_crs, always_xy=True)
        
        start_x, start_y = transformer.transform(start_lon, start_lat)
        end_x, end_y = transformer.transform(end_lon, end_lat)
        
        start_point_utm = Point(start_x, start_y)
        end_point_utm = Point(end_x, end_y)
        
        print(f"UTM координаты старта: ({start_x:.1f}, {start_y:.1f})")
        print(f"UTM координаты финиша: ({end_x:.1f}, {end_y:.1f})")
        
        path_geometry, distance = isochrone_calculator.find_shortest_path(start_point_utm, end_point_utm)
        
        if path_geometry is None or distance is None:
            return jsonify({'success': False, 'error': 'Путь не найден. Возможно, точки слишком далеко или нет связи между дорогами'}), 404
        
        path_wgs84 = isochrone_calculator.convert_to_wgs84(path_geometry)
        
        result = {
            'success': True,
            'distance_meters': round(distance, 1),
            'distance_km': round(distance / 1000, 2),
            'path': {
                'type': 'Feature',
                'geometry': path_wgs84.__geo_interface__,
                'properties': {
                    'distance_meters': round(distance, 1),
                    'distance_km': round(distance / 1000, 2)
                }
            }
        }
        
        print(f"УСПЕХ! Расстояние: {distance:.1f} метров ({distance/1000:.2f} км)")
        print(f"=== ПУТЬ ГОТОВ ===\n")
        
        return jsonify(result)
    
    except Exception as e:
        print(f"ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'status': 'ok', 'message': 'Сервер работает'})

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    """Возвращает статистику по загруженным данным"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        stats = {
            'schools_count': len(data_loader.schools) if data_loader and data_loader.schools is not None else 0,
            'entries_exits_count': len(data_loader.entries_exits) if data_loader and data_loader.entries_exits is not None else 0,
            'roads_count': len(data_loader.roads) if data_loader and data_loader.roads is not None else 0,
            'utm_crs': data_loader.utm_crs if data_loader else 'Unknown',
            'cache_enabled': USE_DATABASE_CACHE,
            'cache_type': 'SQLite' if USE_DATABASE_CACHE else 'None'
        }
        
        # Добавляем статистику из БД
        if graph_builder and graph_builder.use_database:
            db_stats = graph_builder.get_graph_stats()
            if db_stats:
                stats['graph_nodes'] = db_stats['nodes']
                stats['graph_edges'] = db_stats['edges']
                stats['graph_total_km'] = db_stats['total_length_km']
        else:
            stats['graph_nodes'] = graph_builder.graph.number_of_nodes() if graph_builder and graph_builder.graph else 0
            stats['graph_edges'] = graph_builder.graph.number_of_edges() if graph_builder and graph_builder.graph else 0
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        print(f"Ошибка в /api/stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/school/<int:school_id>', methods=['GET', 'OPTIONS'])
def get_school_by_id(school_id):
    """Возвращает информацию о школе по ID"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if data_loader is None or data_loader.schools_wgs84 is None:
            return jsonify({'success': False, 'error': 'Schools data not available'}), 500
        
        if school_id >= len(data_loader.schools_wgs84):
            return jsonify({'success': False, 'error': 'School not found'}), 404
        
        row = data_loader.schools_wgs84.iloc[school_id]
        geom = row.geometry
        
        if geom.geom_type == 'Polygon':
            lat = geom.centroid.y
            lon = geom.centroid.x
        else:
            lat = geom.y
            lon = geom.x
        
        school_info = {
            'id': school_id,
            'name': row.get('name', f'Школа {school_id}'),
            'lat': lat,
            'lon': lon,
            'geometry_type': geom.geom_type
        }
        
        return jsonify({'success': True, 'school': school_info})
    except Exception as e:
        print(f"Ошибка в /api/school/{school_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)