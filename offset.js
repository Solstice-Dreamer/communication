var map;
var lat = 30.5728;
var lon = 114.3055;
var zoom = 13;

if (typeof qt !== "undefined") {
    new QWebChannel(qt.webChannelTransport, function(channel) {
    window.pyBridge = channel.objects.pyBridge;
    if (window.pyBridge && window.pyBridge.onLogMessage) {
        window.pyBridge.onLogMessage("地图初始化完成");
    }
    channel.objects.pyBridge.mapInit.connect(function(lat, lng, zoom) {
        if (lat === undefined || lng === undefined || zoom === undefined) {
        console.error("地图初始化失败，参数未定义:", lat, lng, zoom);
        return;
        }

        console.log("从 Python 接收到初始地图参数:", lat, lng, zoom);

        // 初始化地图
        map = L.map("map").setView([lat, lng], zoom);

        // 添加瓦片图层
        var layer = L.tileLayer(
        "http://localhost:8080/tiles/{z}/{x}/{y}.png",
        {
            minZoom: 12,
            maxZoom: 14,
            tileSize: 256,
            attribution: "Local Tiles",
            errorTileUrl:
            "https://via.placeholder.com/256/ff0000/ffffff?text=Tile+Error",
        }
        );
        layer.addTo(map);

        // 添加绘图控件
        var drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);

        var drawControl = new L.Control.Draw({
        edit: {
            featureGroup: drawnItems,
        },
        draw: {
            polygon: true,
            polyline: false,
            rectangle: false,
            circle: false,
            marker: false,
            circlemarker: false,
        },
        });
        map.addControl(drawControl);

        map.on(L.Draw.Event.CREATED, function (event) {
        try {
            var layer = event.layer;
            drawnItems.addLayer(layer);

            var geojsonStr = JSON.stringify(layer.toGeoJSON());
            console.log("发送给 Python 的 GeoJSON:", geojsonStr);

            if (window.pyBridge && window.pyBridge.onPolygonDrawn) {
            window.pyBridge.onPolygonDrawn(geojsonStr);
            }
        } catch (e) {
            console.error("Error handling draw created event:", e);
        }
        });

        // 通知 Python 初始角点
        notifyPython();
        map.on('moveend', notifyPython);
        map.on('zoomend', notifyPython);
    });
    });
} else {
    console.warn("qt is not defined. Running outside Qt environment.");
}

function getMapCornerCoordinates() {
    if (!map) return null;

    const bounds = map.getBounds();
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();

    return {
    topLeft: [sw.lng, ne.lat],
    topRight: [ne.lng, ne.lat],
    bottomRight: [ne.lng, sw.lat],
    bottomLeft: [sw.lng, sw.lat],
    };
}

function notifyPython() {
    const coords = getMapCornerCoordinates();
    console.log("即将发送角点坐标给 Python:", coords);
    if (window.pyBridge && window.pyBridge.onCornersChanged) {
    window.pyBridge.onCornersChanged(coords);
    } else {
    console.warn("pyBridge 尚未准备好。");
    }
}