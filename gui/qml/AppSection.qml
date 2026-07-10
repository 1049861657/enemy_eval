import QtQuick
import QtQuick.Controls

import "." as Design

Pane {
    id: root

    property string title: ""
    default property alias content: contentColumn.data

    padding: Design.Theme.space4
    background: Rectangle {
        color: Design.Theme.surface
        border.color: "transparent"
        radius: Design.Theme.radiusMedium
    }

    contentItem: Column {
        id: contentColumn
        width: root.availableWidth
        spacing: Design.Theme.space3

        Label {
            visible: root.title.length > 0
            width: parent.width
            text: root.title
            font.pixelSize: Design.Theme.bodyFontSize
            font.weight: Font.DemiBold
            color: Design.Theme.textPrimary
        }
    }
}
