import geopandas as gpd

def check_school_fields():
    print("Проверка полей в файле школ...")
    print("="*60)
    
    try:
        # Загружаем файл
        gdf = gpd.read_file('data/Школы_в_Ижевске.geojson')
        
        print(f"\n✓ Загружено школ: {len(gdf)}")
        print(f"\n✓ ВСЕ доступные поля в файле:")
        
        for i, col in enumerate(gdf.columns, 1):
            if col != 'geometry':
                print(f"{i}. '{col}'")
        
        print("\n" + "="*60)
        print("Пример данных первой школы:")
        print("-"*40)
        
        first_school = gdf.iloc[0]
        for col in gdf.columns:
            if col != 'geometry':
                value = first_school[col]
                if value is not None and str(value) != 'nan':
                    print(f"  {col}: {value}")
        
        print("\n" + "="*60)
        print("Статистика по полям (сколько записей имеют данные):")
        print("-"*40)
        
        for col in gdf.columns:
            if col != 'geometry':
                non_null = gdf[col].notna().sum()
                if non_null > 0:
                    print(f"  {col}: {non_null}/{len(gdf)} записей")
        
        return gdf.columns.tolist()
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    columns = check_school_fields()
    if columns:
        print("\n✓ Список полей для использования в коде:")
        print(f"  {columns}")