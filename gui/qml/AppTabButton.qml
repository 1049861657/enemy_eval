import QtQuick
import QtQuick.Controls

import "." as Design

TabButton {
    id: root

    implicitHeight: 40
    padding: Design.Theme.space2
    hoverEnabled: true
    font.family: Design.Theme.fontFamily
    font.pixelSize: Design.Theme.bodyFontSize
    font.weight: Font.Medium
    contentItem: Label {
        text: root.text
        color: root.checked ? Design.Theme.textPrimary : Design.Theme.textSecondary
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: Design.Theme.radiusMedium
        color: root.checked ? Design.Theme.tabSelected
               : root.down ? Design.Theme.tabPressed
               : root.hovered ? Design.Theme.tabHover
                              : "transparent"
        border.width: root.checked || root.hovered ? 1 : 0
        border.color: root.checked ? Design.Theme.border
                                   : Design.Theme.borderHover

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 3
            width: 18
            height: 3
            radius: 2
            color: Design.Theme.accent
            visible: root.checked
        }

        Design.AppFocusFrame {
            active: root.visualFocus
        }
    }
}
