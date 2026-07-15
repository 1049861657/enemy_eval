import QtQuick
import QtQuick.Controls

import "." as Design

Button {
    id: root

    property bool destructive: false
    property url iconSource: ""
    property string appearance: "primary"

    implicitHeight: Design.Theme.controlHeight
    padding: Design.Theme.space3
    scale: down ? 0.985 : 1
    font.family: Design.Theme.fontFamily
    font.pixelSize: Design.Theme.bodyFontSize
    icon.source: iconSource
    display: iconSource === "" ? AbstractButton.TextOnly : AbstractButton.TextBesideIcon

    Behavior on scale {
        NumberAnimation {
            duration: root.down ? 55 : 110
            easing.type: root.down ? Easing.InCubic : Easing.OutCubic
        }
    }

    background: Rectangle {
        radius: Design.Theme.radiusSmall
        color: !root.enabled ? Design.Theme.disabledSurface
              : root.appearance === "subtle" ? (root.down || root.hovered
                                                 ? (root.destructive
                                                    ? Design.Theme.dangerSubtle
                                                    : Design.Theme.controlHover)
                                                 : "transparent")
              : root.appearance === "secondary" ? (root.down ? (root.destructive
                                                                ? Design.Theme.dangerSubtle
                                                                : Design.Theme.controlPressed)
                                                 : root.hovered ? (root.destructive
                                                                   ? Design.Theme.dangerSubtle
                                                                   : Design.Theme.controlHover)
                                                                : Design.Theme.surface)
              : root.down ? (root.destructive ? Design.Theme.dangerHover : Design.Theme.accentPressed)
              : root.hovered ? (root.destructive ? Design.Theme.dangerHover : Design.Theme.accentHover)
              : (root.destructive ? Design.Theme.danger : Design.Theme.accent)
        border.color: root.appearance === "secondary"
                      ? (root.destructive ? Design.Theme.danger : Design.Theme.border)
                      : "transparent"

        Design.AppFocusFrame {
            active: root.visualFocus
        }
    }
    contentItem: Item {
        implicitWidth: buttonContent.implicitWidth
        implicitHeight: buttonContent.implicitHeight

        Row {
            id: buttonContent
            spacing: root.iconSource.toString().length > 0 && root.text.length > 0
                     ? Design.Theme.space2 : 0
            anchors.centerIn: parent

            Image {
                visible: root.iconSource.toString().length > 0
                source: root.iconSource
                width: Design.Theme.iconSize
                height: Design.Theme.iconSize
                fillMode: Image.PreserveAspectFit
            }
            Text {
                visible: root.text.length > 0
                text: root.text
                color: !root.enabled ? Design.Theme.disabledText
                       : root.appearance === "primary" ? "white"
                       : root.destructive ? Design.Theme.danger : Design.Theme.textPrimary
                font: root.font
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
