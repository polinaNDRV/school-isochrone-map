# check_pedestrian_network.py
import geopandas as gpd
import json

def check_pedestrian_network():
    print("Проверка пешеходной сети Ижевска...")
    print("="*60)
    
    try:
        # Загружаем файл
        print("\n1. Загрузка файла...")
        gdf = gpd.read_file('data/pedestrian_network_Izhevsk.geojson')
        
        print(f"\n✓ Основная информация:")
        print(f"  - Количество объектов: {len(gdf):,}")
        print(f"  - CRS: {gdf.crs}")
        print(f"  - Типы геометрии: {gdf.geometry.geom_type.unique()}")
        print(f"  - Колонки: {list(gdf.columns)[:10]}...")  # Показываем первые 10 колонок
        
        # Проверяем типы линий
        print(f"\n2. Типы геометрии:")
        geom_counts = gdf.geometry.geom_type.value_counts()
        for geom_type, count in geom_counts.items():
            print(f"  - {geom_type}: {count:,}")
        
        # Проверяем длину линий
        if 'LineString' in gdf.geometry.geom_type.values:
            # Вычисляем длины в метрах (если CRS в градусах, конвертируем)
            if gdf.crs and '4326' in str(gdf.crs):
                print(f"\n3. Конвертация в метрическую систему...")
                gdf_utm = gdf.to_crs('EPSG:32640')
                gdf_utm['length_m'] = gdf_utm.geometry.length
                
                print(f"\n✓ Статистика длин сегментов:")
                print(f"  - Минимальная длина: {gdf_utm['length_m'].min():.1f} м")
                print(f"  - Максимальная длина: {gdf_utm['length_m'].max():.1f} м")
                print(f"  - Средняя длина: {gdf_utm['length_m'].mean():.1f} м")
                print(f"  - Общая длина: {gdf_utm['length_m'].sum()/1000:.1f} км")
        
        # Проверяем пример геометрии
        print(f"\n4. Пример геометрии (первый объект):")
        sample = gdf.iloc[0]
        print(f"  - Тип: {sample.geometry.geom_type}")
        if sample.geometry.geom_type == 'LineString':
            print(f"  - Количество точек: {len(sample.geometry.coords)}")
            print(f"  - Начальная точка: {sample.geometry.coords[0]}")
            print(f"  - Конечная точка: {sample.geometry.coords[-1]}")
        
        print("\n" + "="*60)
        print("✓ Проверка завершена успешно!")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    check_pedestrian_network()