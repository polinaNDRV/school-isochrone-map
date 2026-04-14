// Глобальные переменные
let map;
let isochroneLayer = null;
let reachableRoadsLayer = null;
let startMarker = null;
let schoolsLayer = null;
let entriesExitsLayer = null;
let roadsLayer = null;
let pathLayer = null;
let routeStartMarker = null;
let routeEndMarker = null;
let isSelectingRouteStart = false;
let isSelectingRouteEnd = false;

const API_BASE_URL = 'http://localhost:5000/api';

// Инициализация карты
function initMap() {
    map = L.map('map').setView([56.8528, 53.2095], 13);
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; CartoDB',
        subdomains: 'abcd',
        maxZoom: 19,
        minZoom: 3
    }).addTo(map);
    
    // Обработчик для изохрон и маршрутов
    map.on('click', function(e) {
        if (isSelectingRouteStart) {
            // Выбор начальной точки маршрута
            if (routeStartMarker) map.removeLayer(routeStartMarker);
            routeStartMarker = L.marker(e.latlng, {
                icon: L.divIcon({html: '🚩', iconSize: [24, 24], className: 'custom-div-icon'})
            }).addTo(map);
            routeStartMarker.bindPopup('Начало маршрута').openPopup();
            isSelectingRouteStart = false;
            showStatus('Начальная точка выбрана. Теперь выберите конечную точку', 'success');
        } else if (isSelectingRouteEnd) {
            // Выбор конечной точки маршрута
            if (routeEndMarker) map.removeLayer(routeEndMarker);
            routeEndMarker = L.marker(e.latlng, {
                icon: L.divIcon({html: '🏁', iconSize: [24, 24], className: 'custom-div-icon'})
            }).addTo(map);
            routeEndMarker.bindPopup('Конец маршрута').openPopup();
            isSelectingRouteEnd = false;
            showStatus('Конечная точка выбрана. Нажмите "Найти путь"', 'success');
        } else {
            // Обычный клик - обновляем координаты для изохроны
            document.getElementById('lat').value = e.latlng.lat.toFixed(6);
            document.getElementById('lon').value = e.latlng.lng.toFixed(6);
            showStatus('Координаты обновлены', 'success');
        }
    });
    
    loadGeoJSONData();
    loadSchoolsList();
    addRouteControls();
}

// Контролеры для маршрута
function addRouteControls() {
    const controlsPanel = document.querySelector('.controls-panel .panel-content');
    
    if (document.getElementById('selectRouteStartBtn')) return;
    
    const routeDiv = document.createElement('div');
    routeDiv.className = 'input-group';
    routeDiv.style.marginTop = '20px';
    routeDiv.style.borderTop = '1px solid #ddd';
    routeDiv.style.paddingTop = '15px';
    routeDiv.innerHTML = `
        <label style="font-size: 14px; font-weight: bold;">
            <i class="fas fa-route"></i> Поиск маршрута:
        </label>
        <button id="selectRouteStartBtn" style="width: 100%; margin-bottom: 8px; background: #28a745; color: white; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">
            🚩 Выбрать начало маршрута
        </button>
        <button id="selectRouteEndBtn" style="width: 100%; margin-bottom: 8px; background: #dc3545; color: white; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">
            🏁 Выбрать конец маршрута
        </button>
        <button id="findRouteBtn" style="width: 100%; margin-bottom: 8px; background: #007bff; color: white; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">
            🔍 Найти кратчайший путь
        </button>
        <button id="clearRouteBtn" style="width: 100%; background: #6c757d; color: white; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">
            🗑 Очистить маршрут
        </button>
        <div id="routeInfo" style="margin-top: 10px; padding: 8px; background: #f8f9fa; border-radius: 6px; font-size: 12px; text-align: center; display: none;"></div>
    `;
    
    controlsPanel.appendChild(routeDiv);
    
    document.getElementById('selectRouteStartBtn').onclick = () => {
        isSelectingRouteStart = true;
        isSelectingRouteEnd = false;
        showStatus('Кликните на карте для выбора НАЧАЛА маршрута', 'info');
    };
    
    document.getElementById('selectRouteEndBtn').onclick = () => {
        isSelectingRouteEnd = true;
        isSelectingRouteStart = false;
        showStatus('Кликните на карте для выбора КОНЦА маршрута', 'info');
    };
    
    document.getElementById('findRouteBtn').onclick = findShortestPath;
    document.getElementById('clearRouteBtn').onclick = clearRoute;
}

// Поиск кратчайшего пути
async function findShortestPath() {
    if (!routeStartMarker || !routeEndMarker) {
        showStatus('Сначала выберите начальную и конечную точки маршрута!', 'error');
        return;
    }
    
    const start = routeStartMarker.getLatLng();
    const end = routeEndMarker.getLatLng();
    
    showStatus('Поиск кратчайшего пути...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/shortest-path`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                start_lat: start.lat,
                start_lon: start.lng,
                end_lat: end.lat,
                end_lon: end.lng
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (pathLayer) map.removeLayer(pathLayer);
            
            pathLayer = L.geoJSON(data.path, {
                style: {color: '#ff4444', weight: 5, opacity: 0.9}
            }).addTo(map);
            
            const routeInfo = document.getElementById('routeInfo');
            routeInfo.style.display = 'block';
            routeInfo.innerHTML = `
                <strong> Расстояние:</strong> ${data.distance_meters.toFixed(1)} метров<br>
                <strong> В километрах:</strong> ${data.distance_km.toFixed(2)} км
            `;
            
            const bounds = pathLayer.getBounds();
            if (bounds.isValid()) map.fitBounds(bounds);
            
            showStatus(`Путь найден! Расстояние: ${data.distance_meters.toFixed(1)} метров`, 'success');
        } else {
            showStatus(data.error || 'Путь не найден', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showStatus('Ошибка при поиске пути', 'error');
    }
}

// Очистка маршрута
function clearRoute() {
    if (pathLayer) { map.removeLayer(pathLayer); pathLayer = null; }
    if (routeStartMarker) { map.removeLayer(routeStartMarker); routeStartMarker = null; }
    if (routeEndMarker) { map.removeLayer(routeEndMarker); routeEndMarker = null; }
    const routeInfo = document.getElementById('routeInfo');
    if (routeInfo) { routeInfo.style.display = 'none'; routeInfo.innerHTML = ''; }
    showStatus('Маршрут очищен', 'success');
}

// Загрузка данных
async function loadGeoJSONData() {
    try {
        showStatus('Загрузка данных...', 'info');
        
        const roadsResponse = await fetch(`${API_BASE_URL}/roads`);
        const roadsData = await roadsResponse.json();
        roadsLayer = L.geoJSON(roadsData, {
            style: {color: '#1a73e8', weight: 2, opacity: 0.6}
        }).addTo(map);
        
        const schoolsResponse = await fetch(`${API_BASE_URL}/schools-geojson`);
        const schoolsData = await schoolsResponse.json();
        schoolsLayer = L.geoJSON(schoolsData, {
            style: {color: '#ff7800', weight: 2, fillColor: '#ff7800', fillOpacity: 0.3},
            pointToLayer: (feature, latlng) => L.marker(latlng, {
                icon: L.divIcon({html: '🏫', iconSize: [20, 20], className: 'custom-div-icon'})
            }),
            onEachFeature: (feature, layer) => {
                if (feature.properties?.name) layer.bindPopup(`<b>Школа</b><br>${feature.properties.name}`);
            }
        }).addTo(map);
        
        const entriesResponse = await fetch(`${API_BASE_URL}/entries-exits`);
        const entriesData = await entriesResponse.json();
        
        if (entriesData.success && entriesData.entries) {
            entriesData.entries.forEach(entry => {
                L.marker([entry.lat, entry.lon], {
                    icon: L.divIcon({html: '🚪', iconSize: [16, 16], className: 'custom-div-icon'})
                }).bindPopup(`<b>Вход/выход</b><br>${entry.description || 'Точка доступа'}`).addTo(map);
            });
        }
        
        showStatus('Данные загружены', 'success');
    } catch (error) {
        console.error('Ошибка:', error);
        showStatus('Ошибка загрузки данных', 'error');
    }
}

// Загрузка списка школ
async function loadSchoolsList() {
    try {
        const response = await fetch(`${API_BASE_URL}/schools`);
        const data = await response.json();
        
        if (data.success && data.schools) {
            const schoolsList = document.getElementById('schoolsList');
            schoolsList.innerHTML = '';
            
            data.schools.forEach(school => {
                const schoolDiv = document.createElement('div');
                schoolDiv.className = 'school-item';
                schoolDiv.onclick = () => selectSchool(school.lat, school.lon, school.name);
                schoolDiv.innerHTML = `<i class="fas fa-school"></i><div class="school-name">${school.name}</div>`;
                schoolsList.appendChild(schoolDiv);
            });
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

function selectSchool(lat, lon, name) {
    document.getElementById('lat').value = lat;
    document.getElementById('lon').value = lon;
    showStatus(`Выбрана школа: ${name}`, 'success');
    map.setView([lat, lon], 16);
}

// Построение изохроны
async function calculateIsochrone() {
    const lat = parseFloat(document.getElementById('lat').value);
    const lon = parseFloat(document.getElementById('lon').value);
    let time = parseInt(document.getElementById('timeValue').value);
    const speed = parseFloat(document.getElementById('speedSelect').value);
    
    console.log('Построение изохроны:', {lat, lon, time, speed});
    
    if (isNaN(lat) || isNaN(lon)) {
        showStatus('Введите корректные координаты', 'error');
        return;
    }
    
    if (isNaN(time) || time < 1) {
        time = 15;
        document.getElementById('timeValue').value = 15;
        document.getElementById('timeSlider').value = 15;
    }
    
    showStatus('Построение изохроны...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/calculate-isochrone`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({lat: lat, lon: lon, time: time, speed: speed})
        });
        
        const data = await response.json();
        console.log('Ответ сервера:', data);
        
        if (data.success) {
            // Очищаем предыдущие слои
            if (isochroneLayer) { map.removeLayer(isochroneLayer); isochroneLayer = null; }
            if (reachableRoadsLayer) { map.removeLayer(reachableRoadsLayer); reachableRoadsLayer = null; }
            if (startMarker) { map.removeLayer(startMarker); startMarker = null; }
            
            // Добавляем изохрону
            if (data.isochrone) {
                isochroneLayer = L.geoJSON(data.isochrone, {
                    style: {color: '#ff0000', weight: 2, fillColor: '#ff0000', fillOpacity: 0.2}
                }).addTo(map);
            }
            
            // Добавляем достижимые дороги
            if (data.reachable_roads) {
                reachableRoadsLayer = L.geoJSON(data.reachable_roads, {
                    style: {color: '#00ff00', weight: 3, opacity: 0.8}
                }).addTo(map);
            }
            
            // Добавляем маркер старта
            startMarker = L.marker([lat, lon], {
                icon: L.divIcon({html: '📍', iconSize: [30, 30], className: 'custom-div-icon'})
            }).addTo(map);
            
            const stats = data.stats;
            let msg = `Изохрона построена! `;
            if (stats) {
                msg += `${time} мин, ${speed} км/ч = ${stats.max_distance_meters?.toFixed(0) || '?'} м, `;
                msg += `площадь: ${stats.area_hectares?.toFixed(2) || '?'} га`;
            }
            showStatus(msg, 'success');
            
            if (isochroneLayer) {
                const bounds = isochroneLayer.getBounds();
                if (bounds.isValid()) map.fitBounds(bounds);
            }
        } else {
            showStatus(data.error || 'Ошибка построения изохроны', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showStatus('Ошибка соединения с сервером', 'error');
    }
}

// Очистка изохрон
function clearIsochrone() {
    if (isochroneLayer) { map.removeLayer(isochroneLayer); isochroneLayer = null; }
    if (reachableRoadsLayer) { map.removeLayer(reachableRoadsLayer); reachableRoadsLayer = null; }
    if (startMarker) { map.removeLayer(startMarker); startMarker = null; }
    showStatus('Изохроны очищены', 'success');
}

function showStatus(message, type) {
    const statusPanel = document.getElementById('statusPanel');
    const statusMessage = document.getElementById('statusMessage');
    statusMessage.innerHTML = message;
    statusPanel.style.display = 'block';
    
    const icon = statusPanel.querySelector('.status-content i');
    if (type === 'success') {
        icon.className = 'fas fa-check-circle';
        icon.style.color = '#28a745';
    } else if (type === 'error') {
        icon.className = 'fas fa-exclamation-circle';
        icon.style.color = '#dc3545';
    } else {
        icon.className = 'fas fa-spinner fa-spin';
        icon.style.color = '#007bff';
    }
    
    setTimeout(() => { statusPanel.style.display = 'none'; }, 3000);
}

function togglePanel() {
    const panel = document.querySelector('.controls-panel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

function toggleSchoolsPanel() {
    const content = document.querySelector('.schools-panel .panel-content');
    const btn = document.querySelector('.schools-panel .toggle-btn');
    if (content.style.display === 'none') {
        content.style.display = 'block';
        btn.textContent = '−';
    } else {
        content.style.display = 'none';
        btn.textContent = '+';
    }
}

// Синхронизация слайдера
document.addEventListener('DOMContentLoaded', function() {
    const timeSlider = document.getElementById('timeSlider');
    const timeValue = document.getElementById('timeValue');
    
    if (timeSlider && timeValue) {
        timeSlider.addEventListener('input', () => { timeValue.value = timeSlider.value; });
        timeValue.addEventListener('input', () => { timeSlider.value = timeValue.value; });
    }
    
    initMap();
});