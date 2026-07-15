import QtQuick

import "." as Design

Item {
    id: root

    property bool active: false
    property bool hasError: false
    property int cornerLength: 11
    property int strokeWidth: 2
    readonly property color strokeColor: hasError ? Design.Theme.danger
                                                  : Design.Theme.accent

    anchors.fill: parent
    anchors.margins: -3
    visible: active

    Rectangle {
        x: 0
        y: 0
        width: root.cornerLength
        height: root.strokeWidth
        radius: root.strokeWidth / 2
        color: root.strokeColor
    }
    Rectangle {
        x: 0
        y: 0
        width: root.strokeWidth
        height: root.cornerLength
        radius: root.strokeWidth / 2
        color: root.strokeColor
    }
    Rectangle {
        x: root.width - root.cornerLength
        y: 0
        width: root.cornerLength
        height: root.strokeWidth
        radius: root.strokeWidth / 2
        color: root.strokeColor
    }
    Rectangle {
        x: root.width - root.strokeWidth
        y: 0
        width: root.strokeWidth
        height: root.cornerLength
        radius: root.strokeWidth / 2
        color: root.strokeColor
    }
    Rectangle {
        x: 0
        y: root.height - root.strokeWidth
        width: root.cornerLength
        height: root.strokeWidth
        radius: root.strokeWidth / 2
        color: root.strokeColor
    }
    Rectangle {
        x: 0
        y: root.height - root.cornerLength
        width: root.strokeWidth
        height: root.cornerLength
        radius: root.strokeWidth / 2
        color: root.strokeColor
    }
    Rectangle {
        x: root.width - root.cornerLength
        y: root.height - root.strokeWidth
        width: root.cornerLength
        height: root.strokeWidth
        radius: root.strokeWidth / 2
        color: root.strokeColor
    }
    Rectangle {
        x: root.width - root.strokeWidth
        y: root.height - root.cornerLength
        width: root.strokeWidth
        height: root.cornerLength
        radius: root.strokeWidth / 2
        color: root.strokeColor
    }
}
