import geopandas as gpd
import os
import warnings
warnings.filterwarnings('ignore')

class DataLoader:
    def __init__(self, data_path='data/'):
        self.data_path = data_path
        self.schools = None
        self.entries_exits = None
        self.roads = None
        self.schools_wgs84 = None
        self.entries_exits_wgs84 = None
        self.roads_wgs84 = None
        self.schools_utm = None
        self.entries_exits_utm = None
        self.roads_utm = None
        self.schools_polygons_wgs84 = None  
        self.utm_crs = 'EPSG:32640'
        
    def load_all_data(self):
        print("Загрузка данных...")
        
        try:
            # Загрузк школ
            schools_path = f'{self.data_path}Школы_в_Ижевске.geojson'
            if not os.path.exists(schools_path):
                print(f" Файл не найден: {schools_path}")
                return False
            
            self.schools = gpd.read_file(schools_path)
            print(f"  ✓ Школы: {len(self.schools)} объектов")
            print(f"    - Тип геометрии: {self.schools.geometry.geom_type.unique()}")
            
            entries_path = f'{self.data_path}entry-exit.geojson'
            if not os.path.exists(entries_path):
                print(f" Файл не найден: {entries_path}")
                return False
            
            self.entries_exits = gpd.read_file(entries_path)
            print(f" Точки входа/выхода: {len(self.entries_exits)} объектов")
            
            # Загрузка дорог
            roads_path = f'{self.data_path}pedestrian_network_Izhevsk.geojson'
            if not os.path.exists(roads_path):
                print(f"  Файл не найден: {roads_path}")
                return False
            
            self.roads = gpd.read_file(roads_path)
            print(f"  ✓ Дороги: {len(self.roads)} объектов")
            
            # WGS84 
            print("  Конвертация в WGS84...")
            self.schools_wgs84 = self.schools.to_crs('EPSG:4326')
            self.entries_exits_wgs84 = self.entries_exits.to_crs('EPSG:4326')
            
            # СОЗДАЕМ ПОЛИГОНЫ ШКОЛ 
            self.schools_polygons_wgs84 = self._create_school_polygons()
            
            if self.roads.crs is None:
                self.roads_wgs84 = self.roads
            else:
                self.roads_wgs84 = self.roads.to_crs('EPSG:4326')
            
            print(f"  Конвертация в {self.utm_crs} для расчетов...")
            self.schools_utm = self.schools.to_crs(self.utm_crs)
            self.entries_exits_utm = self.entries_exits.to_crs(self.utm_crs)
            
            if self.roads.crs is None:
                self.roads_utm = self.roads.to_crs(self.utm_crs)
            else:
                self.roads_utm = self.roads.to_crs(self.utm_crs)
            
            print(" Загрузка завершена успешно!")
            return True
            
        except Exception as e:
            print(f" ОШИБКА при загрузке данных: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_school_polygons(self):
        """Создает полигоны школ """
        polygons = []
        
        for idx, row in self.schools_wgs84.iterrows():
            geom = row.geometry
            school_name = row.get('name', f'Школа {idx}')
            
            if geom is not None:
                if geom.geom_type == 'Polygon':
                    polygons.append({
                        'geometry': geom,
                        'name': school_name,
                        'type': 'school_polygon'
                    })
                elif geom.geom_type == 'Point':
                    buffer_size = 0.0005
                    polygon = geom.buffer(buffer_size)
                    polygons.append({
                        'geometry': polygon,
                        'name': school_name,
                        'type': 'school_polygon'
                    })
        
        if polygons:
            return gpd.GeoDataFrame(polygons, crs='EPSG:4326')
        return None
    
    def get_schools_list(self):
        schools_list = []
        for idx, row in self.schools_wgs84.iterrows():
            try:
                if row.geometry.geom_type == 'Polygon':
                    lat = row.geometry.centroid.y
                    lon = row.geometry.centroid.x
                else:
                    lat = row.geometry.y
                    lon = row.geometry.x
                
                school_name = row.get('name', f'Школа {idx}')

                def safe_value(value):
                    if value is None or str(value) == 'nan' or str(value) == '':
                        return ''
                    return str(value)
                
                school_info = {
                    'name' : school_name,
                    'lat': float(lat) if lat is not None else 0,
                    'lon': float(lon) if lon is not None else 0,
                    'street': safe_value(row.get('street')),
                    'housenumber': safe_value(row.get('housenumber')),
                    'ref': safe_value(row.get('ref')),
                    'actual_occupancy': safe_value(row.get('actual_occupancy')),
                    'project_capacity': safe_value(row.get('project_capacity')),
                    'occupancy_by_order': safe_value(row.get('оccupancy_by_order')),
                    'plan_occupancy': safe_value(row.get('plan_occupancy ')),  
                
                }
                schools_list.append(school_info)
            except Exception as e:
                print(f"Ошибка при обработке школы {idx}: {e}")
                continue
        
        return schools_list
    
    def get_schools_polygons_geojson(self):
        """Возвращает полигоны школ в формате GeoJSON"""
        if self.schools_polygons_wgs84 is None:
            return None
        
        features = []
        for idx, row in self.schools_polygons_wgs84.iterrows():
            features.append({
                'type': 'Feature',
                'geometry': row.geometry.__geo_interface__,
                'properties': {
                    'name': row['name'],
                    'type': 'school',
                    'area_ha':row.geometry.area * 100
                    
                }
            })
        
        return {
            'type': 'FeatureCollection',
            'features': features
        }
    
    def get_entries_exits_list(self):
        entries = []
        for idx, row in self.entries_exits_wgs84.iterrows():
            try:
                name = row.get('name', None)
                if not name:
                    name = row.get('name:ru', None)
                if not name:
                    name = f'Вход/выход {idx}'
                
                entries.append({
                    'lat': row.geometry.y,
                    'lon': row.geometry.x,
                    'description': name
                })
            except Exception as e:
                print(f"Ошибка при обработке точки входа/выхода {idx}: {e}")
                continue
        return entries
    