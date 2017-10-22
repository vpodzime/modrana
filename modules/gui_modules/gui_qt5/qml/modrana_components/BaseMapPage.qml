import QtQuick 2.0
import QtQuick.Layouts 1.1
import QtSensors 5.0 as Sensors
import UC 1.0
import "../map_components"
import "../functions.js" as F

Page {
    id : baseMapPage

    // general properties
    property bool showCompass : rWin.get("showQt5GUIMapCompass", true,
                                         function(v){baseMapPage.showCompass=v})
    property real compassOpacity : rWin.get("qt5GUIMapCompassOpacity", 0.7,
                                         function(v){baseMapPage.compassOpacity=v})
    property real routeOpacity : rWin.get("qt5GUIRouteOpacity", 1.0,
                                         function(v){baseMapPage.routeOpacity=v})
    // opacity of the tracklog logging trace
    property real tracklogTraceOpacity : rWin.get("qt5GUITracklogTraceOpacity", 1.0,
                                         function(v){baseMapPage.tracklogTraceOpacity=v})
    // opacity of stored tracklogs when shown on the map
    property real tracklogOpacity : rWin.get("qt5GUITracklogOpacity", 1.0,
                                         function(v){baseMapPage.tracklogOpacity=v})

    property bool center : true

    // zoom level
    property int zoomLevel : 15
    property int minZoomLevel : 0
    property int maxZoomLevel : 17

    // routing
    signal clearRoute
    property bool selectRoutingStart : false
    property bool selectRoutingDestination : false
    property bool routingStartSet: false
    property bool routingDestinationSet: false
    property real routingStartLat: 0.
    property real routingStartLon: 0.
    property real routingDestinationLat: 0.
    property real routingDestinationLon: 0.
    property bool routingRequestChanged : false
    property bool routingEnabled: false
    property bool routingP2P: true

    property int mapButtonSize : Math.min(width/8.0, height/8.0)
    property int mapButtonSpacing : mapButtonSize / 50

    function enableRoutingUI(p2p) {
        // enable the routing UI (currently just the 1-3 buttons)
        if (p2p == null) {
            p2p = true
        }
        routingP2P = p2p
        routingEnabled = true
    }

    function disableRoutingUI() {
        // disable the routing UI & hide the route
        routingEnabled = false
        routingP2P = false
    }

    function setRoutingStart(lat, lon) {
        rWin.routingStartPos.latitude = lat
        rWin.routingStartPos.longitude = lon
        rWin.routingStartPos.isValid = true
        routingStartLat = lat
        routingStartLon = lon
        routingStartSet = true
    }

    function setRoutingDestination(lat, lon) {
        rWin.routingDestinationPos.latitude = lat
        rWin.routingDestinationPos.longitude = lon
        rWin.routingDestinationPos.isValid = true
        routingDestinationLat = lat
        routingDestinationLon = lon
        routingDestinationSet = true
    }

    // navigation
    property bool navigationEnabled : false
    property real navigationOverlayHeight : height * 0.3

    // track logging & drawing
    property bool drawTracklogTrace : false
    property bool trackRecordingPaused : false

    function addTracePoint(point) {
        log.error("addTracePoint() is not implemented!")
    }

    function clearTracePoints() {
        log.error("clearTracePoints() is not implemented!")
    }

    function showTracklog(tracklog) {
        log.error("showTracklog() is not implemented!")
    }

    // general functions
    function showOnMap(lat, lon) {
        log.error("showOnMap() is not implemented!")
    }

    function centerMapOnCurrentPosition() {
        log.error("centerMapOnCurrentPosition() is not implemented!")
    }

    function getMap() {
        log.error("getMap() is not implemented!")
    }

    function zoomIn() {
        log.error("zoomIn() is not implemented!")
    }

    function zoomOut() {
        log.error("zoomOut() is not implemented!")
    }

    // signal handlers

    // if the page becomes active, activate the media keys so they can be used
    // for zooming; if the page is deactivated, deactivate them
    onIsActiveChanged: {
        rWin.actions.mediaKeysEnabled = baseMapPage.isActive
    }

    // compass
    Sensors.Compass {
        id : compass
        dataRate : 50
        active : baseMapPage.isActive && baseMapPage.showCompass
        property int old_value: 0
        onReadingChanged : {
            // fix for the "northern wiggle" originally
            // from Sailcompass by THP - Thanks! :)
            var new_value = -1.0 * compass.reading.azimuth
            if (Math.abs(old_value-new_value)>270){
                if (old_value > new_value){
                    new_value += 360.0
                }else{
                    new_value -= 360.0
                }
            }
            old_value = new_value
            compassImage.rotation = new_value
        }
    }
    Image {
        id: compassImage
        visible : baseMapPage.showCompass && !baseMapPage.navigationEnabled
        opacity : baseMapPage.compassOpacity
        // TODO: investigate how to replace this by an image loader
        // what about rendered size ?
        // also why are the edges of the image so jarred ?

        property string rosePath : if (rWin.qrc) {
            "qrc:/themes/" + rWin.theme.id +"/windrose-simple.svg"
        } else {
            "file://" + rWin.platform.themesFolderPath + "/" + rWin.theme.id +"/windrose-simple.svg"
        }

        source : compassImage.rosePath
        transformOrigin: Item.Center

        Behavior on rotation {
            SmoothedAnimation{ velocity: -1; duration:100;maximumEasingTime: 100 }
        }

        anchors.left: parent.left
        anchors.leftMargin: rWin.c.style.main.spacingBig
        anchors.top: parent.top
        anchors.topMargin: rWin.c.style.main.spacingBig
        smooth: true
        width: Math.min(baseMapPage.width/4, baseMapPage.height/4)
        fillMode: Image.PreserveAspectFit
        z: 2
    }

    // routing and navigation buttons
    ColumnLayout {
        layoutDirection : Qt.RightToLeft
        anchors.bottom: buttonsRight.top
        anchors.bottomMargin: rWin.c.style.map.button.margin * 2
        anchors.right: parent.right
        anchors.rightMargin: rWin.c.style.map.button.margin
        spacing: rWin.c.style.map.button.spacing
        visible: baseMapPage.routingEnabled
        MapButton {
            id: routingStart
            text: qsTr("<b>start</b>")
            width: mapButtonSize * 1.25
            height: mapButtonSize
            checked : selectRoutingStart
            toggledColor : Qt.rgba(1, 0, 0, 0.7)
            visible: baseMapPage.routingEnabled && baseMapPage.routingP2P && !baseMapPage.navigationEnabled
            onClicked: {
                selectRoutingStart = !selectRoutingStart
                selectRoutingDestination = false
            }
        }
        MapButton {
            id: routingEnd
            text: qsTr("<b>end</b>")
            width: mapButtonSize * 1.25
            height: mapButtonSize
            checked : selectRoutingDestination
            toggledColor : Qt.rgba(0, 1, 0, 0.7)
            visible: baseMapPage.routingEnabled && baseMapPage.routingP2P && !baseMapPage.navigationEnabled
            onClicked: {
                selectRoutingStart = false
                selectRoutingDestination = !selectRoutingDestination
            }
        }
        MapButton {
            id: navigateButton
            checkable : true
            visible: baseMapPage.routingEnabled && baseMapPage.routeAvailable
            text: qsTr("<b>navigate</b>")
            width: mapButtonSize * 1.6
            height: mapButtonSize
            onClicked: {
                if (baseMapPage.navigationEnabled) {
                    rWin.log.info("stopping navigation")
                } else {
                    rWin.log.info("starting navigation")
                }
                baseMapPage.navigationEnabled = !baseMapPage.navigationEnabled
            }
        }
        MapButton {
            id: clearRouting
            visible: baseMapPage.routingEnabled && !baseMapPage.navigationEnabled
            text: qsTr("<b>clear</b>")
            width: mapButtonSize * 1.25
            height: mapButtonSize
            onClicked: {
                selectRoutingStart = false
                selectRoutingDestination = false
                baseMapPage.routingEnabled = false
                // trigger the clear route signal
                baseMapPage.clearRoute()
            }
        }
    }
    Row {
        id: buttonsRight
        anchors.bottom: parent.bottom
        anchors.bottomMargin: rWin.c.style.map.button.margin
        anchors.right: parent.right
        anchors.rightMargin: rWin.c.style.map.button.margin
        spacing: rWin.c.style.map.button.spacing
        MapButton {
            iconName: "plus_small.png"
            onClicked: {
                baseMapPage.zoomIn()
            }
            width: mapButtonSize
            height: mapButtonSize
            enabled : baseMapPage.zoomLevel != baseMapPage.maxZoomLevel
        }
        MapButton {
            iconName: "minus_small.png"
            onClicked: {
                baseMapPage.zoomOut()
            }
            width: mapButtonSize
            height: mapButtonSize
            enabled : baseMapPage.zoomLevel != baseMapPage.minZoomLevel
        }
    }
    Column {
        id: buttonsLeft
        anchors.bottom: parent.bottom
        anchors.bottomMargin: rWin.c.style.map.button.margin
        anchors.left: parent.left
        anchors.leftMargin: rWin.c.style.map.button.margin
        spacing: mapButtonSpacing
        MapButton {
            iconName : "minimize_small.png"
            checkable : true
            visible: !rWin.platform.fullscreen_only
            onClicked: {
                rWin.toggleFullscreen()
            }
            width: mapButtonSize
            height: mapButtonSize
        }
        MapButton {
            id: followPositionButton
            iconName : "center_small.png"
            width: mapButtonSize
            height: mapButtonSize
            checked : baseMapPage.center
            /*
            checked is bound to baseMapPage.center, no need to toggle
            it's value when the button is pressed
            */
            checkable: false
            onClicked: {
                // toggle map centering
                if (baseMapPage.center) {
                    baseMapPage.center = false // disable
                } else {
                    baseMapPage.center = true // enable
                    if (rWin.llValid) { // recenter at once (TODO: validation ?)
                        baseMapPage.centerMapOnCurrentPosition()
                    }
                }
            }
        }
        MapButton {
            id: mainMenuButton
            iconName: showModeOnMenuButton ? rWin.mode  + "_small.png" : "menu_small.png"
            width: mapButtonSize
            height: mapButtonSize
            onClicked: {
                rWin.log.debug("map page: Menu pushed!")
                rWin.push("Menu", undefined, !rWin.animate)
            }
        }
    }

    // navigation overlay
    NavigationOverlay {
        id : navigationOverlay
        visible : baseMapPage.navigationEnabled
        anchors.top : parent.top
        anchors.left : parent.left
        anchors.right : parent.right
        height : navigationOverlayHeight
    }

}