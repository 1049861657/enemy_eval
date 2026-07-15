import QtQuick
import QtQuick.Controls

import "." as Design

ToolButton {
    id: root

    property string toolTipText: text

    implicitWidth: 32
    implicitHeight: 32
    padding: Design.Theme.space1
    scale: down ? 0.94 : 1
    ToolTip.visible: hovered && ToolTip.text.length > 0
    ToolTip.text: root.toolTipText

    Behavior on scale {
        NumberAnimation {
            duration: root.down ? 50 : 100
            easing.type: Easing.OutCubic
        }
    }

    background: Rectangle {
        radius: Design.Theme.radiusSmall
        color: root.down ? Design.Theme.controlPressed
              : (root.hovered ? Design.Theme.controlHover : "transparent")

        Design.AppFocusFrame {
            active: root.visualFocus
        }
    }
}
