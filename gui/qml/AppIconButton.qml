import QtQuick
import QtQuick.Controls

import "." as Design

ToolButton {
    id: root

    property string toolTipText: text
    property int chromeRadius: Design.Theme.radiusSmall

    implicitWidth: 32
    implicitHeight: 32
    padding: Design.Theme.space1
    icon.color: (root.checkable && root.checked)
                ? Design.Theme.textOnAccent
                : Design.Theme.textPrimary
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
        radius: root.chromeRadius
        color: {
            if (root.checkable && root.checked) {
                if (root.down)
                    return Design.Theme.accentPressed
                if (root.hovered)
                    return Design.Theme.accentHover
                return Design.Theme.accent
            }
            if (root.down)
                return Design.Theme.controlPressed
            if (root.hovered)
                return Design.Theme.controlHover
            return "transparent"
        }

        Design.AppFocusFrame {
            active: root.visualFocus
        }
    }
}
