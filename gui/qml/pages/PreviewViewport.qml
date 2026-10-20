pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import ".." as Design

ColumnLayout {
    id: root

    property url source: ""
    property bool busy: false
    property real zoom: 1.0
    property real baseScale: 1.0
    property int imageWidth: cardImage.implicitWidth
    property int imageHeight: cardImage.implicitHeight
    property bool hasAutoFitted: false
    property int prtsLevelIndex: -1
    property string prtsLevelsJson: ""
    signal exportRequested()
    signal prtsLevelChangeRequested(int levelIndex)

    readonly property var prtsLevels: {
        try {
            return JSON.parse(prtsLevelsJson)
        } catch (error) {
            return []
        }
    }

    function currentPrtsLevelLabel() {
        for (var i = 0; i < prtsLevels.length; ++i) {
            if (prtsLevels[i].index === prtsLevelIndex)
                return prtsLevels[i].label
        }
        return ""
    }

    function fitToView() {
        if (imageWidth <= 0 || imageHeight <= 0 || viewport.width <= 0 || viewport.height <= 0)
            return
        baseScale = Math.min(viewport.width / imageWidth, viewport.height / imageHeight)
        zoom = 1.0
        hasAutoFitted = true
        flickable.contentX = Math.max(0, (flickable.contentWidth - viewport.width) / 2)
        flickable.contentY = Math.max(0, (flickable.contentHeight - viewport.height) / 2)
    }

    function autoFitOnce() {
        if (!hasAutoFitted && cardImage.status === Image.Ready)
            Qt.callLater(fitToView)
    }

    function adjustZoom(delta) {
        zoom = Math.max(0.1, Math.min(2.0, zoom + delta))
    }

    onImageWidthChanged: autoFitOnce()
    onImageHeightChanged: autoFitOnce()
    Component.onCompleted: autoFitOnce()

    RowLayout {
        Layout.fillWidth: true
        Label {
            text: "实时预览"
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.titleFontSize
            font.weight: Font.DemiBold
            Layout.fillWidth: true
            Layout.minimumWidth: 96
            elide: Text.ElideRight
        }
        AppButton {
            id: levelButton
            visible: root.prtsLevels.length >= 2
            text: root.currentPrtsLevelLabel()
            appearance: "secondary"
            menu: true
            active: levelMenu.visible
            onClicked: levelMenu.toggle()

            AppMenu {
                id: levelMenu
                y: levelButton.height

                Repeater {
                    model: root.prtsLevels

                    MenuItem {
                        required property var modelData
                        text: modelData.label
                        checkable: true
                        checked: modelData.index === root.prtsLevelIndex
                        onTriggered: root.prtsLevelChangeRequested(modelData.index)
                    }
                }
            }
        }
        AppButton {
            text: "导出"
            onClicked: root.exportRequested()
        }
        AppIconButton {
            text: "−"
            toolTipText: "缩小预览"
            onClicked: root.adjustZoom(-0.1)
        }
        Label { text: Math.round(root.zoom * 100) + "%" }
        AppIconButton {
            text: "+"
            toolTipText: "放大预览"
            onClicked: root.adjustZoom(0.1)
        }
        AppButton {
            text: "适配窗口"
            appearance: "secondary"
            onClicked: root.fitToView()
        }
    }

    Rectangle {
        id: viewport
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: Design.Theme.previewWell
        radius: Design.Theme.radiusMedium
        clip: true

        Flickable {
            id: flickable
            anchors.fill: parent
            clip: true
            contentWidth: Math.max(width, cardImage.width)
            contentHeight: Math.max(height, cardImage.height)
            boundsBehavior: Flickable.StopAtBounds

            Image {
                id: cardImage
                source: root.source
                asynchronous: true
                width: implicitWidth * root.baseScale * root.zoom
                height: implicitHeight * root.baseScale * root.zoom
                x: Math.max(0, (flickable.contentWidth - width) / 2)
                y: Math.max(0, (flickable.contentHeight - height) / 2)
                fillMode: Image.PreserveAspectFit
                onStatusChanged: {
                    if (status === Image.Ready)
                        root.autoFitOnce()
                }
            }

            WheelHandler {
                onWheel: function(event) {
                    root.adjustZoom(event.angleDelta.y > 0 ? 0.1 : -0.1)
                    event.accepted = true
                }
            }
        }

        BusyIndicator {
            anchors.centerIn: parent
            running: root.busy
            visible: running
        }
        Label {
            anchors.centerIn: parent
            visible: cardImage.status !== Image.Ready && !root.busy
            text: "等待预览"
            color: Design.Theme.textSecondary
        }

        onWidthChanged: root.autoFitOnce()
        onHeightChanged: root.autoFitOnce()
    }

    RowLayout {
        Layout.fillWidth: true
        Slider {
            Layout.fillWidth: true
            from: 0.1
            to: 2.0
            stepSize: 0.05
            value: root.zoom
            onMoved: root.zoom = value
        }
        Label {
            text: root.imageWidth > 0 ? root.imageWidth + " × " + root.imageHeight : ""
            color: Design.Theme.textSecondary
        }
    }

    Shortcut { sequence: "Ctrl+0"; onActivated: root.fitToView() }
    Shortcut { sequence: "Ctrl++"; onActivated: root.adjustZoom(0.1) }
    Shortcut { sequence: "Ctrl+-"; onActivated: root.adjustZoom(-0.1) }
}
